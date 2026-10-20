"""
Homebrew package manager module (Formulae and Casks).
"""

import os
import re

from modules.base import BaseModule, UpdateContext
from ui import StepResult

BREW_CANDIDATE_PATHS = [
    "/opt/homebrew/bin/brew",
    "/usr/local/bin/brew",
    "/home/linuxbrew/.linuxbrew/bin/brew",
]


def find_brew_bin(ctx: UpdateContext) -> str | None:
    found = ctx.which("brew")
    if found:
        return found
    for p in BREW_CANDIDATE_PATHS:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


class BrewModule(BaseModule):
    name = "Homebrew"
    key = "brew"
    category = "Containers & Packages"
    description = "Updates Homebrew taps, formulae, and desktop casks"

    def is_available(self, ctx: UpdateContext) -> bool:
        return find_brew_bin(ctx) is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return StepResult(
                "error",
                "Homebrew cannot update while SystemUpdater is running as root",
                error_output="Run SystemUpdater as the normal user to update Homebrew.",
            )

        brew_bin = find_brew_bin(ctx) or "brew"

        # 1. brew update
        u_code, u_out, u_err = ctx.run_cmd([brew_bin, "update"])
        if u_code != 0:
            return StepResult(
                "error",
                "Homebrew repository update failed",
                error_output=u_err or u_out,
            )

        # 2. brew upgrade (formulae and casks)
        up_code, up_out, up_err = ctx.run_cmd([brew_bin, "upgrade"])
        cask_code, cask_out, cask_err = ctx.run_cmd([brew_bin, "upgrade", "--cask"])

        combined_out = (up_out or "") + "\n" + (cask_out or "")

        upgraded = []
        for line in combined_out.splitlines():
            line_str = line.strip()
            # 1. Matches: "==> Upgrading <name>"
            m_up = re.match(r"==> Upgrading\s+([\w\.\-\@\/]+)", line_str)
            if m_up:
                upgraded.append(m_up.group(1))
                continue

            # 2. Matches table rows like: "systemd 262 -> 262_1"
            m_table = re.match(r"^([\w\.\-\@\/]+)\s+[^\s]+\s+->\s+[^\s]+", line_str)
            if (
                m_table
                and not line_str.startswith("==>")
                and not line_str.startswith("Warning:")
            ):
                upgraded.append(m_table.group(1))

        upgraded = list(dict.fromkeys(upgraded))

        failed_commands = []
        if up_code != 0:
            failed_commands.append(f"Formulae: {up_err or up_out or 'command failed'}")
        if cask_code != 0:
            failed_commands.append(f"Casks: {cask_err or cask_out or 'command failed'}")
        if failed_commands:
            return StepResult(
                "error",
                "Homebrew upgrade failed",
                details=upgraded,
                error_output="\n".join(failed_commands),
            )

        if upgraded:
            count = len(upgraded)
            return StepResult(
                "ok",
                f"{count} package{'s' if count != 1 else ''} upgraded",
                details=upgraded,
            )

        return StepResult("unchanged")
