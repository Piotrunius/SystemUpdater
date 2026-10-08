import unittest
from unittest.mock import Mock

from modules.nobara import RepoSyncModule
from modules.system_pm import ZypperModule
from modules.base import UpdateContext


class PackageSignatureCheckTests(unittest.TestCase):
    def test_nobara_repository_sync_keeps_dnf_signature_verification_enabled(self):
        context = UpdateContext()
        context.run_cmd = Mock(return_value=(0, "Nothing to do", ""))

        RepoSyncModule().run(context)

        command = context.run_cmd.call_args.args[0]
        self.assertNotIn("--nogpgcheck", command)

    def test_zypper_upgrade_keeps_gpg_checks_enabled(self):
        context = UpdateContext()
        context.run_cmd = Mock(return_value=(0, "Nothing to do", ""))

        with unittest.mock.patch(
            "modules.system_pm.get_os_release", return_value={"ID": "opensuse-tumbleweed"}
        ):
            ZypperModule().run(context)

        command = context.run_cmd.call_args.args[0]
        self.assertNotIn("--no-gpg-checks", command)


if __name__ == "__main__":
    unittest.main()
