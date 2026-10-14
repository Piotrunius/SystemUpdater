"""
macOS system software updates using the native softwareupdate command.
"""

from __future__ import annotations

import os
import platform
import re
from typing import ClassVar

from modules.base import BaseModule, UpdateContext
from ui import StepResult


class SoftwareUpdateModule(BaseModule):
    name = "System"
    key = "macos"
    aliases: ClassVar[list[str]] = ["softwareupdate", "apple", "darwin", "system"]
    category = "System Core"
    description = "Updates system software and developer tools via softwareupdate"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        if platform.system() != "Darwin":
            return False
        return ctx.which("softwareupdate") is not None or os.path.isfile(
            "/usr/sbin/softwareupdate"
        )

    def availability_status(self, ctx: UpdateContext) -> str:
        if platform.system() != "Darwin":
            return "[Unavailable]"
        return "[Active]" if self.is_available(ctx) else "[Not Installed]"

    def run(self, ctx: UpdateContext) -> StepResult:
        sw_bin = ctx.which("softwareupdate") or "/usr/sbin/softwareupdate"

        # Check for available software updates
        check_code, check_out, check_err = ctx.run_cmd([sw_bin, "-l"], read_only=True)
        combined_check = (check_out or "") + "\n" + (check_err or "")

        if (
            "no new software available" in combined_check.lower()
            or "no updates are available" in combined_check.lower()
        ):
            return StepResult("unchanged", "up to date")

        if check_code != 0 and not ("software update found" in combined_check.lower()):
            return StepResult(
                "error",
                "Checking for macOS software updates failed",
                error_output=check_err or check_out,
            )

        items, reboot_recommended = self._parse_available(combined_check)
        if not items:
            return StepResult("unchanged", "up to date")

        # Install updates
        install_cmd = [sw_bin, "-ia"]
        ins_code, ins_out, ins_err = ctx.run_cmd(install_cmd)
        combined_ins = (ins_out or "") + "\n" + (ins_err or "")

        if ins_code != 0:
            return StepResult(
                "error",
                "macOS software update failed",
                error_output=ins_err or ins_out,
                details=items,
            )

        reboot_required = (
            reboot_recommended
            or "restart" in combined_ins.lower()
            or "reboot" in combined_ins.lower()
        )

        count = len(items)
        return StepResult(
            "ok",
            f"{count} update{'s' if count != 1 else ''} installed",
            details=items,
            reboot_required=reboot_required,
        )

    def _parse_available(self, output: str) -> tuple[list[str], bool]:
        items: list[str] = []
        needs_restart = False

        for line in output.splitlines():
            line_str = line.strip()
            if not line_str.startswith("*"):
                continue

            if "action: restart" in line_str.lower():
                needs_restart = True

            # Extract Title or Label
            m_title = re.search(r"Title:\s*([^,]+)", line_str)
            m_label = re.search(r"\*\s*(?:Label:\s*)?([^,]+)", line_str)

            if m_title:
                name = m_title.group(1).strip()
                items.append(name)
            elif m_label:
                name = m_label.group(1).strip()
                if name.lower() not in ["title", "label"]:
                    items.append(name)

        return list(dict.fromkeys(items)), needs_restart
