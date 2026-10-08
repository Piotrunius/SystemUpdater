import unittest
from unittest.mock import Mock

from modules.base import UpdateContext
from modules.universal import NixModule


class NixModuleTests(unittest.TestCase):
    def test_channel_refresh_failure_stops_before_environment_upgrade(self):
        context = UpdateContext()
        context.run_cmd = Mock(return_value=(1, "", "channel unavailable"))

        result = NixModule().run(context)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.message, "nix-channel update failed")
        context.run_cmd.assert_called_once_with(["nix-channel", "--update"], timeout=180)


if __name__ == "__main__":
    unittest.main()
