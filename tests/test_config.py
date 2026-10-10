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


if __name__ == "__main__":
    unittest.main()
