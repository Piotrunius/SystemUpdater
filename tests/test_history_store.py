import contextlib
import io
import stat
import tempfile
import unittest
from datetime import UTC, datetime
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
            run_id = store.new_run_id(datetime(2026, 10, 8, tzinfo=UTC))
            run = {
                "id": run_id,
                "started_at": "2026-10-08T00:00:00+00:00",
                "modules": [],
            }

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
            {
                "modules": [
                    {
                        "key": "flatpak",
                        "status": "unchanged",
                        "warnings": ["Runtime warning"],
                    }
                ]
            },
        ]
        current = {
            "key": "flatpak",
            "status": "unchanged",
            "warnings": ["Runtime warning"],
        }

        self.assertTrue(has_new_warnings([current], previous_runs))

    def test_skipped_module_does_not_reset_warning_baseline(self):
        previous_runs = [
            {"modules": [{"key": "flatpak", "status": "skipped", "warnings": []}]},
            {
                "modules": [
                    {
                        "key": "flatpak",
                        "status": "unchanged",
                        "warnings": ["Runtime warning"],
                    }
                ]
            },
        ]
        current = {
            "key": "flatpak",
            "status": "unchanged",
            "warnings": ["Runtime warning"],
        }

        self.assertFalse(has_new_warnings([current], previous_runs))

    def test_history_marks_a_persistent_warning_only_on_its_first_occurrence(self):
        module = {
            "key": "flatpak",
            "name": "Flatpak Packages",
            "status": "unchanged",
            "warnings": ["Runtime is end-of-life"],
        }
        runs = [
            {
                "id": "20261008T030000Z-00000003",
                "status": "warning",
                "update_count": 0,
                "modules": [module],
            },
            {
                "id": "20261008T020000Z-00000002",
                "status": "warning",
                "update_count": 0,
                "modules": [module],
            },
            {
                "id": "20261008T010000Z-00000001",
                "status": "warning",
                "update_count": 0,
                "modules": [module],
            },
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
                    {
                        "key": "flatpak",
                        "status": "unchanged",
                        "warnings": ["Known issue"],
                    }
                ]
            }
        ]

        self.assertEqual(classify_run_status(run, previous), "up-to-date")

    def test_classify_run_status_identifies_interrupted_run(self):
        run = {
            "status": "interrupted",
            "update_count": 0,
            "modules": [
                {"key": "dnf", "status": "ok", "message": "updated"},
                {
                    "key": "distrobox",
                    "status": "interrupted",
                    "message": "Cancelled by user",
                },
            ],
        }
        self.assertEqual(classify_run_status(run, []), "interrupted")

    def test_print_history_formats_interrupted_status(self):
        runs = [
            {
                "id": "20261012T122807Z-b4a1c890",
                "started_at": "2026-10-12T12:28:07+00:00",
                "status": "interrupted",
                "duration": 9.2,
                "update_count": 0,
                "modules": [],
            }
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            print_history(runs)
        rendered = output.getvalue()
        self.assertIn("20261012T122807Z-b4a1c890", rendered)
        self.assertIn("interrupted", rendered)

    def test_print_run_log_formats_interrupted_module(self):
        run = {
            "id": "20261012T122807Z-b4a1c890",
            "started_at": "2026-10-12T12:28:07+00:00",
            "duration": 9.2,
            "status": "interrupted",
            "modules": [
                {
                    "name": "Distrobox",
                    "status": "interrupted",
                    "message": "Cancelled by user",
                    "duration": 5.1,
                    "commands": [
                        {
                            "command": ["distrobox", "upgrade", "--all"],
                            "returncode": 130,
                            "stdout": "Upgrading arch...",
                            "stderr": "Command interrupted by user",
                        }
                    ],
                }
            ],
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            print_run_log(run)
        rendered = output.getvalue()
        self.assertIn("Distrobox", rendered)
        self.assertIn("interrupted", rendered)
        self.assertIn("[~]", rendered)
        self.assertNotIn("Cancelled by user", rendered)

    def test_print_run_log_groups_by_categories_and_indents_commands(self):
        run = {
            "id": "20261012T143702Z-8f5b40e4",
            "started_at": "2026-10-12T14:37:02+00:00",
            "duration": 5.0,
            "status": "ok",
            "modules": [
                {
                    "name": "Snapshot",
                    "key": "snapshot",
                    "status": "unchanged",
                    "duration": 0.1,
                },
                {
                    "name": "Repositories",
                    "key": "reposync",
                    "status": "unchanged",
                    "duration": 1.2,
                    "commands": [
                        {
                            "command": ["sudo", "dnf", "update"],
                            "returncode": 0,
                            "stdout": "Nothing to do.\n",
                        }
                    ],
                },
                {
                    "name": "Flatpak",
                    "key": "flatpak",
                    "status": "unchanged",
                    "duration": 0.8,
                },
            ],
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            print_run_log(run)
        rendered = output.getvalue()
        self.assertIn("── Modules ", rendered)
        self.assertIn("── Command Output ", rendered)
        self.assertIn("── System Protection", rendered)
        self.assertIn("── System Core", rendered)
        self.assertIn("── Applications & Gaming", rendered)
        self.assertIn("  [—] Repositories · up-to-date", rendered)
        self.assertIn("      $ sudo dnf update", rendered)
        self.assertIn("        stdout:", rendered)
        self.assertIn("          Nothing to do.", rendered)

    def test_no_history_flag_is_parsed_without_short_alias(self):
        from unittest.mock import patch

        from main import parse_args

        with patch("sys.argv", ["main.py", "--no-history"]):
            args = parse_args()
            self.assertTrue(args.no_history)

        with patch("sys.argv", ["main.py"]):
            args = parse_args()
            self.assertFalse(args.no_history)

    def test_classify_run_status_returns_reboot_when_reboot_required(self):
        run = {
            "id": "20261014T063116Z-e9ec6afa",
            "status": "ok",
            "update_count": 1,
            "reboot_required": True,
            "modules": [
                {
                    "name": "System",
                    "key": "system",
                    "status": "ok",
                    "reboot_required": True,
                    "details": ["kernel-core: 7.2.9 -> 7.2.10"],
                }
            ],
        }
        self.assertEqual(classify_run_status(run, []), "reboot")

    def test_print_history_displays_reboot_status(self):
        run = {
            "id": "20261014T063116Z-e9ec6afa",
            "started_at": "2026-10-14T06:31:16+00:00",
            "duration": 193.6,
            "status": "reboot",
            "update_count": 4,
            "reboot_required": True,
            "modules": [],
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            print_history([run])
        rendered = output.getvalue()
        self.assertIn("reboot", rendered)
        self.assertIn("20261014T063116Z-e9ec6afa", rendered)

    def test_print_run_log_shows_reboot_marker_and_label(self):
        run = {
            "id": "20261014T063116Z-e9ec6afa",
            "started_at": "2026-10-14T06:31:16+00:00",
            "duration": 10.0,
            "status": "reboot",
            "modules": [
                {
                    "name": "System",
                    "key": "system",
                    "category": "System Core",
                    "status": "ok",
                    "reboot_required": True,
                    "duration": 5.0,
                    "details": ["kernel: 7.2.9 -> 7.2.10"],
                    "commands": [
                        {
                            "command": ["sudo", "dnf", "upgrade"],
                            "returncode": 0,
                            "stdout": "Complete!\n",
                        }
                    ],
                }
            ],
        }
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            print_run_log(run)
        rendered = output.getvalue()
        self.assertIn("[^]", rendered)
        self.assertIn("reboot", rendered)
        self.assertIn("[^] System · reboot", rendered)

    def test_classify_run_status_priority_interrupted_over_all(self):
        run = {
            "id": "20261016T040000Z-00000001",
            "status": "interrupted",
            "reboot_required": True,
            "update_count": 2,
            "modules": [
                {
                    "name": "System",
                    "key": "system",
                    "status": "error",
                    "reboot_required": True,
                    "warnings": ["Warning text"],
                }
            ],
        }
        self.assertEqual(classify_run_status(run, []), "interrupted")

    def test_classify_run_status_priority_error_over_reboot_and_warning(self):
        run = {
            "id": "20261016T040000Z-00000002",
            "status": "error",
            "reboot_required": True,
            "update_count": 2,
            "modules": [
                {
                    "name": "System",
                    "key": "system",
                    "status": "error",
                    "reboot_required": True,
                    "warnings": ["Warning text"],
                }
            ],
        }
        self.assertEqual(classify_run_status(run, []), "error")

    def test_classify_run_status_priority_reboot_over_warning_and_updated(self):
        run = {
            "id": "20261016T040000Z-00000003",
            "status": "ok",
            "reboot_required": True,
            "update_count": 2,
            "modules": [
                {
                    "name": "System",
                    "key": "system",
                    "status": "ok",
                    "reboot_required": True,
                    "warnings": ["Warning text"],
                }
            ],
        }
        self.assertEqual(classify_run_status(run, []), "reboot")

    def test_classify_run_status_priority_warning_over_updated(self):
        run = {
            "id": "20261016T040000Z-00000004",
            "status": "ok",
            "reboot_required": False,
            "update_count": 1,
            "modules": [
                {
                    "name": "Homebrew",
                    "key": "brew",
                    "status": "warning",
                    "warnings": ["Mirror connection timed out"],
                }
            ],
        }
        self.assertEqual(classify_run_status(run, []), "warning")

    def test_classify_run_status_priority_updated_over_uptodate(self):
        run = {
            "id": "20261016T040000Z-00000005",
            "status": "ok",
            "reboot_required": False,
            "update_count": 3,
            "modules": [
                {
                    "name": "Flatpak",
                    "key": "flatpak",
                    "status": "ok",
                    "details": ["app.foo.Bar"],
                }
            ],
        }
        self.assertEqual(classify_run_status(run, []), "updated")


if __name__ == "__main__":
    unittest.main()
