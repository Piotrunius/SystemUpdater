"""
Gear Lever AppImage manager module.
"""

import hashlib
import json
import os

from modules.base import BaseModule, UpdateContext, check_github_api
from ui import StepResult


class GearLeverModule(BaseModule):
    name = "Gear Lever"
    key = "gearlever"
    category = "Applications & Gaming"
    description = "Checks and fetches appimage updates via Gear Lever"
    unit_name = "appimage"
    unit_name_plural = "appimages"

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("flatpak") is None:
            return False
        _, out, _ = ctx.run_cmd(
            ["flatpak", "list", "--app", "--columns=application"], read_only=True
        )
        return "it.mijorus.gearlever" in out

    @staticmethod
    def _read_file_hash(path: str) -> str | None:
        if not path or not os.path.isfile(path):
            return None
        try:
            h = hashlib.sha1()
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()[:7]
        except (OSError, PermissionError):
            return None

    def _resolve_appimage_path(self, update_info: dict) -> str | None:
        path = update_info.get("path")
        if path:
            return path

        name = update_info.get("name", "")
        if name:
            appimages_dir = os.path.expanduser("~/AppImages")
            if os.path.isdir(appimages_dir):
                norm_name = name.lower().replace(" ", "_")
                cand = os.path.join(appimages_dir, f"{norm_name}.appimage")
                if os.path.isfile(cand):
                    return cand
                cand2 = os.path.join(
                    appimages_dir, f"{name.lower().replace(' ', '-')}.appimage"
                )
                if os.path.isfile(cand2):
                    return cand2
                for fname in os.listdir(appimages_dir):
                    if fname.lower().endswith(
                        ".appimage"
                    ) and norm_name in fname.lower().replace(" ", "_"):
                        return os.path.join(appimages_dir, fname)

        return None

    def _get_app_hashes(self, updates: list[dict]) -> dict[str, str]:
        hashes = {}
        for u in updates:
            if not isinstance(u, dict):
                continue
            name = u.get("name", "appimage")
            commit = u.get("current_commit") or u.get("old_commit") or u.get("commit")
            if commit:
                hashes[name] = str(commit)[:7]
                continue

            path = self._resolve_appimage_path(u)
            if path:
                f_hash = self._read_file_hash(path)
                if f_hash:
                    hashes[name] = f_hash
        return hashes

    def _get_updated_hashes(self, updates: list[dict]) -> dict[str, str]:
        hashes = {}
        for u in updates:
            if not isinstance(u, dict):
                continue
            name = u.get("name", "appimage")
            new_commit = u.get("available_commit") or u.get("new_commit")
            if new_commit:
                hashes[name] = str(new_commit)[:7]
                continue

            path = self._resolve_appimage_path(u)
            if path:
                f_hash = self._read_file_hash(path)
                if f_hash:
                    hashes[name] = f_hash
        return hashes

    def run(self, ctx: UpdateContext) -> StepResult:
        gh_check = check_github_api()
        if gh_check is not None:
            return gh_check

        code, out, err = ctx.run_cmd(
            [
                "flatpak",
                "run",
                "--env=LC_ALL=C.UTF-8",
                "it.mijorus.gearlever",
                "--list-updates",
                "--json",
            ]
        )
        combined = (out or "") + "\n" + (err or "")
        if (
            "rate limit" in combined.casefold()
            or "api limit reached" in combined.casefold()
        ):
            return StepResult("warning", "GitHub API rate limit reached")

        if code != 0:
            return StepResult("unchanged")

        updates = []
        try:
            json_start = out.find("{")
            if json_start != -1:
                data = json.loads(out[json_start:])
                updates = data.get("updates", [])
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        if not updates:
            return StepResult("unchanged")

        before_hashes = self._get_app_hashes(updates)

        up_code, up_out, up_err = ctx.run_cmd(
            [
                "flatpak",
                "run",
                "--env=LC_ALL=C.UTF-8",
                "it.mijorus.gearlever",
                "--update",
                "--all",
                "--yes",
            ],
            timeout=300,
        )
        up_combined = (up_out or "") + "\n" + (up_err or "")
        if (
            "rate limit" in up_combined.casefold()
            or "api limit reached" in up_combined.casefold()
        ):
            return StepResult("warning", "GitHub API rate limit reached")

        if up_code != 0:
            return StepResult(
                "error",
                "Gear Lever appimage update failed",
                error_output=up_err or up_out,
            )

        after_hashes = self._get_updated_hashes(updates)

        details = []
        for u in updates:
            if not isinstance(u, dict):
                continue
            name = u.get("name", "appimage")
            old_h = before_hashes.get(name)
            new_h = after_hashes.get(name)
            if old_h and new_h and old_h != new_h:
                details.append(f"{name}: {old_h} -> {new_h}")
            elif new_h and not old_h:
                details.append(f"{name}: -> {new_h}")
            else:
                cur = u.get("current_version")
                avail = u.get("available_version")
                if cur and avail and str(cur) != str(avail):
                    details.append(f"{name}: {cur} -> {avail}")
                elif avail:
                    details.append(f"{name}: -> {avail}")
                else:
                    details.append(name)

        count = len(details)
        return StepResult(
            "ok",
            f"{count} appimage{'s' if count != 1 else ''} updated",
            details=details,
        )
