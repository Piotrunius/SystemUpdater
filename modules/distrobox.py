import re
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class DistroboxModule(BaseModule):
    name = "Distrobox Containers"
    key = "distrobox"
    category = "Applications & Gaming"
    description = "Upgrades packages inside all active Distrobox containers (Arch, Fedora, etc.)"

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("distrobox") is None:
            return "not-installed"
        code, out, _ = ctx.run_cmd(
            ["distrobox", "list", "--no-color"],
            timeout=5,
            read_only=True,
        )
        if code != 0:
            return "unavailable"
        has_containers = any(
            "|" in line and not line.strip().lower().startswith("id")
            for line in out.splitlines()
        )
        return "active" if has_containers else "no-targets"

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
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run distrobox upgrade --all")

        code, out, err = ctx.run_cmd(["distrobox", "upgrade", "--all"])

        if code != 0:
            return StepResult("error", "Distrobox upgrade failed", error_output=err or out)

        # Parse which containers were upgraded
        updated_containers = []
        current_box = None
        box_had_update = False

        for line in (out or "").splitlines():
            m = re.search(r"Upgrading\s+([\w\.\-_]+)\.\.\.", line)
            if m:
                if current_box and box_had_update:
                    updated_containers.append(current_box)
                current_box = m.group(1)
                box_had_update = False
                continue

            line_l = line.lower()
            if any(token in line_l for token in ["upgrading ", "upgrading:", "installing:", "upgraded:"]):
                if "nothing to do" not in line_l and "there is nothing to do" not in line_l:
                    box_had_update = True

        if current_box and box_had_update:
            updated_containers.append(current_box)

        updated_containers = list(dict.fromkeys(updated_containers))

        if updated_containers:
            count = len(updated_containers)
            return StepResult("ok", f"{count} container{'s' if count != 1 else ''} updated", details=updated_containers)

        # Fallback check
        has_pacman_upgrades = "upgrading " in out.lower()
        has_dnf_upgrades = "upgrading:" in out.lower() or "installing:" in out.lower()
        if has_pacman_upgrades or has_dnf_upgrades:
            return StepResult("ok", "updated")

        return StepResult("unchanged")
