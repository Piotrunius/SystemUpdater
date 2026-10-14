import unittest
from typing import Any, cast
from unittest.mock import patch

from modules.macos_update import SoftwareUpdateModule


class FakeContext:
    dry_run = False

    def __init__(self, responses, which_map=None):
        self.responses = iter(responses)
        self.which_map = which_map or {}

    def run_cmd(self, *_args, **_kwargs):
        return next(self.responses)

    def which(self, cmd):
        return self.which_map.get(cmd)


class SoftwareUpdateModuleTests(unittest.TestCase):
    @patch("platform.system", return_value="Linux")
    def test_unavailable_on_linux(self, _mock_sys):
        ctx = FakeContext([], which_map={"softwareupdate": "/usr/sbin/softwareupdate"})
        self.assertFalse(SoftwareUpdateModule().is_available(cast(Any, ctx)))
        self.assertEqual(
            SoftwareUpdateModule().availability_status(cast(Any, ctx)), "[Unavailable]"
        )

    @patch("platform.system", return_value="Darwin")
    def test_available_on_darwin(self, _mock_sys):
        ctx = FakeContext([], which_map={"softwareupdate": "/usr/sbin/softwareupdate"})
        self.assertTrue(SoftwareUpdateModule().is_available(cast(Any, ctx)))
        self.assertEqual(
            SoftwareUpdateModule().availability_status(cast(Any, ctx)), "[Active]"
        )

    def test_up_to_date_when_no_updates(self):
        ctx = FakeContext(
            [(0, "Software Update Tool\n\nNo new software available.\n", "")]
        )
        res = SoftwareUpdateModule().run(cast(Any, ctx))
        self.assertEqual(res.status, "unchanged")
        self.assertEqual(res.message, "up to date")

    def test_updates_detected_and_installed_with_reboot(self):
        check_out = (
            "Software Update found the following new or updated software:\n"
            "* Title: macOS Sonoma 14.5-23F79, Version: 14.5, Size: 1234567K, Recommended: YES, Action: restart,\n"
            "* Title: Command Line Tools for Xcode-15.3, Version: 15.3, Size: 500000K, Recommended: YES,\n"
        )
        install_out = "Installing 14.5\nDone.\nPlease restart your computer.\n"
        ctx = FakeContext(
            [
                (0, check_out, ""),
                (0, install_out, ""),
            ]
        )
        res = SoftwareUpdateModule().run(cast(Any, ctx))
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.message, "2 updates installed")
        self.assertTrue(res.reboot_required)
        self.assertIn("macOS Sonoma 14.5-23F79", res.details)
        self.assertIn("Command Line Tools for Xcode-15.3", res.details)


if __name__ == "__main__":
    unittest.main()
