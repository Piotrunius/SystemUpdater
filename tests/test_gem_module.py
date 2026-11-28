import unittest
from unittest.mock import Mock

from modules.base import UpdateContext
from modules.devtools import GemModule


class GemModuleTests(unittest.TestCase):
    def test_gem_module_reports_single_package_updated_with_version_diff(self):
        context = UpdateContext()
        context.which = Mock(return_value="/home/user/.rbenv/shims/gem")
        context.run_cmd = Mock(
            side_effect=[
                (0, "Installing RubyGems 4.0.22\nRubyGems 4.0.22 installed\n", ""),
                (0, "Nothing to update\n", ""),
            ]
        )

        result = GemModule().run(context)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "1 gem updated")
        self.assertEqual(result.details, ["rubygems-update"])

    def test_gem_module_reports_unchanged_when_already_latest(self):
        context = UpdateContext()
        context.which = Mock(return_value="/home/user/.rbenv/shims/gem")
        context.run_cmd = Mock(
            side_effect=[
                (0, "Latest version already installed. Done.\n", ""),
                (0, "Nothing to update\n", ""),
            ]
        )

        result = GemModule().run(context)
        self.assertEqual(result.status, "unchanged")

    def test_gem_permission_error_returns_warning(self):
        context = UpdateContext()
        context.which = Mock(return_value="/home/user/.rbenv/shims/gem")
        context.run_cmd = Mock(
            return_value=(
                1,
                "Updating rubygems-update\n",
                "ERROR: While executing gem ... (Gem::FilePermissionError)\nYou don't have write permissions for the /Library/Ruby/Gems/2.6.0 directory.",
            )
        )

        result = GemModule().run(context)
        self.assertEqual(result.status, "warning")
        self.assertIn("not writable", result.message)

    def test_gem_homebrew_ruby_skips_system_update_and_updates_homebrew_gems(self):
        context = UpdateContext()
        context.which = Mock(return_value="/home/linuxbrew/.linuxbrew/bin/gem")
        context.run_cmd = Mock(
            return_value=(0, "Updating solargraph\nGems updated: solargraph\n", "")
        )

        result = GemModule().run(context)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "1 gem updated")
        self.assertEqual(result.details, ["solargraph"])
        context.run_cmd.assert_called_once_with(
            [
                "/home/linuxbrew/.linuxbrew/bin/gem",
                "update",
                "--no-document",
            ],
            timeout=180,
        )

    def test_gem_linux_system_ruby_uses_user_install(self):
        from unittest.mock import patch

        context = UpdateContext()
        context.which = Mock(return_value="/usr/bin/gem")
        context.run_cmd = Mock(
            return_value=(0, "Updating solargraph\nGems updated: solargraph\n", "")
        )

        with patch("platform.system", return_value="Linux"):
            result = GemModule().run(context)

        self.assertEqual(result.status, "ok")
        context.run_cmd.assert_called_once_with(
            ["/usr/bin/gem", "update", "--user-install", "--no-document"],
            timeout=180,
        )

    def test_gem_macos_system_ruby_availability_returns_no_targets(self):
        from unittest.mock import patch

        context = UpdateContext()
        context.which = Mock(return_value="/usr/bin/gem")
        with patch("platform.system", return_value="Darwin"):
            self.assertEqual(GemModule()._availability(context), "no-targets")


if __name__ == "__main__":
    unittest.main()
