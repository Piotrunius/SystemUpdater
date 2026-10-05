"""
ProtonPlus runners update module.
"""

import urllib.request
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class ProtonPlusModule(BaseModule):
    name = "ProtonPlus Runners"
    key = "proton"
    category = "Applications & Gaming"
    description = "Updates compatibility tools (Proton-GE, CachyOS, Wine) via ProtonPlus"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("protonplus") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would update Proton runners")

        # Fast health check for GitHub API before launching libsoup queries that could stall
        try:
            req = urllib.request.Request("https://api.github.com/", headers={"User-Agent": "SystemUpdater"})
            with urllib.request.urlopen(req, timeout=3.0):
                pass
        except Exception:
            return StepResult("warning", "GitHub API unreachable or timed out")

        code, out, err = ctx.run_cmd(["protonplus", "update", "all"], timeout=35)
        combined = (out or "") + "\n" + (err or "")

        if "API limit reached" in combined:
            return StepResult("warning", "GitHub API rate limit reached")

        if code != 0:
            return StepResult("error", "ProtonPlus update failed", error_output=err or out)

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
            return StepResult("ok", f"{len(installed)} runner{'s' if len(installed) != 1 else ''} updated", details=installed)

        return StepResult("unchanged")
