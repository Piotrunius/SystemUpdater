import unittest

from completions import (
    generate_bash_completion,
    generate_fish_completion,
    generate_zsh_completion,
)
from modules import get_all_modules


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.modules = get_all_modules()

    def test_generate_bash_completion(self):
        script = generate_bash_completion(self.modules)
        self.assertIn("_sysupdate()", script)
        self.assertIn("complete -F _sysupdate sysupdate", script)
        self.assertIn("--notify", script)
        self.assertIn("--generate-completion", script)
        self.assertIn("--generate-completions", script)
        self.assertIn("dnf", script)
        self.assertIn("flatpak", script)
        self.assertIn("brew", script)

    def test_generate_zsh_completion(self):
        script = generate_zsh_completion(self.modules)
        self.assertIn("#compdef sysupdate", script)
        self.assertIn("_sysupdate()", script)
        self.assertIn("--notify", script)
        self.assertIn("--generate-completion", script)
        self.assertIn("--generate-completions", script)
        self.assertIn("'flatpak'", script)
        self.assertIn("'brew'", script)

    def test_generate_fish_completion(self):
        script = generate_fish_completion(self.modules)
        self.assertIn("complete -c sysupdate", script)
        self.assertIn("-l notify", script)
        self.assertIn("-l generate-completion", script)
        self.assertIn("-l generate-completions", script)
        self.assertIn("flatpak", script)


if __name__ == "__main__":
    unittest.main()
