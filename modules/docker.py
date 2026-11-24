from modules.base import BaseModule, UpdateContext
from ui import StepResult


class DockerModule(BaseModule):
    name = "Docker"
    key = "docker"
    category = "Containers & Packages"
    description = "Pulls latest versions of all locally tracked Docker container images"
    unit_name = "image"
    unit_name_plural = "images"

    @staticmethod
    def _parse_pullable_images(output: str) -> list[str]:
        images: list[str] = []
        for line in output.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("<none>"):
                continue
            if "\t" in line_str:
                img_part, digest_part = line_str.split("\t", 1)
                if digest_part.strip() == "<none>":
                    continue
                img = img_part.strip()
            else:
                img = line_str
            if img and not img.startswith("<none>"):
                images.append(img)
        return images

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("docker") is None:
            return "not-installed"
        # Skip the module when Docker is reachable but has no remote-tracked images.
        code, out, _ = ctx.run_cmd(
            [
                "docker",
                "images",
                "--digests",
                "--format",
                "{{.Repository}}:{{.Tag}}\t{{.Digest}}",
            ],
            timeout=5,
            read_only=True,
        )
        if code != 0:
            return "unavailable"
        return "active" if self._parse_pullable_images(out) else "no-targets"

    def is_available(self, ctx: UpdateContext) -> bool:
        return self._availability(ctx) in ("active", "unavailable")

    def availability_status(self, ctx: UpdateContext) -> str:
        return self.format_availability(self._availability(ctx))

    def run(self, ctx: UpdateContext) -> StepResult:
        code, out, err = ctx.run_cmd(
            [
                "docker",
                "images",
                "--digests",
                "--format",
                "{{.Repository}}:{{.Tag}}\t{{.Digest}}",
            ]
        )
        if code != 0:
            return StepResult("error", "Failed to list Docker images", error_output=err)

        images = self._parse_pullable_images(out)
        if not images:
            return StepResult("unchanged")

        updated = []
        errors = []

        for img in images:
            p_code, p_out, p_err = ctx.run_cmd(
                ["docker", "pull", img], retries=1, retry_delay=3.0
            )
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
