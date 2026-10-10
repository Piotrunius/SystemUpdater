"""
Extended language and SDK update modules (Pipenv, Pyenv, Sdkman, Ghcup, Flutter).
"""

import os
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class PipenvModule(BaseModule):
    name = "Pipenv"
    key = "pipenv"
    category = "Development Environment"
    description = "Updates pipenv packaging tool"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("pipenv") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        pip_bin = ctx.which("pip3") or ctx.which("pip") or "pip"
        code, out, err = ctx.run_cmd(
            [pip_bin, "install", "--upgrade", "pipenv"], timeout=180
        )
        if code != 0:
            return StepResult("error", "pipenv upgrade failed", error_output=err or out)

        if "Requirement already satisfied" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class PyenvModule(BaseModule):
    name = "pyenv"
    key = "pyenv"
    category = "Development Environment"
    description = "Updates pyenv and python definitions via pyenv update"
    is_single_entity = True

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("pyenv") is not None:
            return True
        return os.path.isdir(os.path.expanduser("~/.pyenv/plugins/pyenv-update"))

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["pyenv", "update"], timeout=120)
        if code != 0:
            return StepResult("error", "pyenv update failed", error_output=err or out)

        if "Already up to date" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class SdkmanModule(BaseModule):
    name = "SDKMAN"
    key = "sdkman"
    category = "Development Environment"
    description = "Updates SDKMAN tool and installed candidate versions"
    is_single_entity = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return os.path.isfile(os.path.expanduser("~/.sdkman/bin/sdkman-init.sh"))

    def run(self, ctx: UpdateContext) -> StepResult:
        cmd = [
            "bash",
            "-c",
            'source "$HOME/.sdkman/bin/sdkman-init.sh" && sdk selfupdate && sdk update',
        ]
        code, out, err = ctx.run_cmd(cmd, timeout=180)
        if code != 0:
            return StepResult("error", "sdkman update failed", error_output=err or out)

        return StepResult("ok", "updated")


class GhcupModule(BaseModule):
    name = "GHCup"
    key = "ghcup"
    category = "Development Environment"
    description = "Updates Haskell GHCup toolchain manager"
    is_single_entity = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("ghcup") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["ghcup", "upgrade"], timeout=180)
        if code != 0:
            return StepResult("error", "ghcup upgrade failed", error_output=err or out)

        if (
            "already up to date" in out.lower()
            or "latest version is already installed" in out.lower()
        ):
            return StepResult("unchanged")

        m = re.search(r"from\s+([^\s]+)\s+to\s+([^\s]+)", out, re.I)
        details = [f"{m.group(1)} -> {m.group(2)}"] if m else []
        return StepResult("ok", "updated", details=details)


class FlutterModule(BaseModule):
    name = "Flutter"
    key = "flutter"
    category = "Development Environment"
    description = "Updates Flutter SDK toolchain"
    is_single_entity = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("flutter") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["flutter", "upgrade"], timeout=300)
        if code != 0:
            return StepResult(
                "error", "flutter upgrade failed", error_output=err or out
            )

        if "Flutter is already up to date" in out:
            return StepResult("unchanged")

        m = re.search(r"from\s+([^\s]+)\s+to\s+([^\s]+)", out, re.I)
        details = [f"{m.group(1)} -> {m.group(2)}"] if m else []
        return StepResult("ok", "updated", details=details)
