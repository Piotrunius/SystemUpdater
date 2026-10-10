"""
Firmware upgrades module using fwupdmgr.
"""

import json
import re
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class FirmwareModule(BaseModule):
    name = "Device Firmware"
    key = "firmware"
    category = "System Core"
    description = "Checks and applies hardware/UEFI firmware updates via fwupdmgr"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("fwupdmgr") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would refresh and apply firmware updates")

        # Refresh metadata, but retain refresh failures when cached data is still usable.
        _, refresh_out, refresh_err = ctx.run_cmd(
            ["fwupdmgr", "refresh", "--force"], timeout=30
        )
        refresh_output = "\n".join(part for part in (refresh_out, refresh_err) if part)
        warnings = list(dict.fromkeys(
            line.strip()
            for line in refresh_output.splitlines()
            if re.search(
                r"(?:failed|error|unable|could not).*metadata|metadata.*(?:failed|error|unable|could not)",
                line,
                re.I,
            )
        ))
        # Check updates (read-only query)
        code, out, err = ctx.run_cmd(
            ["fwupdmgr", "get-updates", "--json"], timeout=30, read_only=True
        )
        if code == 2 or "No updates available" in out:
            return StepResult("unchanged", warnings=warnings)
        if code != 0:
            return StepResult(
                "error",
                "Firmware update check failed",
                error_output=err or out,
                warnings=warnings,
            )

        try:
            data = json.loads(out)
            devices = data.get("Devices", [])
            if not isinstance(devices, list) or any(not isinstance(device, dict) for device in devices):
                raise ValueError("Devices must be a JSON list of objects")
        except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as error:
            return StepResult(
                "error",
                "Firmware update check returned invalid data",
                error_output=f"{error}\n{out}".strip(),
                warnings=warnings,
            )

        if not devices:
            return StepResult("unchanged", warnings=warnings)

        # Apply updates if available with safe non-blocking staging
        up_code, up_out, up_err = ctx.run_cmd(
            ["fwupdmgr", "update", "-y", "--no-reboot-check"]
        )
        if up_code == 0 and "No updates" not in up_out:
            rb_code, rb_out, _ = ctx.run_cmd(["fwupdmgr", "check-reboot-needed"])
            reboot_needed = (rb_code == 0 or "reboot is needed" in (rb_out or "").lower())

            details = [
                f"{d.get('Name')} -> {d.get('Version')}"
                for d in devices
                if d.get("Name") and d.get("Version")
            ]
            count = len(details) or len(devices)
            msg = f"{count} package{'s' if count != 1 else ''} updated" if count else "updated"

            fw_warnings = list(warnings)
            if reboot_needed:
                fw_warnings.append("System reboot required to complete pending updates")

            return StepResult(
                "ok",
                msg,
                details=details,
                warnings=fw_warnings,
                reboot_required=reboot_needed,
            )

        if up_code != 0:
            return StepResult(
                "error",
                "Firmware update failed",
                error_output=up_err or up_out,
                warnings=warnings,
            )

        return StepResult("unchanged", warnings=warnings)
