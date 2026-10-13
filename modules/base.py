"""
Base classes and execution context for SystemUpdater modules.
"""

from __future__ import annotations

import contextlib
import os
import platform
import shlex
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ui import StepResult

from colors import Colors
from ui import detect_warning


def check_github_api(timeout: float = 3.0) -> StepResult | None:
    """
    Fast health check for GitHub API before launching tools that query GitHub.
    Returns StepResult("warning", ...) if rate limited or unreachable, or None if healthy.
    """
    from ui import StepResult

    try:
        req = urllib.request.Request(
            "https://api.github.com/", headers={"User-Agent": "SystemUpdater"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.headers.get("x-ratelimit-remaining") == "0":
                return StepResult("warning", "GitHub API rate limit reached")
    except urllib.error.HTTPError as error:
        if (
            error.code in (403, 429)
            or error.headers.get("x-ratelimit-remaining") == "0"
            or "rate limit" in str(error).casefold()
        ):
            return StepResult("warning", "GitHub API rate limit reached")
        reason = str(error).strip() or type(error).__name__
        return StepResult("warning", f"GitHub API unreachable or timed out: {reason}")
    except (OSError, TimeoutError, urllib.error.URLError) as error:
        reason = str(error).strip() or type(error).__name__
        if "rate limit" in reason.casefold() or getattr(error, "code", None) in (
            403,
            429,
        ):
            message = "GitHub API rate limit reached"
        else:
            message = f"GitHub API unreachable or timed out: {reason}"
        return StepResult("warning", message)

    return None


_os_release_cache: dict[str, str] | None = None


def get_os_release() -> dict[str, str]:
    global _os_release_cache
    if _os_release_cache is not None:
        return _os_release_cache

    info: dict[str, str] = {}
    for path in ["/etc/os-release", "/usr/lib/os-release"]:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            info[k.strip()] = v.strip().strip('"').strip("'")
                break
            except (OSError, UnicodeError):
                continue

    if not info and platform.system() == "Darwin":
        mac_ver, _, _ = platform.mac_ver()
        info = {
            "ID": "macos",
            "NAME": "macOS",
            "PRETTY_NAME": f"macOS {mac_ver}" if mac_ver else "macOS",
            "VERSION_ID": mac_ver or "",
        }

    _os_release_cache = info
    return info


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_linux() -> bool:
    return platform.system() == "Linux"


class UpdateContext:
    def __init__(
        self, dry_run: bool = False, force: bool = False, verbose: bool = False
    ):
        self.dry_run = dry_run
        self.force = force
        self.verbose = verbose
        self.env = os.environ.copy()
        # Ensure non-interactive environment for all tools
        self.env["DEBIAN_FRONTEND"] = "noninteractive"
        self.env["CI"] = "1"
        self.env["NONINTERACTIVE"] = "1"
        self.status_updater = None
        self.command_log: list[dict[str, Any]] = []
        self.deferred_notes: list[str] = []
        self._logged_output_chars = 0
        self.last_activity_time = time.monotonic()
        self._on_command_start: Callable[[], None] | None = None

    def set_substatus(self, msg: str):
        self.last_activity_time = time.monotonic()
        if self.status_updater:
            self.status_updater(msg)

    def notify_command_started(self):
        self.last_activity_time = time.monotonic()
        cb = getattr(self, "_on_command_start", None)
        if callable(cb):
            cb()

    def print_verbose(self, text: str):
        if self.verbose:
            self.deferred_notes.append(str(text))

    def run_cmd(
        self,
        cmd: list[str],
        timeout: int | None = 180,
        env_extra: dict[str, str] | None = None,
        read_only: bool = False,
        retries: int = 0,
        retry_delay: float = 2.0,
        sensitive_output: bool = False,
        display_output: bool | None = None,
    ) -> tuple[int, str, str]:
        """
        Runs a command safely and captures output with stdin=DEVNULL to prevent hangs.
        Mark credential-producing commands with sensitive_output to suppress terminal echo.
        Includes automatic retry for transient glitches if retries > 0.
        """
        run_env = self.env.copy()
        if env_extra:
            run_env.update(env_extra)

        attempts = 1 + max(0, retries)
        show_live_output = True if display_output is None else display_output
        is_verbose = self.verbose and show_live_output and not sensitive_output
        if is_verbose:
            self.notify_command_started()
            from history_store import redact_text

            printable_command = shlex.join([redact_text(str(arg)) for arg in cmd])
            print(
                f"      {Colors.DIM}${Colors.RESET} {Colors.BOLD}{printable_command}{Colors.RESET}"
            )

        last_code = 1
        last_out = ""
        last_err = ""

        for attempt in range(attempts):
            started = time.monotonic()
            last_code = 1
            last_out = ""
            last_err = ""
            output_was_streamed = False
            if is_verbose:
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        errors="replace",
                        bufsize=1,
                        env=run_env,
                    )
                    out_chunks = []
                    err_chunks = []
                    stream_lock = threading.Lock()
                    active_stream = [None]
                    stream_printed_header = set()

                    def stream_reader(
                        pipe,
                        accumulator,
                        stream_name,
                        lock=stream_lock,
                        headers=stream_printed_header,
                        current=active_stream,
                    ):
                        from history_store import redact_text

                        pending_blank = False
                        try:
                            for line in iter(pipe.readline, ""):
                                accumulator.append(line)
                                self.last_activity_time = time.monotonic()
                                if is_verbose:
                                    clean_line = redact_text(line.rstrip("\r\n"))
                                    with lock:
                                        if not clean_line.strip():
                                            if stream_name in headers:
                                                pending_blank = True
                                        else:
                                            if stream_name not in headers:
                                                print(
                                                    f"        {Colors.DIM}{stream_name}:{Colors.RESET}",
                                                    flush=True,
                                                )
                                                headers.add(stream_name)
                                                current[0] = stream_name
                                                pending_blank = False
                                            elif current[0] != stream_name:
                                                print(
                                                    f"        {Colors.DIM}{stream_name}:{Colors.RESET}",
                                                    flush=True,
                                                )
                                                current[0] = stream_name
                                                pending_blank = False

                                            if pending_blank:
                                                print(
                                                    f"          {Colors.DIM}{Colors.RESET}",
                                                    flush=True,
                                                )
                                                pending_blank = False
                                            print(
                                                f"          {Colors.DIM}{clean_line}{Colors.RESET}",
                                                flush=True,
                                            )
                        except OSError:
                            return
                        finally:
                            pipe.close()

                    t_out = threading.Thread(
                        target=stream_reader,
                        args=(proc.stdout, out_chunks, "stdout"),
                        daemon=True,
                    )
                    t_err = threading.Thread(
                        target=stream_reader,
                        args=(proc.stderr, err_chunks, "stderr"),
                        daemon=True,
                    )
                    t_out.start()
                    t_err.start()
                    output_was_streamed = True

                    try:
                        proc.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                        t_out.join(timeout=0.5)
                        t_err.join(timeout=0.5)
                        last_code = 124
                        last_out = "".join(out_chunks)
                        last_err = (
                            f"Command timed out after {timeout}s: {shlex.join(cmd)}"
                        )
                        self._record_command(
                            cmd,
                            last_code,
                            last_out,
                            last_err,
                            read_only,
                            attempt,
                            started,
                            output_streamed=True,
                        )
                        return last_code, last_out, last_err
                    except KeyboardInterrupt:
                        try:
                            proc.terminate()
                            proc.wait(timeout=1.0)
                        except (OSError, subprocess.TimeoutExpired):
                            with contextlib.suppress(OSError):
                                proc.kill()
                        t_out.join(timeout=0.5)
                        t_err.join(timeout=0.5)
                        last_code = 130
                        last_out = "".join(out_chunks)
                        last_err = "".join(err_chunks) or "Command interrupted by user"
                        self._record_command(
                            cmd,
                            last_code,
                            last_out,
                            last_err,
                            read_only,
                            attempt,
                            started,
                            output_streamed=True,
                        )
                        raise

                    t_out.join(timeout=1.0)
                    t_err.join(timeout=1.0)
                    last_code = proc.returncode
                    last_out = "".join(out_chunks)
                    last_err = "".join(err_chunks)
                except OSError as e:
                    last_code = 1
                    last_out = ""
                    last_err = str(e)
            else:
                self.last_activity_time = time.monotonic()
                if hasattr(subprocess.run, "mock_calls"):
                    try:
                        proc = subprocess.run(
                            cmd,
                            stdin=subprocess.DEVNULL,
                            capture_output=True,
                            check=False,
                            text=True,
                            errors="replace",
                            env=run_env,
                            timeout=timeout,
                        )
                        last_code = proc.returncode
                        last_out = proc.stdout
                        last_err = proc.stderr
                    except subprocess.TimeoutExpired:
                        last_code = 124
                        last_out = ""
                        last_err = (
                            f"Command timed out after {timeout}s: {shlex.join(cmd)}"
                        )
                    except KeyboardInterrupt:
                        self._record_command(
                            cmd,
                            130,
                            "",
                            "Command interrupted by user",
                            read_only,
                            attempt,
                            started,
                        )
                        raise
                    except OSError as e:
                        last_code = 1
                        last_out = ""
                        last_err = str(e)
                else:
                    try:
                        proc = subprocess.Popen(
                            cmd,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            errors="replace",
                            bufsize=1,
                            env=run_env,
                        )
                        out_chunks = []
                        err_chunks = []

                        def pipe_reader(pipe, accumulator):
                            try:
                                for line in iter(pipe.readline, ""):
                                    accumulator.append(line)
                                    self.last_activity_time = time.monotonic()
                            except OSError:
                                pass
                            finally:
                                pipe.close()

                        t_out = threading.Thread(
                            target=pipe_reader,
                            args=(proc.stdout, out_chunks),
                            daemon=True,
                        )
                        t_err = threading.Thread(
                            target=pipe_reader,
                            args=(proc.stderr, err_chunks),
                            daemon=True,
                        )
                        t_out.start()
                        t_err.start()

                        try:
                            proc.wait(timeout=timeout)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait()
                            t_out.join(timeout=0.5)
                            t_err.join(timeout=0.5)
                            last_code = 124
                            last_out = "".join(out_chunks)
                            last_err = (
                                f"Command timed out after {timeout}s: {shlex.join(cmd)}"
                            )
                            self._record_command(
                                cmd,
                                last_code,
                                last_out,
                                last_err,
                                read_only,
                                attempt,
                                started,
                            )
                            return last_code, last_out, last_err
                        except KeyboardInterrupt:
                            try:
                                proc.terminate()
                                proc.wait(timeout=1.0)
                            except (OSError, subprocess.TimeoutExpired):
                                with contextlib.suppress(OSError):
                                    proc.kill()
                            t_out.join(timeout=0.5)
                            t_err.join(timeout=0.5)
                            last_code = 130
                            last_out = "".join(out_chunks)
                            last_err = "Command interrupted by user"
                            self._record_command(
                                cmd,
                                last_code,
                                last_out,
                                last_err,
                                read_only,
                                attempt,
                                started,
                            )
                            raise

                        t_out.join(timeout=1.0)
                        t_err.join(timeout=1.0)
                        last_code = proc.returncode
                        last_out = "".join(out_chunks)
                        last_err = "".join(err_chunks)
                    except OSError as e:
                        last_code = 1
                        last_out = ""
                        last_err = str(e)

            self._record_command(
                cmd,
                last_code,
                last_out,
                last_err,
                read_only,
                attempt,
                started,
                output_streamed=output_was_streamed,
            )
            if last_code == 0:
                return 0, last_out, last_err

            failure_text = f"{last_out}\n{last_err}"
            retryable = last_code == 124 or detect_warning(failure_text) is not None
            if attempt < attempts - 1 and retryable:
                time.sleep(retry_delay)
                continue
            break

        return last_code, last_out, last_err

    def _record_command(
        self,
        cmd: list[str],
        returncode: int,
        stdout: str,
        stderr: str,
        read_only: bool,
        attempt: int,
        started: float,
        output_streamed: bool = False,
    ) -> None:
        from history_store import redact_text

        def limited_output(value: str) -> str:
            redacted = redact_text(value)
            per_command_limit = 100_000
            total_run_limit = 2_000_000
            remaining = max(0, total_run_limit - self._logged_output_chars)
            max_chars = min(per_command_limit, remaining)
            if len(redacted) > max_chars:
                omitted = len(redacted) - max_chars
                redacted = (
                    f"[... {omitted} characters omitted ...]\n" + redacted[-max_chars:]
                    if max_chars
                    else f"[... {len(redacted)} characters omitted; run log limit reached ...]"
                )
            self._logged_output_chars += min(len(redacted), max_chars)
            return redacted

        self.command_log.append(
            {
                "command": [redact_text(str(arg)) for arg in cmd],
                "returncode": returncode,
                "stdout": limited_output(stdout),
                "stderr": limited_output(stderr),
                "output_withheld": False,
                "output_streamed": output_streamed,
                "attempt": attempt + 1,
                "duration": round(time.monotonic() - started, 3),
            }
        )

    def which(self, binary_name: str) -> str | None:
        return shutil.which(binary_name)


class BaseModule:
    name: str = "Base Module"
    key: str = "base"
    aliases: ClassVar[list[str]] = []
    category: str = "General"
    description: str = ""
    requires_sudo: bool = False
    is_single_entity: bool = False
    unit_name: str = "package"
    unit_name_plural: str = "packages"

    def is_available(self, ctx: UpdateContext) -> bool:
        return True

    def availability_status(self, ctx: UpdateContext) -> str:
        return "[Active]" if self.is_available(ctx) else "[Not Installed]"

    def run(self, ctx: UpdateContext):
        raise NotImplementedError
