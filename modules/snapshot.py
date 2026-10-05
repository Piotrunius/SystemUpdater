"""
Btrfs root snapshot module using Snapper with cooldown tracking.
Directly replaces Topgrade/snapshot.sh.
"""

import os
import time
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class SnapshotModule(BaseModule):
    name = "Btrfs Snapshot"
    key = "snapshot"
    category = "System Protection"
    description = "Creates a protective Btrfs root snapshot via Snapper before updates"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("snapper") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        cache_dir = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
        stamp_file = os.path.join(cache_dir, "topgrade_snapper_stamp")
        os.makedirs(cache_dir, exist_ok=True)

        cooldown_minutes = int(os.environ.get("TOPGRADE_SNAPSHOT_COOLDOWN", 720))

        if os.path.exists(stamp_file) and not ctx.force:
            try:
                last_mod = os.path.getmtime(stamp_file)
                diff_min = int((time.time() - last_mod) // 60)
                if diff_min < cooldown_minutes:
                    return StepResult("unchanged", "cooldown active")
            except Exception:
                pass

        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would create Btrfs root snapshot")

        code, out, err = ctx.run_cmd([
            "sudo", "snapper", "-c", "root", "create",
            "--description", "system-updater",
            "--cleanup", "number",
            "--userdata", "important=yes",
        ], timeout=60)

        if code == 0:
            try:
                with open(stamp_file, "w") as f:
                    f.write(str(int(time.time())))
            except Exception:
                pass
            return StepResult("ok", "Snapshot created successfully")
        else:
            return StepResult("error", "Failed to create Btrfs snapshot", error_output=err or out)
