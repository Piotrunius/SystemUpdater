"""
User-defined custom commands module.
Executes custom commands defined in ~/.config/sysupdate/config.toml ([pre_commands], [commands], [post_commands]).
"""

import shlex
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class CustomCommandModule(BaseModule):
    def __init__(self, name: str, command: str, category: str = "Custom Commands", key: str = "custom"):
        self.name = name
        self.command = command
        self.category = category
        self.key = key
        self.description = f"User custom command: {command}"
        self.requires_sudo = "sudo" in command

    def is_available(self, ctx: UpdateContext) -> bool:
        return bool(self.command.strip())

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", f"[DRY-RUN] Would run: {self.command}")

        # Execute using bash to support pipes and shell builtins if needed
        cmd = ["bash", "-c", self.command]
        code, out, err = ctx.run_cmd(cmd, timeout=300)

        if code != 0:
            return StepResult("error", "Custom command failed", error_output=err or out)

        return StepResult("ok", "Completed")
