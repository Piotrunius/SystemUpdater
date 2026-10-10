"""
Configuration loader for SystemUpdater.
Supports ~/.config/sysupdate/config.toml using standard library tomllib.
Provides parity with Topgrade configuration (custom commands, git repos, disable list).
"""

import os
import sys
from typing import Dict, List, Set, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    tomllib = None


DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/sysupdate/config.toml")


class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.disabled_keys: Set[str] = set()
        self.pre_commands: Dict[str, str] = {}
        self.commands: Dict[str, str] = {}
        self.post_commands: Dict[str, str] = {}
        self.git_repos: List[str] = []
        self.snapshot_cooldown_hours: int = 12
        self._explicit_config_path = config_path is not None
        self.config_path: str = (
            os.path.expanduser(config_path) if config_path else DEFAULT_CONFIG_PATH
        )
        self.load_error: Optional[str] = None

        self._load_config()

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

            misc = data.get("misc", {})
            if not isinstance(misc, dict):
                raise ValueError("[misc] must be a TOML table")

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
                raise ValueError("[git] must be a TOML table")
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
        except (OSError, ValueError) as error:
            self.disabled_keys.clear()
            self.pre_commands.clear()
            self.commands.clear()
            self.post_commands.clear()
            self.git_repos.clear()
            self.snapshot_cooldown_hours = 12
            self.load_error = str(error)


_global_config = None


def get_config(config_path: Optional[str] = None) -> Config:
    global _global_config
    if _global_config is None or (
        config_path and _global_config.config_path != os.path.expanduser(config_path)
    ):
        _global_config = Config(config_path=config_path)
    return _global_config
