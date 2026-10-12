"""
Gear Lever AppImage manager module.
"""

from modules.base import BaseModule, UpdateContext, check_github_api
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
        _, out, _ = ctx.run_cmd(
            ["flatpak", "list", "--app", "--columns=application"], read_only=True
        )
        return "it.mijorus.gearlever" in out

    def run(self, ctx: UpdateContext) -> StepResult:
        gh_check = check_github_api()
        if gh_check is not None:
            return gh_check

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
        combined = (out or "") + "\n" + (err or "")
        if (
            "rate limit" in combined.casefold()
            or "api limit reached" in combined.casefold()
        ):
            return StepResult("warning", "GitHub API rate limit reached")

        if code != 0:
            return StepResult("unchanged")

        import json

        updates = []
        try:
            json_start = out.find("{")
            if json_start != -1:
                data = json.loads(out[json_start:])
                updates = data.get("updates", [])
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        if not updates:
            return StepResult("unchanged")

        details = []
        for u in updates:
            if not isinstance(u, dict):
                continue
            name = u.get("name", "appimage")
            cur = u.get("current_version")
            avail = u.get("available_version")
            if cur and avail and str(cur) != str(avail):
                details.append(f"{name}: {cur} -> {avail}")
            elif avail:
                details.append(f"{name}: -> {avail}")
            else:
                details.append(name)

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
        up_combined = (up_out or "") + "\n" + (up_err or "")
        if (
            "rate limit" in up_combined.casefold()
            or "api limit reached" in up_combined.casefold()
        ):
            return StepResult("warning", "GitHub API rate limit reached")

        if up_code != 0:
            return StepResult(
                "error",
                "Gear Lever appimage update failed",
                error_output=up_err or up_out,
            )

        count = len(details)
        return StepResult(
            "ok",
            f"{count} appimage{'s' if count != 1 else ''} updated",
            details=details,
        )
