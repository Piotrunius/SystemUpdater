"""
Gear Lever AppImage manager module.
"""

from modules.base import BaseModule, UpdateContext
from ui import StepResult


class GearLeverModule(BaseModule):
    name = "Gear Lever"
    key = "gearlever"
    category = "Applications & Gaming"
    description = "Checks and fetches AppImage updates via Gear Lever"

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("flatpak") is None:
            return False
        code, out, _ = ctx.run_cmd(["flatpak", "list", "--app", "--columns=application"], read_only=True)
        return "it.mijorus.gearlever" in out

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would check AppImage updates via Gear Lever")

        code, out, err = ctx.run_cmd(["flatpak", "run", "it.mijorus.gearlever", "--list-updates"])
        if code != 0:
            # Gear Lever might not have GUI session or updates
            return StepResult("unchanged")

        if "No updates available" in out or not out.strip():
            return StepResult("unchanged")

        return StepResult("ok", "AppImage updates available in Gear Lever")
