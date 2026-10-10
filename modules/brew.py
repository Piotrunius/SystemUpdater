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
        return ctx.which("brew") is not None or os.path.exists(
            "/home/linuxbrew/.linuxbrew/bin/brew"
        )

    def run(self, ctx: UpdateContext) -> StepResult:
        brew_bin = ctx.which("brew") or "/home/linuxbrew/.linuxbrew/bin/brew"

        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run brew update and brew upgrade")

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
        version_transitions = {}
        lines = combined_out.splitlines()

        for i, line in enumerate(lines):
            line_str = line.strip()
            # 1. Matches: "==> Upgrading <name>"
            m_up = re.match(r"==> Upgrading\s+([\w\.\-\@\/]+)", line)
            if m_up:
                pkg_name = m_up.group(1)
                upgraded.append(pkg_name)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    m_ver = re.match(r"^([^\s]+)\s+->\s+([^\s]+)$", next_line)
                    if m_ver:
                        version_transitions[pkg_name] = (m_ver.group(1), m_ver.group(2))

            # 2. Matches table rows like: "systemd 262 -> 262_1"
            m_table = re.match(r"^([\w\.\-\@\/]+)\s+([^\s]+)\s+->\s+([^\s]+)", line_str)
            if (
                m_table
                and not line_str.startswith("==>")
                and not line_str.startswith("Warning:")
            ):
                pkg_name = m_table.group(1)
                upgraded.append(pkg_name)
                version_transitions[pkg_name] = (m_table.group(2), m_table.group(3))

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
            # Resolve version for each upgraded package for consistent formatting
            version_map = {}
            queries = list(
                dict.fromkeys(
                    [pkg for pkg in upgraded] + [pkg.split("/")[-1] for pkg in upgraded]
                )
            )
            _, v_out, _ = ctx.run_cmd(
                [brew_bin, "list", "--versions"] + queries, read_only=True
            )
            for line in (v_out or "").splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and not parts[0].startswith("Warning:"):
                    version_map[parts[0]] = parts[-1]

            missing = [pkg for pkg in queries if pkg not in version_map]
            if missing:
                _, c_out, _ = ctx.run_cmd(
                    [brew_bin, "list", "--cask", "--versions"] + missing, read_only=True
                )
                for line in (c_out or "").splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 2 and not parts[0].startswith("Warning:"):
                        version_map[parts[0]] = parts[-1]

            formatted_details = []
            for pkg in upgraded:
                short_pkg = pkg.split("/")[-1]
                if pkg in version_transitions:
                    old_v, new_v = version_transitions[pkg]
                    formatted_details.append(f"{pkg}: {old_v} -> {new_v}")
                elif pkg in version_map:
                    formatted_details.append(f"{pkg} -> {version_map[pkg]}")
                elif short_pkg in version_map:
                    formatted_details.append(f"{pkg} -> {version_map[short_pkg]}")
                else:
                    formatted_details.append(pkg)

            return StepResult(
                "ok",
                f"{count} package{'s' if count != 1 else ''} upgraded",
                details=formatted_details,
            )

        return StepResult("unchanged")
