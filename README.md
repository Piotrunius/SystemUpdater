# SystemUpdater

SystemUpdater (`sysupdate`) runs updates for supported Linux package managers, desktop apps, containers, and development tools from one command. It detects installed tools, runs only applicable modules, and reports results in a consistent terminal summary.

Before system package updates, it can create a Btrfs snapshot through Snapper. It also supports selective runs, custom commands, run history, and optional reboot handling.

## Features

- Detects the distribution from `/etc/os-release` and selects its system package manager.
- Checks installed tools and update targets before running their modules.
- Supports module, category, quiet, and verbose selection.
- Creates cooldown-limited Snapper snapshots before updates when available.
- Detects reboot requirements from updated packages, firmware, and system reboot markers.
- Stores up to 30 private run records, with redacted and size-limited command output.
- Keeps a clean Git checkout updated automatically; Homebrew installations are updated by Homebrew.
- Uses the Python standard library; no Python packages need to be installed.

## Supported update sources

Availability depends on the operating system and tools installed on the machine. Run `sysupdate --list` to see which modules are available on your system.

| Area                         | Sources                                                                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| System                       | DNF/DNF5, APT, Pacman and AUR helpers (yay/paru), Zypper, APK, XBPS, Nobara repository sync                                    |
| Protection and firmware      | Snapper Btrfs snapshots, Firmware (fwupdmgr)                                                                                   |
| Apps and gaming              | Flatpak, Nuvio Desktop, Gear Lever AppImages, ProtonPlus, Distrobox                                                            |
| Containers and package tools | Homebrew, Docker images and Compose services, Podman auto-update, Vagrant boxes, Snap, Nix                                     |
| Development tools            | Shell plugins, Tealdeer, Rust, Python tools, Node.js package managers, Composer, Ruby gems, Mise, asdf, SDKMAN, GHCup, Flutter |
| Editors and extensions       | Neovim, Micro, Helix, VS Code, Cursor, VSCodium, Tmux plugins, GitHub CLI extensions, Agent Skills, Antigravity                |
| User configuration           | Chezmoi, Yadm, configured Git repositories, custom pre/update/post commands                                                    |

## Requirements

- Linux
- Python 3.11 or newer
- Git for a Git checkout installation
- The package managers and tools you want SystemUpdater to manage

SystemUpdater does not install the underlying package managers. Some modules need administrator privileges; use `--no-sudo` to skip modules that require them.

## Install

Choose one method. Installing both can make the command selected by your `PATH` ambiguous.

### Git checkout

```bash
git clone https://github.com/Piotrunius/SystemUpdater.git ~/.local/share/sysupdate
cd ~/.local/share/sysupdate
./install.sh
```

The installer links `~/.local/bin/sysupdate` to the checkout and creates `${XDG_CONFIG_HOME:-~/.config}/sysupdate/config.toml` from the example configuration if no config exists. Add `~/.local/bin` to your `PATH` if needed:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
```

On normal runs, a clean checkout can fast-forward from its configured upstream. Local changes are preserved; self-update is skipped when the working tree is dirty.

### Homebrew

```bash
brew tap piotrunius/systemupdater https://github.com/Piotrunius/SystemUpdater.git
brew trust --formula piotrunius/systemupdater/systemupdater
brew install systemupdater
```

Update the Homebrew-managed installation with:

```bash
brew update && brew upgrade systemupdater
```

Homebrew installations do not use the Git self-updater. The regular `sysupdate` command may also update SystemUpdater through the Homebrew module.

### Optional alias

Add an alias to `~/.bashrc` or `~/.zshrc` if you prefer a shorter command:

```bash
alias update="sysupdate"
```

## Usage

| Option                        | Description                                                                        |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| `-h`, `--help`                | Show command help                                                                  |
| `--version`                   | Show installed and latest available versions                                       |
| `-f`, `--force`               | Bypass safeguards such as the snapshot cooldown                                    |
| `-q`, `--quiet`               | Hide live progress; show the final summary and errors                              |
| `-v`, `--verbose`             | Stream update command output                                                       |
| `--only KEYS`                 | Run only comma-separated module keys or aliases                                    |
| `--skip KEYS`                 | Skip comma-separated module keys                                                   |
| `-c`, `--category CATEGORIES` | Run comma-separated categories, such as `system`, `containers`, `dev`, or `gaming` |
| `--no-sudo`                   | Skip modules requiring administrator privileges                                    |
| `--no-snapshot`               | Skip the protective Btrfs snapshot                                                 |
| `--config PATH`               | Use a configuration file at a custom path                                          |
| `--edit-config`               | Open the configuration file in `$EDITOR`                                           |
| `-l`, `--list`                | List registered modules and check availability                                     |
| `-r`, `--reboot`              | Reboot after the summary and history are saved if updates require it               |
| `--no-history`                | Do not record this run or its command logs in history                              |
| `--history [COUNT]`           | List recent runs (default 10, maximum 30)                                          |
| `--show-log RUN_ID`           | Show the saved details for a run                                                   |

Use `sysupdate --help` for the options supported by the installed version.

## Configuration

The default configuration file is `~/.config/sysupdate/config.toml`. `$XDG_CONFIG_HOME` is respected. The installer creates it from [`config.example.toml`](config.example.toml) only if it does not already exist.

```toml
[misc]
# Permanently disable selected module keys.
# Run `sysupdate --list` to inspect module keys.
# disable = ["snap", "docker", "antigravity"]

# Minimum hours between protective Btrfs snapshots.
cooldown_hours = 12

[git]
# Local repositories to pull during an update run.
# repos = ["~/dotfiles", "~/Projects/my-app"]

[pre_commands]
# Commands to run before update modules.
# "Clean build cache" = "my-cleanup-command"

[commands]
# Additional update commands.
# "Update custom tool" = "my-custom-cli update"

[post_commands]
# Commands to run after update modules.
# "Refresh desktop database" = "update-desktop-database ~/.local/share/applications"
```

The `[commands]`, `[pre_commands]`, and `[post_commands]` tables accept a display name mapped to a shell command. Review custom commands carefully: they run with the permissions available to the `sysupdate` process.

## Reboot handling

SystemUpdater looks for reboot requirements reported by updated core packages, firmware updates, and standard reboot marker files. `--reboot` requests a non-interactive `systemctl reboot` only when a reboot is required. The summary and run history are written before the reboot is requested. Without `--reboot`, the requirement is reported and the machine is left running.

## Run history

Run history is stored under `~/.local/state/sysupdate/history/`, or `$XDG_STATE_HOME/sysupdate/history/` when set. The last 30 runs are retained with private file permissions. Captured command output is redacted for common token and password patterns and size-limited; output from read-only commands is not saved because it may contain credentials.

`sysupdate --history` lists saved runs. Use a run ID with `sysupdate --show-log RUN_ID` to inspect module statuses, commands, exit codes, and captured output. Warning details are included in the relevant module output.

## Development

The project has no third-party Python runtime dependencies. Tests use pytest:

```bash
python3 -m pytest
```

The application entry point is `main.py`; update integrations live in `modules/`, and shared configuration, history, privilege, and terminal UI code live in the project root.

## License

SystemUpdater is released under the [MIT License](LICENSE).
