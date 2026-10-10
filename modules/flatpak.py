"""
Flatpak package update module (User and System installations).
"""

import re
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class FlatpakModule(BaseModule):
    name = "Flatpak Packages"
    key = "flatpak"
    category = "Applications & Gaming"
    description = "Updates user and system Flatpak applications and runtimes"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("flatpak") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would update Flatpak user and system packages")

        updated_items = []
        errors = []
        support_warnings = []

        # 1. User updates
        u_code, u_out, u_err = ctx.run_cmd(["flatpak", "update", "--user", "-y", "--noninteractive"])
        if u_code != 0:
            errors.append(f"User Flatpaks: {u_err or u_out}")
        else:
            updated_items.extend(self._parse_updates(u_out))
            support_warnings.extend(self._find_support_warnings(u_out))

        # 2. System updates (polkit handles authorization)
        s_code, s_out, s_err = ctx.run_cmd(["flatpak", "update", "--system", "-y", "--noninteractive"])
        if s_code != 0:
            errors.append(f"System Flatpaks: {s_err or s_out}")
        else:
            updated_items.extend(self._parse_updates(s_out))
            support_warnings.extend(self._find_support_warnings(s_out))

        if errors:
            return StepResult(
                "error",
                "Flatpak update encountered errors",
                error_output="\n".join(errors),
                warnings=list(dict.fromkeys(support_warnings)),
            )

        # Deduplicate
        unique_updated = list(dict.fromkeys(updated_items))
        support_warnings = list(dict.fromkeys(support_warnings))
        if not unique_updated:
            return StepResult("unchanged", warnings=support_warnings)

        count = len(unique_updated)
        # Post-update version query
        post_map = {}
        v_code, v_out, _ = ctx.run_cmd(["flatpak", "list", "--columns=application,version"], read_only=True)
        if v_code == 0:
            for line in v_out.splitlines():
                parts = line.strip().split("\t")
                if len(parts) >= 2 and parts[1].strip():
                    post_map[parts[0].strip()] = parts[1].strip()

        formatted_details = [
            f"{app} -> {post_map[app]}" if app in post_map else app
            for app in unique_updated
        ]

        return StepResult(
            "ok",
            f"{count} package{'s' if count != 1 else ''} updated",
            details=formatted_details,
            warnings=support_warnings,
        )

    def _find_support_warnings(self, output: str):
        warnings = []
        for line in output.splitlines():
            line = line.strip()
            if "end-of-life" in line.lower() or "no longer receiving fixes and security updates" in line.lower():
                warnings.append(line)
        return warnings

    def _parse_updates(self, output: str):
        items = []
        for line in output.splitlines():
            # Match lines like: " 1. [✓] org.gnome.Platform"
            m = re.search(r"\[✓\]\s+([\w\.\-]+)", line)
            if m:
                items.append(m.group(1))
        return items
