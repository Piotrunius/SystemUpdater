"""
Editor extensions and toolchains update modules (VS Code, Cursor, VSCodium, Helix).
"""

import os
import re

from modules.base import BaseModule, UpdateContext
from ui import StepResult


def _run_vscode_like_update(ctx: UpdateContext, binary: str, label: str) -> StepResult:
    code, out, err = ctx.run_cmd([binary, "--update-extensions"], timeout=180)
    if code != 0:
        return StepResult(
            "error", f"{label} extensions update failed", error_output=err or out
        )

    combined = f"{out or ''}\n{err or ''}"
    lowered = combined.lower()
    if (
        "no extension to update" in lowered
        or "no extensions to update" in lowered
        or not combined.strip()
    ):
        return StepResult("unchanged")

    exts: list[str] = []
    for line in combined.splitlines():
        m = re.search(
            r"Extension\s+'([^']+)'\s+(?:v[^\s]+\s+)?was successfully updated",
            line,
            re.IGNORECASE,
        )
        if not m:
            m = re.search(r"Updated\s+extension\s+([^\s]+)", line, re.IGNORECASE)
        if m:
            exts.append(m.group(1))
    exts = list(dict.fromkeys(exts))

    if exts:
        count = len(exts)
        return StepResult(
            "ok",
            f"{count} extension{'s' if count != 1 else ''} updated",
            details=exts,
        )

    return StepResult("ok", "updated")


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
                subdirs = []
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
        return self.format_availability(self._availability(ctx))

    def run(self, ctx: UpdateContext) -> StepResult:
        return _run_vscode_like_update(ctx, "code", "VS Code")


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
                subdirs = []
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
        return self.format_availability(self._availability(ctx))

    def run(self, ctx: UpdateContext) -> StepResult:
        return _run_vscode_like_update(ctx, "cursor", "Cursor")


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
                subdirs = []
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
        return self.format_availability(self._availability(ctx))

    def run(self, ctx: UpdateContext) -> StepResult:
        return _run_vscode_like_update(ctx, "codium", "VSCodium")


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

        fetch_combined = f"{out or ''}\n{err or ''}".lower()
        build_combined = f"{out_b or ''}\n{err_b or ''}".lower()
        fetch_unchanged = (
            "0 updated" in fetch_combined
            or "already up to date" in fetch_combined
            or not fetch_combined.strip()
        )
        build_unchanged = (
            "0 grammars built" in build_combined
            or "already up to date" in build_combined
            or not build_combined.strip()
        )
        if fetch_unchanged and build_unchanged:
            return StepResult("unchanged")

        return StepResult("ok", "updated")
