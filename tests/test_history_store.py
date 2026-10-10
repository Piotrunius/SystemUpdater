import contextlib
import io
import stat
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from history_store import (
    HistoryStore,
    classify_run_status,
    has_new_warnings,
    print_history,
    print_run_log,
    redact_text,
)


class HistoryStoreTests(unittest.TestCase):
    def test_run_can_be_saved_listed_and_loaded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = HistoryStore(Path(temp_dir))
            run_id = store.new_run_id(datetime(2026, 10, 8, tzinfo=timezone.utc))
            run = {"id": run_id, "started_at": "2026-10-08T00:00:00+00:00", "modules": []}

            path = store.save(run)

            self.assertEqual(store.load(run_id), run)
            self.assertEqual(store.list_runs()[0]["id"], run_id)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_run_id_cannot_escape_the_history_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = HistoryStore(Path(temp_dir))

            self.assertIsNone(store.load("../../outside"))

    def test_common_secret_forms_are_redacted(self):
        text = "Authorization: Bearer abc.def key=xyz https://user:pass@example.com"

        redacted = redact_text(text)

        self.assertNotIn("abc.def", redacted)
        self.assertNotIn("key=xyz", redacted)
        self.assertNotIn("user:pass", redacted)

    def test_persistent_warning_is_not_classified_as_new(self):
        module = {
            "key": "flatpak",
            "status": "unchanged",
            "warnings": ["Runtime is end-of-life"],
        }

        self.assertFalse(has_new_warnings([module], [{"modules": [module]}]))

    def test_changed_warning_is_classified_as_new(self):
        previous = {
            "key": "flatpak",
            "status": "unchanged",
            "warnings": ["Runtime is end-of-life"],
        }
        current = {
            "key": "flatpak",
            "status": "unchanged",
            "warnings": ["Runtime is end-of-life", "New signature warning"],
        }

        self.assertTrue(has_new_warnings([current], [{"modules": [previous]}]))

    def test_warning_is_new_again_after_a_clean_run_of_the_same_module(self):
        previous_runs = [
            {"modules": [{"key": "flatpak", "status": "unchanged", "warnings": []}]},
            {"modules": [{"key": "flatpak", "status": "unchanged", "warnings": ["Runtime warning"]}]},
        ]
        current = {"key": "flatpak", "status": "unchanged", "warnings": ["Runtime warning"]}

        self.assertTrue(has_new_warnings([current], previous_runs))

    def test_skipped_module_does_not_reset_warning_baseline(self):
        previous_runs = [
            {"modules": [{"key": "flatpak", "status": "skipped", "warnings": []}]},
            {
                "modules": [
                    {"key": "flatpak", "status": "unchanged", "warnings": ["Runtime warning"]}
                ]
            },
        ]
        current = {"key": "flatpak", "status": "unchanged", "warnings": ["Runtime warning"]}

        self.assertFalse(has_new_warnings([current], previous_runs))

    def test_history_marks_a_persistent_warning_only_on_its_first_occurrence(self):
        module = {
            "key": "flatpak",
            "name": "Flatpak Packages",
            "status": "unchanged",
            "warnings": ["Runtime is end-of-life"],
        }
        runs = [
            {"id": "20261008T030000Z-00000003", "status": "warning", "update_count": 0, "modules": [module]},
            {"id": "20261008T020000Z-00000002", "status": "warning", "update_count": 0, "modules": [module]},
            {"id": "20261008T010000Z-00000001", "status": "warning", "update_count": 0, "modules": [module]},
        ]
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            print_history(runs)

        lines = output.getvalue().splitlines()
        statuses = [line.split()[2] for line in lines if "20261008T" in line]
        self.assertEqual(statuses, ["up-to-date", "up-to-date", "warning"])

    def test_show_log_does_not_repeat_warnings_already_in_command_output(self):
        warning = "Warning: legacy tap warning"
        run = {
            "id": "20261008T010000Z-00000001",
            "started_at": "2026-10-08T01:00:00+00:00",
            "duration": 1.0,
            "status": "warning",
            "modules": [
                {
                    "name": "Homebrew",
                    "status": "unchanged",
                    "message": "",
                    "warnings": [warning],
                    "commands": [
                        {
                            "command": ["brew", "upgrade"],
                            "returncode": 0,
                            "duration": 1.0,
                            "stdout": "",
                            "stderr": warning + "\n",
                        }
                    ],
                }
            ],
        }
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            print_run_log(run)

        rendered = output.getvalue()
        self.assertEqual(rendered.count(warning), 1)
        self.assertNotIn("── Warnings", rendered)
        self.assertIn("── Command Output", rendered)
        self.assertIn("$ brew upgrade", rendered)
        self.assertNotIn("[exit", rendered)

    def test_warning_without_command_output_shows_reason_inline(self):
        run = {
            "id": "20261008T010000Z-00000001",
            "duration": 0.1,
            "status": "warning",
            "modules": [
                {
                    "name": "ProtonPlus Runners",
                    "status": "warning",
                    "message": "GitHub API unreachable or timed out",
                    "details": ["timed out"],
                }
            ],
        }
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            print_run_log(run)

        rendered = output.getvalue()
        self.assertIn(
            "[!] ProtonPlus Runners · warning — GitHub API unreachable or timed out; timed out",
            rendered,
        )
        self.assertNotIn("Reason:", rendered)
        self.assertNotIn("Details:", rendered)

    def test_classified_log_status_uses_same_new_warning_rule(self):
        run = {
            "status": "warning",
            "update_count": 0,
            "modules": [
                {"key": "flatpak", "status": "unchanged", "warnings": ["Known issue"]}
            ],
        }
        previous = [
            {
                "modules": [
                    {"key": "flatpak", "status": "unchanged", "warnings": ["Known issue"]}
                ]
            }
        ]

        self.assertEqual(classify_run_status(run, previous), "up-to-date")


if __name__ == "__main__":
    unittest.main()
