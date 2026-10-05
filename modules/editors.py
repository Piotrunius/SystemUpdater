"""
Editor extensions and toolchains update modules (VS Code, Cursor, VSCodium, Helix).
"""

from modules.base import BaseModule, UpdateContext
from ui import StepResult


class VsCodeModule(BaseModule):
    name = "VS Code Extensions"
    key = "vscode"
    category = "Development Environment"
    description = "Updates installed VS Code extensions"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("code") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run code --update-extensions")

        code, out, err = ctx.run_cmd(["code", "--update-extensions"], timeout=180)
        if code != 0:
            return StepResult("error", "VS Code extensions update failed", error_output=err or out)

        return StepResult("ok", "updated")


class CursorModule(BaseModule):
    name = "Cursor Extensions"
    key = "cursor"
    category = "Development Environment"
    description = "Updates installed Cursor extensions"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("cursor") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run cursor --update-extensions")

        code, out, err = ctx.run_cmd(["cursor", "--update-extensions"], timeout=180)
        if code != 0:
            return StepResult("error", "Cursor extensions update failed", error_output=err or out)

        return StepResult("ok", "updated")


class VscodiumModule(BaseModule):
    name = "VSCodium Extensions"
    key = "codium"
    category = "Development Environment"
    description = "Updates installed VSCodium extensions"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("codium") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run codium --update-extensions")

        code, out, err = ctx.run_cmd(["codium", "--update-extensions"], timeout=180)
        if code != 0:
            return StepResult("error", "VSCodium extensions update failed", error_output=err or out)

        return StepResult("ok", "updated")


class HelixModule(BaseModule):
    name = "Helix Grammars"
    key = "helix"
    category = "Development Environment"
    description = "Updates Helix editor tree-sitter grammars"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("hx") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run hx --grammar fetch and build")

        code, out, err = ctx.run_cmd(["hx", "--grammar", "fetch"], timeout=120)
        if code != 0:
            return StepResult("error", "Helix grammar fetch failed", error_output=err or out)

        code_b, out_b, err_b = ctx.run_cmd(["hx", "--grammar", "build"], timeout=180)
        if code_b != 0:
            return StepResult("error", "Helix grammar build failed", error_output=err_b or out_b)

        return StepResult("ok", "updated")
