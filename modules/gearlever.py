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
        code, out, _ = ctx.run_cmd(
            ["flatpak", "list", "--app", "--columns=application"], read_only=True
        )
        return "it.mijorus.gearlever" in out

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult(
                "ok", "[DRY-RUN] Would check AppImage updates via Gear Lever"
            )

        code, out, err = ctx.run_cmd(
            [
                "flatpak",
                "run",
                "--env=LC_ALL=C.UTF-8",
                "it.mijorus.gearlever",
                "--list-updates",
                "--json",
            ]
        )
        if code != 0:
            # Gear Lever might not have GUI session or updates
            return StepResult("unchanged")

        import json

        try:
            data = json.loads(out)
            updates = data.get("updates", [])
            if not updates:
                return StepResult("unchanged")
            count = len(updates)
            details = [
                u.get("name", "AppImage") for u in updates if isinstance(u, dict)
            ]
            return StepResult(
                "ok",
                f"{count} update{'s' if count != 1 else ''} available",
                details=details,
            )
        except Exception:
            if (
                "No updates available" in out
                or not out.strip()
                or '"updates": []' in out
            ):
                return StepResult("unchanged")
            return StepResult("ok", "AppImage updates available in Gear Lever")

        return StepResult("ok", "AppImage updates available in Gear Lever")
