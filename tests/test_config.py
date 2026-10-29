import tempfile
import unittest
from pathlib import Path

from config import Config


class ConfigTests(unittest.TestCase):
    def load_config(self, contents: str) -> Config:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        config_path = Path(temp_dir.name) / "config.toml"
        config_path.write_text(contents, encoding="utf-8")
        return Config(str(config_path))

    def test_loads_disabled_modules_commands_and_cooldown(self):
        config = self.load_config(
            "[misc]\n"
            'disable = ["docker", "brew"]\n'
            "cooldown_hours = 4\n"
            "[commands]\n"
            '"Refresh cache" = "tool refresh"\n'
        )

        self.assertIsNone(config.load_error)
        self.assertEqual(config.disabled_keys, {"docker", "brew"})
        self.assertEqual(config.snapshot_cooldown_hours, 4)
        self.assertEqual(config.commands, {"Refresh cache": "tool refresh"})

    def test_rejects_invalid_values_and_restores_defaults(self):
        config = self.load_config('[misc]\ndisable = ["docker"]\ncooldown_hours = -1\n')

        self.assertIsNotNone(config.load_error)
        assert config.load_error is not None
        self.assertIn("non-negative integer", config.load_error)
        self.assertEqual(config.disabled_keys, set())
        self.assertEqual(config.snapshot_cooldown_hours, 12)

    def test_reports_invalid_toml(self):
        config = self.load_config("[misc\n")

        self.assertIsNotNone(config.load_error)
        self.assertEqual(config.snapshot_cooldown_hours, 12)

    def test_reports_missing_explicit_config_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(str(Path(temp_dir) / "missing.toml"))

        self.assertEqual(
            config.load_error,
            "Configuration file does not exist or is not a regular file.",
        )

    def test_parse_args_supports_reboot_flag(self):
        import sys
        from unittest.mock import patch

        from main import parse_args

        with patch.object(sys, "argv", ["sysupdate", "--reboot"]):
            args = parse_args()
            self.assertTrue(args.reboot)

        with patch.object(sys, "argv", ["sysupdate", "-r"]):
            args = parse_args()
            self.assertTrue(args.reboot)

        with patch.object(sys, "argv", ["sysupdate"]):
            args = parse_args()
            self.assertFalse(args.reboot)

    def test_loads_behavior_notifications_modules_and_categories_config(self):
        config = self.load_config(
            "[behavior]\n"
            "reboot = true\n"
            "quiet = true\n"
            "verbose = false\n"
            "no_sudo = true\n"
            "no_snapshot = true\n"
            "no_history = true\n"
            "command_timeout = 240\n"
            "[notifications]\n"
            "enabled = true\n"
            "only_on_error_or_reboot = true\n"
            "[modules]\n"
            'disable = ["snap"]\n'
            'skip = ["brew"]\n'
            'only = ["dnf", "flatpak"]\n'
            "[categories]\n"
            'only = ["system", "dev"]\n'
            'skip = ["gaming"]\n'
        )
        self.assertIsNone(config.load_error)
        self.assertTrue(config.reboot)
        self.assertTrue(config.quiet)
        self.assertFalse(config.verbose)
        self.assertTrue(config.no_sudo)
        self.assertTrue(config.no_snapshot)
        self.assertTrue(config.no_history)
        self.assertEqual(config.command_timeout, 240)
        self.assertTrue(config.notifications_enabled)
        self.assertTrue(config.notifications_only_on_error_or_reboot)
        self.assertEqual(config.disabled_keys, {"snap"})
        self.assertEqual(config.skip_keys, ["brew"])
        self.assertEqual(config.only_keys, ["dnf", "flatpak"])
        self.assertEqual(config.categories, ["system", "dev"])
        self.assertEqual(config.skip_categories, ["gaming"])

    def test_parse_args_supports_notifications_and_completions(self):
        import sys
        from unittest.mock import patch

        from main import parse_args

        with patch.object(
            sys,
            "argv",
            [
                "sysupdate",
                "--notify",
                "--generate-completion",
                "bash",
            ],
        ):
            args = parse_args()
            self.assertTrue(args.notify)
            self.assertEqual(args.generate_completion, "bash")

        with patch.object(
            sys,
            "argv",
            [
                "sysupdate",
                "--generate-completion",
            ],
        ):
            args = parse_args()
            self.assertEqual(args.generate_completion, "auto")


if __name__ == "__main__":
    unittest.main()
