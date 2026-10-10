# SystemUpdater (sysupdate)

SystemUpdater runs supported system package managers, application sources, containers, and developer tools from one command. It detects which tools are available, reports their results, and can create a Snapper snapshot before system updates.

---

## Key Features

- **Distribution Detection**: Reads `/etc/os-release` and selects the matching system package manager.
- **No Python Packages to Install**: The Git installation uses only the Python standard library. Homebrew supplies its own Python runtime.
- **Standardized Terminal Progress & Summaries**: Live ANSI status lines display exact package upgrade counts (e.g. `[✓] Homebrew: 3 packages upgraded`). The final summary formats single-purpose tools inline (`• Tool: old -> new`) and provides clean hierarchical lists for package managers.
- **Intelligent Package Prioritization**: Multi-package managers sort upgraded items by architectural importance (kernel and core system runtimes first, low-level libraries last) and cleanly cap lists at 10 items with a remainder count line.
- **Safe Device Firmware Updates**: Hardware and UEFI firmware upgrades through `fwupdmgr` stage non-blocking capsule updates without abruptly restarting the machine mid-run, with pending reboot requirements reported under verbose diagnostic warnings.
- **Btrfs Snapshots**: Creates Snapper snapshots before system updates, with a configurable cooldown.
- **Target-Aware Modules**: Container and service updates run only when there are local Docker images, Distrobox containers, or a Vagrant project to update.
- **Run History & Inspection**: Securely stores the last 30 update runs with redacted logs, queryable via `--history` and `--show-log`.
- **Sudo Keepalive**: Maintains the sudo timestamp during long update runs.
- **Dry Run and Verbose Modes**: Preview commands with `-n` or stream command output with `-v`.
- **Configuration**: Disable modules, set custom commands, and list Git repositories in `~/.config/sysupdate/config.toml`.
- **Managed Updates**: Git installs update clean checkouts; Homebrew installs are updated by Homebrew.

---

## Supported Ecosystems

| Category                  | Modules & Integrations                                                                                                                                                                                                                                                                    |
| :------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **System Core**           | DNF / DNF5 (Fedora / Nobara / RHEL), APT (Debian / Ubuntu / Mint / Pop!_OS), Pacman & AUR (Arch / Manjaro / CachyOS via `yay` / `paru`), Zypper (openSUSE Tumbleweed & Leap), APK (Alpine), XBPS (Void), Device Firmware (`fwupdmgr` with safe staging & reboot detection), Btrfs Snapper |
| **Applications & Gaming** | Flatpak (User & System), ProtonPlus Runners, Gear Lever AppImages, Nuvio Desktop                                                                                                                                                                                                          |
| **Containers**            | Distrobox (`upgrade --all`), Docker (`docker pull`), Podman (`auto-update`), Vagrant                                                                                                                                                                                                      |
| **Package Managers**      | Homebrew (Formulae & Casks), Snap, Nix                                                                                                                                                                                                                                                    |
| **Development Runtimes**  | Rustup, Cargo, Python (`pip`, `pipx`, `pipenv`, `poetry`, `pyenv`, `uv`), Node (`npm`, `pnpm`, `bun`, `yarn`), PHP (`composer`), Ruby (`gem`), Mise, asdf, SDKMAN, GHCup, Flutter                                                                                                         |
| **Editors & Shells**      | Oh My Zsh, Zinit, Fisher (Fish), Micro Plugins, Neovim (Lazy.nvim), Helix Grammars, VS Code, Cursor, VSCodium, Tmux (TPM), Chezmoi, Yadm                                                                                                                                                  |
| **Tools & CLI**           | GitHub CLI Extensions, Agent Skills, Tealdeer (`tldr`), Antigravity Extensions, Manual Pages Database (`mandb`), Custom Git Repositories                                                                                                                                                  |

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
usage: sysupdate [-h] [--version] [-n] [-f] [-q] [-v] [--only ONLY] [--skip SKIP]
                 [-c CATEGORY] [--no-sudo] [--no-snapshot] [--config PATH]
                 [--edit-config] [-l] [-r] [--history [COUNT] | --show-log RUN_ID]

options:
  -h, --help            show this help message and exit
  --version             Show installed version and latest available version
  -n, --dry-run         Simulate update process without downloading or installing changes
  -f, --force           Force execution (e.g. bypass Btrfs snapshot cooldown)
  -q, --quiet           Suppress live step progress, display only the final summary and errors
  -v, --verbose         Stream update output live while keeping internal probes quiet
  --only ONLY           Comma-separated list of module keys or aliases to run (e.g. 'dnf,flatpak,brew')
  --skip SKIP           Comma-separated list of module keys to skip
  -c, --category CATEGORY
                        Comma-separated list of categories to run (e.g. 'system', 'containers', 'dev', 'gaming')
  --no-sudo             Skip all modules requiring administrator (sudo) privileges
  --no-snapshot         Skip protective Btrfs snapshot
  --config PATH         Path to custom configuration TOML file
  --edit-config         Open configuration file in $EDITOR
  -l, --list            List all registered modules and check their availability
  -r, --reboot          Reboot the system after updates if required by any module (e.g. kernel, systemd, firmware)
  --history [COUNT]     List recent update runs (default: 10, maximum: 30)
  --show-log RUN_ID     Show saved command output for a selected run
```

### Examples

```bash
# Run complete system update
sysupdate

# Preview updates without modifying the system
sysupdate --dry-run

# Run updates and reboot automatically if required by kernel, systemd, or firmware
sysupdate --reboot

# Run only DNF system packages and Homebrew
sysupdate --only dnf,brew

# Run only development tools without sudo
sysupdate --category dev --no-sudo

# Run in quiet mode (suitable for cron or systemd timers)
sysupdate -q

# Show command activity and warnings in the final summary
sysupdate -v

# List the latest update runs
sysupdate --history

# Show the full log for one selected run
sysupdate --show-log 20261008T052420Z-a1b2c3d4

# Open configuration file in default editor ($EDITOR)
sysupdate --edit-config

# Use a configuration file at a custom path
sysupdate --config /path/to/config.toml

# Inspect status of all supported modules on the current system
sysupdate --list

# Show installed version and the latest upstream commit
sysupdate --version
```

### Updates and Versioning

Git installs check their remote at startup and fast-forward only when the working tree is clean. Homebrew installs are updated through the Homebrew module or with `brew upgrade systemupdater`.

`sysupdate --version` reports the installed version and the latest available Git commit or Homebrew formula version.

### Run History

Completed runs are stored in `~/.local/state/sysupdate/history/` (or `$XDG_STATE_HOME/sysupdate/history/`) with private file permissions. The last 30 runs are retained. Command output is redacted for common token and password patterns, capped at 100 KB per command and 2 MB per run, and omitted for read-only commands because it can contain credentials.

Use `sysupdate --history [COUNT]` to list saved runs, then pass the chosen run ID to `sysupdate --show-log RUN_ID` to inspect its module statuses, commands, exit codes, and captured output. Warning details are shown in the relevant module output.

The history status is `warning` only when a module reports warning text not present in that module's latest previous run. Repeated warnings remain available in the saved log but do not keep changing every run's status to `warning`.

### Universal Reboot Detection and Automation

SystemUpdater continuously inspects all update steps for components requiring a machine restart:

- **Core system packages:** Kernel (`kernel`, `linux`, `vmlinuz`), core runtimes (`systemd`, `glibc`, `libc6`, `musl`), bootloaders (`grub`, `shim`).
- **Device & UEFI firmware:** Hardware capsules staged via `fwupdmgr` that require a reboot cycle to flash to the EFI system partition.
- **System markers:** Standard trigger files such as `/run/reboot-required` created by package managers like APT or DNF.

In standard mode, live progress and summary output remain 1:1 identical in structure to all other package modules (`• Device Firmware: 1 package updated`). When any module updates a package requiring a restart:

1. The update is flagged with `reboot_required=True`.
2. In verbose mode (`-v`), diagnostic warnings report `System reboot required to complete pending updates` alongside other warnings.
3. If executed with `-r` or `--reboot`, SystemUpdater invokes non-interactive `systemctl reboot` immediately following summary printing and history logging. If no reboot is needed, the flag has no effect and the process exits normally.

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
├── .gitignore                           # Excludes history, logs, and temporary files
├── main.py                              # CLI, module selection, and update lifecycle
├── config.py                            # Loads user settings from TOML
├── config.example.toml                  # Default configuration template
├── history_store.py                     # Private, redacted run-history storage and viewer
├── sudo.py                              # Sudo credentials and keepalive
├── ui.py                                # Terminal status, progress, and summaries
├── install.sh                           # Git-checkout installer
├── pytest.ini                           # Pytest configuration and Python path resolution
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
    ├── test_command_logging.py      # Capturing commands and withholding read-only output
    ├── test_config.py              # Configuration parsing and validation
    ├── test_distrobox.py           # Distrobox update detection and results
    ├── test_firmware.py            # Firmware update states and metadata warnings
    ├── test_flatpak.py             # Preserving and displaying advisory warnings
    ├── test_history_store.py       # Private run history, selection, and redaction
    ├── test_module_availability.py # Installed tools and update target detection
    ├── test_module_registry.py     # Custom configuration passed to modules
    ├── test_npm_module.py          # Reporting npm registry check failures
    ├── test_nuvio.py               # Architecture-aware RPM selection
    ├── test_package_signature_checks.py # Keeping package signature checks enabled
    ├── test_partial_failures.py    # Reporting failures after partial updates
    ├── test_snapshot.py            # Btrfs detection and snapshot cooldown
    ├── test_ui_summary.py          # Consistent warning and error summaries
    ├── test_universal.py           # Stopping Nix updates when channel refresh fails
    └── test_version.py             # Version output and source metadata
```

---

## License

This project is licensed under the [MIT License](LICENSE).
