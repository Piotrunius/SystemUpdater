"""
Base classes and execution context for SystemUpdater modules.
"""

import os
import re
import shutil
import subprocess
import time
import threading
from typing import List, Tuple, Optional, Dict

NON_FATAL_PATTERNS = [
    (re.compile(r"(api limit reached|rate limit exceeded|too many requests|http[s]? (status )?429)", re.I), "API rate limit reached"),
    (re.compile(r"(could not resolve host|temporary failure in name resolution|connection timed out|timed out after|operation timed out)", re.I), "Network connection timed out"),
    (re.compile(r"(connection refused|network is unreachable|failed to connect to|unable to connect to)", re.I), "Network host unreachable"),
    (re.compile(r"(502 bad gateway|503 service temporarily unavailable|504 gateway timeout|mirror sync in progress)", re.I), "Remote mirror temporarily unavailable"),
    (re.compile(r"(ssl certificate problem|certificate has expired|unable to get local issuer certificate)", re.I), "SSL certificate error"),
    (re.compile(r"(resource temporarily unavailable|database is locked|another instance is running|lock is held by)", re.I), "Resource temporarily locked"),
    (re.compile(r"(bad credentials|authentication failed|invalid token|token expired|permission denied \(publickey\))", re.I), "Authentication/token issue"),
]

def detect_warning(text: str) -> Optional[str]:
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


_os_release_cache: Optional[Dict[str, str]] = None


def get_os_release() -> Dict[str, str]:
    global _os_release_cache
    if _os_release_cache is not None:
        return _os_release_cache

    info: Dict[str, str] = {}
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
            except Exception:
                pass

    _os_release_cache = info
    return info



class UpdateContext:
    def __init__(self, dry_run: bool = False, force: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.force = force
        self.verbose = verbose
        self.env = os.environ.copy()
        # Ensure non-interactive environment for all tools
        self.env["DEBIAN_FRONTEND"] = "noninteractive"
        self.env["CI"] = "1"
        self.env["NONINTERACTIVE"] = "1"
        self.status_updater = None

    def set_substatus(self, msg: str):
        if self.status_updater:
            self.status_updater(msg)

    def notify_command_started(self):
        cb = getattr(self, "_on_command_start", None)
        if callable(cb):
            cb()

    def print_verbose(self, text: str):
        if self.verbose:
            self.notify_command_started()
            print(f"      \033[2m{text}\033[0m")

    def run_cmd(
        self,
        cmd: List[str],
        timeout: Optional[int] = 180,
        env_extra: Optional[Dict[str, str]] = None,
        read_only: bool = False,
        retries: int = 0,
        retry_delay: float = 2.0,
    ) -> Tuple[int, str, str]:
        """
        Runs a command safely and captures output with stdin=DEVNULL to prevent hangs.
        If read_only is True, executes even during dry_run (for system queries).
        Includes automatic retry for transient glitches if retries > 0.
        """
        if self.dry_run and not read_only:
            return 0, f"[DRY-RUN] Would run: {' '.join(cmd)}", ""

        run_env = self.env.copy()
        if env_extra:
            run_env.update(env_extra)

        attempts = 1 + max(0, retries)
        last_code = 1
        last_out = ""
        last_err = ""

        is_verbose = self.verbose and not read_only
        if is_verbose:
            self.notify_command_started()
            print(f"      \033[2m$ {' '.join(cmd)}\033[0m")

        for attempt in range(attempts):
            if is_verbose:
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                        env=run_env,
                    )
                    out_chunks = []
                    err_chunks = []

                    def stream_reader(pipe, accumulator):
                        try:
                            for line in iter(pipe.readline, ""):
                                accumulator.append(line)
                                clean = line.rstrip("\r\n")
                                if clean:
                                    print(f"        \033[2m{clean}\033[0m")
                        except Exception:
                            pass
                        finally:
                            pipe.close()

                    t_out = threading.Thread(target=stream_reader, args=(proc.stdout, out_chunks), daemon=True)
                    t_err = threading.Thread(target=stream_reader, args=(proc.stderr, err_chunks), daemon=True)
                    t_out.start()
                    t_err.start()

                    try:
                        proc.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                        t_out.join(timeout=0.5)
                        t_err.join(timeout=0.5)
                        return 124, "".join(out_chunks), f"Command timed out after {timeout}s: {' '.join(cmd)}"

                    t_out.join(timeout=1.0)
                    t_err.join(timeout=1.0)
                    last_code = proc.returncode
                    last_out = "".join(out_chunks)
                    last_err = "".join(err_chunks)
                    if last_code == 0:
                        return 0, last_out, last_err
                except Exception as e:
                    last_code = 1
                    last_out = ""
                    last_err = str(e)
            else:
                try:
                    proc = subprocess.run(
                        cmd,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=run_env,
                        timeout=timeout,
                    )
                    last_code = proc.returncode
                    last_out = proc.stdout
                    last_err = proc.stderr
                    if last_code == 0:
                        return 0, last_out, last_err
                except subprocess.TimeoutExpired:
                    last_code = 124
                    last_out = ""
                    last_err = f"Command timed out after {timeout}s: {' '.join(cmd)}"
                except Exception as e:
                    last_code = 1
                    last_out = ""
                    last_err = str(e)

            if attempt < attempts - 1:
                time.sleep(retry_delay)

        return last_code, last_out, last_err

    def which(self, binary_name: str) -> Optional[str]:
        return shutil.which(binary_name)


class BaseModule:
    name: str = "Base Module"
    key: str = "base"
    aliases: List[str] = []
    category: str = "General"
    description: str = ""
    requires_sudo: bool = False

    def is_available(self, ctx: UpdateContext) -> bool:
        return True

    def availability_status(self, ctx: UpdateContext) -> str:
        return "[Active]" if self.is_available(ctx) else "[Not Installed]"

    def run(self, ctx: UpdateContext):
        raise NotImplementedError
