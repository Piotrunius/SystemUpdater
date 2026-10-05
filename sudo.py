"""
Sudo credential manager and keepalive background loop for SystemUpdater.
Replaces Topgrade's pre_sudo and --sudoloop with a zero-leak daemon thread.
"""

import os
import subprocess
import threading
import time
from typing import Optional

_stop_event = threading.Event()
_keeper_thread: Optional[threading.Thread] = None


def is_sudo_active() -> bool:
    try:
        res = subprocess.run(["sudo", "-n", "true"], capture_output=True)
        return res.returncode == 0
    except Exception:
        return False


def init_sudo(interactive: bool = True) -> bool:
    """
    Ensures credentials are cached at the start.
    If interactive, prompts the user once cleanly.
    Starts a background keeper thread that refreshes every 50 seconds.
    """
    if os.geteuid() == 0:
        return True

    if not is_sudo_active():
        if not interactive:
            return False
        try:
            res = subprocess.run(["sudo", "-v"])
            if res.returncode != 0:
                return False
        except Exception:
            return False

    start_sudo_keeper()
    return True


def _keeper_worker():
    while not _stop_event.is_set():
        if _stop_event.wait(50):
            break
        try:
            subprocess.run(["sudo", "-n", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def start_sudo_keeper():
    global _keeper_thread
    if _keeper_thread is not None and _keeper_thread.is_alive():
        return
    _stop_event.clear()
    _keeper_thread = threading.Thread(target=_keeper_worker, daemon=True)
    _keeper_thread.start()


def stop_sudo_keeper():
    _stop_event.set()
    global _keeper_thread
    if _keeper_thread is not None:
        _keeper_thread.join(timeout=1.0)
