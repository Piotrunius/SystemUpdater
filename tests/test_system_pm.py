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

    def test_pacman_skips_aur_helpers_when_running_as_root(self):
        from unittest.mock import patch

        from modules.system_pm import PacmanModule

        context = UpdateContext()
        context.which = Mock(return_value="/usr/bin/yay")
        context.run_cmd = Mock(return_value=(0, "there is nothing to do\n", ""))

        with patch("modules.system_pm.os.geteuid", return_value=0, create=True):
            result = PacmanModule().run(context)

        self.assertEqual(result.status, "unchanged")
        context.run_cmd.assert_called_once_with(
            ["pacman", "-Syu", "--noconfirm"], timeout=600
        )

    def test_bootc_and_rpm_ostree_modules(self):
        from unittest.mock import patch

        from modules.nobara import SystemPackagesModule
        from modules.system_pm import BootcModule, RpmOstreeModule

        bootc = BootcModule()
        ostree = RpmOstreeModule()
        dnf_mod = SystemPackagesModule()

        ctx_ostree = UpdateContext()
        ctx_ostree.which = Mock(
            side_effect=lambda b: (
                f"/usr/bin/{b}" if b in ("rpm-ostree", "dnf") else None
            )
        )
        with patch("os.path.exists", side_effect=lambda p: p == "/run/ostree-booted"):
            self.assertTrue(ostree.is_available(ctx_ostree))
            self.assertFalse(bootc.is_available(ctx_ostree))
            self.assertFalse(dnf_mod.is_available(ctx_ostree))

        ctx_ostree.run_cmd = Mock(
            return_value=(
                0,
                "Upgraded:\n  kernel 6.13.0 -> 6.13.1\n  firefox 130.0 -> 131.0\nRun 'systemctl reboot' to start using the new deployment.\n",
                "",
            )
        )
        res = ostree.run(ctx_ostree)
        self.assertEqual(res.status, "ok")
        self.assertTrue(res.reboot_required)
        self.assertEqual(res.details, ["kernel", "firefox"])

        ctx_bootc = UpdateContext()
        ctx_bootc.which = Mock(
            side_effect=lambda b: (
                f"/usr/bin/{b}" if b in ("bootc", "rpm-ostree") else None
            )
        )
        with patch("os.path.exists", side_effect=lambda p: p == "/run/ostree-booted"):
            self.assertTrue(bootc.is_available(ctx_bootc))
            self.assertFalse(ostree.is_available(ctx_bootc))

        ctx_bootc.run_cmd = Mock(
            return_value=(0, "No changes in quay.io/fedora/fedora-bootc:latest\n", "")
        )
        self.assertEqual(bootc.run(ctx_bootc).status, "unchanged")

        ctx_bootc.run_cmd = Mock(
            return_value=(
                0,
                "Queued for next boot: quay.io/fedora/fedora-bootc:latest\n",
                "",
            )
        )
        bootc_res = bootc.run(ctx_bootc)
        self.assertEqual(bootc_res.status, "ok")
        self.assertTrue(bootc_res.reboot_required)


if __name__ == "__main__":
    unittest.main()
