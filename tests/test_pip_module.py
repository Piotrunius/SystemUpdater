import unittest
from unittest.mock import Mock

from modules.base import UpdateContext
from modules.devtools import PipModule


class PipModuleTests(unittest.TestCase):
    def test_pip_module_is_unavailable_when_externally_managed(self):
        context = UpdateContext()
        context.which = Mock(
            side_effect=lambda name: (
                "/home/linuxbrew/.linuxbrew/bin/python3" if name == "python3" else None
            )
        )
        context.run_cmd = Mock(
            side_effect=[
                (0, "pip 26.2.1\n", ""),  # pip --version
                (0, "", ""),  # managed probe exit code 0 (managed)
            ]
        )

        mod = PipModule()
        self.assertFalse(mod.is_available(context))

    def test_pip_module_is_available_when_standalone_pip_exists(self):
        context = UpdateContext()

        def mock_which(name):
            if name in ("python3", "python"):
                return "/home/linuxbrew/.linuxbrew/bin/python3"
            if name in ("pip3", "pip"):
                return "/home/piotrunius/.local/bin/pip3"
            return None

        context.which = Mock(side_effect=mock_which)

        def mock_run_cmd(cmd, **kwargs):
            if cmd == ["/home/piotrunius/.local/bin/pip3", "--version"]:
                return 0, "pip 26.2.1\n", ""
            if cmd == [
                "/home/piotrunius/.local/bin/pip3",
                "install",
                "--upgrade",
                "pip",
            ]:
                return (
                    0,
                    "Requirement already satisfied: pip in ./.local/lib/python3.14/site-packages (26.2.1)\n",
                    "",
                )
            return 0, "", ""

        context.run_cmd = Mock(side_effect=mock_run_cmd)

        mod = PipModule()
        self.assertTrue(mod.is_available(context))
        result = mod.run(context)
        self.assertEqual(result.status, "unchanged")

    def test_pip_module_upgrades_outdated_user_packages(self):
        context = UpdateContext()
        context.which = Mock(
            side_effect=lambda name: (
                "/home/piotrunius/.local/bin/pip3" if name in ("pip3", "pip") else None
            )
        )

        def mock_run_cmd(cmd, **kwargs):
            if cmd == [
                "/home/piotrunius/.local/bin/pip3",
                "install",
                "--upgrade",
                "pip",
            ]:
                return 0, "Requirement already satisfied: pip\n", ""
            if cmd == [
                "/home/piotrunius/.local/bin/pip3",
                "list",
                "--user",
                "--outdated",
                "--format=json",
            ]:
                return (
                    0,
                    (
                        '[{"name": "fastapi", "version": "0.141.1", "latest_version": "0.165.0"}, '
                        '{"name": "httpx", "version": "0.28.1", "latest_version": "0.29.0"}]'
                    ),
                    "",
                )
            if cmd == [
                "/home/piotrunius/.local/bin/pip3",
                "install",
                "--user",
                "--upgrade",
                "fastapi",
                "httpx",
            ]:
                return 0, "Successfully installed fastapi-0.165.0 httpx-0.29.0\n", ""
            return 0, "", ""

        context.run_cmd = Mock(side_effect=mock_run_cmd)
        result = PipModule().run(context)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "2 packages updated")
        self.assertEqual(result.details, ["fastapi", "httpx"])


if __name__ == "__main__":
    unittest.main()
