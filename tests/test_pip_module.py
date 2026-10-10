import unittest
from unittest.mock import Mock

from modules.base import UpdateContext
from modules.devtools import PipModule


class PipModuleTests(unittest.TestCase):
    def test_pip_module_handles_pep668_externally_managed_gracefully(self):
        context = UpdateContext()
        context.which = Mock(side_effect=lambda name: "/home/linuxbrew/.linuxbrew/bin/python3" if name == "python3" else None)
        context.run_cmd = Mock(
            side_effect=[
                (0, "pip 26.2.1\n", ""),
                (1, "", "error: externally-managed-environment\n\n× This environment is externally managed"),
            ]
        )

        result = PipModule().run(context)
        self.assertEqual(result.status, "unchanged")

    def test_pip_module_falls_back_to_standalone_pip_when_externally_managed(self):
        context = UpdateContext()

        def mock_which(name):
            if name in ("python3", "python"):
                return "/home/linuxbrew/.linuxbrew/bin/python3"
            if name in ("pip3", "pip"):
                return "/home/piotrunius/.local/bin/pip3"
            return None

        context.which = Mock(side_effect=mock_which)

        def mock_run_cmd(cmd, **kwargs):
            if cmd == ["/home/linuxbrew/.linuxbrew/bin/python3", "-m", "pip", "--version"]:
                return 0, "pip 26.2.1\n", ""
            if cmd == ["/home/linuxbrew/.linuxbrew/bin/python3", "-m", "pip", "install", "--upgrade", "pip"]:
                return 1, "", "error: externally-managed-environment"
            if cmd == ["/home/piotrunius/.local/bin/pip3", "install", "--upgrade", "pip"]:
                return 0, "Requirement already satisfied: pip in ./.local/lib/python3.14/site-packages (26.2.1)\n", ""
            return 0, "", ""

        context.run_cmd = Mock(side_effect=mock_run_cmd)

        result = PipModule().run(context)
        self.assertEqual(result.status, "unchanged")


if __name__ == "__main__":
    unittest.main()
