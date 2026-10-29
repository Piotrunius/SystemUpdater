#!/usr/bin/env python3
"""
SystemUpdater - Unified, resilient, and standardized system update engine.
Crafted for Nobara Linux with modular architecture and flicker-free TUI.
"""

import argparse
import contextlib
import json
import os
import platform
import re
import shlex

# Ensure script directory is in sys.path
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
SELF_UPDATE_REPOSITORY = "https://github.com/Piotrunius/SystemUpdater.git"
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import sudo
from completions import (
    generate_bash_completion,
    generate_fish_completion,
    generate_zsh_completion,
)
from config import DEFAULT_CONFIG_PATH, get_config
from history_store import (
    HistoryStore,
    classify_run_status,
    print_history,
    print_run_log,
    redact_text,
)
from modules import get_all_modules
from modules.base import BaseModule, UpdateContext
from notifications import send_notification
from ui import UI, StepResult, suppress_terminal_echo


def git_output(*args, timeout=3):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=SCRIPT_DIR,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def get_version():
    """Use the nearest release tag and exact source commit as the version."""
    if is_homebrew_install():
        try:
            with open(
                os.path.join(SCRIPT_DIR, "VERSION"), encoding="utf-8"
            ) as version_file:
                return version_file.read().strip() or "unknown"
        except OSError:
            return "unknown"

    commit = git_output("rev-parse", "--short=12", "HEAD")
    if not commit:
        return "unknown"
    description = git_output("describe", "--tags", "--long", "--always")
    if description:
        parts = description.rsplit("-", 2)
        if len(parts) == 3 and parts[1].isdigit():
            return (
                f"{parts[0]}+{commit}"
                if parts[1] == "0"
                else f"{parts[0]}+{parts[1]}.g{commit}"
            )
    return commit


def is_homebrew_install():
    """Detect a Homebrew-managed installation created by its formula."""
    return os.path.isfile(os.path.join(SCRIPT_DIR, ".homebrew-install"))


def latest_homebrew_version():
    """Read the current formula version directly from the Homebrew tap repository."""
    url = "https://raw.githubusercontent.com/Piotrunius/homebrew-tap/main/Formula/systemupdater.rb"
    request = urllib.request.Request(url, headers={"User-Agent": "SystemUpdater"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            formula = response.read().decode("utf-8")
        match = re.search(r'(?m)^\s*version\s+["\']([^"\']+)["\']\s*$', formula)
        return match.group(1) if match else None
    except (OSError, TimeoutError, urllib.error.URLError, UnicodeDecodeError):
        return None


def latest_remote_commit():
    """Return the upstream branch commit, if the repository has a configured upstream."""
    upstream = git_output(
        "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
    )
    if not upstream or "/" not in upstream:
        return None
    remote, branch = upstream.split("/", 1)
    result = git_output("ls-remote", remote, f"refs/heads/{branch}", timeout=8)
    if result:
        return result.split()[0][:12]
    return None


def latest_upstream_version():
    """Read the latest release version from GitHub releases or the Homebrew formula."""
    url = "https://api.github.com/repos/Piotrunius/SystemUpdater/releases/latest"
    request = urllib.request.Request(url, headers={"User-Agent": "SystemUpdater"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            tag = data.get("tag_name")
            if tag:
                return tag.lstrip("v").strip()
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return latest_homebrew_version()
    return latest_homebrew_version()


def parse_semver(v: str | None) -> tuple[int, int, int]:
    if not v:
        return (0, 0, 0)
    clean = str(v).lstrip("v").strip()
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", clean)
    if match:
        return tuple(map(int, match.groups()))
    return (0, 0, 0)


class VersionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if is_homebrew_install():
            current = get_version()
        else:
            tag = git_output("describe", "--tags", "--abbrev=0")
            current = tag.lstrip("v").strip() if tag else get_version()

        latest = (
            latest_homebrew_version()
            if is_homebrew_install()
            else latest_upstream_version()
        )
        ui = UI()
        ui.print_header("System Updater")
        ui.print_category("Version")
        ui.print_result(
            "Installed version",
            StepResult("unchanged", current),
            show_duration=False,
        )
        if latest:
            ui.print_result(
                "Latest version",
                StepResult("unchanged", latest),
                show_duration=False,
            )
            is_up_to_date = parse_semver(current) >= parse_semver(latest)
            status_text = "up to date" if is_up_to_date else "update available"
            ui.print_result(
                "Status",
                StepResult("unchanged", status_text),
                show_duration=False,
            )
        else:
            ui.print_result(
                "Latest version",
                StepResult("unchanged", "check unavailable"),
                show_duration=False,
            )
        parser.exit()


def self_update():
    """Fast-forward a clean checkout and restart using the updated source."""
    started = time.monotonic()

    if is_homebrew_install():
        return None

    def result(status, message, details=None):
        return status, message, max(0.1, time.monotonic() - started), details or []

    updated_version = os.environ.pop("SYSUPDATE_UPDATED_VERSION", None)
    if updated_version:
        duration = float(os.environ.pop("SYSUPDATE_UPDATE_DURATION", "0.1"))
        old_version = os.environ.pop("SYSUPDATE_OLD_VERSION", None)
        details = (
            [f"{old_version} -> {updated_version}"]
            if old_version and old_version != updated_version
            else [updated_version]
        )
        return "ok", "updated", duration, details
    if not git_output("rev-parse", "--is-inside-work-tree"):
        return result("skipped", "not a Git checkout")
    if git_output("status", "--porcelain", timeout=5):
        return result(
            "warning",
            "Update skipped because local changes were detected.",
        )
    upstream = git_output(
        "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
    )
    remote_names = (git_output("remote", timeout=5) or "").splitlines()
    current_branch = git_output("symbolic-ref", "--quiet", "--short", "HEAD")

    if upstream and "/" in upstream:
        remote, branch = upstream.split("/", 1)
        update_ref = upstream
        fetch_refspec = f"+refs/heads/{branch}:refs/remotes/{remote}/{branch}"
    elif "origin" in remote_names:
        remote = "origin"
        default_branch = git_output(
            "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"
        )
        if default_branch:
            branch = default_branch.removeprefix("origin/")
        else:
            remote_head = git_output("ls-remote", "--symref", remote, "HEAD", timeout=8)
            branch = next(
                (
                    line.split("refs/heads/", 1)[1].split("\t", 1)[0]
                    for line in (remote_head or "").splitlines()
                    if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD")
                ),
                current_branch or "main",
            )
        update_ref = f"refs/remotes/{remote}/{branch}"
        fetch_refspec = f"+refs/heads/{branch}:refs/remotes/{remote}/{branch}"
    else:
        remote = SELF_UPDATE_REPOSITORY
        branch = current_branch or "main"
        update_ref = "FETCH_HEAD"
        fetch_refspec = branch

    try:
        fetched = subprocess.run(
            ["git", "fetch", "--quiet", remote, fetch_refspec],
            cwd=SCRIPT_DIR,
            check=False,
            capture_output=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return result(
            "warning",
            "update skipped",
            ["The upstream could not be reached to check for updates."],
        )
    if fetched.returncode != 0:
        return result(
            "warning",
            "update skipped",
            ["The upstream could not be reached to check for updates."],
        )
    behind = git_output("rev-list", "--count", f"HEAD..{update_ref}")
    if not behind or behind == "0":
        return result("unchanged", "up to date")
    old_version = get_version()
    try:
        merged = subprocess.run(
            ["git", "merge", "--ff-only", "--quiet", update_ref],
            cwd=SCRIPT_DIR,
            check=False,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return result("warning", "update skipped", ["The fast-forward update failed."])
    if merged.returncode != 0:
        return result(
            "warning",
            "update skipped",
            ["The local branch cannot be updated with a fast-forward."],
        )
    os.environ["SYSUPDATE_OLD_VERSION"] = old_version
    os.environ["SYSUPDATE_UPDATED_VERSION"] = get_version()
    os.environ["SYSUPDATE_UPDATE_DURATION"] = str(max(0.1, time.monotonic() - started))
    os.execv(
        sys.executable,
        [sys.executable, os.path.join(SCRIPT_DIR, "main.py"), *sys.argv[1:]],
    )


def edit_config(config_path: str):
    expanded = os.path.abspath(os.path.expanduser(config_path))
    os.makedirs(os.path.dirname(expanded), exist_ok=True)
    if not os.path.exists(expanded):
        example_path = os.path.join(SCRIPT_DIR, "config.example.toml")
        if os.path.exists(example_path):
            shutil.copy(example_path, expanded)
        else:
            with open(expanded, "w") as f:
                f.write("# SystemUpdater configuration\n")

    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        for candidate in ["micro", "nano", "vim", "vi"]:
            if shutil.which(candidate):
                editor = candidate
                break
    if not editor:
        editor = "nano"

    try:
        editor_command = shlex.split(editor)
    except ValueError as error:
        print(f"Error: Invalid editor command: {error}", file=sys.stderr)
        sys.exit(2)
    if not editor_command:
        print("Error: Editor command is empty.", file=sys.stderr)
        sys.exit(2)

    try:
        result = subprocess.run([*editor_command, expanded], check=False)
    except OSError as error:
        print(f"Error: Could not start editor: {error}", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        sys.exit(result.returncode)
    sys.exit(0)


def parse_args():
    prog_name = "sysupdate"
    if sys.argv and sys.argv[0]:
        base = os.path.basename(sys.argv[0])
        if not base.endswith(".py"):
            prog_name = base

    parser = argparse.ArgumentParser(
        prog=prog_name,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  {prog_name}                 Run complete system update
  {prog_name} --only dnf,brew Update only DNF and Homebrew packages
  {prog_name} --category dev  Update all development environment tools
  {prog_name} --no-sudo       Run only unprivileged updates without sudo
  {prog_name} --skip docker   Run everything except Docker containers
  {prog_name} --edit-config   Open configuration file in $EDITOR
  {prog_name} --list          List all supported modules and system availability
  {prog_name} --history       List recent update runs
  {prog_name} --show-log ID   Show a saved update run
  {prog_name} --reboot        Reboot system after update if required by kernel or firmware
""",
    )

    parser.add_argument(
        "--version",
        action=VersionAction,
        nargs=0,
        help="Show installed version and latest available version",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force execution (e.g. bypass Btrfs snapshot cooldown)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress live step progress, display only the final summary and errors",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Stream update command output live; keep internal probes quiet",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send a desktop notification on completion",
    )
    parser.add_argument(
        "--generate-completion",
        "--generate-completions",
        choices=["bash", "zsh", "fish"],
        metavar="SHELL",
        dest="generate_completion",
        help="Generate shell completion script (bash, zsh, fish)",
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
        "-c",
        "--category",
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
        "--config",
        type=str,
        metavar="PATH",
        help="Path to custom configuration TOML file",
    )
    parser.add_argument(
        "--edit-config",
        action="store_true",
        help="Open configuration file in $EDITOR",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all registered modules and check their availability",
    )
    parser.add_argument(
        "-r",
        "--reboot",
        action="store_true",
        help="Reboot the system after updates if required by any module (e.g. kernel, systemd, firmware)",
    )
    history_group = parser.add_mutually_exclusive_group()
    history_group.add_argument(
        "--history",
        nargs="?",
        const=10,
        type=int,
        metavar="COUNT",
        help="List the most recent update runs (default: 10, maximum: 30)",
    )
    history_group.add_argument(
        "--show-log",
        metavar="RUN_ID",
        help="Show the saved command output for a run listed by --history",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Do not record this run or its command logs in history",
    )

    return parser.parse_args()


def handle_sigterm(signum, frame):
    raise KeyboardInterrupt


def _format_history_modules(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": item["name"],
            "key": item.get("key", ""),
            "category": getattr(item.get("module"), "category", "")
            or item.get("category", ""),
            "status": item["result"].status,
            "message": redact_text(item["result"].message),
            "duration": round(item["result"].duration, 2),
            "details": [redact_text(str(detail)) for detail in item["result"].details],
            "warnings": [
                redact_text(str(warning)) for warning in item["result"].warnings
            ],
            "error_output": redact_text(item["result"].error_output),
            "reboot_required": bool(getattr(item["result"], "reboot_required", False)),
            "commands": item.get("commands", []),
        }
        for item in results
    ]


def main():
    signal.signal(signal.SIGTERM, handle_sigterm)

    args = parse_args()
    cfg = get_config(config_path=args.config)

    if args.generate_completion:
        all_mods = get_all_modules(cfg)
        if args.generate_completion == "bash":
            print(generate_bash_completion(all_mods))
        elif args.generate_completion == "zsh":
            print(generate_zsh_completion(all_mods))
        elif args.generate_completion == "fish":
            print(generate_fish_completion(all_mods))
        sys.exit(0)

    history_store = HistoryStore()
    if args.history is not None:
        if args.history < 1 or args.history > 30:
            print("Error: --history count must be between 1 and 30.", file=sys.stderr)
            sys.exit(2)
        print_history(history_store.list_runs(30), limit=args.history)
        sys.exit(0)
    if args.show_log:
        run_data = history_store.load(args.show_log)
        if run_data is None:
            print(
                f"Error: No saved update run found for ID {args.show_log!r}.",
                file=sys.stderr,
            )
            sys.exit(1)
        previous_runs = history_store.list_runs(30)
        matching_index = next(
            (
                index
                for index, item in enumerate(previous_runs)
                if item.get("id") == args.show_log
            ),
            None,
        )
        if matching_index is not None:
            run_data = dict(run_data)
            run_data["status"] = classify_run_status(
                run_data, previous_runs[matching_index + 1 :]
            )
        print_run_log(run_data)
        sys.exit(0)

    self_update_result = None
    if not is_homebrew_install() and not (args.list or args.edit_config):
        self_update_result = self_update()

    if args.edit_config:
        edit_config(args.config or DEFAULT_CONFIG_PATH)

    quiet_mode = args.quiet or cfg.quiet
    verbose_mode = args.verbose or cfg.verbose
    no_sudo_mode = args.no_sudo or cfg.no_sudo
    no_snapshot_mode = args.no_snapshot or cfg.no_snapshot
    no_history_mode = args.no_history or cfg.no_history
    reboot_requested_mode = args.reboot or cfg.reboot
    notify_mode = args.notify or cfg.notifications_enabled

    ctx = UpdateContext(force=args.force, verbose=verbose_mode)
    all_modules: list[BaseModule] = get_all_modules(cfg)

    # List modules mode
    if args.list:
        if cfg.load_error:
            print(
                f"Warning: Could not load configuration from {cfg.config_path}; "
                f"using defaults. {cfg.load_error}",
                file=sys.stderr,
            )
        print(f"{'Key':<14} {'Name':<28} {'Status':<16} {'Description'}")
        print("─" * 80)
        for m in all_modules:
            status = m.availability_status(ctx)
            print(f"{m.key:<14} {m.name:<28} {status:<16} {m.description}")
        sys.exit(0)

    # Filter modules
    selected_keys = (
        [k.strip().lower() for k in args.only.split(",")]
        if args.only
        else (cfg.only_keys if cfg.only_keys else None)
    )
    skip_keys = [k.strip().lower() for k in args.skip.split(",")] if args.skip else []
    if cfg.skip_keys:
        skip_keys.extend(cfg.skip_keys)

    selected_categories = (
        [c.strip().lower() for c in args.category.split(",")]
        if args.category
        else (cfg.categories if cfg.categories else None)
    )
    skip_categories = (
        [c.lower() for c in cfg.skip_categories] if cfg.skip_categories else []
    )

    if no_snapshot_mode:
        skip_keys.append("snapshot")

    modules_to_run: list[BaseModule] = []
    for m in all_modules:
        m_identifiers = {m.key.lower(), *(a.lower() for a in getattr(m, "aliases", []))}
        if selected_keys and not (m_identifiers & set(selected_keys)):
            continue
        cat_lower = getattr(m, "category", "").lower()
        if selected_categories and not any(
            sc in cat_lower for sc in selected_categories
        ):
            continue
        if skip_categories and any(sc in cat_lower for sc in skip_categories):
            continue
        if no_sudo_mode and getattr(m, "requires_sudo", False):
            continue
        if (m_identifiers & set(skip_keys)) or (m_identifiers & cfg.disabled_keys):
            continue
        if m.is_available(ctx):
            modules_to_run.append(m)

    if not modules_to_run:
        print("No matching or available modules selected to run.")
        sys.exit(0)

    # Availability checks can run read-only queries; history records update work only.
    ctx.command_log.clear()
    ctx._logged_output_chars = 0

    # Check if any selected module requires sudo upfront
    needs_sudo = any(getattr(m, "requires_sudo", False) for m in modules_to_run)
    try:
        if needs_sudo and not sudo.init_sudo(interactive=sys.stdin.isatty()):
            print(
                "Error: Administrator privileges (sudo) required but could not be obtained."
            )
            sys.exit(1)
    except KeyboardInterrupt:
        sudo.stop_sudo_keeper()
        sys.exit(130)

    ui = UI(quiet=quiet_mode, verbose=verbose_mode)
    ui.print_header("System Updater")

    results = []
    if cfg.load_error:
        results.append(
            {
                "name": "Configuration",
                "key": "config",
                "category": "System Protection",
                "result": StepResult(
                    "warning",
                    f"Could not load configuration; using defaults: {cfg.load_error}",
                ),
            }
        )
    total_start = time.time()
    started_at = datetime.now(UTC)
    run_id = history_store.new_run_id(started_at)
    current_category = None
    self_update_printed = False

    try:
        with suppress_terminal_echo():
            for m in modules_to_run:
                if m.category != current_category:
                    current_category = m.category
                    ui.print_category(current_category)
                    if (
                        current_category == "Containers & Packages"
                        and self_update_result
                    ):
                        self_update_step = StepResult(
                            *self_update_result[:2],
                            duration=self_update_result[2],
                            details=self_update_result[3],
                        )
                        ui.print_result(
                            "SystemUpdater",
                            self_update_step,
                        )
                        results.append(
                            {
                                "name": "SystemUpdater",
                                "key": "self_update",
                                "category": "Containers & Packages",
                                "result": self_update_step,
                            }
                        )
                        self_update_printed = True
                command_start = len(ctx.command_log)
                try:
                    step_res = ui.run_step(
                        m.name, lambda mod=m: mod.run(ctx), ctx=ctx, module=m
                    )
                except KeyboardInterrupt:
                    results.append(
                        {
                            "name": m.name,
                            "key": m.key,
                            "module": m,
                            "result": getattr(ui, "last_interrupted_result", None)
                            or StepResult(
                                "interrupted",
                                "Cancelled by user",
                            ),
                            "commands": ctx.command_log[command_start:],
                        }
                    )
                    raise
                results.append(
                    {
                        "name": m.name,
                        "key": m.key,
                        "module": m,
                        "result": step_res,
                        "commands": ctx.command_log[command_start:],
                    }
                )
            if self_update_result and not self_update_printed:
                ui.print_category("Containers & Packages")
                self_update_step = StepResult(
                    *self_update_result[:2],
                    duration=self_update_result[2],
                    details=self_update_result[3],
                )
                ui.print_result(
                    "SystemUpdater",
                    self_update_step,
                )
                results.append(
                    {
                        "name": "SystemUpdater",
                        "key": "self_update",
                        "category": "Containers & Packages",
                        "result": self_update_step,
                    }
                )
    except KeyboardInterrupt:
        sudo.stop_sudo_keeper()
        total_elapsed = time.time() - total_start
        update_count = sum(
            r["result"].status == "ok"
            and r.get("key") != "snapshot"
            and getattr(r.get("module"), "category", "") != "System Protection"
            for r in results
        )
        reboot_needed = any(
            getattr(r.get("result"), "reboot_required", False) for r in results
        )
        if not no_history_mode:
            history_data = {
                "id": run_id,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
                "duration": round(total_elapsed, 2),
                "status": "interrupted",
                "update_count": update_count,
                "reboot_required": reboot_needed,
                "modules": _format_history_modules(results),
            }
            with contextlib.suppress(OSError):
                history_store.save(history_data)

        ui.print_summary(results, total_elapsed, interrupted=True)
        sys.exit(130)
    finally:
        sudo.stop_sudo_keeper()

    total_elapsed = time.time() - total_start
    finished_at = datetime.now(UTC)
    has_failures = any(r["result"].status == "error" for r in results)
    update_count = sum(
        r["result"].status == "ok"
        and r.get("key") != "snapshot"
        and getattr(r.get("module"), "category", "") != "System Protection"
        for r in results
    )
    reboot_needed = any(
        getattr(r.get("result"), "reboot_required", False) for r in results
    )

    if not no_history_mode:
        history_data = {
            "id": run_id,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration": round(total_elapsed, 2),
            "status": "unknown",
            "update_count": update_count,
            "reboot_required": reboot_needed,
            "modules": _format_history_modules(results),
        }
        history_data["status"] = classify_run_status(
            history_data, history_store.list_runs(30)
        )
        try:
            history_store.save(history_data)
        except OSError as error:
            results.append(
                {
                    "name": "Run History",
                    "key": "history",
                    "result": StepResult(
                        "warning",
                        "Could not save update history",
                        error_output=str(error),
                    ),
                }
            )

    ui.print_summary(results, total_elapsed)

    if notify_mode:
        only_err = cfg.notifications_only_on_error_or_reboot
        if not (only_err and not (has_failures or reboot_needed)):
            if has_failures:
                send_notification(
                    "System Update Failed",
                    f"Update run finished with errors ({round(total_elapsed, 1)}s)",
                    urgency="critical",
                )
            elif reboot_needed:
                send_notification(
                    "System Restart Required",
                    f"Updates completed. System restart needed ({update_count} packages)",
                    urgency="critical",
                )
            elif update_count > 0:
                noun = "update" if update_count == 1 else "updates"
                send_notification(
                    "System Update Complete",
                    f"{update_count} {noun} applied ({round(total_elapsed, 1)}s)",
                    urgency="normal",
                )
            else:
                send_notification(
                    "System Up To Date",
                    f"No updates required ({round(total_elapsed, 1)}s)",
                    urgency="low",
                )

    if reboot_requested_mode and reboot_needed:
        print("Rebooting system as requested by --reboot...")
        sys.stdout.flush()
        reboot_command = (
            ["sudo", "shutdown", "-r", "now"]
            if platform.system() == "Darwin"
            else ["systemctl", "reboot"]
        )
        reboot_requested = False
        try:
            reboot_requested = (
                subprocess.run(reboot_command, check=False).returncode == 0
            )
        except OSError:
            reboot_requested = False
        if not reboot_requested:
            try:
                reboot_requested = (
                    subprocess.run(["sudo", "reboot"], check=False).returncode == 0
                )
            except OSError:
                reboot_requested = False
        if not reboot_requested:
            print(
                "Error: Could not request a reboot. Please restart the system manually.",
                file=sys.stderr,
            )
            has_failures = True

    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
