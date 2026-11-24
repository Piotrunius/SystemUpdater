import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from history_store import HistoryStore


class CliExecutionTests(unittest.TestCase):
    def test_unknown_only_exits_with_code_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch("sys.argv", ["sysupdate", "--no-self-update", "--only", "nonexistent_tool"]),
                patch("main.HistoryStore", return_value=HistoryStore(Path(tmp) / "history")),
                patch("main.acquire_run_lock") as mock_lock,
                patch("sys.stderr", new_callable=io.StringIO) as err_buf,
            ):
                mock_lock.return_value.__enter__.return_value = None
                with self.assertRaises(SystemExit) as exc:
                    main.main()
            self.assertEqual(exc.exception.code, 2)
            self.assertIn("Unknown value 'nonexistent_tool'", err_buf.getvalue())

    def test_category_flag_overrides_config_only_and_supports_apps_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.toml"
            cfg_path.write_text('[modules]\nonly = ["snap"]\n', encoding="utf-8")

            out = io.StringIO()
            with (
                patch(
                    "sys.argv",
                    [
                        "sysupdate",
                        "--config",
                        str(cfg_path),
                        "--no-self-update",
                        "--no-history",
                        "--no-snapshot",
                        "-c",
                        "apps",
                    ],
                ),
                patch("main.HistoryStore", return_value=HistoryStore(Path(tmp) / "history")),
                patch("main.acquire_run_lock") as mock_lock,
                patch("modules.flatpak.FlatpakModule.is_available", return_value=True),
                patch("modules.flatpak.FlatpakModule.run") as mock_flatpak_run,
                patch("sys.stdout", out),
            ):
                from ui import StepResult

                mock_lock.return_value.__enter__.return_value = None
                mock_flatpak_run.return_value = StepResult("unchanged")
                with self.assertRaises(SystemExit) as exc:
                    main.main()

            self.assertEqual(exc.exception.code, 0)
            mock_flatpak_run.assert_called_once()

    def test_retry_failed_runs_only_failed_or_interrupted_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HistoryStore(Path(tmp) / "history")
            run_id = store.new_run_id()
            store.save(
                {
                    "id": run_id,
                    "started_at": "2026-11-24T00:00:00+00:00",
                    "status": "error",
                    "modules": [
                        {"key": "brew", "name": "Homebrew", "status": "ok"},
                        {"key": "flatpak", "name": "Flatpak", "status": "error"},
                    ],
                }
            )

            out = io.StringIO()
            with (
                patch(
                    "sys.argv",
                    ["sysupdate", "--no-self-update", "--no-history", "--retry-failed"],
                ),
                patch("main.HistoryStore", return_value=store),
                patch("main.acquire_run_lock") as mock_lock,
                patch("modules.flatpak.FlatpakModule.is_available", return_value=True),
                patch("modules.flatpak.FlatpakModule.run") as mock_flatpak_run,
                patch("modules.brew.BrewModule.is_available", return_value=True),
                patch("modules.brew.BrewModule.run") as mock_brew_run,
                patch("sys.stdout", out),
            ):
                from ui import StepResult

                mock_lock.return_value.__enter__.return_value = None
                mock_flatpak_run.return_value = StepResult("unchanged")
                with self.assertRaises(SystemExit) as exc:
                    main.main()

            self.assertEqual(exc.exception.code, 0)
            mock_flatpak_run.assert_called_once()
            mock_brew_run.assert_not_called()

    def test_battery_and_network_preflight_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            ps_root = Path(tmp) / "power_supply"
            ac_dir = ps_root / "AC"
            ac_dir.mkdir(parents=True)
            (ac_dir / "type").write_text("Mains\n", encoding="utf-8")
            (ac_dir / "online").write_text("0\n", encoding="utf-8")

            orig_isdir = os.path.isdir
            orig_isfile = os.path.isfile
            orig_listdir = os.listdir
            orig_open = open

            def fake_isdir(path):
                if path == "/sys/class/power_supply":
                    return True
                return orig_isdir(path)

            def fake_listdir(path):
                if path == "/sys/class/power_supply":
                    return ["AC"]
                return orig_listdir(path)

            def fake_isfile(path):
                if str(path).startswith("/sys/class/power_supply/"):
                    return orig_isfile(str(path).replace("/sys/class/power_supply", str(ps_root)))
                return orig_isfile(path)

            def fake_open(path, *args, **kwargs):
                if str(path).startswith("/sys/class/power_supply/"):
                    return orig_open(
                        str(path).replace("/sys/class/power_supply", str(ps_root)),
                        *args,
                        **kwargs,
                    )
                return orig_open(path, *args, **kwargs)

            with (
                patch("platform.system", return_value="Linux"),
                patch("os.path.isdir", side_effect=fake_isdir),
                patch("os.listdir", side_effect=fake_listdir),
                patch("os.path.isfile", side_effect=fake_isfile),
                patch("builtins.open", side_effect=fake_open),
            ):
                self.assertTrue(main.is_on_battery())

        with patch("socket.create_connection", side_effect=OSError("offline")):
            self.assertFalse(main.is_network_available(timeout=0.1))

    def test_acquire_run_lock_exits_when_already_locked(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.dict(os.environ, {"XDG_RUNTIME_DIR": tmp}),
                patch("fcntl.flock", side_effect=BlockingIOError),
                patch("sys.stderr", new_callable=io.StringIO) as err_buf,
            ):
                with self.assertRaises(SystemExit) as exc:
                    with main.acquire_run_lock():
                        pass
            self.assertEqual(exc.exception.code, 1)
            self.assertIn("already in progress", err_buf.getvalue())

    def test_reboot_is_skipped_when_any_module_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            err = io.StringIO()
            with (
                patch(
                    "sys.argv",
                    [
                        "sysupdate",
                        "--no-self-update",
                        "--no-history",
                        "--no-snapshot",
                        "--only",
                        "flatpak",
                        "--reboot",
                    ],
                ),
                patch("main.HistoryStore", return_value=HistoryStore(Path(tmp) / "history")),
                patch("main.acquire_run_lock") as mock_lock,
                patch("modules.flatpak.FlatpakModule.is_available", return_value=True),
                patch("modules.flatpak.FlatpakModule.run") as mock_flatpak_run,
                patch("main.subprocess.run") as mock_subproc,
                patch("sys.stdout", out),
                patch("sys.stderr", err),
            ):
                from ui import StepResult

                mock_lock.return_value.__enter__.return_value = None
                mock_flatpak_run.return_value = StepResult(
                    "error", "failed", reboot_required=True
                )
                with self.assertRaises(SystemExit) as exc:
                    main.main()

            self.assertEqual(exc.exception.code, 1)
            self.assertIn("Skipping automatic reboot", err.getvalue())
            mock_subproc.assert_not_called()


if __name__ == "__main__":
    unittest.main()
