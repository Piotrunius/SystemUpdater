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

    def is_available(self, ctx: UpdateContext) -> bool:
        omz_dir = os.path.expanduser("~/.oh-my-zsh")
        return os.path.isdir(omz_dir) and ctx.which("git") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        omz_dir = os.path.expanduser("~/.oh-my-zsh")
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would update Oh My Zsh")

        code, out, err = ctx.run_cmd(["git", "-C", omz_dir, "pull", "--rebase", "--stat", "origin", "master"])
        if code != 0:
            return StepResult("error", "Oh My Zsh update failed", error_output=err or out)

        if "Already up to date" in out or "Already up-to-date" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


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

        return StepResult("ok", "updated")


class PipModule(BaseModule):
    name = "Python Pip"
    key = "pip"
    category = "Development Environment"
    description = "Upgrades pip user installation to the latest version"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("pip3") is not None or ctx.which("python3") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would upgrade pip")

        pip_bin = ctx.which("pip3") or ctx.which("pip") or "pip3"
        code, out, err = ctx.run_cmd([pip_bin, "install", "--upgrade", "pip"])
        if code != 0:
            return StepResult("error", "pip upgrade failed", error_output=err or out)

        if "Requirement already satisfied" in out:
            return StepResult("unchanged")

        m = re.search(r"Successfully installed\s+pip-([\w\.\+]+)", out)
        if m:
            return StepResult("ok", "updated", details=[f"pip -> {m.group(1)}"])

        return StepResult("ok", "updated")


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

        code, out, err = ctx.run_cmd(["npm", "outdated", "-g", "--json"])
        try:
            outdated = json.loads(out) if out.strip() else {}
        except Exception:
            outdated = {}

        if not outdated:
            return StepResult("unchanged")

        pkg_names = list(outdated.keys())
        up_code, up_out, up_err = ctx.run_cmd(["npm", "update", "-g"])
        if up_code != 0:
            return StepResult("error", "npm update failed", error_output=up_err or up_out)

        details = [f"{pkg} -> {info.get('latest', 'latest')}" for pkg, info in outdated.items()]
        return StepResult("ok", f"{len(pkg_names)} package{'s' if len(pkg_names) != 1 else ''} updated", details=details)


class PnpmModule(BaseModule):
    name = "PNPM Packages"
    key = "pnpm"
    category = "Development Environment"
    description = "Updates globally installed pnpm packages"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("pnpm") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would update PNPM packages")

        ls_code, ls_out, _ = ctx.run_cmd(["pnpm", "ls", "-g"])
        if "no global packages found" in ls_out.lower() or not ls_out.strip():
            return StepResult("unchanged")

        # Query outdated packages to capture versions
        outdated_code, outdated_out, _ = ctx.run_cmd(["pnpm", "outdated", "-g", "--format", "json"])
        outdated = {}
        if outdated_code == 0 and outdated_out.strip():
            try:
                outdated = json.loads(outdated_out)
            except Exception:
                outdated = {}

        code, out, err = ctx.run_cmd(["pnpm", "update", "-g"])
        combined = ((out or "") + "\n" + (err or "")).lower()

        if "no global packages" in combined or "already up to date" in combined or "nothing to update" in combined:
            return StepResult("unchanged")

        if code != 0:
            return StepResult("error", "pnpm update failed", error_output=err or out)

        if outdated:
            details = [f"{pkg} -> {info.get('latest', 'latest')}" for pkg, info in outdated.items()]
            return StepResult("ok", f"{len(details)} package{'s' if len(details) != 1 else ''} updated", details=details[:10])

        return StepResult("ok", "updated")


class BunModule(BaseModule):
    name = "Bun Packages"
    key = "bun"
    category = "Development Environment"
    description = "Updates globally installed Bun packages"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("bun") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run bun update -g")

        ls_code, ls_out, _ = ctx.run_cmd(["bun", "pm", "ls", "-g"])
        if "no global packages" in ls_out.lower() or not ls_out.strip() or ls_out.strip() == "node_modules":
            return StepResult("unchanged")

        code, out, err = ctx.run_cmd(["bun", "update", "-g"])
        combined = (out or "") + "\n" + (err or "")
        if "No package.json" in combined or "nothing to update" in combined:
            return StepResult("unchanged")

        if code != 0:
            return StepResult("error", "bun update failed", error_output=err or out)

        matches = re.findall(r"(?:installed|\+)\s+([@\w\.\-\/]+)@([\w\.\-]+)", combined)
        if matches:
            details = [f"{p} -> {v}" for p, v in matches]
            return StepResult("ok", f"{len(details)} package{'s' if len(details) != 1 else ''} updated", details=details[:10])

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
            return StepResult("error", "micro plugin update failed", error_output=err or out)

        if "Nothing to install" in out or "Nothing to update" in out:
            return StepResult("unchanged")

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
            return StepResult("error", "gh extension upgrade failed", error_output=err or out)

        if "no installed extensions found" in out.lower() or not out.strip():
            return StepResult("unchanged")

        matches = re.findall(r"[Uu]pgraded\s+([\w\.\-\/]+)(?:\s+to\s+|\s+->\s+|\s+\([^)]*->\s*)([v\w\.\-]+)", out)
        if matches:
            details = [f"{ext} -> {ver.rstrip(')')}" for ext, ver in matches]
            return StepResult("ok", f"{len(details)} extension{'s' if len(details) != 1 else ''} updated", details=details[:10])

        return StepResult("ok", "updated")


class SkillsModule(BaseModule):
    name = "Agent Skills"
    key = "skills"
    category = "Development Environment"
    description = "Updates global Agent Skills via npx skills"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("npx") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run npx -y skills update --global")

        code, out, err = ctx.run_cmd(["npx", "-y", "skills", "update", "--global"])
        if code != 0:
            return StepResult("error", "Skills update failed", error_output=err or out)

        if "All global skills are up to date" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class AntigravityModule(BaseModule):
    name = "Antigravity Extensions"
    key = "antigravity"
    category = "Development Environment"
    description = "Updates Antigravity extensions"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("antigravity") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run antigravity --update-extensions")

        code, out, err = ctx.run_cmd(["antigravity", "--update-extensions"])
        clean_err = "\n".join(l for l in err.splitlines() if "antigravityAnalytics" not in l).strip()
        if code != 0 and clean_err:
            return StepResult("error", "Antigravity update failed", error_output=clean_err)

        if "No extension to update" in out:
            return StepResult("unchanged")

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
            return StepResult("error", "uv tool upgrade failed", error_output=err or out)

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
            return StepResult("error", "pipx upgrade-all failed", error_output=err or out)

        if "versions are already at latest" in out.lower() or "no packages to upgrade" in out.lower():
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

        code, out, err = ctx.run_cmd(["conda", "update", "-n", "base", "--all", "-y"], timeout=300)
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
            return StepResult("error", "cargo install-update failed", error_output=err or out)

        if "No packages need updating" in out or "Everything is up to date" in out:
            return StepResult("unchanged")

        matches = re.findall(r"(?:Updating\s+)?([\w\.\-_]+)\s+(?:from\s+v?[\w\.\-_]+\s+to|->)\s+v?([\w\.\-_]+)", out)
        if matches:
            details = [f"{crate} -> {ver}" for crate, ver in matches]
            return StepResult("ok", f"{len(details)} crate{'s' if len(details) != 1 else ''} updated", details=details[:10])

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
            return StepResult("ok", "[DRY-RUN] Would update Composer and global packages")

        ctx.run_cmd(["composer", "self-update"], timeout=60)
        code, out, err = ctx.run_cmd(["composer", "global", "update"], timeout=180)
        if code != 0:
            return StepResult("error", "composer global update failed", error_output=err or out)

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

        code, out, err = ctx.run_cmd(["gem", "update", "--system"], timeout=180)
        if code != 0:
            return StepResult("error", "gem update failed", error_output=err or out)

        if "Latest version already installed" in out:
            return StepResult("unchanged")

        return StepResult("ok", "updated")


class MiseModule(BaseModule):
    name = "Mise Runtime Tools"
    key = "mise"
    category = "Development Environment"
    description = "Updates mise CLI and installed dev toolchains"

    def is_available(self, ctx: UpdateContext) -> bool:
        return ctx.which("mise") is not None

    def run(self, ctx: UpdateContext) -> StepResult:
        if ctx.dry_run:
            return StepResult("ok", "[DRY-RUN] Would run mise self-update and mise upgrade")

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
            return StepResult("error", "asdf plugin update failed", error_output=err or out)

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

        code, out, err = ctx.run_cmd(["nvim", "--headless", "+Lazy! sync", "+qa"], timeout=120)
        if code != 0:
            return StepResult("error", "Neovim Lazy sync failed", error_output=err or out)

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
