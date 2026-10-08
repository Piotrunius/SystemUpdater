import unittest
from types import SimpleNamespace
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

        result = BrewModule().run(context)

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

        result = DockerModule().run(context)

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

        result = GitReposModule(config).run(context)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.details, ["updated"])
        self.assertIn("repository unavailable", result.error_output)


if __name__ == "__main__":
    unittest.main()
