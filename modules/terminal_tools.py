"""
Terminal utility and prompt update modules (Tealdeer/tldr, Fisher for Fish, Zinit).
"""

import os
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class TealdeerModule(BaseModule):
    name = "Tealdeer"
    key = "tldr"
    category = "Development Environment"
    description = "Updates offline tldr pages database via tealdeer"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("tldr") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["tldr", "--update"], timeout=60)
        if code != 0:
            return StepResult("error", "tldr update failed", error_output=err or out)

        return StepResult("ok", "updated")


class FisherModule(BaseModule):
    name = "Fisher"
    key = "fisher"
    category = "Development Environment"
    description = "Updates Fish shell plugins via Fisher"
    unit_name = "plugin"
    unit_name_plural = "plugins"

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("fish") is None:
            return False
        fisher_path = os.path.expanduser("~/.config/fish/functions/fisher.fish")
        return os.path.isfile(fisher_path)

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["fish", "-c", "fisher update"], timeout=120)
        if code != 0:
            return StepResult("error", "fisher update failed", error_output=err or out)

        return StepResult("ok", "updated")


class ZinitModule(BaseModule):
    name = "Zinit"
    key = "zinit"
    category = "Development Environment"
    description = "Updates Zsh plugins via Zinit"
    unit_name = "plugin"
    unit_name_plural = "plugins"

    def is_available(self, ctx: UpdateContext) -> bool:
        zinit_dirs = [
            os.path.expanduser("~/.local/share/zinit"),
            os.path.expanduser("~/.zinit"),
        ]
        return (
            any(os.path.isdir(d) for d in zinit_dirs) and ctx.which("zsh") is not None
        )

    def run(self, ctx: UpdateContext) -> StepResult:
        cmd = [
            "zsh",
            "-c",
            "source ~/.local/share/zinit/zinit.git/zinit.zsh 2>/dev/null || source ~/.zinit/bin/zinit.zsh 2>/dev/null; zinit update --parallel",
        ]
        code, out, err = ctx.run_cmd(cmd, timeout=180)
        if code != 0:
            return StepResult("error", "zinit update failed", error_output=err or out)

        return StepResult("ok", "updated")
