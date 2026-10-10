"""
Gear Lever AppImage manager module.
"""

from modules.base import BaseModule, UpdateContext
from ui import StepResult


class GearLeverModule(BaseModule):
    name = "Gear Lever"
    key = "gearlever"
    category = "Applications & Gaming"
    description = "Checks and fetches appimage updates via Gear Lever"
    unit_name = "appimage"
    unit_name_plural = "appimages"

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("flatpak") is None:
            return False
        code, out, _ = ctx.run_cmd(
            ["flatpak", "list", "--app", "--columns=application"], read_only=True
        )
        return "it.mijorus.gearlever" in out

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, _ = ctx.run_cmd(
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
            return StepResult("unchanged")

        import json

        updates = []
        try:
            data = json.loads(out)
            updates = data.get("updates", [])
        except Exception:
            pass

        if not updates:
            return StepResult("unchanged")

        names = [u.get("name", "appimage") for u in updates if isinstance(u, dict)]

        up_code, up_out, up_err = ctx.run_cmd(
            [
                "flatpak",
                "run",
                "--env=LC_ALL=C.UTF-8",
                "it.mijorus.gearlever",
                "--update",
                "--all",
                "--yes",
            ],
            timeout=300,
        )

        if up_code != 0:
            return StepResult(
                "error",
                "Gear Lever appimage update failed",
                error_output=up_err or up_out,
            )

        count = len(names)
        return StepResult(
            "ok",
            f"{count} appimage{'s' if count != 1 else ''} updated",
            details=names,
        )
