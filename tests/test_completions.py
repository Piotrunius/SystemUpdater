import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from completions import (
    generate_bash_completion,
    generate_fish_completion,
    generate_zsh_completion,
    install_completions,
)
from modules import get_all_modules
from modules.base import BaseModule


class CompletionTests(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.modules: list[BaseModule] = []

    def setUp(self):
        self.modules = get_all_modules()

    def test_generate_bash_completion(self):
        script = generate_bash_completion(self.modules)
        self.assertIn("_sysupdate()", script)
        self.assertIn("complete -F _sysupdate sysupdate", script)
        self.assertIn("--notify", script)
        self.assertIn("--generate-completion", script)
        self.assertNotIn("--generate-completions", script)
        self.assertIn("dnf", script)
        self.assertIn("flatpak", script)
        self.assertIn("brew", script)

    def test_generate_zsh_completion(self):
        script = generate_zsh_completion(self.modules)
        self.assertIn("#compdef sysupdate", script)
        self.assertIn("_sysupdate()", script)
        self.assertIn("--notify", script)
        self.assertIn("--generate-completion", script)
        self.assertNotIn("--generate-completions", script)
        self.assertIn("'flatpak'", script)
        self.assertIn("'brew'", script)

    def test_generate_fish_completion(self):
        script = generate_fish_completion(self.modules)
        self.assertIn("complete -c sysupdate", script)
        self.assertIn("-l notify", script)
        self.assertIn("-l generate-completion", script)
        self.assertNotIn("-l generate-completions", script)
        self.assertIn("flatpak", script)

    def test_install_completions_to_target_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            home_dir = tmp_path / "home"
            home_dir.mkdir()

            with (
                patch.dict(
                    "os.environ",
                    {
                        "HOME": str(home_dir),
                        "XDG_DATA_HOME": str(home_dir / ".local" / "share"),
                        "XDG_CONFIG_HOME": str(home_dir / ".config"),
                        "SHELL": "/bin/zsh",
                    },
                ),
                patch("os.path.expanduser", lambda p: p.replace("~", str(home_dir))),
            ):
                results = install_completions(self.modules, target_shell="auto")
                labels = [label for label, _ in results]
                self.assertIn("Zsh", labels)
                self.assertIn("Bash", labels)

                zsh_file = home_dir / ".zsh" / "completions" / "_sysupdate"
                bash_file = (
                    home_dir
                    / ".local"
                    / "share"
                    / "bash-completion"
                    / "completions"
                    / "sysupdate"
                )
                self.assertTrue(zsh_file.exists())
                self.assertTrue(bash_file.exists())
                self.assertIn(
                    "#compdef sysupdate", zsh_file.read_text(encoding="utf-8")
                )
                self.assertIn("_sysupdate()", bash_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
