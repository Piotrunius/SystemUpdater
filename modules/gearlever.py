"""
Gear Lever AppImage manager module.
"""

import json

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
            return StepResult(
                "error",
                "Gear Lever update check failed",
                error_output=err or out,
            )

        try:
            json_start = out.find("{")
            if json_start == -1:
                raise ValueError("JSON update data was not found")
            data, _ = json.JSONDecoder().raw_decode(out[json_start:])
            if not isinstance(data, dict) or not isinstance(data.get("updates"), list):
                raise TypeError("The update list has an unexpected format")
            updates = data["updates"]
            if any(not isinstance(update, dict) for update in updates):
                raise TypeError("An update entry has an unexpected format")
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            return StepResult(
                "error",
                "Gear Lever returned invalid update data",
                error_output=str(error),
            )

        if not updates:
            return StepResult("unchanged")

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

        details = [str(update.get("name") or "appimage") for update in updates]
        count = len(details)
        return StepResult(
            "ok",
            f"{count} appimage{'s' if count != 1 else ''} updated",
            details=details,
        )
