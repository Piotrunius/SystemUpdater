"""
Dotfiles management update modules (chezmoi, yadm).
"""

import os

from config import xdg_directory
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class ChezmoiModule(BaseModule):
    name = "Chezmoi"
    key = "chezmoi"
    category = "Development Environment"
    description = "Updates managed dotfiles via chezmoi update"

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("chezmoi") is None:
            return "not-installed"
        data_home = xdg_directory("XDG_DATA_HOME", "~/.local/share")
        source_dir = os.path.join(data_home, "chezmoi")
        if os.path.isdir(source_dir):
            return "active"
        return "no-targets"

    def is_available(self, ctx: UpdateContext) -> bool:
        return self._availability(ctx) == "active"

    def availability_status(self, ctx: UpdateContext) -> str:
        return self.format_availability(self._availability(ctx))

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(
            ["chezmoi", "update", "--no-tty"], timeout=120
        )
        if code != 0:
            return StepResult("error", "chezmoi update failed", error_output=err or out)

        combined = f"{out or ''}\n{err or ''}".lower()
        if not combined.strip() or "already up to date" in combined:
            return StepResult("unchanged")

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
