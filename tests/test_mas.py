import unittest
from typing import Any, cast

from modules.mas import MasModule
from ui import StepResult


class FakeContext:
    dry_run = False

    def __init__(self, responses, which_map=None):
        self.responses = iter(responses)
        self.which_map = which_map or {}

    def run_cmd(self, *_args, **_kwargs):
        return next(self.responses)

    def which(self, cmd):
        return self.which_map.get(cmd)


class MasModuleTests(unittest.TestCase):
    def test_available_when_mas_installed(self):
        ctx = FakeContext([], which_map={"mas": "/usr/local/bin/mas"})
        self.assertTrue(MasModule().is_available(cast(Any, ctx)))

    def test_unavailable_when_mas_missing(self):
        ctx = FakeContext([], which_map={})
        self.assertFalse(MasModule().is_available(cast(Any, ctx)))

    def test_up_to_date_when_no_outdated(self):
        ctx = FakeContext([(0, "", "")])
        res = MasModule().run(cast(Any, ctx))
        self.assertEqual(res.status, "unchanged")

    def test_upgrade_success_with_version_transitions(self):
        outdated_out = (
            "497799835 Xcode (15.2 -> 15.3)\n409183694 Keynote (13.2 -> 14.0)\n"
        )
        upgrade_out = "==> Upgrading Xcode\n==> Upgrading Keynote\n"
        ctx = FakeContext(
            [
                (0, outdated_out, ""),
                (0, upgrade_out, ""),
            ]
        )
        res = MasModule().run(cast(Any, ctx))
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.message, "2 apps updated")
        self.assertIn("Xcode 15.2 -> 15.3", res.details)
        self.assertIn("Keynote 13.2 -> 14.0", res.details)

    def test_upgrade_failure_reports_error(self):
        outdated_out = "497799835 Xcode (15.2 -> 15.3)\n"
        ctx = FakeContext(
            [
                (0, outdated_out, ""),
                (1, "", "Error: Failed to install Xcode"),
            ]
        )
        res = MasModule().run(cast(Any, ctx))
        self.assertEqual(res.status, "error")
        self.assertEqual(res.message, "Mac App Store upgrade failed")
        self.assertIn("Failed to install Xcode", res.error_output)


if __name__ == "__main__":
    unittest.main()
