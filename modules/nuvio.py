"""
Nuvio Desktop updater module.
Checks GitHub releases for NuvioDesktop and installs RPM updates.
"""

import contextlib
import json
import os
import platform
import re
import tempfile
import urllib.error
import urllib.request
from typing import Any

from config import xdg_directory
from modules.base import BaseModule, UpdateContext, check_github_api
from ui import StepResult

REPO = "NuvioMedia/NuvioDesktop"
TAG_FILE = os.path.join(
    xdg_directory("XDG_CONFIG_HOME", "~/.config"),
    "nuvio",
    "installed_release_tag",
)


class NuvioModule(BaseModule):
    name = "Nuvio Desktop"
    key = "nuvio"
    category = "Applications & Gaming"
    description = "Checks GitHub releases for Nuvio and installs RPM updates"
    requires_sudo = True
    is_single_entity = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return os.path.exists("/opt/nuvio") or ctx.which("nuvio") is not None

    def _get_github_token(self, ctx: UpdateContext) -> str | None:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            code, out, _ = ctx.run_cmd(
                ["gh", "auth", "token"], read_only=True, sensitive_output=True
            )
            if code == 0 and out.strip():
                token = out.strip()
        return token or None

    def run(self, ctx: UpdateContext) -> StepResult:
        installed_tag = self._get_installed_tag(ctx)

        # Check GitHub API reachability if no authentication token is available
        token = self._get_github_token(ctx)
        if not token:
            gh_check = check_github_api()
            if gh_check is not None:
                return gh_check

        # Fetch latest release from GitHub
        try:
            release = self._fetch_latest_release(ctx, token=token)
        except urllib.error.HTTPError as error:
            if (
                error.code in (403, 429)
                or getattr(error, "headers", {}).get("x-ratelimit-remaining") == "0"
                or "rate limit" in str(error).casefold()
            ):
                return StepResult("warning", "GitHub API rate limit reached")
            reason = str(error).strip() or type(error).__name__
            return StepResult("warning", f"Unable to check GitHub: {reason}")
        except (OSError, TimeoutError, urllib.error.URLError) as e:
            err_msg = str(e).lower()
            if "rate limit" in err_msg:
                return StepResult("warning", "GitHub API rate limit reached")
            if "timed out" in err_msg or "timeout" in err_msg:
                return StepResult("warning", "GitHub API timed out")
            return StepResult("warning", f"Unable to check GitHub: {e}")
        except (json.JSONDecodeError, ValueError) as e:
            return StepResult("warning", f"Unable to parse GitHub release data: {e}")

        latest_tag = release.get("tag_name", "")
        latest_key = self._parse_version_key(latest_tag)
        installed_key = self._parse_version_key(installed_tag)

        # Check if update is available
        if installed_tag and latest_key <= installed_key:
            return StepResult("unchanged")

        # Update is available
        rpm_url, _ = self._find_rpm_asset(release.get("assets", []))
        if not rpm_url:
            return StepResult(
                "warning",
                f"New version {latest_tag} found, but no compatible RPM asset found",
            )

        fd, temp_rpm = tempfile.mkstemp(prefix="Nuvio-update-", suffix=".rpm")
        os.close(fd)
        try:
            # 1. Download RPM
            dl_code, _, dl_err = ctx.run_cmd(
                ["curl", "-sSL", "--fail", "-o", temp_rpm, rpm_url]
            )
            if dl_code != 0:
                return StepResult(
                    "error",
                    f"Failed to download RPM for {latest_tag}",
                    error_output=dl_err,
                )

            # 2. Upgrade RPM package
            up_code, up_out, up_err = ctx.run_cmd(
                ["sudo", "dnf", "upgrade", "-y", "-q", temp_rpm]
            )
            if up_code != 0:
                up_code, up_out, up_err = ctx.run_cmd(
                    ["sudo", "rpm", "-U", "--replacepkgs", temp_rpm]
                )
                if up_code != 0:
                    return StepResult(
                        "error",
                        f"Failed to install RPM {latest_tag}",
                        error_output=up_err or up_out,
                    )

            # Record the installed release tag
            try:
                os.makedirs(os.path.dirname(TAG_FILE), exist_ok=True)
                with open(TAG_FILE, "w") as f:
                    f.write(latest_tag + "\n")
            except OSError as error:
                raise RuntimeError(
                    f"Could not save installed Nuvio release tag: {error}"
                ) from error

            return StepResult("ok", "updated")

        finally:
            with contextlib.suppress(FileNotFoundError):
                os.remove(temp_rpm)

    def _get_installed_tag(self, ctx: UpdateContext) -> str:
        if os.path.exists(TAG_FILE):
            try:
                with open(TAG_FILE, "r") as f:
                    val = f.read().strip()
                    if val:
                        return val
            except OSError as error:
                ctx.print_verbose(
                    f"Could not read the stored Nuvio release tag: {error}"
                )

        code, out, _ = ctx.run_cmd(
            ["rpm", "-q", "--qf", "%{VERSION}", "nuvio"], read_only=True
        )
        if code == 0 and out.strip():
            rpm_ver = out.strip()
            m = re.match(r"^1\.(\d+\.\d+)", rpm_ver)
            if m:
                tag = f"0.{m.group(1)}-alpha"
                os.makedirs(os.path.dirname(TAG_FILE), exist_ok=True)
                with open(TAG_FILE, "w") as f:
                    f.write(tag + "\n")
                return tag
        return ""

    def _parse_version_key(self, v_str: str) -> tuple[int, ...]:
        if not v_str:
            return ()
        clean = v_str.strip().lstrip("vV")
        parts = clean.split("-", 1)
        core = parts[0]
        core_nums = [int(n) for n in re.findall(r"\d+", core)]
        while len(core_nums) < 3:
            core_nums.append(0)

        if len(parts) > 1:
            prerelease = parts[1].lower()
            if "alpha" in prerelease:
                stage = 1
            elif "beta" in prerelease:
                stage = 2
            elif "rc" in prerelease:
                stage = 3
            else:
                stage = 0
            extra_nums = [int(n) for n in re.findall(r"\d+", prerelease)]
            extra = extra_nums[0] if extra_nums else 0
            return tuple(core_nums[:3]) + (stage, extra)
        else:
            return tuple(core_nums[:3]) + (999, 0)

    def _find_rpm_asset(self, assets: list[dict[str, Any]]) -> tuple[str | None, str]:
        rpm_assets = [a for a in assets if a.get("name", "").endswith(".rpm")]
        if not rpm_assets:
            return None, ""

        machine = platform.machine().lower()
        architecture_aliases = {
            "x86_64": ("x86_64", "amd64", "x64"),
            "aarch64": ("aarch64", "arm64"),
            "armv7l": ("armv7", "armhf"),
            "i686": ("i686", "i386"),
        }
        supported_arches = architecture_aliases.get(machine)
        matching_assets = []
        generic_assets = []
        for asset in rpm_assets:
            asset_name = asset.get("name", "").lower()
            declared_arches = {
                alias
                for aliases in architecture_aliases.values()
                for alias in aliases
                if alias in asset_name
            }
            if supported_arches and declared_arches.intersection(supported_arches):
                matching_assets.append(asset)
            elif not declared_arches:
                generic_assets.append(asset)

        target = next(iter(matching_assets), None)
        if target is None and len(generic_assets) == 1:
            target = generic_assets[0]
        if target is None:
            target = next(
                (
                    asset
                    for asset in generic_assets
                    if "linux" in asset.get("name", "").lower()
                ),
                None,
            )

        if target:
            url = target.get("browser_download_url")
            size_b = target.get("size", 0)
            size_str = f"{size_b / (1024 * 1024):.0f} MB" if size_b else ""
            return url, size_str

        return None, ""

    def _fetch_latest_release(
        self, ctx: UpdateContext, token: str | None = None
    ) -> dict[str, Any]:
        url = f"https://api.github.com/repos/{REPO}/releases/latest"
        headers = {
            "User-Agent": "SystemUpdater-Nuvio",
            "Accept": "application/vnd.github.v3+json",
        }
        active_token = token if token is not None else self._get_github_token(ctx)
        if active_token:
            headers["Authorization"] = f"Bearer {active_token}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
