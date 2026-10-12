"""Private local history for completed SystemUpdater runs."""

import contextlib
import json
import os
import re
import shlex
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from colors import Colors, get_status_marker

RUN_ID_PATTERN = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
TOKEN_PATTERN = re.compile(
    r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
)
BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
URL_CREDENTIAL_PATTERN = re.compile(r"(https?://)[^/@\s]+:[^/@\s]+@")
ASSIGNMENT_SECRET_PATTERN = re.compile(
    r"(?i)\b(token|password|passwd|secret|key|api[_-]?key)(\s*[=:]\s*)([^\s,;]+)"
)
FLAG_SECRET_PATTERN = re.compile(
    r"(?i)(--(?:token|password|secret|api-key)(?:=|\s+))([^\s]+)"
)


def _modified_time(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def redact_text(value: str) -> str:
    """Mask common credentials while retaining useful surrounding log context."""
    redacted = URL_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]@", value)
    redacted = BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
    redacted = TOKEN_PATTERN.sub("[REDACTED_TOKEN]", redacted)
    redacted = ASSIGNMENT_SECRET_PATTERN.sub(r"\1\2[REDACTED]", redacted)
    return FLAG_SECRET_PATTERN.sub(r"\1[REDACTED]", redacted)


def _warning_signatures(module: dict[str, Any]) -> set[str]:
    status = str(module.get("status", ""))
    if status in ("skipped", "interrupted", "cancelled"):
        return set()

    messages = []
    if status == "warning":
        message = str(module.get("message", "")).strip()
        if message and message.casefold() != "warning":
            messages.append(message)
    messages.extend(
        str(item).strip()
        for item in (module.get("warnings") or [])
        if str(item).strip()
    )
    if status == "warning" and not messages:
        messages.extend(
            str(item).strip()
            for item in (module.get("details") or [])
            if str(item).strip()
        )
        if not messages:
            messages.append("warning")

    return {" ".join(message.casefold().split()) for message in messages}


def has_new_warnings(
    current_modules: list[dict[str, Any]], previous_runs: list[dict[str, Any]]
) -> bool:
    """Return whether a module has warning text absent from its latest previous run."""
    latest_module_by_key: dict[str, dict[str, Any]] = {}
    for run in previous_runs:
        for module in run.get("modules") or []:
            if module.get("status") == "skipped":
                continue
            key = str(module.get("key") or module.get("name") or "").casefold()
            if key:
                latest_module_by_key.setdefault(key, module)

    for module in current_modules:
        current_signatures = _warning_signatures(module)
        if not current_signatures:
            continue
        key = str(module.get("key") or module.get("name") or "").casefold()
        previous_signatures = _warning_signatures(latest_module_by_key.get(key, {}))
        if current_signatures - previous_signatures:
            return True
    return False


def classify_run_status(
    run: dict[str, Any], previous_runs: list[dict[str, Any]]
) -> str:
    if run.get("status") in ("interrupted", "cancelled"):
        return "interrupted"
    modules = run.get("modules") or []
    if any(module.get("status") in ("interrupted", "cancelled") for module in modules):
        return "interrupted"
    if run.get("status") == "error" or any(
        module.get("status") == "error" for module in modules
    ):
        return "error"
    if has_new_warnings(modules, previous_runs):
        return "warning"
    if run.get("status") == "warning" and not modules:
        return "warning"
    if int(run.get("update_count", 0) or 0) > 0:
        return "updated"
    return "up-to-date"


def _state_directory() -> Path:
    root = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return Path(root) / "sysupdate" / "history"


class HistoryStore:
    def __init__(self, directory: Path | None = None, retention: int = 30):
        self.directory = Path(directory) if directory else _state_directory()
        self.retention = max(1, retention)

    @staticmethod
    def new_run_id(now: datetime | None = None) -> str:
        timestamp = now or datetime.now(UTC)
        return f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"

    def save(self, run_data: dict[str, Any]) -> Path:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(self.directory.parent, 0o700)
        os.chmod(self.directory, 0o700)
        run_id = run_data.get("id", "")
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("Invalid run history ID")

        fd, temporary_path = tempfile.mkstemp(
            prefix=".run-", suffix=".tmp", dir=self.directory
        )
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(run_data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            final_path = self.directory / f"{run_id}.json"
            os.replace(temporary_path, final_path)
            self._prune()
            return final_path
        except Exception:
            with contextlib.suppress(OSError):
                os.close(fd)
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary_path)
            raise

    def list_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self.directory.is_dir():
            return []
        files = sorted(
            self.directory.glob("*.json"),
            key=_modified_time,
            reverse=True,
        )
        runs = []
        for path in files[: max(1, limit)]:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict) and RUN_ID_PATTERN.fullmatch(
                    str(data.get("id", ""))
                ):
                    runs.append(data)
            except (OSError, json.JSONDecodeError):
                continue
        return runs

    def load(self, run_id: str) -> dict[str, Any] | None:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            return None
        path = self.directory / f"{run_id}.json"
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) and data.get("id") == run_id else None

    def _prune(self) -> None:
        files = sorted(
            self.directory.glob("*.json"),
            key=_modified_time,
            reverse=True,
        )
        for stale_path in files[self.retention :]:
            try:
                stale_path.unlink()
            except OSError:
                continue


def _display_time(value: str) -> str:
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return value or "unknown"


def _status_label(status: str) -> tuple[str, str]:
    labels = {
        "ok": ("✓", "updated"),
        "unchanged": ("—", "up-to-date"),
        "warning": ("!", "warning"),
        "error": ("✗", "failed"),
        "skipped": ("—", "skipped"),
        "updated": ("✓", "updated"),
        "up-to-date": ("—", "up-to-date"),
        "interrupted": ("~", "interrupted"),
        "cancelled": ("~", "cancelled"),
    }
    return labels.get(status, ("?", status or "unknown"))


def _status_marker(status: str) -> str:
    plain = not sys.stdout.isatty() or os.environ.get("NO_COLOR") is not None
    return get_status_marker(status, plain=plain)


def print_history(runs: list[dict[str, Any]], limit: int = 10) -> None:
    if not runs:
        print("No saved update runs.")
        return

    use_color = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    c_dim = Colors.DIM if use_color else ""
    c_reset = Colors.RESET if use_color else ""

    calculated_statuses = {}
    previous_runs = []
    for run in reversed(runs):
        calculated_statuses[run.get("id")] = classify_run_status(
            run, list(reversed(previous_runs))
        )
        previous_runs.append(run)

    header = (
        f"{'Run ID':<26}  {'Started':<19}  {'Status':<11}  {'Duration':<9}  Updates"
    )
    print(header)
    print(f"{c_dim}" + "─" * 80 + f"{c_reset}")
    for run in runs[: max(1, limit)]:
        duration = f"{float(run.get('duration', 0)):.1f}s"
        status_val = calculated_statuses.get(
            run.get("id"), run.get("status", "unknown")
        )
        print(
            f"{run.get('id', ''):<26}  "
            f"{_display_time(run.get('started_at', '')):<19}  "
            f"{status_val:<11}  "
            f"{duration:<9}  "
            f"{run.get('update_count', 0)}"
        )


KNOWN_CATEGORIES: dict[str, str] = {
    # System Protection
    "snapshot": "System Protection",
    "config": "System Protection",
    "configuration": "System Protection",
    # System Core
    "reposync": "System Core",
    "repositories": "System Core",
    "system": "System Core",
    "nobara_repos": "System Core",
    "nobara_system": "System Core",
    "system_packages": "System Core",
    "firmware": "System Core",
    "device_firmware": "System Core",
    "maintenance": "System Core",
    "apt": "System Core",
    "apt_packages": "System Core",
    "pacman": "System Core",
    "arch_packages": "System Core",
    "dnf": "System Core",
    "zypper": "System Core",
    "zypper_packages": "System Core",
    "apk": "System Core",
    "alpine_packages": "System Core",
    "xbps": "System Core",
    "xbps_packages": "System Core",
    # Applications & Gaming
    "flatpak": "Applications & Gaming",
    "gearlever": "Applications & Gaming",
    "gear_lever": "Applications & Gaming",
    "protonplus": "Applications & Gaming",
    "proton": "Applications & Gaming",
    "distrobox": "Applications & Gaming",
    "nuvio": "Applications & Gaming",
    "nuvio_desktop": "Applications & Gaming",
    # Containers & Packages
    "brew": "Containers & Packages",
    "homebrew": "Containers & Packages",
    "docker": "Containers & Packages",
    "podman": "Containers & Packages",
    "vagrant": "Containers & Packages",
    "nix": "Containers & Packages",
    "snap": "Containers & Packages",
    "self_update": "Containers & Packages",
    "systemupdater": "Containers & Packages",
    # Development Environment
    "asdf": "Development Environment",
    "bun": "Development Environment",
    "cargo_update": "Development Environment",
    "cargo": "Development Environment",
    "composer": "Development Environment",
    "conda": "Development Environment",
    "gem": "Development Environment",
    "gh_extensions": "Development Environment",
    "github_cli_extensions": "Development Environment",
    "micro": "Development Environment",
    "mise": "Development Environment",
    "neovim": "Development Environment",
    "npm": "Development Environment",
    "oh_my_zsh": "Development Environment",
    "pip": "Development Environment",
    "pipx": "Development Environment",
    "pnpm": "Development Environment",
    "poetry": "Development Environment",
    "rust": "Development Environment",
    "rustup": "Development Environment",
    "ruby": "Development Environment",
    "skills": "Development Environment",
    "agents": "Development Environment",
    "tmux_plugins": "Development Environment",
    "uv": "Development Environment",
    "yarn": "Development Environment",
    "chezmoi": "Development Environment",
    "yadm": "Development Environment",
    "cursor": "Development Environment",
    "helix": "Development Environment",
    "vscode": "Development Environment",
    "vscodium": "Development Environment",
    "git_repos": "Development Environment",
    "flutter": "Development Environment",
    "ghcup": "Development Environment",
    "pipenv": "Development Environment",
    "pyenv": "Development Environment",
    "sdkman": "Development Environment",
    "fisher": "Development Environment",
    "tealdeer": "Development Environment",
    "zinit": "Development Environment",
    "antigravity": "Development Environment",
}


def _module_category(module: dict[str, Any]) -> str:
    category = str(module.get("category", "")).strip()
    if category:
        return category
    key = str(module.get("key", "")).strip().lower()
    if key in KNOWN_CATEGORIES:
        return KNOWN_CATEGORIES[key]
    name = str(module.get("name", "")).strip().lower().replace(" ", "_")
    if name in KNOWN_CATEGORIES:
        return KNOWN_CATEGORIES[name]
    name_no_spaces = name.replace("_", "")
    for k, v in KNOWN_CATEGORIES.items():
        if k.replace("_", "") == name_no_spaces:
            return v
    return "Other"


def print_run_log(run: dict[str, Any]) -> None:
    modules = run.get("modules", [])
    width = 80
    use_color = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    c_cyan = Colors.BOLD_CYAN if use_color else ""
    c_dim = Colors.DIM if use_color else ""
    c_bold = Colors.BOLD if use_color else ""
    c_gray = Colors.GRAY if use_color else ""
    c_reset = Colors.RESET if use_color else ""

    run_prefix = "── Update Run "
    print(f"{c_cyan}{run_prefix}{'─' * max(0, width - len(run_prefix))}{c_reset}")
    print(f"  {c_dim}ID:{c_reset}       {run.get('id', 'unknown')}")
    print(f"  {c_dim}Started:{c_reset}  {_display_time(run.get('started_at', ''))}")
    print(f"  {c_dim}Duration:{c_reset} {float(run.get('duration', 0)):.1f}s")

    mod_prefix = "── Modules "
    print(f"\n{c_cyan}{mod_prefix}{'─' * max(0, width - len(mod_prefix))}{c_reset}")
    for module in modules:
        module_status = str(module.get("status", "unknown"))
        if module_status == "unchanged" and module.get("warnings"):
            module_status = "warning"
        _, module_label = _status_label(module_status)
        dur_str = f"{float(module.get('duration', 0)):.1f}s"
        print(
            f"  {_status_marker(module_status)} {module.get('name', 'Module'):<30} "
            f"{module_label:<12} {c_gray}{dur_str}{c_reset}"
        )

    cmd_prefix = "── Command Output "
    print(f"\n{c_cyan}{cmd_prefix}{'─' * max(0, width - len(cmd_prefix))}{c_reset}")

    current_category = None
    for module in modules:
        cat = _module_category(module)
        is_new_category = False
        if cat != current_category:
            current_category = cat
            is_new_category = True
            cat_prefix = f"── {current_category} "
            print(
                f"\n{c_cyan}{cat_prefix}{'─' * max(0, width - len(cat_prefix))}{c_reset}"
            )

        message = str(module.get("message", "")).strip()
        module_status = str(module.get("status", "unknown"))
        if module_status == "unchanged" and module.get("warnings"):
            module_status = "warning"
        _, module_label = _status_label(module_status)
        commands = module.get("commands", [])
        error_output = module.get("error_output", "")
        # A command is already the explanation; keep its failure reason in the
        # captured output instead of repeating the module message in the heading.
        has_command_output = bool(commands) or bool(error_output)
        details = [
            " ".join(str(detail).split())
            for detail in module.get("details", [])
            if str(detail).strip()
        ]
        if module_status in ("interrupted", "cancelled"):
            reason = ""
        elif not has_command_output and module_status == "warning":
            reason_parts = (
                [message] if message and message.casefold() != "warning" else []
            )
            reason_parts.extend(details)
            if not reason_parts:
                reason_parts.extend(
                    str(warning)
                    for warning in module.get("warnings", [])
                    if str(warning).strip()
                )
            reason = "; ".join(reason_parts)
        elif not has_command_output:
            reason = message
        else:
            reason = ""
        module_heading = f"{_status_marker(module_status)} {c_bold}{module.get('name', 'Module')}{c_reset} {c_dim}·{c_reset} {module_label}"
        if reason:
            module_heading += f" {c_dim}—{c_reset} {reason}"
        if is_new_category:
            print(f"  {module_heading}")
        else:
            print(f"\n  {module_heading}")
        if has_command_output:
            for detail in details:
                print(f"      {c_dim}-{c_reset} {detail}")
        captured_lines = {
            " ".join(line.casefold().split())
            for command in commands
            for stream_name in ("stdout", "stderr")
            for line in command.get(stream_name, "").splitlines()
        }
        for command in commands:
            command_text = shlex.join(command.get("command", []))
            print(f"      {c_dim}${c_reset} {c_bold}{command_text}{c_reset}")
            if command.get("output_withheld"):
                print(
                    f"        {c_dim}[output withheld for a read-only command]{c_reset}"
                )
            for stream_name in ("stdout", "stderr"):
                output = command.get(stream_name, "")
                if output and output.strip():
                    print(f"        {c_dim}{stream_name}:{c_reset}")
                    pending_blank = False
                    for line in output.strip().splitlines():
                        if not line.strip():
                            pending_blank = True
                        else:
                            if pending_blank:
                                print()
                                pending_blank = False
                            print(f"          {c_dim}{line.rstrip()}{c_reset}")
        if error_output:
            diagnostic_lines = [
                line.rstrip() for line in error_output.rstrip().splitlines()
            ]
            unseen_lines = [
                line
                for line in diagnostic_lines
                if " ".join(line.casefold().split()) not in captured_lines
            ]
            if unseen_lines:
                print(f"      {c_dim}Diagnostic output:{c_reset}")
                for line in unseen_lines:
                    print(f"        {c_dim}{line}{c_reset}")
