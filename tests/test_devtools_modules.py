import unittest
from unittest.mock import Mock

from modules.base import UpdateContext
from modules.devtools import GhExtensionsModule, RustupModule


class DevtoolsModulesTests(unittest.TestCase):
    def test_rustup_parses_modern_toolchain_update_output(self):
        context = UpdateContext()
        output = "\n  stable-x86_64-unknown-linux-gnu updated - rustc 1.99.1 (from rustc 1.99.0)\n\n"
        context.run_cmd = Mock(return_value=(0, output, ""))

        result = RustupModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "1 toolchain updated")
        self.assertEqual(result.details, ["stable-x86_64-unknown-linux-gnu"])

    def test_rustup_parses_legacy_arrow_toolchain_update_output(self):
        context = UpdateContext()
        output = (
            "stable-x86_64-unknown-linux-gnu updated - rustc 1.98.0 -> rustc 1.99.0\n"
        )
        context.run_cmd = Mock(return_value=(0, output, ""))

        result = RustupModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "1 toolchain updated")
        self.assertEqual(result.details, ["stable-x86_64-unknown-linux-gnu"])

    def test_rustup_self_update(self):
        context = UpdateContext()
        output = "info: rustup updated to 1.28.0\n"
        context.run_cmd = Mock(return_value=(0, output, ""))

        result = RustupModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "1 toolchain updated")
        self.assertEqual(result.details, ["rustup"])

    def test_rustup_unchanged(self):
        context = UpdateContext()
        output = "stable-x86_64-unknown-linux-gnu unchanged - rustc 1.99.1\n"
        context.run_cmd = Mock(return_value=(0, output, ""))

        result = RustupModule().run(context)

        self.assertEqual(result.status, "unchanged")

    def test_gh_extension_upgrade_parses_extension_names(self):
        context = UpdateContext()
        output = "✓ Upgraded dlvhdr/gh-dash to v3.15.0\n✓ Upgraded seachicken/gh-poi\n"
        context.run_cmd = Mock(return_value=(0, output, ""))

        result = GhExtensionsModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "2 extensions updated")
        self.assertEqual(result.details, ["dlvhdr/gh-dash", "seachicken/gh-poi"])


if __name__ == "__main__":
    unittest.main()
