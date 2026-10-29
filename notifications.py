"""
Desktop notifications for SystemUpdater.
Cross-platform support for Linux (notify-send) and macOS (osascript).
"""

from __future__ import annotations

import platform
import shutil
import subprocess


def send_notification(
    title: str,
    message: str,
    urgency: str = "normal",  # "low", "normal", "critical"
    app_name: str = "SystemUpdater",
) -> bool:
    """Send a native desktop notification on Linux or macOS.

    Returns True if the notification command completed successfully, False otherwise.
    """
    sys_name = platform.system()

    if sys_name == "Linux":
        notifier = shutil.which("notify-send")
        if not notifier:
            return False

        urgency_arg = urgency if urgency in ("low", "normal", "critical") else "normal"
        cmd = [notifier, "-a", app_name, "-u", urgency_arg, title, message]
        try:
            res = subprocess.run(cmd, check=False, capture_output=True, timeout=5)
            return res.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    if sys_name == "Darwin":
        osascript = shutil.which("osascript")
        if not osascript:
            return False

        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
        script = f'display notification "{safe_message}" with title "{safe_title}"'
        try:
            res = subprocess.run(
                [osascript, "-e", script],
                check=False,
                capture_output=True,
                timeout=5,
            )
            return res.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    return False
