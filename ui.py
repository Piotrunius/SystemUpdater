"""
Terminal UI and step progress renderer for SystemUpdater.
Strictly adheres to flicker-free ANSI standards and zero-emoji policy.
"""

import atexit
import contextlib
import os
import re
import sys
import termios
import threading
import time
from collections.abc import Callable
from typing import Any

_original_termios: list[Any] | None = None


def _restore_terminal():
    global _original_termios
    if _original_termios is not None:
        if sys.stdin.isatty():
            with contextlib.suppress(termios.error, OSError):
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
            with contextlib.suppress(termios.error, OSError):
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, _original_termios)
        _original_termios = None


atexit.register(_restore_terminal)


@contextlib.contextmanager
def suppress_terminal_echo():
    """Context manager to suppress terminal echo and unwanted keypresses during execution."""
    global _original_termios
    if not sys.stdin.isatty():
        yield
        return

    with contextlib.suppress(termios.error, OSError):
        old_attr = termios.tcgetattr(sys.stdin)
        _original_termios = old_attr
        new_attr = list(old_attr)
        # Disable ECHO and ECHOCTL so typed keys and ^C are not printed onto the terminal
        new_attr[3] = new_attr[3] & ~termios.ECHO
        if hasattr(termios, "ECHOCTL"):
            new_attr[3] = new_attr[3] & ~termios.ECHOCTL
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new_attr)

    try:
        yield
    finally:
        _restore_terminal()


from colors import Colors, get_status_marker

RUNNING_FRAMES = [
    f"{Colors.DIM}[{Colors.RESET}{Colors.CYAN}|{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
    f"{Colors.DIM}[{Colors.RESET}{Colors.CYAN}/{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
    f"{Colors.DIM}[{Colors.RESET}{Colors.CYAN}\\{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
]

DIAGNOSTIC_LINE_PATTERN = re.compile(
    r"\b(warn(?:ing)?|deprecated|error|failed|failure|unable|could not|cannot|denied|"
    r"refused|rejected|invalid|unsupported|not supported|not found|not registered|rate limit|"
    r"end[- ]of[- ]life|no longer|timed?[- ]out|timeout|known issue|"
    r"please report this issue)\b|/Casks/[^:\s]+:\d+",
    re.IGNORECASE,
)

IGNORED_DIAGNOSTIC_SUBSTRINGS = (
    "antigravityAnalytics",
    "LVFS-Triaged-Issue",
    "dbx-does-not-apply-on-reboot",
    "Update failure is a known issue",
    "Error writing credentials to socket",
    "[RPM] file",
    "remove failed: No such file or directory",
    "Sandbox unavailable",
)

REBOOT_TRIGGER_PATTERNS = re.compile(
    r"(^|[\-_])(kernel|linux|systemd|glibc|libc6|musl|grub|shim|nvidia|microcode|ucode|firmware|dbus|kmod|akmod|dracut)([\-_]|$)",
    re.IGNORECASE,
)

NON_FATAL_PATTERNS = [
    (
        re.compile(
            r"(api limit reached|rate limit exceeded|too many requests|http[s]? (status )?429)",
            re.IGNORECASE,
        ),
        "API rate limit reached",
    ),
    (
        re.compile(
            r"(could not resolve host|temporary failure in name resolution|connection timed out|timed out after|operation timed out)",
            re.IGNORECASE,
        ),
        "Network connection timed out",
    ),
    (
        re.compile(
            r"(connection refused|network is unreachable|failed to connect to|unable to connect to)",
            re.IGNORECASE,
        ),
        "Network host unreachable",
    ),
    (
        re.compile(
            r"(502 bad gateway|503 service temporarily unavailable|504 gateway timeout|mirror sync in progress)",
            re.IGNORECASE,
        ),
        "Remote mirror temporarily unavailable",
    ),
    (
        re.compile(
            r"(ssl certificate problem|certificate has expired|unable to get local issuer certificate)",
            re.IGNORECASE,
        ),
        "SSL certificate error",
    ),
    (
        re.compile(
            r"(resource temporarily unavailable|database is locked|another instance is running|lock is held by)",
            re.IGNORECASE,
        ),
        "Resource temporarily locked",
    ),
    (
        re.compile(
            r"(bad credentials|authentication failed|invalid token|token expired|permission denied \(publickey\))",
            re.IGNORECASE,
        ),
        "Authentication issue",
    ),
]


def detect_warning(text: str) -> str | None:
    """
    Analyzes output or error messages to detect if failure was caused by a transient,
    quota-related, or external condition that warrants a warning [!] rather than an error [✗].
    """
    if not text:
        return None
    for pattern, label in NON_FATAL_PATTERNS:
        if pattern.search(text):
            return label
    return None


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


def get_reboot_trigger_packages(package_lines: list[str]) -> list[str]:
    """Return all package lines that triggered a reboot requirement."""
    matched = []
    seen = set()
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


class StepResult:
    def __init__(
        self,
        status: str,  # "ok", "unchanged", "warning", "error", "skipped"
        message: str = "",
        details: list[str] | None = None,
        duration: float = 0.0,
        error_output: str = "",
        warnings: list[str] | None = None,
        reboot_required: bool = False,
    ):
        self.status = status
        self.message = message
        self.details = details or []
        self.duration = duration
        self.error_output = error_output
        self.warnings = warnings or []
        self.reboot_required = reboot_required


class UI:
    def __init__(
        self,
        is_interactive: bool | None = None,
        quiet: bool = False,
        verbose: bool = False,
    ):
        self.is_tty = (
            is_interactive if is_interactive is not None else sys.stdout.isatty()
        )
        self.terminal_width = self._get_width()
        self.quiet = quiet
        self.verbose = verbose
        self.last_interrupted_result: StepResult | None = None
        self._last_step_multiline: bool = False
        self._category_has_output: bool = False

    def _get_width(self) -> int:
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80

    def print_header(self, title: str = "System Updater"):
        if self.quiet:
            return
        width = min(self.terminal_width, 80)
        time_str = time.strftime("%H:%M:%S")
        prefix = f"── {title} ─ {time_str} "
        dashes = "─" * max(0, width - len(prefix))
        print()
        print(f"{Colors.BOLD}{Colors.CYAN}{prefix}{dashes}{Colors.RESET}")

    def run_step(
        self,
        label: str,
        target: Callable[[], StepResult],
        ctx: Any | None = None,
        module: Any | None = None,
    ) -> StepResult:
        command_start = len(getattr(ctx, "command_log", [])) if ctx is not None else 0
        note_start = len(getattr(ctx, "deferred_notes", [])) if ctx is not None else 0

        if self.quiet:
            start_time = time.time()
            try:
                res = target()
            except KeyboardInterrupt:
                res = StepResult(
                    "interrupted",
                    "Cancelled by user",
                    duration=time.time() - start_time,
                )
                self.last_interrupted_result = res
                self._complete_step(res, ctx, command_start, note_start=note_start)
                raise
            except Exception as e:  # noqa: BLE001
                res = StepResult("error", str(e), error_output=str(e))
            if res.status == "error":
                is_core = (
                    module is not None
                    and getattr(module, "category", "") == "System Core"
                )
                if not is_core:
                    warn_reason = detect_warning(f"{res.message}\n{res.error_output}")
                    if warn_reason:
                        res.status = "warning"
                        res.message = warn_reason
            res.duration = time.time() - start_time
            self._complete_step(res, ctx, command_start, note_start=note_start)
            return res

        is_verbose = ctx is not None and getattr(ctx, "verbose", False)
        if not self.is_tty or is_verbose:
            commands_printed = False

            def on_cmd_start():
                nonlocal commands_printed
                if not commands_printed:
                    commands_printed = True
                    if self._category_has_output:
                        print()
                    frame = get_status_marker(":")
                    print(f"  {frame} {Colors.BOLD}{label}{Colors.RESET}...")
                    self._last_step_multiline = True
                    self._category_has_output = True

            if ctx is not None:
                ctx._on_command_start = on_cmd_start

            start_time = time.time()
            try:
                res = target()
            except KeyboardInterrupt:
                res = StepResult(
                    "interrupted",
                    "Cancelled by user",
                    duration=time.time() - start_time,
                )
                self._complete_step(
                    res,
                    ctx,
                    command_start,
                    note_start=note_start,
                    show_command_output=is_verbose,
                )
                self.last_interrupted_result = res
                dur_val = max(0.1, res.duration)
                time_tag = f"{Colors.GRAY}({dur_val:.1f}s){Colors.RESET}"
                if commands_printed:
                    self._last_step_multiline = True
                    self._category_has_output = True
                    marker = get_status_marker("~")
                    print(f"      {marker} interrupted {time_tag}")
                else:
                    self._print_static_result(label, res, module=module)
                raise
            except Exception as e:  # noqa: BLE001
                res = StepResult("error", str(e), error_output=str(e))
            finally:
                if ctx is not None:
                    ctx._on_command_start = None

            if res.status == "error":
                is_core = (
                    module is not None
                    and getattr(module, "category", "") == "System Core"
                )
                if not is_core:
                    warn_reason = detect_warning(f"{res.message}\n{res.error_output}")
                    if warn_reason:
                        res.status = "warning"
                        res.message = warn_reason

            res.duration = time.time() - start_time
            self._complete_step(
                res,
                ctx,
                command_start,
                note_start=note_start,
                show_command_output=is_verbose,
            )

            if commands_printed:
                self._last_step_multiline = True
                self._category_has_output = True
                dur_val = max(0.1, res.duration)
                time_tag = f"{Colors.GRAY}({dur_val:.1f}s){Colors.RESET}"
                sym, msg = self._resolve_step_display(
                    label, res, module=module, verbose=self.verbose
                )
                marker = get_status_marker(sym)
                print(f"      {marker} {msg} {time_tag}")
            else:
                self._print_static_result(label, res, module=module)

            return res

        # Interactive running execution with [:] indicator
        stop_event = threading.Event()
        current_status = {"text": label}
        if ctx is not None and hasattr(ctx, "status_updater"):
            ctx.status_updater = lambda msg: current_status.__setitem__(
                "text", f"{label}: {msg}" if msg else label
            )

        start_time = time.time()
        spinner_thread = threading.Thread(
            target=self._spinner_worker,
            args=(stop_event, current_status, ctx),
            daemon=True,
        )

        spinner_thread.start()

        try:
            res = target()
        except KeyboardInterrupt:
            res = StepResult(
                "interrupted",
                "Cancelled by user",
                duration=time.time() - start_time,
            )
            self._complete_step(res, ctx, command_start, note_start=note_start)
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            self._print_static_result(label, res, module=module)
            self.last_interrupted_result = res
            raise
        except Exception as e:  # noqa: BLE001
            res = StepResult("error", str(e), error_output=str(e))
        finally:
            if ctx is not None and hasattr(ctx, "status_updater"):
                ctx.status_updater = None
            stop_event.set()
            spinner_thread.join()
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()

        res.duration = time.time() - start_time
        self._complete_step(res, ctx, command_start, note_start=note_start)
        # Clear the status line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

        if res.status == "error":
            is_core = (
                module is not None and getattr(module, "category", "") == "System Core"
            )
            if not is_core:
                warn_reason = detect_warning(f"{res.message}\n{res.error_output}")
                if warn_reason:
                    res.status = "warning"
                    res.message = warn_reason

        self._print_static_result(label, res, module=module)
        return res

    def _complete_step(
        self,
        result: StepResult,
        ctx: Any | None,
        command_start: int,
        note_start: int = 0,
        show_command_output: bool = False,
    ) -> None:
        from history_store import redact_text

        records = (
            getattr(ctx, "command_log", [])[command_start:] if ctx is not None else []
        )
        notes = (
            getattr(ctx, "deferred_notes", [])[note_start:] if ctx is not None else []
        )
        warning_lines = [
            w
            for w in (list(result.warnings) + list(notes))
            if not any(ign in str(w) for ign in IGNORED_DIAGNOSTIC_SUBSTRINGS)
        ]
        failed_output = []

        for record in records:
            outputs = [record.get("stdout", ""), record.get("stderr", "")]
            if record.get("returncode", 0) != 0:
                failed_output.extend(
                    line
                    for output in outputs
                    for line in output.splitlines()
                    if line.strip()
                    and not any(ign in line for ign in IGNORED_DIAGNOSTIC_SUBSTRINGS)
                )
                if result.status == "warning":
                    warning_lines.extend(failed_output)
                continue

            for output in outputs:
                for line in output.splitlines():
                    if any(ign in line for ign in IGNORED_DIAGNOSTIC_SUBSTRINGS):
                        continue
                    if DIAGNOSTIC_LINE_PATTERN.search(line):
                        warning_lines.append(line.strip())

        if result.status == "error" and failed_output:
            existing = result.error_output.strip()
            combined = "\n".join(failed_output)
            if combined and combined not in existing:
                result.error_output = f"{existing}\n{combined}".strip()

        result.message = redact_text(result.message)
        result.details = [redact_text(str(detail)) for detail in result.details]
        result.error_output = redact_text(result.error_output)
        result.warnings = list(
            dict.fromkeys(
                redact_text(line)
                for line in warning_lines
                if line.strip()
                and not any(ign in line for ign in IGNORED_DIAGNOSTIC_SUBSTRINGS)
            )
        )

        # Universal reboot detection across all modules
        if result.status in ("ok", "unchanged"):
            reboot_needed, _ = check_packages_require_reboot(result.details)
            if (
                result.reboot_required
                or reboot_needed
                or os.path.exists("/run/reboot-required")
                or os.path.exists("/var/run/reboot-required")
            ):
                result.reboot_required = True

        if show_command_output and not self.quiet:
            for record in records:
                if record.get("output_withheld") or record.get("output_streamed"):
                    continue
                for stream_name in ("stdout", "stderr"):
                    lines = [
                        line.rstrip()
                        for line in record.get(stream_name, "").splitlines()
                        if line.strip()
                    ]
                    if lines:
                        print(f"        {Colors.DIM}{stream_name}:{Colors.RESET}")
                        for line in lines:
                            print(f"          {Colors.DIM}{line}{Colors.RESET}")

    def _spinner_worker(
        self,
        stop_event: threading.Event,
        status: dict[str, str],
        ctx: Any | None = None,
    ):
        frame_idx = 0
        while not stop_event.is_set():
            last_activity = getattr(ctx, "last_activity_time", None) if ctx else None
            now = time.monotonic()
            is_active = (last_activity is None) or ((now - last_activity) < 1.5)
            frame = RUNNING_FRAMES[frame_idx % len(RUNNING_FRAMES)]
            text = status["text"]
            sys.stdout.write(f"\r\033[K  {frame} {text}...")
            sys.stdout.flush()
            if is_active:
                frame_idx += 1
            time.sleep(0.12)

    def print_category(self, title: str):
        if self.quiet:
            return
        width = min(self.terminal_width, 80)
        print()
        print(
            f"{Colors.BOLD}{Colors.CYAN}── {title} "
            + "─" * max(0, width - len(title) - 4)
            + Colors.RESET
        )
        self._last_step_multiline = False
        self._category_has_output = False

    def _clean_ok_message(self, label: str, msg: str) -> str:
        if not msg:
            return "updated"
        msg_clean = msg.strip()
        label_lower = label.lower().strip()
        msg_lower = msg_clean.lower()
        if (
            msg_lower == label_lower
            or msg_lower
            in (
                f"{label_lower} updated",
                f"{label_lower} upgraded",
                f"{label_lower} upgraded successfully",
            )
            or (
                msg_lower.endswith(" updated") and msg_lower[:-8].strip() in label_lower
            )
            or (
                msg_lower.endswith(" upgraded")
                and msg_lower[:-9].strip() in label_lower
            )
            or (
                msg_lower.endswith(" upgraded successfully")
                and msg_lower[:-22].strip() in label_lower
            )
            or (
                msg_lower.endswith(" updated successfully")
                and msg_lower[:-20].strip() in label_lower
            )
        ):
            return "updated"
        return msg_clean

    def _resolve_ok_msg(
        self, label: str, res: StepResult, module: Any | None = None
    ) -> str:
        msg_text = self._clean_ok_message(label, res.message)
        item_meta = {
            "name": label,
            "key": getattr(res, "key", "") or getattr(module, "key", ""),
            "module": module,
        }
        if (
            not is_single_entity_module(item_meta)
            and res.details
            and not any(c.isdigit() for c in msg_text)
        ):
            valid = [
                d for d in res.details if d and not str(d).strip().startswith("... and")
            ]
            if valid:
                unit = get_module_unit_name(item_meta, len(valid))
                msg_text = f"{len(valid)} {unit} updated"
        return msg_text

    def _resolve_step_display(
        self,
        label: str,
        res: StepResult,
        module: Any | None = None,
        verbose: bool = False,
    ) -> tuple[str, str]:
        if res.status == "ok":
            msg_text = self._resolve_ok_msg(label, res, module=module)
            if res.reboot_required:
                return ("^", msg_text or "updated")
            return ("✓", msg_text or "updated")

        if res.status == "warning" or (
            verbose and res.status == "unchanged" and res.warnings
        ):
            if verbose:
                return ("!", "warning")
            if res.reboot_required:
                return ("^", "up to date")
            return ("—", "up to date")

        if res.status == "skipped":
            if verbose:
                return ("!", "skipped")
            return ("—", "up to date")

        if res.status == "unchanged":
            if res.reboot_required:
                return ("^", res.message if res.message else "up to date")
            return ("—", res.message if res.message else "up to date")

        if res.status in ("interrupted", "cancelled"):
            return ("~", "interrupted")

        return ("✗", "failed")

    def _print_static_result(
        self,
        label: str,
        res: StepResult,
        module: Any | None = None,
        show_duration: bool = True,
    ):
        if getattr(self, "_category_has_output", False) and getattr(
            self, "_last_step_multiline", False
        ):
            print()
        self._last_step_multiline = False
        self._category_has_output = True
        dur_val = max(0.1, res.duration)
        time_tag = (
            f" {Colors.GRAY}({dur_val:.1f}s){Colors.RESET}" if show_duration else ""
        )

        sym, msg = self._resolve_step_display(
            label, res, module=module, verbose=self.verbose
        )
        marker = get_status_marker(sym)
        if sym in ("✓", "^") and (not msg or msg.lower() == label.lower()):
            msg_part = ""
        else:
            msg_part = f": {msg}" if msg else ""
        print(f"  {marker} {label}{msg_part}{time_tag}")

    def print_result(
        self,
        label: str,
        result: StepResult,
        module: Any | None = None,
        show_duration: bool = True,
    ):
        """Render an already completed result using the standard step style."""
        if not self.quiet:
            self._print_static_result(
                label, result, module=module, show_duration=show_duration
            )

    def print_interrupted(self):
        if self.quiet:
            return
        width = min(self.terminal_width, 80)
        prefix = "── Interrupted "
        fill = "─" * max(0, width - len(prefix))
        marker = get_status_marker("~")
        print()
        print(f"{Colors.BOLD_CYAN}{prefix}{fill}{Colors.RESET}")
        print(f"  {marker} Update cancelled by user.")
        print()
        print(f"{Colors.CYAN}" + "─" * width + f"{Colors.RESET}")

    def print_summary(
        self,
        results: list[dict[str, Any]],
        total_elapsed: float,
        interrupted: bool = False,
    ):
        width = min(self.terminal_width, 80)
        minutes = int(total_elapsed // 60)
        seconds = int(total_elapsed % 60)
        duration_str = f"{minutes}m {seconds:02d}s" if minutes > 0 else f"{seconds}s"
        is_interrupted = interrupted or any(
            r["result"].status in ("interrupted", "cancelled") for r in results
        )

        package_updates = [
            r
            for r in results
            if r["result"].status == "ok"
            and r["result"].message
            and getattr(r.get("module"), "category", "") != "System Protection"
            and r.get("key") != "snapshot"
        ]
        all_warning_items = [
            r
            for r in results
            if r["result"].status in ("warning", "skipped") or r["result"].warnings
        ]
        warning_items = all_warning_items if self.verbose else []
        error_items = [r for r in results if r["result"].status == "error"]

        def print_details(lines: list[str], indent: str = "      "):
            printed = set()
            for detail in lines:
                for line in str(detail).strip().splitlines():
                    normalized = line.strip()
                    if normalized and normalized not in printed:
                        printed.add(normalized)
                        print(f"{indent}- {normalized}")

        def diagnostic_lines(output: str) -> list[str]:
            lines = [
                line.rstrip() for line in output.strip().splitlines() if line.strip()
            ]
            if len(lines) > 20:
                lines = ["... (previous output omitted) ..."] + lines[-20:]
            return lines

        def print_diagnostic_heading(title: str):
            prefix = f"── {title} "
            fill = "─" * max(0, width - len(prefix))
            print(f"{Colors.BOLD_CYAN}{prefix}{fill}{Colors.RESET}")

        # ── 1. Summary Section ────────────────────────────────────────────────
        summary_prefix = f"── Summary ─ {duration_str} "
        summary_dashes = "─" * max(0, width - len(summary_prefix))
        print()
        print(
            f"{Colors.BOLD}{Colors.CYAN}{summary_prefix}{summary_dashes}{Colors.RESET}"
        )
        if package_updates:
            marker = get_status_marker("✓")
            print(f"  {marker} Updated components:")
            for item in package_updates:
                res = item["result"]
                msg_text = self._clean_ok_message(item["name"], res.message)
                if is_single_entity_module(item):
                    print(f"    • {item['name']}: {msg_text}")
                else:
                    if res.details and not any(c.isdigit() for c in msg_text):
                        valid = [
                            d
                            for d in res.details
                            if d
                            and not str(d).strip().startswith("... and")
                            and not str(d).strip().startswith("and ")
                            and not str(d).strip().startswith("(+")
                        ]
                        if valid:
                            unit = get_module_unit_name(item, len(valid))
                            msg_text = f"{len(valid)} {unit} updated"
                    print(f"    • {item['name']}: {msg_text}")
                    formatted_details = format_package_list(
                        res.details, msg_text, limit=10
                    )
                    for detail in formatted_details:
                        print(f"      - {detail}")
        else:
            marker = get_status_marker("—")
            print(f"  {marker} All components are up to date.")

        reboot_items = [
            r for r in results if getattr(r.get("result"), "reboot_required", False)
        ]
        if reboot_items:
            print()
            print_diagnostic_heading("Reboot")
            marker = get_status_marker("^")
            print(f"  {marker} Reboot required:")
            for item in reboot_items:
                triggers = get_reboot_trigger_details(item)
                if triggers:
                    inline_triggers = format_package_list_inline(triggers, limit=5)
                    print(f"    • {item['name']}: {inline_triggers}")
                else:
                    msg = item["result"].message
                    if msg and msg.lower() not in ("updated", "up to date"):
                        print(f"    • {item['name']}: {msg}")
                    else:
                        print(f"    • {item['name']}")

        # Warning details stay hidden in normal mode; keep this existing contract.
        if warning_items:
            print()
            print_diagnostic_heading("Warnings")
            marker = get_status_marker("!")
            print(f"  {marker} Component warnings:")
            for item in warning_items:
                res = item["result"]
                if res.status == "skipped":
                    message = "skipped"
                    msg_detail = (
                        [res.message]
                        if res.message and res.message.lower() != "skipped"
                        else []
                    )
                    details = msg_detail + list(res.details)
                elif res.status == "ok":
                    message = "warning"
                    details = []
                else:
                    message = "warning"
                    details = list(res.details)
                details.extend(res.warnings)
                details.extend(diagnostic_lines(res.error_output))
                if (
                    res.status == "warning"
                    and res.message
                    and res.message.lower() != "warning"
                ):
                    details.insert(0, res.message)
                print(f"    • {item['name']}: {message}")
                print_details(details, indent="      ")

        if error_items:
            print()
            print_diagnostic_heading("Errors")
            marker = get_status_marker("✗")
            print(f"  {marker} Failed components:")
            for item in error_items:
                res = item["result"]
                details = (
                    list(res.details)
                    + list(res.warnings)
                    + diagnostic_lines(res.error_output)
                )
                if not details and res.message and res.message.lower() != "failed":
                    details.append(res.message)
                print(f"    • {item['name']}: failed")
                print_details(details, indent="      ")

        if is_interrupted:
            print()
            print_diagnostic_heading("Interrupted")
            interrupted_marker = get_status_marker("~")
            print(f"  {interrupted_marker} Update cancelled by user.")

        print()
        print(f"{Colors.CYAN}" + "─" * width + f"{Colors.RESET}")


SINGLE_ENTITY_NAMES = {
    "nuvio desktop",
    "oh my zsh",
    "systemupdater",
    "self update",
    "pip",
    "python pip",
    "poetry",
    "python poetry",
    "ghcup",
    "ghcup (haskell)",
    "flutter",
    "flutter sdk",
    "pyenv",
    "pyenv runtimes",
    "sdkman",
    "sdkman (java/jvm)",
    "manual pages db",
    "manual pages database",
}

SINGLE_ENTITY_KEYS = {
    "nuvio",
    "omz",
    "self_update",
    "pip",
    "poetry",
    "ghcup",
    "flutter",
    "pyenv",
    "sdkman",
    "maintenance",
    "mandb",
}

MODULE_UNIT_NAMES: dict[str, tuple[str, str]] = {
    "gearlever": ("appimage", "appimages"),
    "firmware": ("device", "devices"),
    "proton": ("runner", "runners"),
    "distrobox": ("container", "containers"),
    "docker": ("image", "images"),
    "podman": ("container", "containers"),
    "vagrant": ("box", "boxes"),
    "rustup": ("toolchain", "toolchains"),
    "cargo": ("crate", "crates"),
    "gem": ("gem", "gems"),
    "skills": ("skill", "skills"),
    "antigravity": ("extension", "extensions"),
    "vscode": ("extension", "extensions"),
    "cursor": ("extension", "extensions"),
    "codium": ("extension", "extensions"),
    "gh": ("extension", "extensions"),
    "neovim": ("plugin", "plugins"),
    "micro": ("plugin", "plugins"),
    "tmux": ("plugin", "plugins"),
    "asdf": ("plugin", "plugins"),
    "zinit": ("plugin", "plugins"),
    "fisher": ("plugin", "plugins"),
    "helix": ("grammar", "grammars"),
    "git": ("repository", "repositories"),
    "snapshot": ("snapshot", "snapshots"),
    "snap": ("snap", "snaps"),
    "uv": ("tool", "tools"),
    "pipx": ("app", "apps"),
}


def get_module_unit_name(item_meta: dict[str, Any], count: int = 1) -> str:
    """Return lowercase unit noun (singular or plural) for a given module."""
    mod = item_meta.get("module")
    if mod is not None:
        if count == 1 and getattr(mod, "unit_name", None):
            return str(mod.unit_name).lower()
        if count != 1 and getattr(mod, "unit_name_plural", None):
            return str(mod.unit_name_plural).lower()

    key = str(item_meta.get("key") or "").lower().strip()
    if not key and mod is not None:
        key = getattr(mod, "key", "").lower().strip()

    name = str(item_meta.get("name") or "").lower().strip()
    if not name and mod is not None:
        name = getattr(mod, "name", "").lower().strip()

    pair = MODULE_UNIT_NAMES.get(key)
    if not pair:
        if "extension" in name or name in (
            "vscode",
            "cursor",
            "vscodium",
            "antigravity",
            "github cli",
        ):
            pair = ("extension", "extensions")
        elif "container" in name or name in ("distrobox", "podman"):
            pair = ("container", "containers")
        elif "runner" in name or name == "protonplus":
            pair = ("runner", "runners")
        elif "plugin" in name or name in (
            "asdf",
            "neovim",
            "micro",
            "tmux",
            "zinit",
            "fisher",
        ):
            pair = ("plugin", "plugins")
        elif "toolchain" in name or name == "rust":
            pair = ("toolchain", "toolchains")
        elif "agent" in name or "skill" in name:
            pair = ("skill", "skills")
        elif "gear lever" in name or "appimage" in name:
            pair = ("appimage", "appimages")
        elif "firmware" in name:
            pair = ("device", "devices")
        elif "docker" in name:
            pair = ("image", "images")
        elif "box" in name or name == "vagrant":
            pair = ("box", "boxes")
        elif "gem" in name or name == "ruby":
            pair = ("gem", "gems")
        elif "crate" in name or "binary" in name or name == "cargo":
            pair = ("crate", "crates")
        elif "grammar" in name or name == "helix":
            pair = ("grammar", "grammars")
        elif "repository" in name or "repo" in name or name == "git":
            pair = ("repository", "repositories")
        elif name == "uv":
            pair = ("tool", "tools")
        elif name == "pipx":
            pair = ("app", "apps")
        else:
            pair = ("package", "packages")

    return pair[0] if count == 1 else pair[1]


def is_single_entity_module(item: dict[str, Any]) -> bool:
    mod = item.get("module")
    if mod is not None and getattr(mod, "is_single_entity", False):
        return True
    key = str(item.get("key") or "").lower().strip()
    if key in SINGLE_ENTITY_KEYS:
        return True
    name = str(item.get("name") or "").lower().strip()
    return name in SINGLE_ENTITY_NAMES


def extract_single_entity_version(details: list[str], message: str) -> str:
    """Return standard status label for single-purpose modules."""
    return "updated"


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
    # Core system check
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

    # Penalize subpackages / secondary components
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
    cleaned = []
    seen = set()
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
    cleaned = []
    seen = set()
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

    # First check if specific packages matched the reboot trigger
    triggers = get_reboot_trigger_packages(res.details)
    if triggers:
        return triggers

    # For modules with details where items are relevant (e.g. firmware or macos update)
    mod_key = str(item.get("key") or getattr(item.get("module"), "key", "")).lower()
    if mod_key in ("firmware", "device_firmware", "macos_update", "system"):
        valid = []
        seen = set()
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
