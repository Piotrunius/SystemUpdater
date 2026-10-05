"""
Extended language and SDK update modules (Pipenv, Pyenv, Sdkman, Ghcup, Flutter).
"""

import os
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class PipenvModule(BaseModule):
    name = "Python Pipenv"
    key = "pipenv"
    category = "Development Environment"
    description = "Updates pipenv packaging tool"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("pipenv") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run pip install --upgrade pipenv")

        pip_bin = ctx.which("pip3") or ctx.which("pip") or "pip"
        code, out, err = ctx.run_cmd([pip_bin, "install", "--upgrade", "pipenv"], timeout=180)
        if code != 0:
            return StepResult("error", "pipenv upgrade failed", error_output=err or out)

        if "Requirement already satisfied" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class PyenvModule(BaseModule):
    name = "pyenv Runtimes"
    key = "pyenv"
    category = "Development Environment"
    description = "Updates pyenv and python definitions via pyenv update"

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("pyenv") is not None:
            return True
        return os.path.isdir(os.path.expanduser("~/.pyenv/plugins/pyenv-update"))

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run pyenv update")

        code, out, err = ctx.run_cmd(["pyenv", "update"], timeout=120)
        if code != 0:
            return StepResult("error", "pyenv update failed", error_output=err or out)

        if "Already up to date" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class SdkmanModule(BaseModule):
    name = "SDKMAN (Java/JVM)"
    key = "sdkman"
    category = "Development Environment"
    description = "Updates SDKMAN tool and installed candidate versions"

    def is_available(self, ctx: UpdateContext) -> bool:
        return os.path.isfile(os.path.expanduser("~/.sdkman/bin/sdkman-init.sh"))

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run sdk selfupdate && sdk update")

        cmd = [
            "bash", "-c",
            'source "$HOME/.sdkman/bin/sdkman-init.sh" && sdk selfupdate && sdk update'
        ]
        code, out, err = ctx.run_cmd(cmd, timeout=180)
        if code != 0:
            return StepResult("error", "sdkman update failed", error_output=err or out)

        return StepResult("ok", "updated")


class GhcupModule(BaseModule):
    name = "GHCup (Haskell)"
    key = "ghcup"
    category = "Development Environment"
    description = "Updates Haskell GHCup toolchain manager"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("ghcup") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run ghcup upgrade")

        code, out, err = ctx.run_cmd(["ghcup", "upgrade"], timeout=180)
        if code != 0:
            return StepResult("error", "ghcup upgrade failed", error_output=err or out)

        if "already up to date" in out.lower() or "latest version is already installed" in out.lower():
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class FlutterModule(BaseModule):
    name = "Flutter SDK"
    key = "flutter"
    category = "Development Environment"
    description = "Updates Flutter SDK toolchain"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("flutter") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run flutter upgrade")

        code, out, err = ctx.run_cmd(["flutter", "upgrade"], timeout=300)
        if code != 0:
            return StepResult("error", "flutter upgrade failed", error_output=err or out)

        if "Flutter is already up to date" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")
