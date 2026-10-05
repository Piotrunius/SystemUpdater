"""
Terminal UI and step progress renderer for SystemUpdater.
Strictly adheres to flicker-free ANSI standards and zero-emoji policy.
"""

import os
import sys
import time
import threading
from typing import Callable, Any, Optional, Dict, List


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"

    BOLD_GREEN = "\033[1;32m"
    BOLD_RED = "\033[1;31m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_CYAN = "\033[1;36m"


RUNNING_FRAMES = [
    f"{Colors.DIM}[{Colors.RESET}{Colors.BOLD_CYAN}:{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
    f"{Colors.DIM}[{Colors.RESET}{Colors.CYAN}:{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
    f"{Colors.DIM}[{Colors.RESET}{Colors.BLUE}:{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
    f"{Colors.DIM}[{Colors.RESET}{Colors.CYAN}:{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
]


class StepResult:
    def __init__(
        self,
        status: str,  # "ok", "unchanged", "warning", "error", "skipped"
        message: str = "",
        details: Optional[List[str]] = None,
        duration: float = 0.0,
        error_output: str = "",
    ):
        self.status = status
        self.message = message
        self.details = details or []
        self.duration = duration
        self.error_output = error_output


class UI:
    def __init__(self, is_interactive: Optional[bool] = None, quiet: bool = False):
        self.is_tty = is_interactive if is_interactive is not None else sys.stdout.isatty()
        self.terminal_width = self._get_width()
        self.quiet = quiet

    def _get_width(self) -> int:
        try:
            return os.get_terminal_size().columns
        except Exception:
            return 80

    def print_header(self, title: str = "System Updater"):
        if self.quiet:
            return
        width = min(self.terminal_width, 80)
        time_str = time.strftime("%H:%M:%S")
        print()
        print(f"{Colors.BOLD}{Colors.CYAN}── {title} ─ {time_str} {Colors.RESET}" + "─" * max(0, width - len(title) - len(time_str) - 8))
        print()

    def run_step(
        self,
        label: str,
        target: Callable[[], StepResult],
        ctx: Optional[Any] = None,
        module: Optional[Any] = None,
    ) -> StepResult:
        from modules.base import detect_warning

        if self.quiet:
            start_time = time.time()
            try:
                res = target()
            except Exception as e:
                res = StepResult("error", str(e), error_output=str(e))
            if res.status == "error":
                is_core = module is not None and getattr(module, "category", "") == "System Core"
                if not is_core:
                    warn_reason = detect_warning(f"{res.message}\n{res.error_output}")
                    if warn_reason:
                        res.status = "warning"
                        res.message = warn_reason
            res.duration = time.time() - start_time
            return res

        is_verbose = ctx is not None and getattr(ctx, "verbose", False)
        if not self.is_tty or is_verbose:
            commands_printed = False

            def on_cmd_start():
                nonlocal commands_printed
                if not commands_printed:
                    commands_printed = True
                    frame = f"{Colors.DIM}[{Colors.RESET}{Colors.BOLD_CYAN}:{Colors.RESET}{Colors.DIM}]{Colors.RESET}"
                    print(f"  {frame} {label}...")

            if ctx is not None:
                ctx._on_command_start = on_cmd_start

            start_time = time.time()
            try:
                res = target()
            except Exception as e:
                res = StepResult("error", str(e), error_output=str(e))
            finally:
                if ctx is not None:
                    ctx._on_command_start = None

            if res.status == "error":
                is_core = module is not None and getattr(module, "category", "") == "System Core"
                if not is_core:
                    warn_reason = detect_warning(f"{res.message}\n{res.error_output}")
                    if warn_reason:
                        res.status = "warning"
                        res.message = warn_reason

            res.duration = time.time() - start_time

            if commands_printed:
                dur_val = max(0.1, res.duration)
                time_tag = f"{Colors.GRAY}({dur_val:.1f}s){Colors.RESET}"
                if res.status == "ok":
                    msg_text = self._clean_ok_message(label, res.message)
                    print(f"      {Colors.DIM}[{Colors.RESET}{Colors.BOLD_GREEN}✓{Colors.RESET}{Colors.DIM}]{Colors.RESET} {msg_text or 'updated'} {time_tag}")
                elif res.status == "unchanged":
                    msg = res.message if res.message else "up to date"
                    print(f"      {Colors.DIM}[—]{Colors.RESET} {msg} {time_tag}")
                elif res.status == "warning":
                    print(f"      {Colors.DIM}[{Colors.RESET}{Colors.BOLD_YELLOW}!{Colors.RESET}{Colors.DIM}]{Colors.RESET} {res.message} {time_tag}")
                else:  # error
                    print(f"      {Colors.DIM}[{Colors.RESET}{Colors.BOLD_RED}✗{Colors.RESET}{Colors.DIM}]{Colors.RESET} {res.message or 'failed'} {time_tag}")
            else:
                self._print_static_result(label, res)

            return res

        # Interactive running execution with [:] indicator
        stop_event = threading.Event()
        current_status = {"text": label}
        if ctx is not None and hasattr(ctx, "status_updater"):
            ctx.status_updater = lambda msg: current_status.__setitem__("text", f"{label}: {msg}" if msg else label)

        start_time = time.time()
        spinner_thread = threading.Thread(
            target=self._spinner_worker,
            args=(stop_event, current_status),
            daemon=True,
        )

        spinner_thread.start()

        try:
            res = target()
        except Exception as e:
            res = StepResult("error", str(e), error_output=str(e))
        finally:
            if ctx is not None and hasattr(ctx, "status_updater"):
                ctx.status_updater = None
            stop_event.set()
            spinner_thread.join()

        res.duration = time.time() - start_time
        # Clear the status line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

        if res.status == "error":
            is_core = module is not None and getattr(module, "category", "") == "System Core"
            if not is_core:
                warn_reason = detect_warning(f"{res.message}\n{res.error_output}")
                if warn_reason:
                    res.status = "warning"
                    res.message = warn_reason

        self._print_static_result(label, res)
        return res

    def _spinner_worker(self, stop_event: threading.Event, status: Dict[str, str]):
        frame_idx = 0
        while not stop_event.is_set():
            frame = RUNNING_FRAMES[frame_idx % len(RUNNING_FRAMES)]
            text = status["text"]
            sys.stdout.write(f"\r\033[K  {frame} {text}...")
            sys.stdout.flush()
            frame_idx += 1
            time.sleep(0.15)

    def print_category(self, title: str):
        if self.quiet:
            return
        width = min(self.terminal_width, 80)
        print()
        print(f"{Colors.BOLD}{Colors.CYAN}── {title} " + "─" * max(0, width - len(title) - 4) + Colors.RESET)

    def _clean_ok_message(self, label: str, msg: str) -> str:
        if not msg:
            return "updated"
        msg_clean = msg.strip()
        label_lower = label.lower().strip()
        msg_lower = msg_clean.lower()
        if (
            msg_lower == label_lower
            or msg_lower in (f"{label_lower} updated", f"{label_lower} upgraded", f"{label_lower} upgraded successfully")
            or (msg_lower.endswith(" updated") and msg_lower[:-8].strip() in label_lower)
            or (msg_lower.endswith(" upgraded") and msg_lower[:-9].strip() in label_lower)
            or (msg_lower.endswith(" upgraded successfully") and msg_lower[:-22].strip() in label_lower)
            or (msg_lower.endswith(" updated successfully") and msg_lower[:-20].strip() in label_lower)
        ):
            return "updated"
        return msg_clean

    def _print_static_result(self, label: str, res: StepResult):
        dur_val = max(0.1, res.duration)
        time_tag = f"{Colors.GRAY}({dur_val:.1f}s){Colors.RESET}"

        if res.status == "ok":
            msg_text = self._clean_ok_message(label, res.message)
            msg = f": {msg_text}" if msg_text else ""
            print(f"  {Colors.DIM}[{Colors.RESET}{Colors.BOLD_GREEN}✓{Colors.RESET}{Colors.DIM}]{Colors.RESET} {label}{msg} {time_tag}")
        elif res.status == "unchanged":
            msg = res.message if res.message else "up to date"
            print(f"  {Colors.DIM}[—]{Colors.RESET} {label}: {msg} {time_tag}")
        elif res.status == "skipped":
            msg = f": {res.message}" if res.message else ""
            print(f"  {Colors.DIM}[—]{Colors.RESET} {label}{msg}")
        elif res.status == "warning":
            print(f"  {Colors.DIM}[{Colors.RESET}{Colors.BOLD_YELLOW}!{Colors.RESET}{Colors.DIM}]{Colors.RESET} {label}: {res.message} {time_tag}")
        else:  # error
            print(f"  {Colors.DIM}[{Colors.RESET}{Colors.BOLD_RED}✗{Colors.RESET}{Colors.DIM}]{Colors.RESET} {label}: {res.message or 'failed'} {time_tag}")

    def print_result(self, label: str, result: StepResult):
        """Render an already completed result using the standard step style."""
        if not self.quiet:
            self._print_static_result(label, result)

    def print_summary(self, results: List[Dict[str, Any]], total_elapsed: float):
        width = min(self.terminal_width, 80)
        minutes = int(total_elapsed // 60)
        seconds = int(total_elapsed % 60)
        duration_str = f"{minutes}m {seconds:02d}s" if minutes > 0 else f"{seconds}s"

        package_updates = [
            r for r in results
            if r["result"].status == "ok"
            and r["result"].message
            and getattr(r.get("module"), "category", "") != "System Protection"
            and r.get("key") != "snapshot"
        ]
        snapshot_result = next((r for r in results if r.get("key") == "snapshot"), None)
        snapshot_created = (
            snapshot_result is not None
            and snapshot_result["result"].status == "ok"
            and "created" in (snapshot_result["result"].message or "").lower()
        )

        warning_items = [r for r in results if r["result"].status == "warning"]
        error_items = [r for r in results if r["result"].status == "error"]

        # ── 1. Summary Section ────────────────────────────────────────────────
        print()
        print(f"{Colors.BOLD}{Colors.CYAN}── Summary ─ {duration_str} " + "─" * max(0, width - len(duration_str) - 14) + Colors.RESET)

        if package_updates:
            print("  Updates applied:")
            for item in package_updates:
                msg_text = self._clean_ok_message(item['name'], item['result'].message)
                print(f"    • {item['name']}: {msg_text}")
                for d in item['result'].details:
                    print(f"      - {d}")
        elif not warning_items and not error_items:
            print("  All components are fully up to date.")
        else:
            print("  No package updates were applied.")

        print(f"{Colors.CYAN}" + "─" * width + f"{Colors.RESET}")

        # ── 2. Warnings Section (only if warnings occurred) ───────────────────
        if warning_items:
            print()
            title = "Warnings"
            print(f"{Colors.BOLD}{Colors.CYAN}── {title} " + "─" * max(0, width - len(title) - 4) + Colors.RESET)
            for item in warning_items:
                res = item["result"]
                print(f"  • {item['name']}: {res.message}")
                for d in res.details:
                    print(f"    - {d}")
            print(f"{Colors.CYAN}" + "─" * width + f"{Colors.RESET}")

        # ── 3. Errors Section (only if failures occurred) ─────────────────────
        if error_items:
            print()
            title = "Errors"
            print(f"{Colors.BOLD}{Colors.CYAN}── {title} " + "─" * max(0, width - len(title) - 4) + Colors.RESET)
            for item in error_items:
                res = item["result"]
                print(f"  • {item['name']}: {res.message or 'failed'}")
                if res.error_output:
                    lines = res.error_output.strip().splitlines()
                    if len(lines) > 20:
                        lines = ["... (previous output omitted) ..."] + lines[-20:]
                    for l in lines:
                        print(f"    {Colors.DIM}{l}{Colors.RESET}")
            print(f"{Colors.CYAN}" + "─" * width + f"{Colors.RESET}")

        print()
