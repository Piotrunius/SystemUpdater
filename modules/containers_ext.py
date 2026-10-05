"""
Extended container update modules (Podman auto-update, Vagrant).
"""

from modules.base import BaseModule, UpdateContext
from ui import StepResult


class PodmanModule(BaseModule):
    name = "Podman Containers"
    key = "podman"
    category = "Containers & Packages"
    description = "Updates containers using podman auto-update"

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("podman") is None:
            return False
        # Only available if user actually has containers configured with auto-update
        code, out, _ = ctx.run_cmd(
            ["podman", "ps", "-a", "--filter", "label=io.containers.autoupdate", "-q"],
            timeout=5,
            read_only=True,
        )
        return code == 0 and bool(out.strip())

    def availability_status(self, ctx: UpdateContext) -> str:
        if ctx.which("podman") is None:
            return "[Not Installed]"
        return "[Active]" if self.is_available(ctx) else "[No Targets]"

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run podman auto-update")

        code, out, err = ctx.run_cmd(["podman", "auto-update"], timeout=300)
        if code != 0:
            return StepResult("error", "podman auto-update failed", error_output=err or out)

        if not out.strip() or "nothing to update" in out.lower():
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class VagrantModule(BaseModule):
    name = "Vagrant Boxes"
    key = "vagrant"
    category = "Containers & Packages"
    description = "Checks and updates installed Vagrant boxes"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("vagrant") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run vagrant box update")

        code, out, err = ctx.run_cmd(["vagrant", "box", "update"], timeout=300)
        if code != 0:
            return StepResult("error", "vagrant box update failed", error_output=err or out)

        return StepResult("ok", "updated")
