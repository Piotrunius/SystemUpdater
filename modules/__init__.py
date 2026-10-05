"""
Registry of all update modules for SystemUpdater grouped cleanly by category.
Modules automatically detect whether their underlying tools are installed on the system.
Also loads user custom commands and git repositories from ~/.config/sysupdate/config.toml.
"""

from typing import List
from modules.base import BaseModule
from config import get_config

# System Protection
from modules.snapshot import SnapshotModule

# System Core
from modules.nobara import RepoSyncModule, SystemPackagesModule
from modules.system_pm import AptModule, PacmanModule, ZypperModule, ApkModule, XbpsModule
from modules.firmware import FirmwareModule

# Applications & Gaming
from modules.flatpak import FlatpakModule
from modules.nuvio import NuvioModule
from modules.gearlever import GearLeverModule
from modules.proton import ProtonPlusModule
from modules.distrobox import DistroboxModule

# Containers & Packages
from modules.brew import BrewModule
from modules.docker import DockerModule
from modules.containers_ext import PodmanModule, VagrantModule
from modules.universal import SnapModule, NixModule

# Development Environment - Languages & Toolchains
from modules.devtools import (
    OhMyZshModule,
    RustupModule,
    PipModule,
    UvModule,
    PipxModule,
    PoetryModule,
    CondaModule,
    CargoUpdateModule,
    NpmModule,
    PnpmModule,
    BunModule,
    YarnModule,
    ComposerModule,
    GemModule,
    MiseModule,
    AsdfModule,
    NeovimModule,
    MicroModule,
    TmuxPluginsModule,
    GhExtensionsModule,
    SkillsModule,
    AntigravityModule,
)
from modules.languages_ext import (
    PipenvModule,
    PyenvModule,
    SdkmanModule,
    GhcupModule,
    FlutterModule,
)
from modules.dotfiles import ChezmoiModule, YadmModule
from modules.editors import (
    VsCodeModule,
    CursorModule,
    VscodiumModule,
    HelixModule,
)
from modules.terminal_tools import TealdeerModule, FisherModule, ZinitModule
from modules.git_repos import GitReposModule
from modules.custom import CustomCommandModule


def get_all_modules() -> List[BaseModule]:
    cfg = get_config()
    modules: List[BaseModule] = []

    # 1. Custom Pre-Commands (if defined in config.toml)
    for name, cmd in cfg.pre_commands.items():
        modules.append(CustomCommandModule(name, cmd, category="Custom Pre-Commands", key=f"pre_{name.lower().replace(' ', '_')}"))

    # 2. System Protection
    modules.append(SnapshotModule())

    # 3. System Core (Distro-specific repository sync and package manager)
    modules.append(RepoSyncModule())      # Active exclusively on Nobara Linux
    modules.extend([
        SystemPackagesModule(),           # DNF / RPM (Fedora, Nobara, RHEL, CentOS, Rocky)
        AptModule(),                      # APT (Debian, Ubuntu, Linux Mint, Pop!_OS)
        PacmanModule(),                   # Pacman / AUR / Yay / Paru (Arch, Manjaro, CachyOS)
        ZypperModule(),                   # Zypper (openSUSE Tumbleweed / Leap)
        ApkModule(),                      # APK (Alpine Linux)
        XbpsModule(),                     # XBPS (Void Linux)
        FirmwareModule(),
    ])

    # 4. Applications & Gaming
    modules.extend([
        FlatpakModule(),
        NuvioModule(),
        GearLeverModule(),
        ProtonPlusModule(),
        DistroboxModule(),
    ])

    # 5. Containers & Virtualization
    modules.extend([
        BrewModule(),
        DockerModule(),
        PodmanModule(),
        VagrantModule(),
        SnapModule(),
        NixModule(),
    ])

    # 6. Development Environment - Dotfiles & Shells
    modules.extend([
        ChezmoiModule(),
        YadmModule(),
        OhMyZshModule(),
        ZinitModule(),
        FisherModule(),
        TealdeerModule(),
    ])

    # 7. Development Environment - Languages, Toolchains & Package Managers
    modules.extend([
        RustupModule(),
        CargoUpdateModule(),
        PipModule(),
        UvModule(),
        PipxModule(),
        PipenvModule(),
        PoetryModule(),
        CondaModule(),
        PyenvModule(),
        NpmModule(),
        PnpmModule(),
        BunModule(),
        YarnModule(),
        ComposerModule(),
        GemModule(),
        MiseModule(),
        AsdfModule(),
        SdkmanModule(),
        GhcupModule(),
        FlutterModule(),
    ])

    # 8. Development Environment - Editors & Extensions
    modules.extend([
        NeovimModule(),
        MicroModule(),
        HelixModule(),
        VsCodeModule(),
        CursorModule(),
        VscodiumModule(),
        TmuxPluginsModule(),
        GhExtensionsModule(),
        SkillsModule(),
        AntigravityModule(),
    ])

    # 9. Development Environment - Local Git Repositories
    modules.append(GitReposModule())

    # 10. Custom Commands (if defined in config.toml)
    for name, cmd in cfg.commands.items():
        modules.append(CustomCommandModule(name, cmd, category="Custom Commands", key=f"cmd_{name.lower().replace(' ', '_')}"))

    # 11. Custom Post-Commands (if defined in config.toml)
    for name, cmd in cfg.post_commands.items():
        modules.append(CustomCommandModule(name, cmd, category="Custom Post-Commands", key=f"post_{name.lower().replace(' ', '_')}"))

    return modules
