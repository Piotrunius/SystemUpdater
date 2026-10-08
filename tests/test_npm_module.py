import unittest
from unittest.mock import Mock

from modules.base import UpdateContext
from modules.devtools import NpmModule


class NpmModuleTests(unittest.TestCase):
    def test_registry_check_failure_is_not_reported_as_up_to_date(self):
        context = UpdateContext()
        context.run_cmd = Mock(return_value=(1, "", "network unavailable"))

        result = NpmModule().run(context)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.message, "npm outdated check failed")


if __name__ == "__main__":
    unittest.main()
