"""
Developer tools, language runtimes, and shell extensions modules.
"""

import json
import os
import re
from modules.base import BaseModule, UpdateContext
from ui import StepResult


class OhMyZshModule(BaseModule):
    name = "Oh My Zsh"
    key = "omz"
    category = "Development Environment"
    description = "Updates Oh My Zsh framework"
    is_single_entity = True

    def is_available(self, ctx: UpdateContext) -> bool:
        omz_dir = os.path.expanduser("~/.oh-my-zsh")
        return os.path.isdir(omz_dir) and ctx.which("git") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        omz_dir = os.path.expanduser("~/.oh-my-zsh")
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would update Oh My Zsh")

        _, old_head, _ = ctx.run_cmd(
            ["git", "-C", omz_dir, "rev-parse", "--short", "HEAD"], read_only=True
        )
        old_commit = old_head.strip()

        code, out, err = ctx.run_cmd(
            ["git", "-C", omz_dir, "pull", "--rebase", "--stat", "origin", "master"]
        )
        if code != 0:
            return StepResult(
                "error", "Oh My Zsh update failed", error_output=err or out
            )

        if "Already up to date" in out or "Already up-to-date" in out:
            return StepResult("unchanged")

        m = re.search(r"Updating\s+([0-9a-fA-F]+)\.\.([0-9a-fA-F]+)", out)
        if m:
            ver_change = f"{m.group(1)} -> {m.group(2)}"
        else:
            _, new_head, _ = ctx.run_cmd(
                ["git", "-C", omz_dir, "rev-parse", "--short", "HEAD"], read_only=True
            )
            new_commit = new_head.strip()
            if old_commit and new_commit and old_commit != new_commit:
                ver_change = f"{old_commit} -> {new_commit}"
            else:
                ver_change = "updated"

        return StepResult("ok", "updated", details=[ver_change])


class RustupModule(BaseModule):
    name = "Rust Toolchains"
    key = "rustup"
    category = "Development Environment"
    description = "Updates Rust compiler toolchains and rustup itself"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("rustup") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run rustup update")

        code, out, err = ctx.run_cmd(["rustup", "update"])
        if code != 0:
            return StepResult("error", "rustup update failed", error_output=err or out)

        if "unchanged" in out and "update available" not in out:
            return StepResult("unchanged")

        matches = re.findall(
            r"([\w\.\-]+)\s+updated\s+-\s+rustc\s+([^\s]+).*?->\s+rustc\s+([^\s]+)", out
        )
        if matches:
            details = [f"{tc}: {old} -> {new}" for tc, old, new in matches]
            count = len(details)
            return StepResult(
                "ok",
                f"{count} toolchain{'s' if count != 1 else ''} updated",
                details=details,
            )

        m_self = re.search(r"rustup updated.*?([0-9\.]+)\s+to\s+([0-9\.]+)", out)
        if m_self:
            return StepResult(
                "ok",
                "1 toolchain updated",
                details=[f"rustup: {m_self.group(1)} -> {m_self.group(2)}"],
            )

        return StepResult("ok", "toolchain updated")


class PipModule(BaseModule):
    name = "Python Pip"
    key = "pip"
    category = "Development Environment"
    description = "Upgrades pip user installation to the latest version"
    is_single_entity = True

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("pip3") is not None or ctx.which("pip") is not None:
            return True
        py_bin = ctx.which("python3") or ctx.which("python")
        if py_bin:
            code, _, _ = ctx.run_cmd([py_bin, "-m", "pip", "--version"], read_only=True)
            return code == 0
        return False

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would upgrade pip")

        py_bin = ctx.which("python3") or ctx.which("python")
        pip_bin = ctx.which("pip3") or ctx.which("pip")
        if py_bin:
            cmd_prefix = [py_bin, "-m", "pip"]
        elif pip_bin:
            cmd_prefix = [pip_bin]
        else:
            return StepResult("skipped", "pip not available")

        _, pre_v, _ = ctx.run_cmd(cmd_prefix + ["--version"], read_only=True)
        m_old = re.search(r"pip\s+([^\s]+)", pre_v or "")
        old_ver = m_old.group(1) if m_old else ""

        code, out, err = ctx.run_cmd(cmd_prefix + ["install", "--upgrade", "pip"])
        if code != 0:
            combined = f"{out}\n{err}".lower()
            if "externally-managed-environment" in combined:
                # If managed externally (e.g. Homebrew, PEP 668), check if standalone pip binary exists
                pip_standalone = ctx.which("pip3") or ctx.which("pip")
                if pip_standalone and (not py_bin or pip_standalone != py_bin):
                    code_user, out_user, err_user = ctx.run_cmd([pip_standalone, "install", "--upgrade", "pip"])
                    if code_user == 0:
                        code, out, err = code_user, out_user, err_user
                    elif "externally-managed-environment" in f"{out_user}\n{err_user}".lower():
                        return StepResult("unchanged")
                    else:
                        return StepResult("error", "pip upgrade failed", error_output=err_user or out_user)
                else:
                    return StepResult("unchanged")
            else:
                return StepResult("error", "pip upgrade failed", error_output=err or out)

        if "Requirement already satisfied" in out:
            return StepResult("unchanged")

        m_new = re.search(r"Successfully installed\s+pip-([\w\.\+]+)", out)
        new_ver = m_new.group(1) if m_new else ""

        if not new_ver:
            _, post_v, _ = ctx.run_cmd(cmd_prefix + ["--version"], read_only=True)
            m_post = re.search(r"pip\s+([^\s]+)", post_v or "")
            new_ver = m_post.group(1) if m_post else ""

        if old_ver and new_ver and old_ver != new_ver:
            ver_change = f"{old_ver} -> {new_ver}"
        elif new_ver:
            ver_change = f"-> {new_ver}"
        else:
            ver_change = "updated"

        return StepResult("ok", "updated", details=[ver_change])


class NpmModule(BaseModule):
    name = "NPM Packages"
    key = "npm"
    category = "Development Environment"
    description = "Updates globally installed Node.js npm packages"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("npm") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would check and update NPM packages")

        code, out, err = ctx.run_cmd(
            ["npm", "outdated", "-g", "--json"], read_only=True
        )
        if code not in (0, 1):
            return StepResult(
                "error", "npm outdated check failed", error_output=err or out
            )

        try:
            outdated = json.loads(out) if out.strip() else {}
        except json.JSONDecodeError:
            return StepResult(
                "error", "npm outdated returned invalid JSON", error_output=err or out
            )

        if not isinstance(outdated, dict):
            return StepResult(
                "error", "npm outdated returned unexpected data", error_output=out
            )
        if code == 1 and not outdated:
            return StepResult(
                "error", "npm outdated check failed", error_output=err or out
            )

        if not outdated:
            return StepResult("unchanged")

        pkg_names = list(outdated.keys())
        up_code, up_out, up_err = ctx.run_cmd(["npm", "update", "-g"])
        if up_code != 0:
            return StepResult(
                "error", "npm update failed", error_output=up_err or up_out
            )

        details = []
        for pkg, info in outdated.items():
            curr = info.get("current")
            latest = info.get("latest") or info.get("wanted")
            if curr and latest and curr != latest:
                details.append(f"{pkg}: {curr} -> {latest}")
            elif latest:
                details.append(f"{pkg} -> {latest}")
            else:
                details.append(pkg)

        count = len(pkg_names)
        return StepResult(
            "ok", f"{count} package{'s' if count != 1 else ''} updated", details=details
        )


class PnpmModule(BaseModule):
    name = "PNPM Packages"
    key = "pnpm"
    category = "Development Environment"
    description = "Updates globally installed pnpm packages"

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("pnpm") is None:
            return "not-installed"
        code, out, err = ctx.run_cmd(["pnpm", "ls", "-g"], timeout=10, read_only=True)
        output = f"{out}\n{err}".strip().lower()
        if "no global packages found" in output or not output:
            return "no-targets"
        return "active" if code == 0 else "unavailable"

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
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would update PNPM packages")

        ls_code, ls_out, ls_err = ctx.run_cmd(["pnpm", "ls", "-g"])
        ls_output = f"{ls_out}\n{ls_err}"
        if "no global packages found" in ls_output.lower() or not ls_output.strip():
            return StepResult("unchanged")
        if ls_code != 0:
            return StepResult(
                "error", "pnpm package list failed", error_output=ls_err or ls_out
            )

        # Query outdated packages to capture versions
        outdated_code, outdated_out, _ = ctx.run_cmd(
            ["pnpm", "outdated", "-g", "--format", "json"]
        )
        outdated = {}
        metadata_warning = None
        if outdated_code == 0 and outdated_out.strip():
            try:
                outdated = json.loads(outdated_out)
                if not isinstance(outdated, dict):
                    raise json.JSONDecodeError(
                        "Expected a JSON object", outdated_out, 0
                    )
            except json.JSONDecodeError:
                metadata_warning = "Could not parse pnpm outdated package metadata"
        elif outdated_code != 0:
            metadata_warning = "Could not check pnpm package versions before updating"
        if metadata_warning:
            ctx.print_verbose(metadata_warning)

        code, out, err = ctx.run_cmd(["pnpm", "update", "-g"])
        combined = ((out or "") + "\n" + (err or "")).lower()

        if (
            "no global packages" in combined
            or "already up to date" in combined
            or "nothing to update" in combined
        ):
            return StepResult("unchanged")

        if code != 0:
            return StepResult("error", "pnpm update failed", error_output=err or out)

        if outdated:
            details = [
                f"{pkg} -> {info.get('latest', 'latest')}"
                for pkg, info in outdated.items()
            ]
            return StepResult(
                "ok",
                f"{len(details)} package{'s' if len(details) != 1 else ''} updated",
                details=details,
            )

        return StepResult("ok", "updated")


class BunModule(BaseModule):
    name = "Bun Packages"
    key = "bun"
    category = "Development Environment"
    description = "Updates globally installed Bun packages"

    def _availability(self, ctx: UpdateContext) -> str:
        if ctx.which("bun") is None:
            return "not-installed"
        code, out, err = ctx.run_cmd(
            ["bun", "pm", "ls", "-g"], timeout=10, read_only=True
        )
        output = f"{out}\n{err}".strip().lower()
        if (
            "no package.json was found" in output
            or "no global packages" in output
            or not output
            or output == "node_modules"
        ):
            return "no-targets"
        return "active" if code == 0 else "unavailable"

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
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run bun update -g")

        ls_code, ls_out, ls_err = ctx.run_cmd(["bun", "pm", "ls", "-g"])
        ls_output = f"{ls_out}\n{ls_err}"
        if (
            "no package.json was found" in ls_output.lower()
            or "no global packages" in ls_output.lower()
            or not ls_output.strip()
            or ls_output.strip() == "node_modules"
        ):
            return StepResult("unchanged")
        if ls_code != 0:
            return StepResult(
                "error", "Bun global package list failed", error_output=ls_err or ls_out
            )

        code, out, err = ctx.run_cmd(["bun", "update", "-g"])
        combined = (out or "") + "\n" + (err or "")
        if "No package.json" in combined or "nothing to update" in combined:
            return StepResult("unchanged")

        if code != 0:
            return StepResult("error", "bun update failed", error_output=err or out)

        matches = re.findall(r"(?:installed|\+)\s+([@\w\.\-\/]+)@([\w\.\-]+)", combined)
        if matches:
            details = [f"{p} -> {v}" for p, v in matches]
            return StepResult(
                "ok",
                f"{len(details)} package{'s' if len(details) != 1 else ''} updated",
                details=details,
            )

        return StepResult("ok", "updated")


class MicroModule(BaseModule):
    name = "Micro Plugins"
    key = "micro"
    category = "Development Environment"
    description = "Updates plugins installed in the Micro text editor"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("micro") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run micro -plugin update")

        code, out, err = ctx.run_cmd(["micro", "-plugin", "update"])
        if code != 0:
            return StepResult(
                "error", "micro plugin update failed", error_output=err or out
            )

        if "Nothing to install" in out or "Nothing to update" in out:
            return StepResult("unchanged")

        plugins = []
        for line in out.splitlines():
            m = re.search(
                r"(?:Updated|Installed|Updating)\s+plugin\s+([\w\.\-_]+)", line, re.I
            )
            if m:
                plugins.append(m.group(1))
        plugins = list(dict.fromkeys(plugins))

        if plugins:
            count = len(plugins)
            return StepResult(
                "ok",
                f"{count} plugin{'s' if count != 1 else ''} updated",
                details=plugins,
            )

        return StepResult("ok", "updated")


class GhExtensionsModule(BaseModule):
    name = "GitHub CLI Extensions"
    key = "gh"
    category = "Development Environment"
    description = "Updates installed GitHub CLI extensions"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("gh") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run gh extension upgrade --all")

        code, out, err = ctx.run_cmd(["gh", "extension", "upgrade", "--all"])
        if code != 0:
            return StepResult(
                "error", "gh extension upgrade failed", error_output=err or out
            )

        if "no installed extensions found" in out.lower() or not out.strip():
            return StepResult("unchanged")

        matches = re.findall(
            r"[Uu]pgraded\s+([\w\.\-\/]+)(?:\s+to\s+|\s+->\s+|\s+\([^)]*->\s*)([v\w\.\-]+)",
            out,
        )
        if matches:
            details = [f"{ext} -> {ver.rstrip(')')}" for ext, ver in matches]
            count = len(details)
            return StepResult(
                "ok",
                f"{count} extension{'s' if count != 1 else ''} updated",
                details=details,
            )

        return StepResult("ok", "updated")


class SkillsModule(BaseModule):
    name = "Agent Skills"
    key = "skills"
    category = "Development Environment"
    description = "Updates global Agent Skills via npx skills"

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("npx") is None:
            return False
        # Only activate if agent skills are actually installed locally or globally
        lock_file = os.path.expanduser("~/.agents/.skill-lock.json")
        skills_dir = os.path.expanduser("~/.agents/skills")
        return os.path.isfile(lock_file) or (
            os.path.isdir(skills_dir) and bool(os.listdir(skills_dir))
        )

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run npx -y skills update --global")

        code, out, err = ctx.run_cmd(["npx", "-y", "skills", "update", "--global"])
        if code != 0:
            return StepResult("error", "Skills update failed", error_output=err or out)

        if (
            "All global skills are up to date" in out
            or "No global skills tracked in lock file" in out
            or "No global skills found" in out
        ):
            return StepResult("unchanged")

        skills = []
        for line in out.splitlines():
            line_s = line.strip()
            m = re.search(r"[Uu]pdated\s+([@\w\.\-\/]+)", line_s)
            if m:
                cand = m.group(1).rstrip("…").rstrip(".")
                if "skill" not in cand.lower() and not cand.startswith("from"):
                    skills.append(cand)
        skills = list(dict.fromkeys(skills))

        count = len(skills)
        if count == 0:
            m_cnt = re.search(r"[Uu]pdated\s+(\d+)\s+skill", out)
            if m_cnt:
                count = int(m_cnt.group(1))
            else:
                return StepResult("unchanged")
            return StepResult("ok", f"{count} skill{'s' if count != 1 else ''} updated")

        return StepResult(
            "ok", f"{count} skill{'s' if count != 1 else ''} updated", details=skills
        )


class AntigravityModule(BaseModule):
    name = "Antigravity Extensions"
    key = "antigravity"
    category = "Development Environment"
    description = "Updates Antigravity extensions"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("antigravity") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult(
                "ok", "[DRY-RUN] Would run antigravity --update-extensions"
            )

        code, out, err = ctx.run_cmd(["antigravity", "--update-extensions"])
        clean_err = "\n".join(
            l for l in err.splitlines() if "antigravityAnalytics" not in l
        ).strip()
        if code != 0 and clean_err:
            return StepResult(
                "error", "Antigravity update failed", error_output=clean_err
            )

        if "No extension to update" in out:
            return StepResult("unchanged")

        exts = []
        for line in out.splitlines():
            m = re.search(
                r"Extension\s+'([^']+)'\s+(?:v[^\s]+\s+)?was successfully updated",
                line,
                re.I,
            )
            if not m:
                m = re.search(r"Updated\s+extension\s+([^\s]+)", line, re.I)
            if m:
                exts.append(m.group(1))
        exts = list(dict.fromkeys(exts))

        if exts:
            count = len(exts)
            return StepResult(
                "ok",
                f"{count} extension{'s' if count != 1 else ''} updated",
                details=exts,
            )

        return StepResult("ok", "updated")


class YarnModule(BaseModule):
    name = "Yarn Packages"
    key = "yarn"
    category = "Development Environment"
    description = "Updates globally installed Yarn packages"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("yarn") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run yarn global upgrade")

        code, out, err = ctx.run_cmd(["yarn", "global", "upgrade"], timeout=180)
        if code != 0:
            return StepResult("error", "yarn upgrade failed", error_output=err or out)

        if "success Already up-to-date" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class UvModule(BaseModule):
    name = "uv Tools"
    key = "uv"
    category = "Development Environment"
    description = "Updates uv executable and all installed uv tools"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("uv") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would update uv and uv tools")

        ctx.run_cmd(["uv", "self", "update"], timeout=30)
        code, out, err = ctx.run_cmd(["uv", "tool", "upgrade", "--all"], timeout=180)
        if code != 0:
            return StepResult(
                "error", "uv tool upgrade failed", error_output=err or out
            )

        if "Nothing to upgrade" in out or not out.strip():
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class PipxModule(BaseModule):
    name = "Python Pipx Applications"
    key = "pipx"
    category = "Development Environment"
    description = "Updates all pipx-installed CLI applications"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("pipx") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run pipx upgrade-all")

        code, out, err = ctx.run_cmd(["pipx", "upgrade-all"], timeout=300)
        if code != 0:
            return StepResult(
                "error", "pipx upgrade-all failed", error_output=err or out
            )

        if (
            "versions are already at latest" in out.lower()
            or "no packages to upgrade" in out.lower()
        ):
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class PoetryModule(BaseModule):
    name = "Python Poetry"
    key = "poetry"
    category = "Development Environment"
    description = "Updates Poetry packaging tool"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("poetry") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run poetry self update")

        code, out, err = ctx.run_cmd(["poetry", "self", "update"], timeout=120)
        if code != 0:
            return StepResult("error", "poetry update failed", error_output=err or out)

        if "You are using the latest version" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class CondaModule(BaseModule):
    name = "Conda Environment"
    key = "conda"
    category = "Development Environment"
    description = "Updates Conda base environment packages"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("conda") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run conda update -n base --all -y")

        code, out, err = ctx.run_cmd(
            ["conda", "update", "-n", "base", "--all", "-y"], timeout=300
        )
        if code != 0:
            return StepResult("error", "conda update failed", error_output=err or out)

        if "# All requested packages already installed" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class CargoUpdateModule(BaseModule):
    name = "Cargo Binaries"
    key = "cargo"
    category = "Development Environment"
    description = "Updates installed cargo crates via cargo-update"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("cargo-install-update") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run cargo install-update -a")

        code, out, err = ctx.run_cmd(["cargo", "install-update", "-a"], timeout=600)
        if code != 0:
            return StepResult(
                "error", "cargo install-update failed", error_output=err or out
            )

        if "No packages need updating" in out or "Everything is up to date" in out:
            return StepResult("unchanged")

        matches = re.findall(
            r"(?:Updating\s+)?([\w\.\-_]+)\s+(?:from\s+v?[\w\.\-_]+\s+to|->)\s+v?([\w\.\-_]+)",
            out,
        )
        if matches:
            details = [f"{crate} -> {ver}" for crate, ver in matches]
            return StepResult(
                "ok",
                f"{len(details)} crate{'s' if len(details) != 1 else ''} updated",
                details=details,
            )

        return StepResult("ok", "updated")


class ComposerModule(BaseModule):
    name = "PHP Composer"
    key = "composer"
    category = "Development Environment"
    description = "Updates Composer executable and global dependencies"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("composer") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult(
                "ok", "[DRY-RUN] Would update Composer and global packages"
            )

        ctx.run_cmd(["composer", "self-update"], timeout=60)
        code, out, err = ctx.run_cmd(["composer", "global", "update"], timeout=180)
        if code != 0:
            return StepResult(
                "error", "composer global update failed", error_output=err or out
            )

        if "Nothing to modify in lock file" in out or "Nothing to install" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class GemModule(BaseModule):
    name = "Ruby Gems"
    key = "gem"
    category = "Development Environment"
    description = "Updates RubyGems system and installed gems"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("gem") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run gem update --system")

        # Capture old RubyGems version
        old_ver_code, old_ver_out, _ = ctx.run_cmd(["gem", "--version"], read_only=True)
        old_system_ver = (
            old_ver_out.strip() if old_ver_code == 0 and old_ver_out.strip() else None
        )

        code, out, err = ctx.run_cmd(["gem", "update", "--system"], timeout=180)
        if code != 0:
            return StepResult("error", "gem update failed", error_output=err or out)

        if "Latest version already installed" in out:
            return StepResult("unchanged")

        details = []
        # Check if RubyGems version was updated
        m_ver = re.search(r"RubyGems\s+([0-9\.]+)\s+installed", out, re.I) or re.search(
            r"Installing RubyGems\s+([0-9\.]+)", out, re.I
        )
        new_system_ver = m_ver.group(1) if m_ver else None
        if not new_system_ver:
            new_code, new_out, _ = ctx.run_cmd(["gem", "--version"], read_only=True)
            if new_code == 0 and new_out.strip():
                new_system_ver = new_out.strip()

        if new_system_ver:
            if old_system_ver and old_system_ver != new_system_ver:
                details.append(f"rubygems-update: {old_system_ver} -> {new_system_ver}")
            else:
                details.append(f"rubygems-update -> {new_system_ver}")

        count = len(details)
        if count > 0:
            msg = f"{count} package{'s' if count != 1 else ''} updated"
            return StepResult("ok", msg, details=details)

        return StepResult("ok", "1 package updated")


class MiseModule(BaseModule):
    name = "Mise Runtime Tools"
    key = "mise"
    category = "Development Environment"
    description = "Updates mise CLI and installed dev toolchains"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("mise") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult(
                "ok", "[DRY-RUN] Would run mise self-update and mise upgrade"
            )

        ctx.run_cmd(["mise", "self-update", "-y"], timeout=60)
        code, out, err = ctx.run_cmd(["mise", "upgrade", "-y"], timeout=300)
        if code != 0:
            return StepResult("error", "mise upgrade failed", error_output=err or out)

        return StepResult("ok", "updated")


class AsdfModule(BaseModule):
    name = "asdf Plugins"
    key = "asdf"
    category = "Development Environment"
    description = "Updates asdf version manager plugins"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("asdf") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run asdf plugin update --all")

        code, out, err = ctx.run_cmd(["asdf", "plugin", "update", "--all"], timeout=120)
        if code != 0:
            return StepResult(
                "error", "asdf plugin update failed", error_output=err or out
            )

        return StepResult("ok", "updated")


class NeovimModule(BaseModule):
    name = "Neovim Plugins"
    key = "neovim"
    category = "Development Environment"
    description = "Updates Neovim plugins via Lazy.nvim"

    def is_available(self, ctx: UpdateContext) -> bool:
        if ctx.which("nvim") is None:
            return False
        lazy_dir = os.path.expanduser("~/.local/share/nvim/lazy")
        return os.path.isdir(lazy_dir)

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run nvim Lazy sync")

        code, out, err = ctx.run_cmd(
            ["nvim", "--headless", "+Lazy! sync", "+qa"], timeout=120
        )
        if code != 0:
            return StepResult(
                "error", "Neovim Lazy sync failed", error_output=err or out
            )

        return StepResult("ok", "updated")


class TmuxPluginsModule(BaseModule):
    name = "Tmux Plugins"
    key = "tmux"
    category = "Development Environment"
    description = "Updates tmux plugins via TPM"

    def is_available(self, ctx: UpdateContext) -> bool:
        tpm_script = os.path.expanduser("~/.tmux/plugins/tpm/bin/update_plugins")
        return os.path.isfile(tpm_script)

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run TPM update_plugins all")

        tpm_script = os.path.expanduser("~/.tmux/plugins/tpm/bin/update_plugins")
        code, out, err = ctx.run_cmd([tpm_script, "all"], timeout=120)
        if code != 0:
            return StepResult("error", "TPM update failed", error_output=err or out)

        return StepResult("ok", "updated")
