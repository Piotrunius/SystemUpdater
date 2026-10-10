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

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("docker") is None:
            return "not-installed"
        # Skip the module when Docker is reachable but has no images to update.
        code, out, _ = ctx.run_cmd(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            timeout=5,
            read_only=True,
        )
        if code != 0:
            return "unavailable"
        images = [line.strip() for line in out.splitlines()]
        has_images = any(image and not image.startswith("<none>") for image in images)
        return "active" if has_images else "no-targets"

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
            return StepResult("ok", "[DRY-RUN] Would pull latest Docker images")

        code, out, err = ctx.run_cmd(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"]
        )
        if code != 0:
            return StepResult("error", "Failed to list Docker images", error_output=err)

        images = [
            img.strip()
            for img in out.splitlines()
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

        if errors:
            return StepResult(
                "error",
                "Docker pull encountered errors",
                details=updated,
                error_output="\n".join(errors),
            )

        if updated:
            return StepResult(
                "ok",
                f"{len(updated)} image{'s' if len(updated) != 1 else ''} updated",
                details=updated,
            )

        return StepResult("unchanged")
