"""
Extended container update modules (Podman auto-update, Vagrant).
"""

import os
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class PodmanModule(BaseModule):
    name = "Podman"
    key = "podman"
    category = "Containers & Packages"
    description = "Updates containers using podman auto-update"
    unit_name = "container"
    unit_name_plural = "containers"

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("podman") is None:
            return "not-installed"
        # Only available if user actually has containers configured with auto-update
        code, out, _ = ctx.run_cmd(
            ["podman", "ps", "-a", "--filter", "label=io.containers.autoupdate", "-q"],
            timeout=5,
            read_only=True,
        )
        if code != 0:
            return "unavailable"
        return "active" if out.strip() else "no-targets"

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
        code, out, err = ctx.run_cmd(["podman", "auto-update"], timeout=300)
        if code != 0:
            return StepResult(
                "error", "podman auto-update failed", error_output=err or out
            )

        if not out.strip() or "nothing to update" in out.lower():
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class VagrantModule(BaseModule):
    name = "Vagrant"
    key = "vagrant"
    category = "Containers & Packages"
    description = "Checks and updates installed Vagrant boxes"
    unit_name = "box"
    unit_name_plural = "boxes"

    def is_available(self, ctx: UpdateContext) -> bool:
        return self._availability(ctx) == "active"

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("vagrant") is None:
            return "not-installed"
        # `vagrant box update` operates on the project selected by the current directory.
        project_dir = os.getcwd()
        while True:
            if os.path.isfile(os.path.join(project_dir, "Vagrantfile")):
                return "active"
            parent_dir = os.path.dirname(project_dir)
            if parent_dir == project_dir:
                return "no-project"
            project_dir = parent_dir

    def availability_status(self, ctx: UpdateContext) -> str:
        return {
            "not-installed": "[Not Installed]",
            "no-project": "[No Project]",
            "active": "[Active]",
        }[self._availability(ctx)]

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(["vagrant", "box", "update"], timeout=300)
        if code != 0:
            return StepResult(
                "error", "vagrant box update failed", error_output=err or out
            )

        return StepResult("ok", "updated")
