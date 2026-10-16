import unittest
from unittest.mock import Mock

from modules.base import UpdateContext
from modules.system_pm import ApkModule


class ApkModuleTests(unittest.TestCase):
    def test_apk_upgrade_parses_packages_with_transitions(self):
        context = UpdateContext()
        output = (
            "(1/3) Upgrading musl (1.2.4-r1 -> 1.2.4-r2)\n"
            "(2/3) Upgrading busybox (1.36.1-r0 -> 1.36.1-r1)\n"
            "(3/3) Purging old packages\n"
            "OK: 15 MiB in 25 packages\n"
        )
        context.run_cmd = Mock(return_value=(0, output, ""))

        result = ApkModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "2 packages upgraded")
        self.assertEqual(result.details, ["musl", "busybox"])

    def test_apk_upgrade_parses_packages_without_version_transitions(self):
        context = UpdateContext()
        output = "(1/1) Upgrading curl (8.6.0-r0)\nOK: 16 MiB in 26 packages\n"
        context.run_cmd = Mock(return_value=(0, output, ""))

        result = ApkModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.message, "1 package upgraded")
        self.assertEqual(result.details, ["curl"])

    def test_apk_unchanged_when_no_upgrades(self):
        context = UpdateContext()
        output = "OK: 15 MiB in 25 packages\n"
        context.run_cmd = Mock(return_value=(0, output, ""))

        result = ApkModule().run(context)

        self.assertEqual(result.status, "unchanged")


if __name__ == "__main__":
    unittest.main()
