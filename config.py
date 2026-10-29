"""
Configuration loader for SystemUpdater.
Supports the XDG config directory using the standard library tomllib.
Provides full customization for modules, behavior, notifications, and custom commands.
"""

from __future__ import annotations

import os
import tomllib


def xdg_directory(variable: str, fallback: str) -> str:
    """Return an absolute XDG directory or its expanded default."""
    path = os.environ.get(variable, "")
    return path if path and os.path.isabs(path) else os.path.expanduser(fallback)


CONFIG_HOME = xdg_directory("XDG_CONFIG_HOME", "~/.config")
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_HOME, "sysupdate", "config.toml")


class Config:
    def __init__(self, config_path: str | None = None):
        self.disabled_keys: set[str] = set()
        self.skip_keys: list[str] = []
        self.only_keys: list[str] = []
        self.categories: list[str] = []
        self.skip_categories: list[str] = []
        self.pre_commands: dict[str, str] = {}
        self.commands: dict[str, str] = {}
        self.post_commands: dict[str, str] = {}
        self.git_repos: list[str] = []
        self.snapshot_cooldown_hours: int = 12
        self.reboot: bool = False
        self.quiet: bool = False
        self.verbose: bool = False
        self.no_sudo: bool = False
        self.no_snapshot: bool = False
        self.no_history: bool = False
        self.notifications_enabled: bool = False
        self.notifications_only_on_error_or_reboot: bool = False
        self.command_timeout: int | None = None
        self._explicit_config_path = config_path is not None
        self.config_path: str = (
            os.path.expanduser(config_path) if config_path else DEFAULT_CONFIG_PATH
        )
        self.load_error: str | None = None

        self._load_config()

    def _reset_defaults(self):
        self.disabled_keys.clear()
        self.skip_keys.clear()
        self.only_keys.clear()
        self.categories.clear()
        self.skip_categories.clear()
        self.pre_commands.clear()
        self.commands.clear()
        self.post_commands.clear()
        self.git_repos.clear()
        self.snapshot_cooldown_hours = 12
        self.reboot = False
        self.quiet = False
        self.verbose = False
        self.no_sudo = False
        self.no_snapshot = False
        self.no_history = False
        self.notifications_enabled = False
        self.notifications_only_on_error_or_reboot = False
        self.command_timeout = None

    def _load_config(self):
        target_path = self.config_path
        if not os.path.isfile(target_path):
            if self._explicit_config_path:
                self.load_error = (
                    "Configuration file does not exist or is not a regular file."
                )
            return
        if tomllib is None:
            self.load_error = "TOML configuration requires Python 3.11 or newer."
            return

        try:
            with open(target_path, "rb") as f:
                data = tomllib.load(f)

            # [misc] table (backward compatibility)
            misc = data.get("misc", {})
            if not isinstance(misc, dict):
                raise TypeError("[misc] must be a TOML table")

            if "disable" in misc:
                disabled = misc["disable"]
                if not isinstance(disabled, list) or not all(
                    isinstance(key, str) for key in disabled
                ):
                    raise ValueError("misc.disable must be a list of strings")
                self.disabled_keys = {key.lower().strip() for key in disabled}

            if "cooldown_hours" in misc:
                cooldown = misc["cooldown_hours"]
                if (
                    isinstance(cooldown, bool)
                    or not isinstance(cooldown, int)
                    or cooldown < 0
                ):
                    raise ValueError(
                        "misc.cooldown_hours must be a non-negative integer"
                    )
                self.snapshot_cooldown_hours = cooldown

            if "command_timeout" in misc:
                timeout_val = misc["command_timeout"]
                if (
                    isinstance(timeout_val, bool)
                    or not isinstance(timeout_val, int)
                    or timeout_val <= 0
                ):
                    raise ValueError("misc.command_timeout must be a positive integer")
                self.command_timeout = timeout_val

            # [behavior] table
            if "behavior" in data:
                beh = data["behavior"]
                if not isinstance(beh, dict):
                    raise TypeError("[behavior] must be a TOML table")
                for bool_field in (
                    "reboot",
                    "quiet",
                    "verbose",
                    "no_sudo",
                    "no_snapshot",
                    "no_history",
                ):
                    if bool_field in beh:
                        val = beh[bool_field]
                        if not isinstance(val, bool):
                            raise ValueError(f"behavior.{bool_field} must be a boolean")
                        setattr(self, bool_field, val)
                if "command_timeout" in beh:
                    timeout_val = beh["command_timeout"]
                    if (
                        isinstance(timeout_val, bool)
                        or not isinstance(timeout_val, int)
                        or timeout_val <= 0
                    ):
                        raise ValueError(
                            "behavior.command_timeout must be a positive integer"
                        )
                    self.command_timeout = timeout_val

            # [notifications] table
            if "notifications" in data:
                notif_sec = data["notifications"]
                if not isinstance(notif_sec, dict):
                    raise TypeError("[notifications] must be a TOML table")
                if "enabled" in notif_sec:
                    if not isinstance(notif_sec["enabled"], bool):
                        raise ValueError("notifications.enabled must be a boolean")
                    self.notifications_enabled = notif_sec["enabled"]
                if "only_on_error_or_reboot" in notif_sec:
                    if not isinstance(notif_sec["only_on_error_or_reboot"], bool):
                        raise ValueError(
                            "notifications.only_on_error_or_reboot must be a boolean"
                        )
                    self.notifications_only_on_error_or_reboot = notif_sec[
                        "only_on_error_or_reboot"
                    ]

            # [modules] table
            if "modules" in data:
                mod_sec = data["modules"]
                if not isinstance(mod_sec, dict):
                    raise TypeError("[modules] must be a TOML table")
                if "disable" in mod_sec:
                    disabled = mod_sec["disable"]
                    if not isinstance(disabled, list) or not all(
                        isinstance(k, str) for k in disabled
                    ):
                        raise ValueError("modules.disable must be a list of strings")
                    self.disabled_keys.update(k.lower().strip() for k in disabled)
                if "skip" in mod_sec:
                    skip_list = mod_sec["skip"]
                    if not isinstance(skip_list, list) or not all(
                        isinstance(k, str) for k in skip_list
                    ):
                        raise ValueError("modules.skip must be a list of strings")
                    self.skip_keys = [k.lower().strip() for k in skip_list]
                if "only" in mod_sec:
                    only_list = mod_sec["only"]
                    if not isinstance(only_list, list) or not all(
                        isinstance(k, str) for k in only_list
                    ):
                        raise ValueError("modules.only must be a list of strings")
                    self.only_keys = [k.lower().strip() for k in only_list]

            # [categories] table
            if "categories" in data:
                cat_sec = data["categories"]
                if not isinstance(cat_sec, dict):
                    raise TypeError("[categories] must be a TOML table")
                if "only" in cat_sec:
                    cats = cat_sec["only"]
                    if not isinstance(cats, list) or not all(
                        isinstance(c, str) for c in cats
                    ):
                        raise ValueError("categories.only must be a list of strings")
                    self.categories = [c.lower().strip() for c in cats]
                if "skip" in cat_sec:
                    skip_cats = cat_sec["skip"]
                    if not isinstance(skip_cats, list) or not all(
                        isinstance(c, str) for c in skip_cats
                    ):
                        raise ValueError("categories.skip must be a list of strings")
                    self.skip_categories = [c.lower().strip() for c in skip_cats]

            # Custom commands sections
            for section_name in ("pre_commands", "commands", "post_commands"):
                section = data.get(section_name, {})
                if not isinstance(section, dict) or not all(
                    isinstance(name, str) and isinstance(command, str)
                    for name, command in section.items()
                ):
                    raise ValueError(f"[{section_name}] must contain string commands")
                setattr(self, section_name, section)

            # Git repositories to pull
            git_sec = data.get("git", {})
            if not isinstance(git_sec, dict):
                raise TypeError("[git] must be a TOML table")
            if "repos" in git_sec:
                repos = git_sec["repos"]
                if not isinstance(repos, list) or not all(
                    isinstance(path, str) for path in repos
                ):
                    raise ValueError("git.repos must be a list of paths")
                self.git_repos = [
                    os.path.expanduser(path)
                    for path in repos
                    if os.path.isdir(os.path.expanduser(path))
                ]
        except (OSError, ValueError, TypeError) as error:
            self._reset_defaults()
            self.load_error = str(error)


_global_config = None


def get_config(config_path: str | None = None) -> Config:
    global _global_config
    if _global_config is None or (
        config_path and _global_config.config_path != os.path.expanduser(config_path)
    ):
        _global_config = Config(config_path=config_path)
    return _global_config
