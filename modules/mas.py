"""
Mac App Store application update module using the mas CLI.
"""

from __future__ import annotations

import re
from typing import ClassVar

from modules.base import BaseModule, UpdateContext, is_macos
from ui import StepResult


class MasModule(BaseModule):
    name = "App Store"
    key = "mas"
    aliases: ClassVar[list[str]] = ["macappstore", "appstore"]
    category = "Applications & Gaming"
    description = "Updates Mac App Store applications via mas"
    unit_name = "app"
    unit_name_plural = "apps"

    def _availability(self, ctx: UpdateContext) -> str:
        if not is_macos():
            return "unavailable"
        if ctx.which("mas") is None:
            return "not-installed"
        code, out, _ = ctx.run_cmd(["mas", "list"], timeout=5, read_only=True)
        if code != 0:
            return "unavailable"
        has_apps = any(line.strip() for line in (out or "").splitlines())
        return "active" if has_apps else "no-targets"

    def is_available(self, ctx: UpdateContext) -> bool:
        if not is_macos():
            return False
        return self._availability(ctx) in ("active", "unavailable")

    def availability_status(self, ctx: UpdateContext) -> str:
        return {
            "not-installed": "[Not Installed]",
            "no-targets": "[No Targets]",
            "unavailable": "[Unavailable]",
            "active": "[Active]",
        }[self._availability(ctx)]

    def run(self, ctx: UpdateContext) -> StepResult:
        # Check for outdated applications first
        o_code, o_out, o_err = ctx.run_cmd(["mas", "outdated"], read_only=True)
        if o_code != 0 and "not signed in" in (o_err or o_out).lower():
            return StepResult(
                "warning",
                "Mac App Store requires sign-in",
                warnings=["Sign in to the Mac App Store to enable updates via mas."],
            )

        outdated_map = self._parse_outdated(o_out or "")
        if not outdated_map and o_code == 0:
            return StepResult("unchanged", "up to date")

        # Perform upgrade
        u_code, u_out, u_err = ctx.run_cmd(["mas", "upgrade"])
        if u_code != 0:
            return StepResult(
                "error",
                "Mac App Store upgrade failed",
                error_output=u_err or u_out,
            )

        # Parse upgraded items or fallback to outdated list
        upgraded = self._parse_upgraded(u_out or "", outdated_map)
        if not upgraded:
            if "everything is up to date" in (u_out or "").lower():
                return StepResult("unchanged", "up to date")
            # If mas upgrade succeeded and we had outdated items, use them
            upgraded = list(outdated_map.keys())

        if not upgraded:
            return StepResult("unchanged", "up to date")

        count = len(upgraded)
        return StepResult(
            "ok",
            f"{count} app{'s' if count != 1 else ''} updated",
            details=upgraded,
        )

    def _parse_outdated(self, output: str) -> dict[str, tuple[str, str]]:
        outdated: dict[str, tuple[str, str]] = {}
        for line in output.splitlines():
            line_str = line.strip()
            # Format: 497799835 Xcode (15.2 -> 15.3) or 497799835 Xcode (15.3)
            m = re.match(r"^\s*\d+\s+(.+?)(?:\s+\((.+?)\))?\s*$", line_str)
            if m:
                app_name = m.group(1).strip()
                ver_info = m.group(2) or ""
                if "->" in ver_info:
                    parts = [p.strip() for p in ver_info.split("->", 1)]
                    outdated[app_name] = (parts[0], parts[1])
                else:
                    outdated[app_name] = ("", ver_info.strip())
        return outdated

    def _parse_upgraded(
        self, output: str, outdated_map: dict[str, tuple[str, str]]
    ) -> list[str]:
        upgraded: list[str] = []
        for line in output.splitlines():
            line_str = line.strip()
            # Match lines like "==> Upgrading Xcode" or "Upgrading Xcode"
            m = re.search(r"Upgrading\s+(.+)$", line_str, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                upgraded.append(name)
        return list(dict.fromkeys(upgraded))
