"""
Docker container images update module.
"""

from modules.base import BaseModule, UpdateContext
from ui import StepResult


class DockerModule(BaseModule):
    name = "Docker Containers"
    key = "docker"
    category = "Containers & Packages"
    description = "Pulls latest versions of all locally tracked Docker container images"

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("docker") is None:
            return False
        # Check if docker daemon is reachable
        code, _, _ = ctx.run_cmd(["docker", "info"], timeout=5, read_only=True)
        return code == 0

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would pull latest Docker images")

        code, out, err = ctx.run_cmd(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"])
        if code != 0:
            return StepResult("error", "Failed to list Docker images", error_output=err)

        images = [
            img.strip() for img in out.splitlines()
            if img.strip() and not img.startswith("<none>")
        ]

        if not images:
            return StepResult("unchanged")

        updated = []
        errors = []

        for img in images:
            p_code, p_out, p_err = ctx.run_cmd(["docker", "pull", img])
            if p_code != 0:
                errors.append(f"{img}: {p_err or p_out}")
            elif "Downloaded newer image" in p_out or "Pull complete" in p_out:
                updated.append(img)

        if errors and not updated:
            return StepResult("error", "Docker pull encountered errors", error_output="\n".join(errors))

        if updated:
            return StepResult("ok", f"{len(updated)} image{'s' if len(updated) != 1 else ''} updated", details=updated)

        return StepResult("unchanged")
