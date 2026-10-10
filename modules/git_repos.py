"""
Git repositories auto-pull module.
Pulls fast-forward updates for git repositories configured in config.toml [git].
"""

import os
from modules.base import BaseModule, UpdateContext
from config import Config
from ui import StepResult


class GitReposModule(BaseModule):
    name = "Git Repositories"
    key = "git"
    category = "Development Environment"
    description = "Pulls latest commits for repositories configured in config.toml"

    def __init__(self, config: Config):
        self.config = config

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("git") is None:
            return False
        return len(self.config.git_repos) > 0

    def availability_status(self, ctx: UpdateContext) -> str:
        if ctx.which("git") is None:
            return "[Not Installed]"
        if not self.config.git_repos:
            return "[Unconfigured]"
        return "[Active]"

    def run(self, ctx: UpdateContext) -> StepResult:
        if not self.config.git_repos:
            return StepResult("unchanged")

        if ctx.dry_run:
            return StepResult(
                "ok",
                f"[DRY-RUN] Would pull {len(self.config.git_repos)} configured git repositories",
            )

        updated = []
        errors = []

        for repo_dir in self.config.git_repos:
            repo_name = os.path.basename(repo_dir)
            code, out, err = ctx.run_cmd(
                ["git", "-C", repo_dir, "pull", "--ff-only"], timeout=60
            )
            if code != 0:
                errors.append(f"{repo_name}: {err or out}")
            elif "Already up to date" not in out:
                updated.append(repo_name)

        if errors:
            return StepResult(
                "error",
                "Git pull encountered errors",
                details=updated,
                error_output="\n".join(errors),
            )

        if updated:
            return StepResult(
                "ok",
                f"{len(updated)} repo{'s' if len(updated) != 1 else ''} updated",
                details=updated,
            )

        return StepResult("unchanged")
