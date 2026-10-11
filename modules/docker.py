import os
import re

from modules.base import BaseModule, UpdateContext
from ui import StepResult


class DockerModule(BaseModule):
    name = "Docker"
    key = "docker"
    category = "Containers & Packages"
    description = "Pulls latest versions of all locally tracked Docker container images"
    unit_name = "image"
    unit_name_plural = "images"

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
        code, out, err = ctx.run_cmd(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}"]
        )
        if code != 0:
            return StepResult("error", "Failed to list Docker images", error_output=err)

        images = []
        old_ids = {}
        for line in out.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("<none>"):
                continue
            parts = line_str.split("\t", 1)
            img = parts[0].strip()
            if img:
                images.append(img)
                if len(parts) > 1 and parts[1].strip():
                    old_ids[img] = parts[1].strip()[:12]

        if not images:
            return StepResult("unchanged")

        updated = []
        updated_images = set()
        errors = []

        for img in images:
            p_code, p_out, p_err = ctx.run_cmd(["docker", "pull", img])
            if p_code != 0:
                errors.append(f"{img}: {p_err or p_out}")
            elif "Downloaded newer image" in p_out or "Pull complete" in p_out:
                updated_images.add(img)
                old_id = old_ids.get(img, "")
                new_id = ""
                m = re.search(r"Digest:\s+sha256:([0-9a-fA-F]{12})", p_out)
                if m:
                    new_id = m.group(1)
                if old_id and new_id and old_id != new_id:
                    updated.append(f"{img}: {old_id} -> {new_id}")
                else:
                    updated.append(img)

        if errors:
            return StepResult(
                "error",
                "Docker pull encountered errors",
                details=updated,
                error_output="\n".join(errors),
            )

        if updated:
            if updated_images and not ctx.dry_run:
                try:
                    ps_code, ps_out, _ = ctx.run_cmd(
                        [
                            "docker",
                            "ps",
                            "--format",
                            '{{.Image}}\t{{.Label "com.docker.compose.project.config_files"}}\t{{.Label "com.docker.compose.project.working_dir"}}',
                        ],
                        read_only=True,
                    )
                    if ps_code == 0 and ps_out.strip():
                        compose_targets = set()
                        for line in ps_out.splitlines():
                            parts = line.strip().split("\t")
                            if len(parts) >= 2:
                                c_img = parts[0].strip()
                                c_cfg = parts[1].strip()
                                c_dir = parts[2].strip() if len(parts) > 2 else ""
                                if c_cfg and (
                                    c_img in updated_images
                                    or any(
                                        u.startswith(c_img.split(":")[0])
                                        for u in updated_images
                                    )
                                ):
                                    compose_targets.add((c_cfg, c_dir))
                        for cfg, wdir in compose_targets:
                            up_cmd = ["docker", "compose"]
                            if wdir and os.path.isdir(wdir):
                                up_cmd.extend(["--project-directory", wdir])
                            for f in cfg.split(","):
                                f_clean = f.strip()
                                if f_clean:
                                    up_cmd.extend(["-f", f_clean])
                            up_cmd.extend(["up", "-d"])
                            ctx.run_cmd(up_cmd)
                except (OSError, RuntimeError, KeyError, ValueError, StopIteration):
                    pass

            return StepResult(
                "ok",
                f"{len(updated)} image{'s' if len(updated) != 1 else ''} updated",
                details=updated,
            )

        return StepResult("unchanged")
