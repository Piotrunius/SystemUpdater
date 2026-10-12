"""
ProtonPlus runners update module.
"""

from modules.base import BaseModule, UpdateContext, check_github_api
from ui import StepResult


class ProtonPlusModule(BaseModule):
    name = "ProtonPlus"
    key = "proton"
    category = "Applications & Gaming"
    description = (
        "Updates compatibility tools like Proton-GE, CachyOS, and Wine via ProtonPlus"
    )
    unit_name = "runner"
    unit_name_plural = "runners"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("protonplus") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        # Fast health check for GitHub API before launching queries that could stall
        gh_check = check_github_api()
        if gh_check is not None:
            return gh_check

        code, out, err = ctx.run_cmd(["protonplus", "update", "all"], timeout=35)
        combined = (out or "") + "\n" + (err or "")

        if (
            "api limit reached" in combined.casefold()
            or "rate limit" in combined.casefold()
        ):
            return StepResult("warning", "GitHub API rate limit reached")

        if code != 0:
            return StepResult(
                "error", "ProtonPlus update failed", error_output=err or out
            )

        installed = []
        for line in out.splitlines():
            line_s = line.strip()
            if "Installed:" in line_s or "Updated:" in line_s:
                parts = line_s.split(":", 1)
                val = parts[1].strip() if len(parts) > 1 else line_s
                sub = val.split(None, 1)
                if len(sub) == 2:
                    installed.append(f"{sub[0]} -> {sub[1]}")
                else:
                    installed.append(val)

        if installed:
            return StepResult(
                "ok",
                f"{len(installed)} runner{'s' if len(installed) != 1 else ''} updated",
                details=installed,
            )

        return StepResult("unchanged")
