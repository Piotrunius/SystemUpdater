import unittest
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

from modules.brew import BrewModule
from modules.docker import DockerModule
from modules.git_repos import GitReposModule


class PartialFailureTests(unittest.TestCase):
    def test_homebrew_cask_failure_is_reported_after_formula_upgrade(self):
        context = SimpleNamespace(
            dry_run=False,
            which=Mock(return_value="/usr/bin/brew"),
            run_cmd=Mock(
                side_effect=[
                    (0, "Updated taps", ""),
                    (0, "==> Upgrading formula-one", ""),
                    (1, "", "cask download failed"),
                ]
            ),
        )

        result = BrewModule().run(cast(Any, context))

        self.assertEqual(result.status, "error")
        self.assertEqual(result.details, ["formula-one"])
        self.assertIn("cask download failed", result.error_output)

    def test_docker_pull_failure_is_reported_even_if_another_image_updated(self):
        context = SimpleNamespace(
            dry_run=False,
            run_cmd=Mock(
                side_effect=[
                    (0, "image-one:latest\nimage-two:latest", ""),
                    (0, "Downloaded newer image", ""),
                    (1, "", "registry unavailable"),
                ]
            ),
        )

        result = DockerModule().run(cast(Any, context))

        self.assertEqual(result.status, "error")
        self.assertEqual(result.details, ["image-one:latest"])
        self.assertIn("registry unavailable", result.error_output)

    def test_git_pull_failure_is_reported_even_if_another_repository_updated(self):
        config = SimpleNamespace(git_repos=["/repos/failed", "/repos/updated"])
        context = SimpleNamespace(
            dry_run=False,
            which=Mock(return_value="/usr/bin/git"),
            run_cmd=Mock(
                side_effect=[
                    (1, "", "repository unavailable"),
                    (0, "Updating abc..def", ""),
                ]
            ),
        )

        result = GitReposModule(cast(Any, config)).run(cast(Any, context))

        self.assertEqual(result.status, "error")
        self.assertEqual(result.details, ["updated"])
        self.assertIn("repository unavailable", result.error_output)

    def test_partial_failure_summary_renders_updated_and_error_separately(self):
        import contextlib
        import io
        import re

        from ui import UI, StepResult

        brew_res = StepResult(
            "error",
            "Homebrew upgrade failed",
            details=["openssl@3", "libffi"],
            error_output="Casks: Error: lulu: App source not found",
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            UI(is_interactive=False, verbose=False).print_summary(
                [{"name": "Homebrew", "key": "brew", "result": brew_res}], 1.0
            )
        plain = re.sub(r"\x1b\[[0-9;]*m", "", out.getvalue())

        # Should be listed under Updated components
        self.assertIn("Updated components:", plain)
        self.assertIn("• Homebrew: 2 packages updated", plain)
        self.assertIn("- openssl@3", plain)
        self.assertIn("- libffi", plain)

        # In Errors section, only the actual error should be shown, not the successful packages
        self.assertIn("Failed components:", plain)
        self.assertIn("• Homebrew: failed", plain)
        self.assertIn("- Casks: Error: lulu: App source not found", plain)
        # Verify openssl@3 is NOT duplicated under Failed components
        error_section = plain.split("Failed components:")[1]
        self.assertNotIn("- openssl@3", error_section)
        self.assertNotIn("- libffi", error_section)


if __name__ == "__main__":
    unittest.main()
