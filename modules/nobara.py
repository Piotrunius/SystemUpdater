import os
from modules.base import BaseModule, UpdateContext, get_os_release
from ui import StepResult


IGNORED_DNF_TOKENS = {
    "package", "packages", "architecture", "version", "repository", "size",
    "transaction", "summary", "upgrading", "installing", "upgrading:", "installing:",
    "total", "download", "downloading", "complete!", "action", "upgraded", "installed",
    "replacing:", "replacing", "reinstalling:", "reinstalling"
}


def _clean_epoch(ver: str) -> str:
    return re.sub(r"^\d+:", "", ver)


def parse_dnf_packages(output: str) -> list:
    packages = []
    capture = False
    pending_pkg = None  # (name, ver)
    for line in output.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("=") or line_clean.startswith("-"):
            continue
        if "Upgrading:" in line or "Installing:" in line or "Upgrading" in line:
            capture = True
            continue
        if line_clean.startswith("Transaction Summary") or line_clean.startswith("Transaction complete"):
            capture = False
            continue
        if capture:
            parts = line_clean.split()
            if line_clean.startswith("replacing ") or line_clean.startswith("replacing:"):
                # e.g.: replacing sudo x86_64 0:1.9.17-8.p2.fc44 ...
                if pending_pkg and len(parts) >= 4:
                    old_ver = _clean_epoch(parts[3])
                    name, new_ver = pending_pkg
                    packages.append(f"{name}: {old_ver} -> {_clean_epoch(new_ver)}")
                    pending_pkg = None
                    continue
            if len(parts) >= 3:
                name = parts[0]
                arch = parts[1]
                ver = parts[2]
                if name.lower() not in IGNORED_DNF_TOKENS and arch in ("x86_64", "noarch", "i686", "aarch64", "armv7hl"):
                    if pending_pkg:
                        packages.append(f"{pending_pkg[0]} -> {_clean_epoch(pending_pkg[1])}")
                    pending_pkg = (name, ver)
    if pending_pkg:
        packages.append(f"{pending_pkg[0]} -> {_clean_epoch(pending_pkg[1])}")
    return list(dict.fromkeys(packages))


class RepoSyncModule(BaseModule):
    name = "Repository Sync"
    key = "reposync"
    aliases = ["repos"]
    category = "System Core"
    description = "Synchronizes Nobara repository configs, GPG keys, and updater packages"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("dnf") is None:
            return False
        os_info = get_os_release()
        return os_info.get("ID") == "nobara" or os.path.exists("/etc/nobara-release")

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would sync Nobara repositories and GPG keys")

        sync_cmd = [
            "sudo", "dnf", "update",
            "nobara-repos", "nobara-gpg-keys", "fedora-repos", "fedora-gpg-keys", "nobara-updater",
            "--refresh", "-y", "-q"
        ]
        # Allow 1 retry in case of transient repository network glitch or lock
        code, out, err = ctx.run_cmd(sync_cmd, timeout=300, retries=1, retry_delay=3.0)

        if code != 0:
            return StepResult("error", "Repository sync failed", error_output=err or out)

        upgraded = parse_dnf_packages(out)
        if upgraded:
            msg = f"{len(upgraded)} package{'s' if len(upgraded) != 1 else ''} updated"
            return StepResult("ok", msg, details=upgraded)

        if "Complete!" in out or "Nothing to do" in out or "Upgrading" in out:
            # If dnf upgraded something but package names weren't in output (e.g. quiet mode)
            if "Upgrading" in out:
                return StepResult("ok", "Repositories and core updater updated")
            return StepResult("unchanged")

        return StepResult("unchanged")


class SystemPackagesModule(BaseModule):
    name = "System Packages"
    key = "system"
    aliases = ["dnf", "rpm"]
    category = "System Core"
    description = "Performs full DNF system package upgrade"
    requires_sudo = True

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("dnf") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would upgrade DNF system packages")

        code, out, err = ctx.run_cmd(["sudo", "dnf", "upgrade", "--refresh", "-y"], timeout=600, retries=1, retry_delay=3.0)

        if code != 0:
            return StepResult("error", "DNF upgrade failed", error_output=err or out)

        if "Nothing to do" in out:
            return StepResult("unchanged")

        # Parse upgraded packages
        upgraded_pkgs = parse_dnf_packages(out)
        count = len(upgraded_pkgs)
        if count > 0:
            msg = f"{count} package{'s' if count != 1 else ''} upgraded"
            return StepResult("ok", msg, details=upgraded_pkgs)

        return StepResult("ok", "System packages upgraded successfully")
