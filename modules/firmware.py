"""
Firmware upgrades module using fwupdmgr.
"""

import json
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

        # Refresh metadata
        ctx.run_cmd(["fwupdmgr", "refresh", "--force"], timeout=30)

        # Check updates
        code, out, err = ctx.run_cmd(["fwupdmgr", "get-updates", "--json"], timeout=30)
        if code == 2 or "No updates available" in out:
            return StepResult("unchanged")

        devices = []
        if code == 0:
            try:
                data = json.loads(out)
                devices = data.get("Devices", [])
                if not devices:
                    return StepResult("unchanged")
            except Exception:
                pass

        if code != 0:
            return StepResult("unchanged")

        # Apply updates if available
        up_code, up_out, up_err = ctx.run_cmd(["fwupdmgr", "update", "-y"])
        if up_code == 0 and "No updates" not in up_out:
            details = [
                f"{d.get('Name')} -> {d.get('Version')}"
                for d in devices
                if d.get("Name") and d.get("Version")
            ]
            count = len(details) or len(devices)
            return StepResult("ok", f"{count} device firmware update{'s' if count != 1 else ''} applied" if count else "updated", details=details)

        return StepResult("unchanged")
