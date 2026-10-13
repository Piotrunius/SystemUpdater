import unittest
from typing import Any, cast
from unittest.mock import patch

from modules.mas import MasModule


class FakeContext:
    dry_run = False

    def __init__(self, responses, which_map=None):
        self.responses = list(responses)
        self.which_map = which_map or {}

    def run_cmd(self, *_args, **_kwargs):
        if not self.responses:
            return 0, "", ""
        if len(self.responses) == 1:
            return self.responses[0]
        return self.responses.pop(0)

    def which(self, cmd):
        return self.which_map.get(cmd)


class MasModuleTests(unittest.TestCase):
    @patch("modules.mas.is_macos", return_value=True)
    def test_available_when_mas_installed_with_apps(self, _mock_macos):
        ctx = FakeContext(
            [(0, "497799835 Xcode (15.2)\n", "")],
            which_map={"mas": "/usr/local/bin/mas"},
        )
        self.assertTrue(MasModule().is_available(cast(Any, ctx)))
        self.assertEqual(MasModule().availability_status(cast(Any, ctx)), "[Active]")

    @patch("modules.mas.is_macos", return_value=True)
    def test_no_targets_when_mas_has_no_apps(self, _mock_macos):
        ctx = FakeContext([(0, "", "")], which_map={"mas": "/usr/local/bin/mas"})
        self.assertFalse(MasModule().is_available(cast(Any, ctx)))
        self.assertEqual(
            MasModule().availability_status(cast(Any, ctx)), "[No Targets]"
        )

    @patch("modules.mas.is_macos", return_value=True)
    def test_unavailable_when_mas_probe_fails(self, _mock_macos):
        ctx = FakeContext([(1, "", "error")], which_map={"mas": "/usr/local/bin/mas"})
        self.assertTrue(MasModule().is_available(cast(Any, ctx)))
        self.assertEqual(
            MasModule().availability_status(cast(Any, ctx)), "[Unavailable]"
        )

    @patch("modules.mas.is_macos", return_value=False)
    def test_unavailable_when_not_macos(self, _mock_macos):
        ctx = FakeContext([], which_map={"mas": "/usr/local/bin/mas"})
        self.assertFalse(MasModule().is_available(cast(Any, ctx)))
        self.assertEqual(
            MasModule().availability_status(cast(Any, ctx)), "[Unavailable]"
        )

    @patch("modules.mas.is_macos", return_value=True)
    def test_unavailable_when_mas_missing(self, _mock_macos):
        ctx = FakeContext([], which_map={})
        self.assertFalse(MasModule().is_available(cast(Any, ctx)))
        self.assertEqual(
            MasModule().availability_status(cast(Any, ctx)), "[Not Installed]"
        )

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
