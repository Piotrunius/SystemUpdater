"""
Reboot detection, package importance scoring, and package list formatting for SystemUpdater.
"""

from __future__ import annotations

import contextlib
import os
import re
import sys
from typing import Any

REBOOT_TRIGGER_PATTERNS = re.compile(
    r"(^|[\-_])(kernel|linux|systemd|glibc|libc6|musl|grub|shim|nvidia|microcode|ucode|firmware|dbus|kmod|akmod|dracut)([\-_]|$)",
    re.IGNORECASE,
)

CORE_SYSTEM_KEYWORDS = {
    "kernel",
    "linux",
    "systemd",
    "glibc",
    "libc6",
    "musl",
    "grub",
    "shim",
    "mesa",
    "nvidia",
    "xorg",
    "wayland",
    "pipewire",
    "wireplumber",
    "openssl",
    "ca-certificates",
    "networkmanager",
    "firewalld",
    "systemupdater",
    "sudo",
    "openssh",
    "ssh",
    "dbus",
    "polkit",
    "pam",
    "microcode",
    "ucode",
    "dracut",
    "kmod",
    "akmod",
    "nobara",
}

DEV_TOOLS_KEYWORDS = {
    "python",
    "python3",
    "node",
    "nodejs",
    "rust",
    "rustc",
    "gcc",
    "llvm",
    "clang",
    "golang",
    "ruby",
    "bun",
    "deno",
    "git",
    "docker",
    "containerd",
    "podman",
    "moby",
    "runc",
    "antigravity",
    "ripgrep",
    "tmux",
    "zsh",
    "bash",
    "fish",
    "curl",
    "wget",
    "wget2",
    "cursor",
    "neovim",
    "nvim",
    "helix",
    "vim",
    "fzf",
    "bat",
    "eza",
    "jq",
    "yq",
    "socat",
    "rsync",
    "7zip",
    "brave",
    "firefox",
    "chrome",
}

EXACT_SHORT_KEYWORDS = {"go", "gh", "code", "tar"}


def extract_package_name(item: str) -> str:
    clean = str(item).strip()
    if ":" in clean:
        clean = clean.split(":", 1)[0].strip()
    if "->" in clean:
        clean = clean.split("->", 1)[0].strip()
    if "(" in clean:
        clean = clean.split("(", 1)[0].strip()
    parts = clean.split()
    if len(parts) > 1 and any(c.isdigit() for c in parts[-1]):
        clean = " ".join(parts[:-1]).strip()
    return clean


def check_packages_require_reboot(
    package_lines: list[str],
) -> tuple[bool, str | None]:
    """Check if any package in the upgraded list requires a system reboot."""
    for line in package_lines:
        clean = str(line).strip()
        name = clean.split(":")[0].split("->")[0].split()[0].lower().strip()
        short_name = name.split("/")[-1].split("@")[0]
        if REBOOT_TRIGGER_PATTERNS.search(name) or REBOOT_TRIGGER_PATTERNS.search(
            short_name
        ):
            return True, name
    return False, None


def get_reboot_trigger_packages(package_lines: list[str]) -> list[str]:
    """Return all package lines that triggered a reboot requirement."""
    matched: list[str] = []
    seen: set[str] = set()
    for line in package_lines:
        clean = str(line).strip()
        if not clean or clean.startswith(("... and ", "... ", "and ", "(+")):
            continue
        pkg_name = extract_package_name(clean)
        name = pkg_name.lower()
        short_name = name.split("/")[-1].split("@")[0]
        if (
            REBOOT_TRIGGER_PATTERNS.search(name)
            or REBOOT_TRIGGER_PATTERNS.search(short_name)
        ) and pkg_name not in seen:
            seen.add(pkg_name)
            matched.append(pkg_name)
    return matched


def is_reboot_eligible_module(module: Any) -> bool:
    """Return True if the module is capable of requiring a host machine reboot."""
    if module is None:
        return True

    if getattr(module, "can_trigger_reboot", False):
        return True
    if isinstance(module, dict) and module.get("can_trigger_reboot"):
        return True

    cat = (
        str(
            getattr(module, "category", "")
            or (module.get("category", "") if isinstance(module, dict) else "")
        )
        .strip()
        .lower()
    )
    key = (
        str(
            getattr(module, "key", "")
            or (module.get("key", "") if isinstance(module, dict) else "")
        )
        .strip()
        .lower()
    )

    non_system_categories = {
        "containers & packages",
        "applications & gaming",
        "development environment",
        "shell & dotfiles",
        "system protection",
        "app store",
    }
    if cat in non_system_categories:
        return False

    if cat in ("system core", "firmware"):
        return True
    return key in (
        "system",
        "apt",
        "pacman",
        "zypper",
        "apk",
        "xbps",
        "ostree",
        "bootc",
        "macos",
        "firmware",
    )


def check_system_reboot_required(
    ctx: Any | None = None,
    upgraded_packages: list[str] | None = None,
    module: Any | None = None,
) -> tuple[bool, str | None]:
    """
    Dynamically detect whether the host operating system requires a reboot.
    Combines filesystem markers, running kernel state verification,
    and package pattern fallbacks.
    """
    for marker_path in (
        "/run/reboot-required",
        "/var/run/reboot-required",
        "/run/reboot-needed",
        "/var/run/reboot-needed",
    ):
        if os.path.exists(marker_path):
            return True, f"marker file {marker_path} present"

    if sys.platform.startswith("linux") and hasattr(os, "uname"):
        try:
            running_release = os.uname().release
            modules_dir = f"/lib/modules/{running_release}"
            if os.path.isdir("/lib/modules") and not os.path.exists(modules_dir):
                return True, f"running kernel {running_release} modules removed"
        except OSError:
            pass

    if upgraded_packages:
        needed, pkg = check_packages_require_reboot(upgraded_packages)
        if needed:
            return True, f"core package updated ({pkg})"

    return False, None


def package_importance_score(pkg_line: str) -> int:
    clean = pkg_line.strip()
    name = clean.split(":")[0].split("->")[0].split()[0].lower().strip()
    short_name = name.split("/")[-1].split("@")[0]
    tokens = set(re.split(r"[-_.]", short_name))

    is_selinux = (
        "selinux" in tokens
        or short_name.endswith("-selinux")
        or short_name.startswith("selinux-")
    )
    is_sub_firmware = short_name.endswith("-firmware") and short_name not in (
        "linux-firmware",
        "nvidia-gpu-firmware",
        "amd-gpu-firmware",
        "intel-gpu-firmware",
    )

    score = 50
    matched_core = False
    for kw in CORE_SYSTEM_KEYWORDS:
        if kw == "linux" and is_selinux:
            continue
        if kw in tokens or (len(kw) >= 5 and (kw in short_name or kw in name)):
            score = 100
            matched_core = True
            break

    if not matched_core:
        if short_name.endswith("-firmware") or "firmware" in tokens:
            score = 75
        else:
            for kw in DEV_TOOLS_KEYWORDS:
                if kw in tokens or (len(kw) >= 5 and (kw in short_name or kw in name)):
                    score = 80
                    break
            else:
                if any(kw in tokens for kw in EXACT_SHORT_KEYWORDS):
                    score = 80

    if is_selinux:
        score = min(score, 60)
    elif is_sub_firmware:
        score = min(score, 70)

    if short_name.endswith(
        (
            "-server",
            "-client",
            "-clients",
            "-askpass",
            "-whence",
            "-plugin",
            "-plugins",
        )
    ):
        score = max(10, score - 5)

    if (
        short_name.startswith(("lib", "@types/"))
        or short_name.endswith(
            (
                "-devel",
                "-headers",
                "-libs",
                "-common",
                "-static",
                "-matched",
                "-tools",
                "-doc",
                "-dbg",
                "-debuginfo",
                "-filesystem",
                "-macros",
                "-qt",
                "-qt5",
                "-qt6",
                "-gtk",
                "-gtk3",
                "-gtk4",
            )
        )
        or "-plugins-" in short_name
        or "-plugin-" in short_name
    ):
        score = max(10, score - 20)

    return score


def format_package_list(
    details: list[str], msg_text: str = "", limit: int = 10
) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in details:
        line = str(item).strip()
        if not line or line.startswith(("... and ", "... ", "and ", "(+")):
            continue
        pkg_name = extract_package_name(line)
        if pkg_name and pkg_name not in seen:
            seen.add(pkg_name)
            cleaned.append(pkg_name)

    total = len(cleaned)
    if total == 0:
        return []

    sorted_items = sorted(cleaned, key=package_importance_score, reverse=True)

    if total <= limit:
        return sorted_items

    displayed = sorted_items[:limit]
    remaining = total - limit
    pkg_word = "package" if remaining == 1 else "packages"
    remainder_line = f"(+{remaining} more {pkg_word})"
    return displayed + [remainder_line]


def format_package_list_inline(details: list[str], limit: int = 5) -> str:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in details:
        line = str(item).strip()
        if not line or line.startswith(("... and ", "... ", "and ", "(+")):
            continue
        pkg_name = extract_package_name(line)
        if pkg_name and pkg_name not in seen:
            seen.add(pkg_name)
            cleaned.append(pkg_name)

    total = len(cleaned)
    if total == 0:
        return ""

    sorted_items = sorted(cleaned, key=package_importance_score, reverse=True)

    if total <= limit:
        return ", ".join(sorted_items)

    displayed = sorted_items[:limit]
    remaining = total - limit
    pkg_word = "package" if remaining == 1 else "packages"
    remainder_line = f"(+{remaining} more {pkg_word})"
    return ", ".join(displayed + [remainder_line])


def get_reboot_trigger_details(item: dict[str, Any]) -> list[str]:
    """Return the list of packages or reasons triggering a reboot for a module."""
    res = item.get("result")
    if not res or not getattr(res, "reboot_required", False):
        return []

    triggers = get_reboot_trigger_packages(res.details)
    if triggers:
        return triggers

    if os.path.exists("/run/reboot-required.pkgs"):
        with (
            contextlib.suppress(OSError),
            open("/run/reboot-required.pkgs", encoding="utf-8") as f,
        ):
            pkgs = [line.strip() for line in f if line.strip()]
            if pkgs:
                return pkgs

    mod_key = str(item.get("key") or getattr(item.get("module"), "key", "")).lower()
    if mod_key in (
        "firmware",
        "device_firmware",
        "macos",
        "macos_update",
        "system",
        "ostree",
        "bootc",
    ):
        valid: list[str] = []
        seen: set[str] = set()
        for d in res.details:
            s = str(d).strip()
            if not s or s.startswith(("... and ", "... ", "and ", "(+")):
                continue
            name = extract_package_name(s)
            if name and name not in seen:
                seen.add(name)
                valid.append(name)
        if valid:
            return valid

    return []
