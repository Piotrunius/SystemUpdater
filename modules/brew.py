"""
Homebrew package manager module (Formulae and Casks).
"""

import os
import re
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class BrewModule(BaseModule):
    name = "Homebrew"
    key = "brew"
    category = "Containers & Packages"
    description = "Updates Homebrew taps, formulae, and desktop casks"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("brew") is not None or os.path.exists("/home/linuxbrew/.linuxbrew/bin/brew")

    def run(self, ctx: UpdateContext) -> StepResult:
        brew_bin = ctx.which("brew") or "/home/linuxbrew/.linuxbrew/bin/brew"

        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run brew update and brew upgrade")

        # 1. brew update
        u_code, u_out, u_err = ctx.run_cmd([brew_bin, "update"])
        if u_code != 0:
            return StepResult("error", "Homebrew repository update failed", error_output=u_err or u_out)

        # 2. brew upgrade (formulae and casks)
        up_code, up_out, up_err = ctx.run_cmd([brew_bin, "upgrade"])
        cask_code, cask_out, cask_err = ctx.run_cmd([brew_bin, "upgrade", "--cask"])

        combined_out = (up_out or "") + "\n" + (cask_out or "")

        upgraded = []
        for line in combined_out.splitlines():
            # Matches: "==> Upgrading <name>"
            m = re.match(r"==> Upgrading\s+([\w\.\-\@\/]+)", line)
            if m:
                upgraded.append(m.group(1))

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
            # Resolve version for each upgraded package for consistent "name -> version" formatting
            version_map = {}
            _, v_out, _ = ctx.run_cmd([brew_bin, "list", "--versions"] + upgraded, read_only=True)
            for line in (v_out or "").splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and not parts[0].startswith("Warning:"):
                    version_map[parts[0]] = parts[-1]

            missing = [pkg for pkg in upgraded if pkg not in version_map]
            if missing:
                _, c_out, _ = ctx.run_cmd([brew_bin, "list", "--cask", "--versions"] + missing, read_only=True)
                for line in (c_out or "").splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 2 and not parts[0].startswith("Warning:"):
                        version_map[parts[0]] = parts[-1]

            formatted_details = [
                f"{pkg} -> {version_map[pkg]}" if pkg in version_map else pkg
                for pkg in upgraded[:10]
            ]
            if count > 10:
                formatted_details.append(f"... and {count - 10} more")

            return StepResult("ok", f"{count} package{'s' if count != 1 else ''} upgraded", details=formatted_details)

        return StepResult("unchanged")
