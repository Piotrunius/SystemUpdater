"""
Git repositories auto-pull module.
Pulls fast-forward updates for git repositories configured in config.toml [git].
"""

import os
from modules.base import BaseModule, UpdateContext
from config import get_config
from ui import StepResult


class GitReposModule(BaseModule):
    name = "Git Repositories"
    key = "git"
    category = "Development Environment"
    description = "Pulls latest commits for repositories configured in config.toml"

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("git") is None:
            return False
        cfg = get_config()
        return len(cfg.git_repos) > 0

    def availability_status(self, ctx: UpdateContext) -> str:
        if ctx.which("git") is None:
            return "[Not Installed]"
        cfg = get_config()
        if not cfg.git_repos:
            return "[Unconfigured]"
        return "[Active]"

    def run(self, ctx: UpdateContext) -> StepResult:
        cfg = get_config()
        if not cfg.git_repos:
            return StepResult("unchanged")

        if ctx.dry_run:
            return StepResult("ok", f"[DRY-RUN] Would pull {len(cfg.git_repos)} configured git repositories")

        updated = []
        errors = []

        for repo_dir in cfg.git_repos:
            repo_name = os.path.basename(repo_dir)
            code, out, err = ctx.run_cmd(["git", "-C", repo_dir, "pull", "--ff-only"], timeout=60)
            if code != 0:
                errors.append(f"{repo_name}: {err or out}")
            elif "Already up to date" not in out:
                updated.append(repo_name)

        if errors and not updated:
            return StepResult("error", "Git pull encountered errors", error_output="\n".join(errors))

        if updated:
            return StepResult("ok", f"{len(updated)} repo{'s' if len(updated) != 1 else ''} updated", details=updated)

        return StepResult("unchanged")
