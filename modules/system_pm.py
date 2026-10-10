"""
Universal system package managers for all major Linux distributions:
- APT (Debian, Ubuntu, Linux Mint, Pop!_OS, Kali)
- Pacman / AUR (Arch Linux, Manjaro, EndeavourOS, CachyOS)
- Zypper (openSUSE Tumbleweed, Leap)
- APK (Alpine Linux)
- XBPS (Void Linux)
"""

import os
import re
from typing import List
from modules.base import BaseModule, UpdateContext, get_os_release
from ui import StepResult


class AptModule(BaseModule):
    name = "System"
    key = "apt"
    aliases = ["deb", "debian", "ubuntu", "system"]
    category = "System Core"
    description = "Updates system packages via APT"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("apt-get") is not None and ctx.which("dpkg") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        env = {"DEBIAN_FRONTEND": "noninteractive"}

        # 1. Update package lists
        u_code, u_out, u_err = ctx.run_cmd(
            ["sudo", "apt-get", "update", "-q"], env_extra=env
        )
        if u_code != 0:
            refresh_output = u_err or u_out
            if "Failed to fetch" in refresh_output:
                return StepResult(
                    "warning",
                    "APT repository refresh encountered network warnings",
                    error_output=refresh_output,
                )
            return StepResult(
                "error", "APT repository refresh failed", error_output=refresh_output
            )

        # 2. Upgrade packages
        up_code, up_out, up_err = ctx.run_cmd(
            [
                "sudo",
                "apt-get",
                "dist-upgrade",
                "-y",
                "-o",
                "Dpkg::Options::=--force-confdef",
                "-o",
                "Dpkg::Options::=--force-confold",
            ],
            env_extra=env,
            timeout=600,
        )

        if up_code != 0:
            return StepResult(
                "error", "APT upgrade failed", error_output=up_err or up_out
            )

        # Parse upgraded packages from apt output
        # Matches: "Setting up package (version) ..." or "Preparing to unpack .../package_version_arch.deb"
        upgraded = []
        for line in (up_out or "").splitlines():
            m = re.search(r"Setting up\s+([\w\.\-]+)\s+\(([^)]+)\)", line)
            if m:
                upgraded.append(f"{m.group(1)} -> {m.group(2)}")
            else:
                m2 = re.search(
                    r"Preparing to unpack \S+/([a-zA-Z0-9\.\-]+)_([a-zA-Z0-9\.\-\:\+~]+)_[^._]+\.deb",
                    line,
                )
                if m2:
                    upgraded.append(f"{m2.group(1)} -> {m2.group(2)}")

        upgraded = list(dict.fromkeys(upgraded))

        # 3. Clean up obsolete packages
        cleanup_code, _, _ = ctx.run_cmd(
            ["sudo", "apt-get", "autoremove", "-y", "-q"], env_extra=env, timeout=120
        )
        cleanup_warnings = []
        if cleanup_code != 0:
            cleanup_warnings.append("APT autoremove failed")

        if upgraded:
            count = len(upgraded)
            return StepResult(
                "ok",
                f"{count} package{'s' if count != 1 else ''} upgraded",
                details=upgraded,
                warnings=cleanup_warnings,
            )

        if "0 upgraded, 0 newly installed" in up_out:
            return StepResult("unchanged", warnings=cleanup_warnings)

        return StepResult("unchanged", warnings=cleanup_warnings)


class PacmanModule(BaseModule):
    name = "System"
    key = "pacman"
    aliases = ["arch", "aur", "yay", "paru", "system"]
    category = "System Core"
    description = "Updates system and AUR packages via Pacman / Yay / Paru"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("pacman") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        aur_helper = None
        for candidate in ["yay", "paru"]:
            if ctx.which(candidate):
                aur_helper = candidate
                break

        cmd = [
            aur_helper or "sudo",
            "pacman" if not aur_helper else aur_helper,
            "-Syu",
            "--noconfirm",
        ]
        if aur_helper:
            cmd = [aur_helper, "-Syu", "--noconfirm"]
        else:
            cmd = ["sudo", "pacman", "-Syu", "--noconfirm"]

        code, out, err = ctx.run_cmd(cmd, timeout=600)
        if code != 0:
            return StepResult(
                "error",
                f"{aur_helper or 'pacman'} upgrade failed",
                error_output=err or out,
            )

        if "there is nothing to do" in out.lower():
            return StepResult("unchanged")

        # Parse upgraded packages from pacman output
        # Matches: "upgrading foo (1.0 -> 2.0)" or "installing bar (1.0 -> 2.0)"
        upgraded = []
        for line in out.splitlines():
            m = re.search(
                r"(?:upgrading|installing)\s+([\w\.\-_]+)\s+\([^)]*->\s*([^)]+)\)", line
            )
            if m:
                upgraded.append(f"{m.group(1)} -> {m.group(2)}")

        upgraded = list(dict.fromkeys(upgraded))
        if upgraded:
            count = len(upgraded)
            return StepResult(
                "ok",
                f"{count} package{'s' if count != 1 else ''} upgraded",
                details=upgraded,
            )

        return StepResult("ok", "System packages upgraded")


class ZypperModule(BaseModule):
    name = "System"
    key = "zypper"
    aliases = ["suse", "opensuse", "system"]
    category = "System Core"
    description = "Updates system packages via Zypper"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("zypper") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        os_info = get_os_release()
        is_tumbleweed = (
            "tumbleweed" in os_info.get("ID", "").lower()
            or "tumbleweed" in os_info.get("PRETTY_NAME", "").lower()
        )
        subcmd = "dup" if is_tumbleweed else "update"

        # Do not proceed with stale repository metadata if refresh fails.
        refresh_code, refresh_out, refresh_err = ctx.run_cmd(
            ["sudo", "zypper", "--non-interactive", "refresh"], timeout=180
        )
        if refresh_code != 0:
            return StepResult(
                "error",
                "zypper repository refresh failed",
                error_output=refresh_err or refresh_out,
            )

        code, out, err = ctx.run_cmd(
            [
                "sudo",
                "zypper",
                "--non-interactive",
                subcmd,
                "--auto-agree-with-licenses",
            ],
            timeout=600,
        )

        if code != 0:
            return StepResult(
                "error", f"zypper {subcmd} failed", error_output=err or out
            )

        if "Nothing to do" in out or "No updates found" in out:
            return StepResult("unchanged")

        upgraded = []
        for line in out.splitlines():
            # Matches: "Installing: foo-1.2.3" or "Upgrading: bar-2.3.4"
            m = re.search(
                r"(?:Installing|Upgrading):\s+([\w\.\-_]+)-([0-9][\w\.\-_]*)", line
            )
            if m:
                upgraded.append(f"{m.group(1)} -> {m.group(2)}")

        upgraded = list(dict.fromkeys(upgraded))
        if upgraded:
            count = len(upgraded)
            return StepResult(
                "ok",
                f"{count} package{'s' if count != 1 else ''} upgraded",
                details=upgraded,
            )

        return StepResult("ok", "System packages upgraded")


class ApkModule(BaseModule):
    name = "System"
    key = "apk"
    aliases = ["alpine", "system"]
    category = "System Core"
    description = "Updates system packages via APK"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("apk") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(
            ["sudo", "apk", "upgrade", "--update"], timeout=300
        )
        if code != 0:
            return StepResult("error", "apk upgrade failed", error_output=err or out)

        if "OK:" in out and "Upgrading" not in out:
            return StepResult("unchanged")

        upgraded = []
        for line in out.splitlines():
            # Matches: "(1/5) Upgrading foo (1.0 -> 2.0)"
            m = re.search(r"Upgrading\s+([\w\.\-_]+)\s+\([^)]*->\s*([^)]+)\)", line)
            if m:
                upgraded.append(f"{m.group(1)} -> {m.group(2)}")

        upgraded = list(dict.fromkeys(upgraded))
        if upgraded:
            count = len(upgraded)
            return StepResult(
                "ok",
                f"{count} package{'s' if count != 1 else ''} upgraded",
                details=upgraded,
            )

        return StepResult("unchanged")


class XbpsModule(BaseModule):
    name = "System"
    key = "xbps"
    aliases = ["void", "system"]
    category = "System Core"
    description = "Updates system packages via XBPS"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("xbps-install") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(
            ["sudo", "xbps-install", "-Syu", "-y"], timeout=600
        )
        if code != 0:
            return StepResult("error", "xbps-install failed", error_output=err or out)

        if "0 to update" in out or "up to date" in out.lower():
            return StepResult("unchanged")

        upgraded = []
        for line in out.splitlines():
            # Matches: "foo-1.0_1: updating to 2.0_1 ..."
            m = re.search(r"([\w\.\-_]+)-[0-9].*:\s+updating to\s+([\w\.\-_]+)", line)
            if m:
                upgraded.append(f"{m.group(1)} -> {m.group(2)}")

        upgraded = list(dict.fromkeys(upgraded))
        if upgraded:
            count = len(upgraded)
            return StepResult(
                "ok",
                f"{count} package{'s' if count != 1 else ''} upgraded",
                details=upgraded,
            )

        return StepResult("ok", "System packages upgraded")
