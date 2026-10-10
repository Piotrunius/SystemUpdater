import subprocess
import unittest
from unittest.mock import patch

from modules.base import UpdateContext


class CommandLoggingTests(unittest.TestCase):
    def test_command_output_is_recorded_with_common_secrets_redacted(self):
        context = UpdateContext()
        completed = subprocess.CompletedProcess(
            args=["example"], returncode=0, stdout="token=abc123\n", stderr=""
        )

        with patch("modules.base.subprocess.run", return_value=completed):
            code, stdout, _ = context.run_cmd(["example", "password=hunter2"])

        self.assertEqual(code, 0)
        self.assertEqual(stdout, "token=abc123\n")
        self.assertEqual(context.command_log[0]["stdout"], "token=[REDACTED]\n")
        self.assertEqual(context.command_log[0]["command"][1], "password=[REDACTED]")

    def test_read_only_command_output_is_not_saved(self):
        context = UpdateContext()
        completed = subprocess.CompletedProcess(
            args=["gh"],
            returncode=0,
            stdout="ghp_sensitive_value_12345678901234567890",
            stderr="",
        )

        with patch("modules.base.subprocess.run", return_value=completed):
            code, stdout, _ = context.run_cmd(["gh", "auth", "token"], read_only=True)

        self.assertEqual(code, 0)
        self.assertIn("ghp_sensitive_value", stdout)
        self.assertEqual(context.command_log[0]["stdout"], "")
        self.assertTrue(context.command_log[0]["output_withheld"])


if __name__ == "__main__":
    unittest.main()
