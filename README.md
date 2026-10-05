# SystemUpdater (sysupdate)

SystemUpdater runs supported system package managers, application sources, containers, and developer tools from one command. It detects which tools are available, reports their results, and can create a Snapper snapshot before system updates.

---

## Key Features

- **Distribution Detection**: Reads `/etc/os-release` and selects the matching system package manager.
- **No Python Packages to Install**: The Git installation uses only the Python standard library. Homebrew supplies its own Python runtime.
- **Terminal Progress**: ANSI status lines and summaries show each module's result and duration.
- **Btrfs Snapshots**: Creates Snapper snapshots before system updates, with a configurable cooldown.
- **Package Change Details**: Reports upgraded package names and versions when the package manager provides them.
- **Target-Aware Modules**: Container updates run only when there are local Docker images, Distrobox containers, or a Vagrant project to update.
- **Sudo Keepalive**: Maintains the sudo timestamp during long update runs.
- **Dry Run and Verbose Modes**: Preview commands with `-n` or stream command output with `-v`.
- **Configuration**: Disable modules, set custom commands, and list Git repositories in `~/.config/sysupdate/config.toml`.
- **Managed Updates**: Git installs update clean checkouts; Homebrew installs are updated by Homebrew.

---

## Supported Ecosystems

| Category | Modules & Integrations |
| :--- | :--- |
| **System Core** |DNF / DNF5 (Fedora / Nobara / RHEL), APT (Debian / Ubuntu / Mint / Pop!_OS), Pacman & AUR (Arch / Manjaro / CachyOS via `yay` / `paru`), Zypper (openSUSE Tumbleweed & Leap), APK (Alpine), XBPS (Void), Device Firmware (`fwupdmgr`), Btrfs Snapper |
| **Applications & Gaming** | Flatpak (User & System), ProtonPlus Runners, Gear Lever AppImages, Nuvio Desktop |
| **Containers** | Distrobox (`upgrade --all`), Docker (`docker pull`), Podman (`auto-update`), Vagrant |
| **Package Managers** | Homebrew (Formulae & Casks), Snap, Nix |
| **Development Runtimes** | Rustup, Cargo, Python (`pip`, `pipx`, `pipenv`, `poetry`, `pyenv`, `uv`), Node (`npm`, `pnpm`, `bun`, `yarn`), PHP (`composer`), Ruby (`gem`), Mise, asdf, SDKMAN, GHCup, Flutter |
| **Editors & Shells** | Oh My Zsh, Zinit, Fisher (Fish), Micro Plugins, Neovim (Lazy.nvim), Helix Grammars, VS Code, Cursor, VSCodium, Tmux (TPM) |
| **Tools & CLI** | GitHub CLI Extensions, Agent Skills, Tealdeer (`tldr`), Antigravity Extensions, Custom Git Repositories |

---

## Installation

Choose one installation method. Both provide the `sysupdate` command and use the same configuration file.

### Git checkout

This method is suitable when you want the source checkout under your home directory. It requires Python 3.11 or newer and `git`.

```bash
git clone https://github.com/Piotrunius/SystemUpdater.git ~/.local/share/sysupdate
cd ~/.local/share/sysupdate
./install.sh
```

The installer links `~/.local/bin/sysupdate` to the checkout and creates the default configuration at `~/.config/sysupdate/config.toml`. Add `~/.local/bin` to your `PATH` if needed:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
```

On normal runs, this installation checks its Git remote and updates itself when the checkout is clean. Local edits are preserved; the updater reports why it skipped a self-update if it cannot safely fast-forward.

### Homebrew

Use Homebrew if you want it to manage the program version. The project repository is also the tap, so add it with its Git URL:

```bash
brew tap Piotrunius/SystemUpdater https://github.com/Piotrunius/SystemUpdater.git
brew install systemupdater
```

The formula update workflow refreshes its source URL, checksum, and version after changes reach `main`. To install those formula changes:

```bash
brew update && brew upgrade systemupdater
```

Homebrew-managed installations do not run the Git self-updater. A normal `sysupdate` run also runs the Homebrew module, which can upgrade SystemUpdater along with other formulae.

Avoid installing both methods at once unless you manage which `sysupdate` comes first in your `PATH`.

### Optional shell alias

To use `update` as a shorter command, add this to `~/.bashrc` or `~/.zshrc`:

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
  -V, --version         show installed version and latest available version
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

### Updates and Versioning

Git installs check their remote at startup and fast-forward only when the working tree is clean. Homebrew installs are updated through the Homebrew module or with `brew upgrade systemupdater`.

`sysupdate --version` reports the installed version and the latest available Git commit or Homebrew formula version.

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
├── .github/
│   └── workflows/
│       └── update-homebrew-formula.yml  # Refreshes the tap formula after changes to main
├── Formula/
│   └── systemupdater.rb                 # Homebrew package definition
├── main.py                              # CLI, module selection, and update lifecycle
├── config.py                            # Loads user settings from TOML
├── config.example.toml                  # Default configuration template
├── sudo.py                              # Sudo credentials and keepalive
├── ui.py                                # Terminal status, progress, and summaries
├── install.sh                           # Git-checkout installer
├── LICENSE                              # MIT license
├── README.md                            # Installation, usage, and configuration guide
├── modules/
│   ├── __init__.py       # Registers modules and assigns update categories
│   ├── base.py           # Shared module API, command runner, and warning detection
│   ├── nobara.py         # DNF repository sync and system package updates
│   ├── system_pm.py      # APT, Pacman/AUR, Zypper, APK, and XBPS
│   ├── firmware.py       # Device firmware updates through fwupd
│   ├── snapshot.py       # Btrfs snapshots through Snapper
│   ├── maintenance.py    # Manual-page index updates through mandb
│   ├── flatpak.py        # Flatpak applications
│   ├── nuvio.py          # Nuvio Desktop releases
│   ├── gearlever.py      # Gear Lever AppImages
│   ├── proton.py         # ProtonPlus compatibility tools
│   ├── distrobox.py      # Distrobox containers
│   ├── brew.py           # Homebrew formulae and casks
│   ├── docker.py         # Docker images
│   ├── containers_ext.py # Podman and Vagrant
│   ├── universal.py      # Snap and Nix
│   ├── devtools.py       # Language runtimes, package managers, and extensions
│   ├── languages_ext.py  # Additional language toolchains
│   ├── editors.py        # VS Code, Cursor, VSCodium, and Helix
│   ├── terminal_tools.py # Shell plugins and Tealdeer
│   ├── dotfiles.py       # Chezmoi and Yadm repositories
│   ├── git_repos.py      # User-configured Git repositories
│   └── custom.py         # User-configured pre-, update, and post-commands
└── tests/
    ├── test_config.py              # Configuration parsing and validation
    ├── test_flatpak.py             # Preserving and displaying advisory warnings
    ├── test_module_availability.py # Installed tools and update target detection
    ├── test_module_registry.py     # Custom configuration passed to modules
    └── test_snapshot.py            # Btrfs detection and snapshot cooldown
```

---

## License

This project is licensed under the [MIT License](LICENSE).
