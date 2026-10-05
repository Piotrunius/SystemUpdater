#!/usr/bin/env python3
"""
SystemUpdater - Unified, resilient, and standardized system update engine.
Crafted for Nobara Linux with modular architecture and flicker-free TUI.
"""

import argparse
import os
import signal
import sys
import time
from typing import List

# Ensure script directory is in sys.path
import shutil
import subprocess
import time
from typing import List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from modules.base import UpdateContext, BaseModule
from modules import get_all_modules
from ui import UI, StepResult
from config import get_config, DEFAULT_CONFIG_PATH
import sudo

def get_version():
    """Return version string, trying to include git commit/tag."""
    base = "1.0.0"
    try:
        # Try to get short commit hash
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=1,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
            # Try to get tag if available
            tag_result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                cwd=SCRIPT_DIR,
                capture_output=True,
                text=True,
                timeout=1,
            )
            if tag_result.returncode == 0:
                tag = tag_result.stdout.strip()
                # If tag contains commit (describe), use it, else combine
                if tag.startswith("v") or "-" in tag:
                    return tag
                return f"{base}-{commit}"
            return f"{base}-{commit}"
    except Exception:
        pass
    return base


VERSION = get_version()


def edit_config(config_path: str):
    expanded = os.path.expanduser(config_path)
    os.makedirs(os.path.dirname(expanded), exist_ok=True)
    if not os.path.exists(expanded):
        example_path = os.path.join(SCRIPT_DIR, "config.example.toml")
        if os.path.exists(example_path):
            shutil.copy(example_path, expanded)
        else:
            with open(expanded, "w") as f:
                f.write("# ~/.config/sysupdate/config.toml\n")

    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        for candidate in ["micro", "nano", "vim", "vi"]:
            if shutil.which(candidate):
                editor = candidate
                break
    if not editor:
        editor = "nano"

    subprocess.run([editor, expanded])
    sys.exit(0)


def parse_args():
    prog_name = "sysupdate"
    if sys.argv and sys.argv[0]:
        base = os.path.basename(sys.argv[0])
        if not base.endswith(".py"):
            prog_name = base

    parser = argparse.ArgumentParser(
        prog=prog_name,
        description="Unified System Updater for Linux (Fedora, Nobara, Debian, Ubuntu, Arch, openSUSE), Flatpaks, Homebrew, Containers, and Runtimes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  {prog_name}                 Run complete system update
  {prog_name} --dry-run       Simulate updates without making changes
  {prog_name} --only dnf,brew Update only DNF and Homebrew packages
  {prog_name} --category dev  Update all development environment tools
  {prog_name} --no-sudo       Run only unprivileged updates without sudo
  {prog_name} --skip docker   Run everything except Docker containers
  {prog_name} --edit-config   Open configuration file in $EDITOR
  {prog_name} --list          List all supported modules and system availability
""",
    )

    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Simulate update process without downloading or installing changes",
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force execution (e.g. bypass Btrfs snapshot cooldown)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress live step progress, display only the final summary and errors",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable detailed logging output with live command streaming",
    )
    parser.add_argument(
        "--only",
        type=str,
        help="Comma-separated list of module keys or aliases to run (e.g. 'dnf,flatpak,brew')",
    )
    parser.add_argument(
        "--skip",
        type=str,
        help="Comma-separated list of module keys to skip",
    )
    parser.add_argument(
        "-C", "--category",
        type=str,
        help="Comma-separated list of categories to run (e.g. 'system', 'containers', 'dev', 'gaming')",
    )
    parser.add_argument(
        "--no-sudo",
        action="store_true",
        help="Skip all modules requiring administrator (sudo) privileges",
    )
    parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Skip protective Btrfs snapshot",
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        help="Path to custom configuration TOML file",
    )
    parser.add_argument(
        "--edit-config",
        action="store_true",
        help="Open configuration file in $EDITOR",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all registered modules and check their availability",
    )

    return parser.parse_args()


def handle_interrupt(signum, frame):
    sudo.stop_sudo_keeper()
    print("\n\nUpdate cancelled by user.")
    sys.exit(130)


def main():
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    args = parse_args()

    if args.edit_config:
        edit_config(args.config or DEFAULT_CONFIG_PATH)

    ctx = UpdateContext(dry_run=args.dry_run, force=args.force, verbose=args.verbose)
    all_modules: List[BaseModule] = get_all_modules()

    cfg = get_config(config_path=args.config)

    # List modules mode
    if args.list:
        print("\nRegistered Update Modules:")
        print(f"{'Key':<14} {'Name':<28} {'Status':<16} {'Description'}")
        print("─" * 85)
        for m in all_modules:
            status = m.availability_status(ctx)
            print(f"{m.key:<14} {m.name:<28} {status:<16} {m.description}")
        print()
        sys.exit(0)

    # Filter modules
    selected_keys = [k.strip().lower() for k in args.only.split(",")] if args.only else None
    skip_keys = [k.strip().lower() for k in args.skip.split(",")] if args.skip else []
    selected_categories = [c.strip().lower() for c in args.category.split(",")] if args.category else None

    if args.no_snapshot:
        skip_keys.append("snapshot")

    modules_to_run: List[BaseModule] = []
    for m in all_modules:
        m_identifiers = {m.key.lower(), *(a.lower() for a in getattr(m, "aliases", []))}
        if selected_keys and not (m_identifiers & set(selected_keys)):
            continue
        if selected_categories:
            cat_lower = getattr(m, "category", "").lower()
            if not any(sc in cat_lower for sc in selected_categories):
                continue
        if args.no_sudo and getattr(m, "requires_sudo", False):
            continue
        if (m_identifiers & set(skip_keys)) or (m_identifiers & cfg.disabled_keys):
            continue
        if m.is_available(ctx):
            modules_to_run.append(m)

    if not modules_to_run:
        print("No matching or available modules selected to run.")
        sys.exit(0)

    # Check if any selected module requires sudo upfront
    needs_sudo = any(getattr(m, "requires_sudo", False) for m in modules_to_run)
    if needs_sudo and not args.dry_run:
        if not sudo.init_sudo(interactive=sys.stdin.isatty()):
            print("Error: Administrator privileges (sudo) required but could not be obtained.")
            sys.exit(1)

    ui = UI(quiet=args.quiet)
    ui.print_header("System Updater")

    results = []
    total_start = time.time()
    current_category = None

    try:
        for m in modules_to_run:
            if m.category != current_category:
                current_category = m.category
                ui.print_category(current_category)
            step_res = ui.run_step(m.name, lambda mod=m: mod.run(ctx), ctx=ctx, module=m)
            results.append({"name": m.name, "key": m.key, "result": step_res})
    finally:
        sudo.stop_sudo_keeper()

    total_elapsed = time.time() - total_start
    ui.print_summary(results, total_elapsed)

    has_failures = any(r["result"].status == "error" for r in results)
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    main()
