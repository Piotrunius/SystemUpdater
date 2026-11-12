#!/usr/bin/env python3
"""
SystemUpdater - Web Metadata Generator
Extracts module definitions, categories, and CLI configuration from the Python codebase
into a structured JSON file consumed by the Next.js web application.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# Ensure repository root is in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from config import Config
from modules import get_all_modules

# In the CLI TUI, system package managers all use name="System" so the terminal summary
# displays a standardized "[-] System: up to date". On the website, we give them distinct names.
SYSTEM_PM_NAMES = {
    "system": "DNF / RPM",
    "apt": "APT",
    "pacman": "Pacman & AUR",
    "zypper": "Zypper",
    "apk": "APK",
    "xbps": "XBPS",
    "macos": "macOS Software Update",
    "reposync": "Nobara Repositories",
    "snapshot": "Snapper Btrfs Snapshots",
}
MACOS_ONLY_KEYS = {"macos", "mas"}
LINUX_ONLY_KEYS = {
    "reposync",
    "system",
    "apt",
    "pacman",
    "zypper",
    "apk",
    "xbps",
    "snapshot",
    "firmware",
    "flatpak",
    "distrobox",
    "gearlever",
    "proton",
    "nuvio",
    "snap",
}


def get_platform(key: str) -> str:
    if key in MACOS_ONLY_KEYS:
        return "macos"
    if key in LINUX_ONLY_KEYS:
        return "linux"
    return "universal"


def export_metadata(output_path: str | None = None) -> dict[str, Any]:
    cfg = Config()
    modules = get_all_modules(cfg)

    # Filter out empty custom command placeholders if any
    filtered_modules = [
        m
        for m in modules
        if not m.key.startswith("cmd_")
        and not m.key.startswith("pre_")
        and not m.key.startswith("post_")
    ]

    module_data: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for m in filtered_modules:
        if m.key in seen_keys:
            continue
        seen_keys.add(m.key)

        module_data.append(
            {
                "key": m.key,
                "name": SYSTEM_PM_NAMES.get(m.key, m.name),
                "aliases": list(getattr(m, "aliases", []) or []),
                "category": m.category,
                "description": getattr(m, "description", "").strip(),
                "requires_sudo": bool(getattr(m, "requires_sudo", False)),
                "unit_name": getattr(m, "unit_name", "package"),
                "unit_name_plural": getattr(m, "unit_name_plural", "packages"),
                "platform": get_platform(m.key),
            }
        )

    categories = sorted({m["category"] for m in module_data})

    cli_flags = [
        {
            "flags": ["--help", "-h"],
            "description": "Show help message and exit",
            "category": "General",
        },
        {
            "flags": ["--version"],
            "description": "Show installed version and check for latest available release",
            "category": "General",
        },
        {
            "flags": ["-q", "--quiet"],
            "description": "Suppress live step progress; show only final summary and errors",
            "category": "Output",
        },
        {
            "flags": ["-v", "--verbose"],
            "description": "Stream update command output live; keep internal probes quiet",
            "category": "Output",
        },
        {
            "flags": ["--notify"],
            "description": "Send native desktop notification on completion (Linux notify-send / macOS osascript)",
            "category": "Execution",
        },
        {
            "flags": ["--no-sudo"],
            "description": "Skip all modules requiring administrator (sudo) privileges",
            "category": "Execution",
        },
        {
            "flags": ["--no-snapshot"],
            "description": "Skip protective Btrfs snapshot creation before update",
            "category": "Protection",
        },
        {
            "flags": ["-f", "--force"],
            "description": "Force execution (e.g. bypass Btrfs snapshot cooldown)",
            "category": "Protection",
        },
        {
            "flags": ["--only <modules>"],
            "description": "Comma-separated module keys or aliases to run (e.g. 'dnf,brew')",
            "category": "Filtering",
        },
        {
            "flags": ["--skip <modules>"],
            "description": "Comma-separated module keys to skip",
            "category": "Filtering",
        },
        {
            "flags": ["-c", "--category <names>"],
            "description": "Comma-separated categories to run (e.g. 'system', 'dev')",
            "category": "Filtering",
        },
        {
            "flags": ["-l", "--list"],
            "description": "List all registered modules and check their system availability",
            "category": "Discovery",
        },
        {
            "flags": ["--history [COUNT]"],
            "description": "List recent update runs (default: 10, maximum: 30)",
            "category": "History",
        },
        {
            "flags": ["--show-log <ID>"],
            "description": "Show saved command output for a run listed by --history",
            "category": "History",
        },
        {
            "flags": ["--no-history"],
            "description": "Do not record this run or its command logs in history",
            "category": "History",
        },
        {
            "flags": ["-r", "--reboot"],
            "description": "Reboot system after update if required by kernel or firmware",
            "category": "Execution",
        },
        {
            "flags": ["--generate-completion [SHELL]"],
            "description": "Install shell completions for bash, zsh, or fish",
            "category": "General",
        },
        {
            "flags": ["--edit-config"],
            "description": "Open configuration file in $EDITOR",
            "category": "Configuration",
        },
        {
            "flags": ["--config <PATH>"],
            "description": "Path to custom configuration TOML file",
            "category": "Configuration",
        },
    ]

    data = {
        "generated_at_comment": "Auto-generated by scripts/export_metadata.py. Do not edit manually.",
        "modules": module_data,
        "categories": categories,
        "cli_flags": cli_flags,
    }

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Exported {len(module_data)} modules and metadata to {output_path}")

    return data


if __name__ == "__main__":
    out = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.join(REPO_ROOT, "web", "src", "data", "generated-metadata.json")
    )
    export_metadata(out)
