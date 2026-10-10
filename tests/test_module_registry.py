import tempfile
import unittest
from pathlib import Path

from config import Config
from modules import get_all_modules
from modules.git_repos import GitReposModule
from modules.snapshot import SnapshotModule


class ModuleRegistryTests(unittest.TestCase):
    def test_modules_use_the_supplied_configuration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_path = root / "dotfiles"
            repo_path.mkdir()
            config_path = root / "custom.toml"
            config_path.write_text(
                "[misc]\n"
                "cooldown_hours = 3\n"
                "[git]\n"
                f'repos = ["{repo_path}"]\n'
                "[commands]\n"
                '"Custom task" = "custom-tool update"\n',
                encoding="utf-8",
            )
            config = Config(str(config_path))

            modules = get_all_modules(config)

        snapshot = next(
            module for module in modules if isinstance(module, SnapshotModule)
        )
        git_repos = next(
            module for module in modules if isinstance(module, GitReposModule)
        )
        custom_task = next(module for module in modules if module.name == "Custom task")

        self.assertEqual(snapshot.cooldown_hours, 3)
        self.assertEqual(git_repos.config, config)
        self.assertEqual(git_repos.config.git_repos, [str(repo_path)])
        self.assertEqual(custom_task.command, "custom-tool update")


if __name__ == "__main__":
    unittest.main()
