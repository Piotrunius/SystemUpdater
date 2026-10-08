"""Private local history for completed SystemUpdater runs."""

import contextlib
import json
import os
import re
import shlex
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


RUN_ID_PATTERN = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
TOKEN_PATTERN = re.compile(r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")
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


def _warning_signatures(module: Dict[str, Any]) -> set[str]:
    status = str(module.get("status", ""))
    if status == "skipped":
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


def has_new_warnings(current_modules: List[Dict[str, Any]], previous_runs: List[Dict[str, Any]]) -> bool:
    """Return whether a module has warning text absent from its latest previous run."""
    latest_module_by_key: Dict[str, Dict[str, Any]] = {}
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


def classify_run_status(run: Dict[str, Any], previous_runs: List[Dict[str, Any]]) -> str:
    modules = run.get("modules") or []
    if run.get("status") == "error" or any(module.get("status") == "error" for module in modules):
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
    def __init__(self, directory: Optional[Path] = None, retention: int = 30):
        self.directory = Path(directory) if directory else _state_directory()
        self.retention = max(1, retention)

    @staticmethod
    def new_run_id(now: Optional[datetime] = None) -> str:
        timestamp = now or datetime.now(timezone.utc)
        return f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"

    def save(self, run_data: Dict[str, Any]) -> Path:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(self.directory.parent, 0o700)
        os.chmod(self.directory, 0o700)
        run_id = run_data.get("id", "")
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("Invalid run history ID")

        fd, temporary_path = tempfile.mkstemp(prefix=".run-", suffix=".tmp", dir=self.directory)
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

    def list_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
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
                if isinstance(data, dict) and RUN_ID_PATTERN.fullmatch(str(data.get("id", ""))):
                    runs.append(data)
            except (OSError, json.JSONDecodeError):
                continue
        return runs

    def load(self, run_id: str) -> Optional[Dict[str, Any]]:
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
        "skipped": ("-", "skipped"),
        "updated": ("✓", "updated"),
        "up-to-date": ("—", "up-to-date"),
    }
    return labels.get(status, ("?", status or "unknown"))


def _status_marker(status: str) -> str:
    symbol, _ = _status_label(status)
    colors = {"ok": "\033[32m", "warning": "\033[33m", "error": "\033[31m"}
    if not os.isatty(1) or os.environ.get("NO_COLOR") is not None:
        return f"[{symbol}]"
    color = colors.get(status, "\033[2m")
    return f"{color}[{symbol}]\033[0m"


def print_history(runs: List[Dict[str, Any]], limit: int = 10) -> None:
    if not runs:
        print("No saved update runs.")
        return

    calculated_statuses = {}
    previous_runs = []
    for run in reversed(runs):
        calculated_statuses[run.get("id")] = classify_run_status(
            run, list(reversed(previous_runs))
        )
        previous_runs.append(run)

    print(f"{'RUN ID':<26}  {'STARTED':<19}  {'STATUS':<12}  {'DURATION':<10}  UPDATES")
    for run in runs[: max(1, limit)]:
        duration = f"{float(run.get('duration', 0)):.1f}s"
        print(
            f"{run.get('id', ''):<26}  "
            f"{_display_time(run.get('started_at', '')):<19}  "
            f"{calculated_statuses.get(run.get('id'), run.get('status', 'unknown')):<12}  "
            f"{duration:<10}  "
            f"{run.get('update_count', 0)}"
        )


def print_run_log(run: Dict[str, Any]) -> None:
    modules = run.get("modules", [])
    status = str(run.get("status", "unknown"))
    print(f"── Update Run ──────────────────────────────────────────────────────")
    print(f"  ID:       {run.get('id', 'unknown')}")
    print(f"  Started:  {_display_time(run.get('started_at', ''))}")
    print(f"  Duration: {float(run.get('duration', 0)):.1f}s")

    print("\n── Modules ─────────────────────────────────────────────────────────")
    for module in modules:
        module_status = str(module.get("status", "unknown"))
        if module_status == "unchanged" and module.get("warnings"):
            module_status = "warning"
        _, module_label = _status_label(module_status)
        print(
            f"  {_status_marker(module_status)} {module.get('name', 'Module'):<30} "
            f"{module_label:<12} {float(module.get('duration', 0)):.1f}s"
        )

    print("\n── Command Output ──────────────────────────────────────────────────")

    for module in modules:
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
        if not has_command_output and module_status == "warning":
            reason_parts = [message] if message and message.casefold() != "warning" else []
            reason_parts.extend(details)
            if not reason_parts:
                reason_parts.extend(str(warning) for warning in module.get("warnings", []) if str(warning).strip())
            reason = "; ".join(reason_parts)
        elif not has_command_output:
            reason = message
        else:
            reason = ""
        module_heading = f"{_status_marker(module_status)} {module.get('name', 'Module')} · {module_label}"
        if reason:
            module_heading += f" — {reason}"
        print(f"\n{module_heading}")
        if has_command_output:
            for detail in details:
                print(f"  - {detail}")
        captured_lines = {
            " ".join(line.casefold().split())
            for command in commands
            for stream_name in ("stdout", "stderr")
            for line in command.get(stream_name, "").splitlines()
        }
        for command in commands:
            command_text = shlex.join(command.get("command", []))
            print(f"  $ {command_text}")
            if command.get("output_withheld"):
                print("    [output withheld for a read-only command]")
            for stream_name in ("stdout", "stderr"):
                output = command.get(stream_name, "")
                if output:
                    print(f"    {stream_name}:")
                    for line in output.rstrip().splitlines():
                        print(f"      {line}")
        if error_output:
            diagnostic_lines = [line.rstrip() for line in error_output.rstrip().splitlines()]
            unseen_lines = [
                line for line in diagnostic_lines
                if " ".join(line.casefold().split()) not in captured_lines
            ]
            if unseen_lines:
                print("  Diagnostic output:")
                for line in unseen_lines:
                    print(f"    {line}")
