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

    def test_read_only_command_output_is_saved(self):
        context = UpdateContext()
        completed = subprocess.CompletedProcess(
            args=["git"],
            returncode=0,
            stdout="abc1234\n",
            stderr="",
        )

        with patch("modules.base.subprocess.run", return_value=completed):
            code, stdout, _ = context.run_cmd(
                ["git", "rev-parse", "HEAD"], read_only=True
            )

        self.assertEqual(code, 0)
        self.assertEqual(stdout, "abc1234\n")
        self.assertEqual(context.command_log[0]["stdout"], "abc1234\n")
        self.assertFalse(context.command_log[0]["output_withheld"])

    def test_sensitive_output_withholds_stdout_and_stderr_from_command_log(self):
        context = UpdateContext()
        completed = subprocess.CompletedProcess(
            args=["gh", "auth", "token"],
            returncode=0,
            stdout="custom-opaque-secret-value\n",
            stderr="debug secret\n",
        )

        with patch("modules.base.subprocess.run", return_value=completed):
            code, stdout, stderr = context.run_cmd(
                ["gh", "auth", "token"], read_only=True, sensitive_output=True
            )

        self.assertEqual(code, 0)
        self.assertEqual(stdout, "custom-opaque-secret-value\n")
        self.assertEqual(stderr, "debug secret\n")
        self.assertTrue(context.command_log[0]["output_withheld"])
        self.assertEqual(context.command_log[0]["stdout"], "")
        self.assertEqual(context.command_log[0]["stderr"], "")

    def test_default_timeout_and_english_locale_are_applied(self):
        context = UpdateContext(default_timeout=240)
        self.assertEqual(context.env["LC_MESSAGES"], "C")
        self.assertEqual(context.env["LANGUAGE"], "C")

        completed = subprocess.CompletedProcess(
            args=["dnf", "upgrade"], returncode=0, stdout="Nothing to do.\n", stderr=""
        )
        with patch("modules.base.subprocess.run", return_value=completed) as mock_run:
            context.run_cmd(["dnf", "upgrade"], timeout=600)
            self.assertEqual(mock_run.call_args.kwargs["timeout"], 240)

            context.run_cmd(["dnf", "check"], timeout=30, read_only=True)
            self.assertEqual(mock_run.call_args.kwargs["timeout"], 30)

    def test_popen_retries_after_timeout(self):
        import subprocess as real_subprocess

        context = UpdateContext()
        calls = {"count": 0}

        class FakePipe:
            def __init__(self, data: str):
                self._lines = iter(data.splitlines(keepends=True))

            def readline(self):
                return next(self._lines, "")

            def close(self):
                pass

        class FakeProc:
            def __init__(self):
                calls["count"] += 1
                self.attempt = calls["count"]
                self.pid = 12345
                self.returncode = 0
                self.stdout = FakePipe("Downloaded newer image\n" if self.attempt == 2 else "")
                self.stderr = FakePipe("")

            def wait(self, timeout=None):
                if self.attempt == 1:
                    raise real_subprocess.TimeoutExpired(cmd=["docker"], timeout=timeout or 1)
                return 0

            def terminate(self):
                pass

            def kill(self):
                pass

        with (
            patch("modules.base.subprocess.Popen", side_effect=lambda *a, **kw: FakeProc()),
            patch("modules.base._stop_process_tree"),
        ):
            code, stdout, _ = context.run_cmd(["docker", "pull", "img"], retries=1, retry_delay=0)

        self.assertEqual(code, 0)
        self.assertIn("Downloaded newer image", stdout)
        self.assertEqual(len(context.command_log), 2)
        self.assertEqual(context.command_log[0]["returncode"], 124)
        self.assertEqual(context.command_log[1]["returncode"], 0)


if __name__ == "__main__":
    unittest.main()
