"""
Editor extensions and toolchains update modules (VS Code, Cursor, VSCodium, Helix).
"""

import os
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class VsCodeModule(BaseModule):
    name = "VS Code"
    key = "vscode"
    category = "Development Environment"
    description = "Updates installed VS Code extensions"
    unit_name = "extension"
    unit_name_plural = "extensions"

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("code") is None:
            return "not-installed"
        ext_dir = os.path.expanduser("~/.vscode/extensions")
        if os.path.isdir(ext_dir):
            try:
                subdirs = [
                    d
                    for d in os.listdir(ext_dir)
                    if not d.startswith(".") and os.path.isdir(os.path.join(ext_dir, d))
                ]
                if subdirs:
                    return "active"
            except OSError:
                pass
        code, out, _ = ctx.run_cmd(
            ["code", "--list-extensions"], timeout=5, read_only=True
        )
        if code != 0:
            return "unavailable"
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        return "active" if lines else "no-targets"

    def is_available(self, ctx: UpdateContext) -> bool:
        return self._availability(ctx) in ("active", "unavailable")

    def availability_status(self, ctx: UpdateContext) -> str:
        return {
            "not-installed": "[Not Installed]",
            "no-targets": "[No Targets]",
            "unavailable": "[Unavailable]",
            "active": "[Active]",
        }[self._availability(ctx)]

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["code", "--update-extensions"], timeout=180)
        if code != 0:
            return StepResult(
                "error", "VS Code extensions update failed", error_output=err or out
            )

        return StepResult("ok", "updated")


class CursorModule(BaseModule):
    name = "Cursor"
    key = "cursor"
    category = "Development Environment"
    description = "Updates installed Cursor extensions"
    unit_name = "extension"
    unit_name_plural = "extensions"

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("cursor") is None:
            return "not-installed"
        ext_dir = os.path.expanduser("~/.cursor/extensions")
        if os.path.isdir(ext_dir):
            try:
                subdirs = [
                    d
                    for d in os.listdir(ext_dir)
                    if not d.startswith(".") and os.path.isdir(os.path.join(ext_dir, d))
                ]
                if subdirs:
                    return "active"
            except OSError:
                pass
        code, out, _ = ctx.run_cmd(
            ["cursor", "--list-extensions"], timeout=5, read_only=True
        )
        if code != 0:
            return "unavailable"
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        return "active" if lines else "no-targets"

    def is_available(self, ctx: UpdateContext) -> bool:
        return self._availability(ctx) in ("active", "unavailable")

    def availability_status(self, ctx: UpdateContext) -> str:
        return {
            "not-installed": "[Not Installed]",
            "no-targets": "[No Targets]",
            "unavailable": "[Unavailable]",
            "active": "[Active]",
        }[self._availability(ctx)]

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["cursor", "--update-extensions"], timeout=180)
        if code != 0:
            return StepResult(
                "error", "Cursor extensions update failed", error_output=err or out
            )

        return StepResult("ok", "updated")


class VscodiumModule(BaseModule):
    name = "VSCodium"
    key = "codium"
    category = "Development Environment"
    description = "Updates installed VSCodium extensions"
    unit_name = "extension"
    unit_name_plural = "extensions"

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("codium") is None:
            return "not-installed"
        ext_dir = os.path.expanduser("~/.vscode-oss/extensions")
        if os.path.isdir(ext_dir):
            try:
                subdirs = [
                    d
                    for d in os.listdir(ext_dir)
                    if not d.startswith(".") and os.path.isdir(os.path.join(ext_dir, d))
                ]
                if subdirs:
                    return "active"
            except OSError:
                pass
        code, out, _ = ctx.run_cmd(
            ["codium", "--list-extensions"], timeout=5, read_only=True
        )
        if code != 0:
            return "unavailable"
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        return "active" if lines else "no-targets"

    def is_available(self, ctx: UpdateContext) -> bool:
        return self._availability(ctx) in ("active", "unavailable")

    def availability_status(self, ctx: UpdateContext) -> str:
        return {
            "not-installed": "[Not Installed]",
            "no-targets": "[No Targets]",
            "unavailable": "[Unavailable]",
            "active": "[Active]",
        }[self._availability(ctx)]

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["codium", "--update-extensions"], timeout=180)
        if code != 0:
            return StepResult(
                "error", "VSCodium extensions update failed", error_output=err or out
            )

        return StepResult("ok", "updated")


class HelixModule(BaseModule):
    name = "Helix"
    key = "helix"
    category = "Development Environment"
    description = "Updates Helix editor tree-sitter grammars"
    unit_name = "grammar"
    unit_name_plural = "grammars"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("hx") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["hx", "--grammar", "fetch"], timeout=120)
        if code != 0:
            return StepResult(
                "error", "Helix grammar fetch failed", error_output=err or out
            )

        code_b, out_b, err_b = ctx.run_cmd(["hx", "--grammar", "build"], timeout=180)
        if code_b != 0:
            return StepResult(
                "error", "Helix grammar build failed", error_output=err_b or out_b
            )

        return StepResult("ok", "updated")
