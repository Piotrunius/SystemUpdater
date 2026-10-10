import unittest

from modules.firmware import FirmwareModule


class FakeContext:
    dry_run = False

    def __init__(self, responses):
        self.responses = iter(responses)
        self.commands = []

    def run_cmd(self, cmd, *_args, **_kwargs):
        self.commands.append(cmd)
        return next(self.responses)


class FirmwareTests(unittest.TestCase):
    def test_metadata_refresh_failure_is_reported_even_when_cached_check_is_empty(self):
        warning = "Failed to update metadata for lvfs: signing timestamp is older"
        context = FakeContext(
            [
                (0, "", warning),
                (0, '{"Devices": []}', ""),
            ]
        )

        result = FirmwareModule().run(context)

        self.assertEqual(result.status, "unchanged")
        self.assertEqual(result.warnings, [warning])

    def test_telemetry_rejection_after_metadata_download_is_not_a_warning(self):
        context = FakeContext(
            [
                (
                    1,
                    "Successfully downloaded new metadata:\n • 10 devices are updatable",
                    "server rejected report: too many reports for this machine and firmware today",
                ),
                (0, '{"Devices": []}', ""),
            ]
        )

        result = FirmwareModule().run(context)

        self.assertEqual(result.status, "unchanged")
        self.assertEqual(result.warnings, [])

    def test_update_check_failure_is_an_error(self):
        context = FakeContext([(0, "", ""), (1, "", "device service unavailable")])

        result = FirmwareModule().run(context)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.error_output, "device service unavailable")

    def test_invalid_device_entries_are_reported_as_invalid_data(self):
        context = FakeContext([(0, "", ""), (0, '{"Devices": [null]}', "")])

        result = FirmwareModule().run(context)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.message, "Firmware update check returned invalid data")

    def test_firmware_update_failure_is_an_error(self):
        context = FakeContext(
            [
                (0, "", ""),
                (0, '{"Devices": [{"Name": "Device", "Version": "2.0"}]}', ""),
                (1, "", "installation failed"),
            ]
        )

        result = FirmwareModule().run(context)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.error_output, "installation failed")

    def test_firmware_update_staged_with_reboot_required(self):
        context = FakeContext(
            [
                (0, "", ""),
                (
                    0,
                    '{"Devices": [{"Name": "UEFI System Firmware", "Version": "1.2.0"}]}',
                    "",
                ),
                (0, "Decompressing...\nUpdating UEFI System Firmware...", ""),
                (0, "Reboot required to apply", ""),
            ]
        )

        result = FirmwareModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertTrue(result.reboot_required)
        self.assertEqual(result.message, "1 device updated")
        self.assertEqual(result.details, ["UEFI System Firmware -> 1.2.0"])
        self.assertEqual(
            result.warnings, ["System reboot required to complete pending updates"]
        )
        self.assertIn(
            ["fwupdmgr", "update", "-y", "--no-reboot-check"], context.commands
        )
        self.assertIn(["fwupdmgr", "check-reboot-needed"], context.commands)

    def test_firmware_update_applied_without_reboot(self):
        context = FakeContext(
            [
                (0, "", ""),
                (
                    0,
                    '{"Devices": [{"Name": "Wireless Dongle", "Version": "3.1.0"}]}',
                    "",
                ),
                (0, "Updating Wireless Dongle...", ""),
                (2, "No reboot is necessary", ""),
            ]
        )

        result = FirmwareModule().run(context)

        self.assertEqual(result.status, "ok")
        self.assertFalse(result.reboot_required)
        self.assertEqual(result.message, "1 device updated")
        self.assertEqual(result.details, ["Wireless Dongle -> 3.1.0"])


if __name__ == "__main__":
    unittest.main()
