"""
System maintenance modules (mandb).
"""

from modules.base import BaseModule, UpdateContext
from ui import StepResult


class MandbModule(BaseModule):
    name = "Manual Pages DB (mandb)"
    key = "mandb"
    category = "System Core"
    description = "Updates the manual page index caches via mandb -q"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("mandb") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run mandb -q")

        code, out, err = ctx.run_cmd(["mandb", "-q"], timeout=120)
        if code != 0:
            return StepResult("error", "mandb failed", error_output=err or out)

        return StepResult("ok", "Manual pages database updated")
