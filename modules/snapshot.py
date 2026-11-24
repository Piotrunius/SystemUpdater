"""
System snapshot module using Snapper (Btrfs) or Timeshift with cooldown tracking.
"""

import os
import time

from config import xdg_directory
from modules.base import BaseModule, UpdateContext
from ui import StepResult


def _root_filesystem_type() -> str | None:
    """Return the filesystem type mounted at /, as reported by mountinfo."""
    try:
        with open("/proc/self/mountinfo", "r", encoding="utf-8") as mountinfo:
            for line in mountinfo:
                fields = line.split()
                separator = fields.index("-")
                if fields[4] == "/":
                    return fields[separator + 1]
    except (OSError, ValueError, IndexError):
        return None
    return None


class SnapshotModule(BaseModule):
    name = "Snapshot"
    key = "snapshot"
    category = "System Protection"
    description = (
        "Creates a protective system snapshot via Snapper or Timeshift before updates"
    )
    requires_sudo = True

    def __init__(self, cooldown_hours: int = 12):
        self.cooldown_hours = cooldown_hours

    def _detect_backend(self, ctx: UpdateContext) -> str | None:
        if (
            ctx.which("snapper") is not None
            and _root_filesystem_type() == "btrfs"
            and os.path.isfile("/etc/snapper/configs/root")
        ):
            return "snapper"
        if ctx.which("timeshift") is not None and os.path.isfile(
            "/etc/timeshift/timeshift.json"
        ):
            return "timeshift"
        return None

    def is_available(self, ctx: UpdateContext) -> bool:
        return self._detect_backend(ctx) is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        backend = self._detect_backend(ctx) or "snapper"
        cache_dir = xdg_directory("XDG_CACHE_HOME", "~/.cache")
        os.makedirs(cache_dir, exist_ok=True)

        if backend == "timeshift":
            stamp_file = os.path.join(cache_dir, "sysupdate_timeshift_stamp")
        else:
            stamp_file = os.path.join(cache_dir, "sysupdate_snapper_stamp")
            legacy_stamp_file = os.path.join(cache_dir, "topgrade_snapper_stamp")
            if os.path.exists(legacy_stamp_file):
                if not os.path.exists(stamp_file):
                    try:
                        os.replace(legacy_stamp_file, stamp_file)
                    except OSError:
                        stamp_file = legacy_stamp_file
                else:
                    try:
                        os.remove(legacy_stamp_file)
                    except OSError:
                        pass

        cooldown_minutes = self.cooldown_hours * 60

        stamp_mtime = None
        if os.path.exists(stamp_file) and not ctx.force:
            try:
                stamp_mtime = os.path.getmtime(stamp_file)
            except OSError:
                ctx.print_verbose(
                    "Could not read the previous snapshot timestamp; creating a new snapshot"
                )
        if stamp_mtime is not None:
            diff_min = int((time.time() - stamp_mtime) // 60)
            if diff_min < cooldown_minutes:
                return StepResult("unchanged", "cooldown active")

        if backend == "timeshift":
            code, out, err = ctx.run_cmd(
                [
                    "sudo",
                    "timeshift",
                    "--create",
                    "--comments",
                    "system-updater",
                    "--scripted",
                ],
                timeout=180,
            )
            failure_msg = "Failed to create Timeshift snapshot"
        else:
            code, out, err = ctx.run_cmd(
                [
                    "sudo",
                    "snapper",
                    "-c",
                    "root",
                    "create",
                    "--description",
                    "system-updater",
                    "--cleanup",
                    "number",
                    "--userdata",
                    "important=yes",
                ],
                timeout=60,
            )
            failure_msg = "Failed to create Btrfs snapshot"

        if code == 0:
            warnings = []
            try:
                with open(stamp_file, "w") as f:
                    f.write(str(int(time.time())))
            except OSError as error:
                warnings.append(f"Could not save snapshot cooldown timestamp: {error}")
            return StepResult("ok", "Snapshot created successfully", warnings=warnings)

        return StepResult("error", failure_msg, error_output=err or out)
