import unittest
from unittest.mock import Mock

from modules.base import UpdateContext
from modules.devtools import GemModule


class GemModuleTests(unittest.TestCase):
    def test_gem_module_reports_single_package_updated_with_version_diff(self):
        context = UpdateContext()
        context.which = Mock(return_value="/usr/bin/gem")

        def mock_run_cmd(cmd, **kwargs):
            if cmd == ["gem", "--version"]:
                return 0, "4.0.21\n", ""
            if cmd == ["gem", "update", "--system"]:
                return 0, "Installing RubyGems 4.0.22\nRubyGems 4.0.22 installed\n", ""
            return 0, "", ""

        context.run_cmd = Mock(side_effect=mock_run_cmd)

        result = GemModule().run(context)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "1 package updated")
        self.assertEqual(result.details, ["rubygems-update: 4.0.21 -> 4.0.22"])

    def test_gem_module_reports_unchanged_when_already_latest(self):
        context = UpdateContext()
        context.which = Mock(return_value="/usr/bin/gem")
        context.run_cmd = Mock(
            side_effect=[
                (0, "4.0.22\n", ""),
                (0, "Latest version already installed. Done.\n", ""),
            ]
        )

        result = GemModule().run(context)
        self.assertEqual(result.status, "unchanged")


if __name__ == "__main__":
    unittest.main()
