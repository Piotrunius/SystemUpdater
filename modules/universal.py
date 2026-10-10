"""
Universal and alternate system package managers (Snap, Nix).
"""

from modules.base import BaseModule, UpdateContext
from ui import StepResult


class SnapModule(BaseModule):
    name = "Snap"
    key = "snap"
    category = "Containers & Packages"
    description = "Updates installed Snap packages via snap refresh"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("snap") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["sudo", "snap", "refresh"], timeout=300)
        if code != 0:
            return StepResult("error", "snap refresh failed", error_output=err or out)

        if "All snaps up to date" in out:
            return StepResult("unchanged")

        return StepResult("ok", "Snap packages refreshed")


class NixModule(BaseModule):
    name = "Nix"
    key = "nix"
    category = "Containers & Packages"
    description = "Updates Nix package channels and user environment"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("nix-channel") is not None and ctx.which("nix-env") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        channel_code, channel_out, channel_err = ctx.run_cmd(
            ["nix-channel", "--update"], timeout=180
        )
        if channel_code != 0:
            return StepResult(
                "error",
                "nix-channel update failed",
                error_output=channel_err or channel_out,
            )

        code, out, err = ctx.run_cmd(["nix-env", "-u"], timeout=300)
        if code != 0:
            return StepResult("error", "nix-env update failed", error_output=err or out)

        return StepResult("ok", "updated")
