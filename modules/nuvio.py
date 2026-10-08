"""
Unified Nuvio Desktop updater and high-quality image bytecode patcher.
Consolidates check_update.py, update_nuvio.sh, and patch_nuvio.py.
"""

import contextlib
import glob
import json
import os
import platform
import re
import tempfile
import urllib.request
import zipfile
from typing import Optional, Tuple
from modules.base import BaseModule, UpdateContext
from ui import StepResult

REPO = "NuvioMedia/NuvioDesktop"
TAG_FILE = os.path.expanduser("~/.config/nuvio/installed_release_tag")
TARGET_DIR = "/opt/nuvio/lib/app"
CLASS_PATH = "com/nuvio/app/core/ui/AsyncImage_desktopKt.class"
PATCH_SIGNATURE = b"\x57\x57\x00\x00\x00\x00\x00\x04\xb3"


class NuvioModule(BaseModule):
    name = "Nuvio Desktop"
    key = "nuvio"
    category = "Applications & Gaming"
    description = "Checks GitHub releases for Nuvio, installs RPM, and applies Coil3 Linux image patch"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return os.path.exists("/opt/nuvio") or ctx.which("nuvio") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        installed_tag = self._get_installed_tag(ctx)

        # Fetch latest release from GitHub
        try:
            release = self._fetch_latest_release(ctx)
        except Exception as e:
            err_msg = str(e).lower()
            if "timed out" in err_msg or "timeout" in err_msg:
                return StepResult("warning", "GitHub API timed out")
            return StepResult("warning", f"Unable to check GitHub: {e}")

        latest_tag = release.get("tag_name", "")
        latest_key = self._parse_version_key(latest_tag)
        installed_key = self._parse_version_key(installed_tag)

        # Check if update is available
        if installed_tag and latest_key <= installed_key:
            target_jar = self._find_target_jar()
            if not target_jar:
                return StepResult("warning", "Nuvio application JAR was not found; image patch was skipped")
            if ctx.dry_run:
                if not self._is_jar_patched(target_jar):
                    return StepResult("ok", "[DRY-RUN] Would re-apply image patch")
                return StepResult("unchanged")
            # Verify and ensure patch is applied on current jar
            patch_applied = self._ensure_patched(ctx)
            if patch_applied:
                return StepResult("ok", f"Re-applied image patch on {installed_tag}")
            return StepResult("unchanged")

        # Update is available
        rpm_url, _ = self._find_rpm_asset(release.get("assets", []))
        if not rpm_url:
            return StepResult("warning", f"New version {latest_tag} found, but no compatible RPM asset found")

        if ctx.dry_run:
            return StepResult("ok", f"[DRY-RUN] Would update to {latest_tag}")

        fd, temp_rpm = tempfile.mkstemp(prefix="Nuvio-update-", suffix=".rpm")
        os.close(fd)
        try:
            # 1. Download RPM
            dl_code, _, dl_err = ctx.run_cmd(["curl", "-sSL", "--fail", "-o", temp_rpm, rpm_url])
            if dl_code != 0:
                return StepResult("error", f"Failed to download RPM for {latest_tag}", error_output=dl_err)

            # 2. Upgrade RPM package
            up_code, up_out, up_err = ctx.run_cmd(["sudo", "dnf", "upgrade", "-y", "-q", temp_rpm])
            if up_code != 0:
                up_code, up_out, up_err = ctx.run_cmd(["sudo", "rpm", "-U", "--replacepkgs", temp_rpm])
                if up_code != 0:
                    return StepResult("error", f"Failed to install RPM {latest_tag}", error_output=up_err or up_out)

            # Record the installed release before patching so a patch failure does not
            # cause the next run to reinstall the same RPM.
            try:
                os.makedirs(os.path.dirname(TAG_FILE), exist_ok=True)
                with open(TAG_FILE, "w") as f:
                    f.write(latest_tag + "\n")
            except OSError as error:
                raise RuntimeError(f"Could not save installed Nuvio release tag: {error}") from error

            # Apply the image patch after recording the package upgrade.
            if not self._ensure_patched(ctx, force=True):
                return StepResult(
                    "warning",
                    f"Updated Nuvio to {latest_tag}, but its application JAR was not found; image patch was skipped",
                    details=[f"nuvio -> {latest_tag}"],
                )

            return StepResult("ok", "updated", details=[f"nuvio -> {latest_tag}"])

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
                ctx.print_verbose(f"Could not read the stored Nuvio release tag: {error}")

        code, out, _ = ctx.run_cmd(["rpm", "-q", "--qf", "%{VERSION}", "nuvio"], read_only=True)
        if code == 0 and out.strip():
            rpm_ver = out.strip()
            m = re.match(r"^1\.(\d+\.\d+)", rpm_ver)
            if m:
                tag = f"0.{m.group(1)}-alpha"
                if not ctx.dry_run:
                    os.makedirs(os.path.dirname(TAG_FILE), exist_ok=True)
                    with open(TAG_FILE, "w") as f:
                        f.write(tag + "\n")
                return tag
        return ""

    def _parse_version_key(self, v_str: str) -> tuple:
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

    def _find_rpm_asset(self, assets: list) -> Tuple[Optional[str], str]:
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
                (asset for asset in generic_assets if "linux" in asset.get("name", "").lower()),
                None,
            )

        if target:
            url = target.get("browser_download_url")
            size_b = target.get("size", 0)
            size_str = f"{size_b / (1024 * 1024):.0f} MB" if size_b else ""
            return url, size_str

        return None, ""

    def _fetch_latest_release(self, ctx: UpdateContext) -> dict:
        url = f"https://api.github.com/repos/{REPO}/releases/latest"
        headers = {
            "User-Agent": "SystemUpdater-Nuvio",
            "Accept": "application/vnd.github.v3+json",
        }
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            code, out, _ = ctx.run_cmd(
                ["gh", "auth", "token"], read_only=True, sensitive_output=True
            )
            if code == 0 and out.strip():
                token = out.strip()

        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())

    def _find_target_jar(self) -> Optional[str]:
        matches = glob.glob(os.path.join(TARGET_DIR, "composeApp-desktop-*.jar"))
        matches = [m for m in matches if not m.endswith(".bak")]
        return max(matches, key=os.path.getmtime) if matches else None

    def _is_jar_patched(self, jar_path: str) -> bool:
        try:
            with zipfile.ZipFile(jar_path, "r") as z:
                data = z.read(CLASS_PATH)
                return PATCH_SIGNATURE in data
        except (OSError, KeyError, zipfile.BadZipFile):
            return False

    def _patch_bytecode(self, data: bytearray) -> bytearray:
        pos = 0
        found = False
        while True:
            idx = data.find(b"\xb1", pos)
            if idx == -1:
                break
            if idx >= 26 and data[idx - 3] == 0xb3 and data[idx - 4] == 0x03:
                clinit_start = idx - 26
                data[clinit_start + 15 : clinit_start + 23] = bytes([0x57, 0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04])
                found = True
                break
            pos = idx + 1

        if not found and PATCH_SIGNATURE not in data:
            raise ValueError("Could not locate AsyncImage_desktopKt.<clinit> bytecode pattern")

        return data

    def _ensure_patched(self, ctx: UpdateContext, force: bool = False) -> bool:
        target_jar = self._find_target_jar()
        if not target_jar:
            return False

        if not force and self._is_jar_patched(target_jar):
            return False

        if ctx.dry_run:
            return False

        # Generate a private temporary jar instead of using a predictable /tmp path.
        fd, temp_patched = tempfile.mkstemp(prefix="nuvio-patched-", suffix=".jar")
        os.close(fd)

        try:
            with zipfile.ZipFile(target_jar, "r") as zin:
                raw_class = bytearray(zin.read(CLASS_PATH))
                patched_class = self._patch_bytecode(raw_class)

                with zipfile.ZipFile(temp_patched, "w", compression=zipfile.ZIP_DEFLATED) as zout:
                    for item in zin.infolist():
                        if item.filename == CLASS_PATH:
                            zout.writestr(item, patched_class)
                        else:
                            zout.writestr(item, zin.read(item.filename))

            # Backup original if not backed up
            backup_path = f"{target_jar}.bak"
            if not os.path.exists(backup_path):
                code, out, err = ctx.run_cmd(["sudo", "cp", "-p", target_jar, backup_path])
                if code != 0:
                    raise RuntimeError(f"Could not back up Nuvio jar: {err or out}")

            # Replace with patched jar
            code, out, err = ctx.run_cmd(["sudo", "cp", "-f", temp_patched, target_jar])
            if code != 0:
                raise RuntimeError(f"Could not install patched Nuvio jar: {err or out}")
            # Clear coil cache
            ctx.run_cmd(["rm", "-rf", "/tmp/coil3_disk_cache"])
            return True
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.remove(temp_patched)
