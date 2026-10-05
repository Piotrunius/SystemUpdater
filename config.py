"""
Configuration loader for SystemUpdater.
Supports ~/.config/sysupdate/config.toml using standard library tomllib.
Provides parity with Topgrade configuration (custom commands, git repos, disable list).
"""

import os
import sys
from typing import Dict, List, Set, Any, Optional

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
        self.config_path: str = os.path.expanduser(config_path) if config_path else DEFAULT_CONFIG_PATH

        self._load_config()

    def _load_config(self):
        target_path = self.config_path
        if not os.path.isfile(target_path) or tomllib is None:
            return

        try:
            with open(target_path, "rb") as f:
                data = tomllib.load(f)

            misc = data.get("misc", {})
            if "disable" in misc and isinstance(misc["disable"], list):
                self.disabled_keys = {str(k).lower().strip() for k in misc["disable"]}

            if "cooldown_hours" in misc:
                self.snapshot_cooldown_hours = int(misc["cooldown_hours"])

            # Custom commands sections
            if "pre_commands" in data and isinstance(data["pre_commands"], dict):
                self.pre_commands = {str(k): str(v) for k, v in data["pre_commands"].items()}

            if "commands" in data and isinstance(data["commands"], dict):
                self.commands = {str(k): str(v) for k, v in data["commands"].items()}

            if "post_commands" in data and isinstance(data["post_commands"], dict):
                self.post_commands = {str(k): str(v) for k, v in data["post_commands"].items()}

            # Git repositories to pull
            git_sec = data.get("git", {})
            if "repos" in git_sec and isinstance(git_sec["repos"], list):
                self.git_repos = [
                    os.path.expanduser(p) for p in git_sec["repos"]
                    if os.path.isdir(os.path.expanduser(p))
                ]
        except Exception:
            pass


_global_config = None


def get_config(config_path: Optional[str] = None) -> Config:
    global _global_config
    if _global_config is None or (config_path and _global_config.config_path != os.path.expanduser(config_path)):
        _global_config = Config(config_path=config_path)
    return _global_config
