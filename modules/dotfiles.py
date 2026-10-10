"""
Dotfiles management update modules (chezmoi, yadm).
"""

from modules.base import BaseModule, UpdateContext
from ui import StepResult


class ChezmoiModule(BaseModule):
    name = "Chezmoi"
    key = "chezmoi"
    category = "Development Environment"
    description = "Updates managed dotfiles via chezmoi update"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("chezmoi") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["chezmoi", "update"], timeout=120)
        if code != 0:
            return StepResult("error", "chezmoi update failed", error_output=err or out)

        return StepResult("ok", "updated")


class YadmModule(BaseModule):
    name = "Yadm"
    key = "yadm"
    category = "Development Environment"
    description = "Updates dotfiles via yadm pull"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("yadm") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["yadm", "pull"], timeout=120)
        if code != 0:
            return StepResult("error", "yadm pull failed", error_output=err or out)

        if "Already up to date" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")
