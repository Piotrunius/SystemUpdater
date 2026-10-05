# SystemUpdater (sysupdate)

A modern, fast, modular system updater for Linux.

Built as a lightweight, zero-dependency Python 3 replacement for monolithic updaters. Features automatic distribution detection, a flicker-free ANSI terminal interface, automated pre-update Btrfs root snapshots, unified version diffing, and fine-grained module control.

---

## Key Features

- **Automatic Distribution Detection**: Dynamically inspects `/etc/os-release` and activates the native package manager (DNF, APT, Pacman, Zypper, APK, XBPS).
- **Zero External Dependencies**: Pure Python 3 standard library implementation.
- **Flicker-Free Terminal UI**: Minimalist ANSI rendering without screen clearing or rotating spinner artifacts.
- **Pre-Update Safety**: Automated Btrfs root snapshotting via Snapper with configurable cooldown tracking.
- **Unified Version Reporting**: Standardized `package -> new_version` reporting across all package managers without duplicate entries.
- **Sudo Session Preservation**: Non-blocking background credentials keepalive prevents mid-run authentication prompts.
- **Deep Modular Ecosystem**: Over 55 built-in modules spanning system packages, containers, desktop apps, editors, and language runtimes.
- **Dry-Run & Verbose Execution**: Full simulation mode (`-n`) and detailed live shell streaming (`-v`).
- **Flexible Configuration**: Declarative configuration via `~/.config/sysupdate/config.toml`.
- **Self-Updates**: Checks the configured Git upstream at startup and applies clean, fast-forward updates automatically.

---

## Supported Ecosystems

| Category | Modules & Integrations |
| :--- | :--- |
| **System Core** | Automatic Distro Detection, DNF / DNF5 (Fedora / Nobara / RHEL), APT (Debian / Ubuntu / Mint / Pop!_OS), Pacman & AUR (Arch / Manjaro / CachyOS via `yay` / `paru`), Zypper (openSUSE Tumbleweed & Leap), APK (Alpine), XBPS (Void), Device Firmware (`fwupdmgr`), Btrfs Snapper |
| **Applications & Gaming** | Flatpak (User & System), ProtonPlus Runners, Gear Lever AppImages, Nuvio Desktop |
| **Containers** | Distrobox (`upgrade --all`), Docker (`docker pull`), Podman (`auto-update`), Vagrant |
| **Package Managers** | Homebrew (Formulae & Casks), Snap, Nix |
| **Development Runtimes** | Rustup, Cargo, Python (`pip`, `pipx`, `pipenv`, `poetry`, `pyenv`, `uv`), Node (`npm`, `pnpm`, `bun`, `yarn`), PHP (`composer`), Ruby (`gem`), Mise, asdf, SDKMAN, GHCup, Flutter |
| **Editors & Shells** | Oh My Zsh, Zinit, Fisher (Fish), Micro Plugins, Neovim (Lazy.nvim), Helix Grammars, VS Code, Cursor, VSCodium, Tmux (TPM) |
| **Tools & CLI** | GitHub CLI Extensions, Agent Skills, Tealdeer (`tldr`), Antigravity Extensions, Custom Git Repositories |

---

## Installation

### Quick Install

Clone the repository and run the automated installer:

```bash
git clone https://github.com/piotrunius/SystemUpdater.git ~/.local/share/sysupdate
cd ~/.local/share/sysupdate
./install.sh
```

### Homebrew

Install from the project tap:

```bash
brew install Piotrunius/SystemUpdater/systemupdater
```

Homebrew manages this installation, so the built-in Git self-updater is disabled. The tap formula is refreshed automatically after changes reach `main`. Update the installed command with:

```bash
brew update && brew upgrade systemupdater
```

Ensure `~/.local/bin` is in your `PATH`:

```bash
# Add to ~/.bashrc or ~/.zshrc if not already present
export PATH="${HOME}/.local/bin:${PATH}"
```

Optional shell alias (in `~/.bashrc` or `~/.zshrc`):

```bash
alias update="sysupdate"
```

---

## Usage

```text
usage: sysupdate [-h] [-V] [-n] [-f] [-q] [-v] [--only ONLY] [--skip SKIP]
                 [-C CATEGORY] [--no-sudo] [--no-snapshot] [-c CONFIG]
                 [--edit-config] [-l]

Unified System Updater for Nobara Linux, Flatpaks, Homebrew, Containers, and Runtimes.

options:
  -h, --help            show this help message and exit
  -V, --version         show installed version and latest upstream commit
  -n, --dry-run         Simulate update process without downloading or installing changes
  -f, --force           Force execution (e.g. bypass Btrfs snapshot cooldown)
  -q, --quiet           Suppress live step progress, display only the final summary and errors
  -v, --verbose         Enable detailed logging output with live command streaming
  --only ONLY           Comma-separated list of module keys or aliases to run (e.g. 'dnf,flatpak,brew')
  --skip SKIP           Comma-separated list of module keys to skip
  -C, --category CAT    Comma-separated list of categories to run (e.g. 'system', 'containers', 'dev', 'gaming')
  --no-sudo             Skip all modules requiring administrator (sudo) privileges
  --no-snapshot         Skip protective Btrfs snapshot
  -c, --config CONFIG   Path to custom configuration TOML file
  --edit-config         Open configuration file in $EDITOR
  -l, --list            List all registered modules and check their availability
```

### Examples

```bash
# Run complete system update
sysupdate

# Preview updates without modifying the system
sysupdate --dry-run

# Run only DNF system packages and Homebrew
sysupdate --only dnf,brew

# Run only development tools without sudo
sysupdate --category dev --no-sudo

# Run in quiet mode (suitable for cron or systemd timers)
sysupdate -q

# Run update with live shell command streaming
sysupdate -v

# Open configuration file in default editor ($EDITOR)
sysupdate --edit-config

# Inspect status of all supported modules on the current system
sysupdate --list

# Show installed version and the latest upstream commit
sysupdate --version
```

### Self-Updates and Versioning

On normal runs, `sysupdate` detects the current Git upstream or the project's default repository and fast-forwards when updates are available. It does this only for a clean checkout; local changes are preserved and reported, and divergent branches are left untouched. If the network is unavailable, the regular system update continues with the installed version. Homebrew installations are updated by Homebrew and skip this check.

`sysupdate --version` reports the installed source version and the latest available upstream or Homebrew formula version.

---

## Configuration

Settings are managed in `~/.config/sysupdate/config.toml`:

```toml
[misc]
# Modules to permanently ignore
# disable = ["snap", "docker", "antigravity"]

# Minimum hours between Btrfs root snapshots (default: 12)
cooldown_hours = 12

[git]
# Local Git repositories to pull during update
repos = [
    "~/dotfiles",
    "~/Projects/my-app"
]

[pre_commands]
# Commands executed before updates begin
# "Clear Cache" = "rm -rf /tmp/build-cache-*"

[commands]
# Custom update commands
# "Custom Tool" = "my-custom-updater"

[post_commands]
# Commands executed after all updates finish
# "Refresh Icons" = "gtk-update-icon-cache ~/.local/share/icons/*"
```

---

## Architecture

```text
SystemUpdater/
├── main.py              # CLI entry point, argument parsing, execution pipeline
├── config.py            # TOML configuration loader (standard library tomllib)
├── sudo.py              # Non-blocking sudo session management and keepalive thread
├── ui.py                # Flicker-free ANSI terminal UI, timing, and report formatting
├── install.sh           # Automated installer and PATH checker
└── modules/
    ├── base.py          # BaseModule, UpdateContext, process execution and warning detection
    ├── nobara.py        # Nobara / Fedora DNF repositories and system package upgrades
    ├── flatpak.py       # Flatpak user and system application updates
    ├── brew.py          # Homebrew formulae and cask upgrades with version mapping
    ├── snapshot.py      # Snapper Btrfs root snapshotting with cooldown management
    ├── proton.py        # ProtonPlus compatibility runners
    ├── nuvio.py         # Nuvio Desktop GitHub release management
    ├── docker.py        # Docker image pulls
    ├── devtools.py      # Node, Python, Rust, shell, and editor runtime modules
    └── ...
```

---

## License

This project is licensed under the [MIT License](LICENSE).
