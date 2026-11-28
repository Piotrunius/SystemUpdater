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

    def test_rustup_runs_self_update_and_reports_rustup_when_toolchains_unchanged(self):
        context = UpdateContext()
        context.run_cmd = Mock(
            side_effect=[
                (0, "info: rustup updated to 1.29.3\n", ""),
                (0, "stable-x86_64-unknown-linux-gnu unchanged - rustc 1.100.1\n", ""),
            ]
        )

        result = RustupModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.details, ["rustup"])

    def test_gh_extension_upgrade_parses_extension_names(self):
        context = UpdateContext()
        output = "✓ Upgraded dlvhdr/gh-dash to v3.15.0\n✓ Upgraded seachicken/gh-poi\n"
        context.run_cmd = Mock(return_value=(0, output, ""))

        result = GhExtensionsModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "2 extensions updated")
        self.assertEqual(result.details, ["dlvhdr/gh-dash", "seachicken/gh-poi"])

    def test_uv_reports_ok_when_self_updated_even_if_tools_unchanged(self):
        from modules.devtools import UvModule

        context = UpdateContext()
        context.which = Mock(return_value="/home/user/.local/bin/uv")
        context.run_cmd = Mock(
            side_effect=[
                (0, "Updating uv from v0.6.0 to v0.6.1\n", ""),
                (0, "Nothing to upgrade\n", ""),
            ]
        )
        result = UvModule().run(context)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.details, ["uv"])

    def test_uv_skips_self_update_when_managed_by_homebrew(self):
        from modules.devtools import UvModule

        context = UpdateContext()
        context.which = Mock(return_value="/home/linuxbrew/.linuxbrew/bin/uv")
        context.run_cmd = Mock(return_value=(0, "", "Nothing to upgrade\n"))

        result = UvModule().run(context)
        self.assertEqual(result.status, "unchanged")
        context.run_cmd.assert_called_once_with(
            ["uv", "tool", "upgrade", "--all"], timeout=180
        )

    def test_mise_composer_poetry_handle_package_manager_managed_self_update(self):
        from modules.devtools import ComposerModule, MiseModule, PoetryModule

        mise_ctx = UpdateContext()
        mise_ctx.run_cmd = Mock(
            side_effect=[
                (1, "", "self-update is disabled (installed via Homebrew)"),
                (0, "mise all tools are up to date\n", ""),
            ]
        )
        self.assertEqual(MiseModule().run(mise_ctx).status, "unchanged")

        comp_ctx = UpdateContext()
        comp_ctx.run_cmd = Mock(
            side_effect=[
                (1, "", 'Command "self-update" is not defined.'),
                (0, "Nothing to modify in lock file\n", ""),
            ]
        )
        self.assertEqual(ComposerModule().run(comp_ctx).status, "unchanged")

        poetry_ctx = UpdateContext()
        poetry_ctx.run_cmd = Mock(
            return_value=(1, "", 'Command "self update" is not defined.')
        )
        self.assertEqual(PoetryModule().run(poetry_ctx).status, "unchanged")

    def test_editors_return_unchanged_when_no_extensions_need_update(self):
        from modules.editors import CursorModule, VsCodeModule, VscodiumModule

        for mod in (VsCodeModule(), CursorModule(), VscodiumModule()):
            ctx = UpdateContext()
            ctx.run_cmd = Mock(return_value=(0, "No extension to update.\n", ""))
            self.assertEqual(mod.run(ctx).status, "unchanged")


if __name__ == "__main__":
    unittest.main()
