import unittest
from unittest.mock import patch
from typing import Any, cast

import modules.base as base
from modules.brew import BrewModule, find_brew_bin


class FakeContext:
    dry_run = False

    def __init__(self, which_map=None):
        self.which_map = which_map or {}

    def which(self, cmd):
        return self.which_map.get(cmd)


class MacOSPlatformTests(unittest.TestCase):
    def setUp(self):
        base._os_release_cache = None

    def tearDown(self):
        base._os_release_cache = None

    @patch("os.path.isfile", return_value=False)
    @patch("platform.system", return_value="Darwin")
    @patch("platform.mac_ver", return_value=("14.4.1", ("", "", ""), ""))
    def test_os_release_on_macos(self, _mock_ver, _mock_sys, _mock_isfile):
        info = base.get_os_release()
        self.assertEqual(info.get("ID"), "macos")
        self.assertEqual(info.get("NAME"), "macOS")
        self.assertEqual(info.get("VERSION_ID"), "14.4.1")
        self.assertEqual(info.get("PRETTY_NAME"), "macOS 14.4.1")
        self.assertTrue(base.is_macos())
        self.assertFalse(base.is_linux())

    @patch("os.path.isfile")
    @patch("os.access")
    def test_find_brew_apple_silicon_path(self, mock_access, mock_isfile):
        ctx = FakeContext(which_map={})

        def isfile_side_effect(path):
            return path == "/opt/homebrew/bin/brew"

        mock_isfile.side_effect = isfile_side_effect
        mock_access.return_value = True

        self.assertEqual(find_brew_bin(cast(Any, ctx)), "/opt/homebrew/bin/brew")
        self.assertTrue(BrewModule().is_available(cast(Any, ctx)))


if __name__ == "__main__":
    unittest.main()
