# SystemUpdater

SystemUpdater (`sysupdate`) runs updates for supported Linux and macOS package managers, desktop apps, containers, and development tools from one command. It detects installed tools, runs only applicable modules, and reports results in a consistent terminal summary.

Before system package updates, it can create a Btrfs snapshot through Snapper. It also supports selective runs, custom commands, run history, and optional reboot handling.

<p align="center">
  <img src="assets/gifs/demo_full_update.gif" alt="SystemUpdater execution demo" width="800" style="border-radius: 10px; border: 1px solid #30363d;" />
</p>

## Features

- Detects the distribution from `/etc/os-release` on Linux or system version on macOS and selects applicable package managers.
- Checks installed tools and update targets before running their modules.
- Supports module, category, quiet, and verbose selection.
- Generates native shell completions for Bash, Zsh, and Fish (`--generate-completion`).
- Sends native desktop notifications on Linux (`notify-send`) and macOS (`osascript`) upon completion (`--notify`).
- Creates cooldown-limited Snapper snapshots before updates when available.
- Detects reboot requirements from updated packages, firmware, macOS system updates, and system reboot markers.
- Stores up to 30 private run records, with redacted and size-limited command output.
- Keeps a clean Git checkout updated automatically; Homebrew installations are updated by Homebrew.
- Uses the Python standard library; no Python packages need to be installed.

## Supported update sources

Availability depends on the operating system and tools installed on the machine. Run `sysupdate --list` to see which modules are available on your system.

| Area                         | Sources                                                                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| System                       | DNF/DNF5, APT, Pacman and AUR helpers (yay/paru), Zypper, APK, XBPS, Nobara repository sync, macOS Software Update             |
| Protection and firmware      | Snapper Btrfs snapshots, Firmware (fwupdmgr)                                                                                   |
| Apps and gaming              | Flatpak, Nuvio Desktop, Gear Lever AppImages, ProtonPlus, Distrobox, Mac App Store (mas)                                       |
| Containers and package tools | Homebrew, Docker images and Compose services, Podman auto-update, Vagrant boxes, Snap, Nix                                     |
| Development tools            | Shell plugins, Tealdeer, Rust, Python tools, Node.js package managers, Composer, Ruby gems, Mise, asdf, SDKMAN, GHCup, Flutter |
| Editors and extensions       | Neovim, Micro, Helix, VS Code, Cursor, VSCodium, Tmux plugins, GitHub CLI extensions, Agent Skills, Antigravity                |
| User configuration           | Chezmoi, Yadm, configured Git repositories, custom pre/update/post commands                                                    |

## Requirements

- Linux or macOS
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

Install with one command via the official tap:

```bash
brew install Piotrunius/tap/systemupdater
```

Or add the tap first and then install:

```bash
brew tap Piotrunius/tap
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

| Option                                                    | Description                                                                        |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `-h`, `--help`                                            | Show command help                                                                  |
| `--version`                                               | Show installed and latest available versions                                       |
| `-f`, `--force`                                           | Bypass safeguards such as the snapshot cooldown                                    |
| `-q`, `--quiet`                                           | Hide live progress; show the final summary and errors                              |
| `-v`, `--verbose`                                         | Stream update command output                                                       |
| `--notify`                                                | Send desktop notification on completion (Linux `notify-send` / macOS `osascript`)  |
| `--generate-completion`, `--generate-completions` `SHELL` | Generate shell completions for `bash`, `zsh`, or `fish`                            |
| `--only KEYS`                                             | Run only comma-separated module keys or aliases                                    |
| `--skip KEYS`                                             | Skip comma-separated module keys                                                   |
| `-c`, `--category CATEGORIES`                             | Run comma-separated categories, such as `system`, `containers`, `dev`, or `gaming` |
| `--no-sudo`                                               | Skip modules requiring administrator privileges                                    |
| `--no-snapshot`                                           | Skip the protective Btrfs snapshot                                                 |
| `--config PATH`                                           | Use a configuration file at a custom path                                          |
| `--edit-config`                                           | Open the configuration file in `$EDITOR`                                           |
| `-l`, `--list`                                            | List registered modules and check availability                                     |
| `-r`, `--reboot`                                          | Reboot after the summary and history are saved if updates require it               |
| `--no-history`                                            | Do not record this run or its command logs in history                              |
| `--history [COUNT]`                                       | List recent runs (default 10, maximum 30)                                          |
| `--show-log RUN_ID`                                       | Show the saved details for a run                                                   |

Use `sysupdate --help` for the options supported by the installed version.

### Shell completion

SystemUpdater includes native autocompletions for Bash, Zsh, and Fish:

```bash
# Bash
mkdir -p ~/.local/share/bash-completion/completions
sysupdate --generate-completion bash > ~/.local/share/bash-completion/completions/sysupdate

# Zsh
mkdir -p ~/.zsh/completions
sysupdate --generate-completion zsh > ~/.zsh/completions/_sysupdate

# Fish
mkdir -p ~/.config/fish/completions
sysupdate --generate-completion fish > ~/.config/fish/completions/sysupdate.fish
```

### Desktop notifications

Send a notification upon completion with `--notify`:

```bash
sysupdate --notify
```

You can also enable notifications by default in `~/.config/sysupdate/config.toml`:

```toml
[notifications]
enabled = true
only_on_error_or_reboot = false
```

### Verbose streaming

Pass `-v` or `--verbose` to inspect real-time command output, repository syncs, and warnings across all modules:

<p align="center">
  <img src="assets/gifs/demo_verbose.gif" alt="SystemUpdater verbose mode demo" width="800" style="border-radius: 10px; border: 1px solid #30363d;" />
</p>

## Configuration

The default configuration file is `${XDG_CONFIG_HOME:-$HOME/.config}/sysupdate/config.toml`. If `XDG_CONFIG_HOME` is unset, empty, or relative, SystemUpdater uses `$HOME/.config`. The installer creates the file from [`config.example.toml`](config.example.toml) only if it does not already exist.

```toml
[misc]
# Minimum hours between protective Btrfs snapshots (default: 12)
cooldown_hours = 12

# Maximum seconds allowed per update command before timing out (default: 180)
# command_timeout = 300

[behavior]
# Automatically reboot after updates if required by kernel or firmware (default: false)
# reboot = false

# Hide live step progress and display only final summary and errors (default: false)
# quiet = false

# Stream update command output live (default: false)
# verbose = false

# Skip all modules requiring administrator (sudo) privileges (default: false)
# no_sudo = false

# Skip protective Btrfs snapshot creation (default: false)
# no_snapshot = false

# Do not record update runs in history (default: false)
# no_history = false

[notifications]
# Send desktop notifications on completion (Linux notify-send / macOS osascript)
# enabled = false
# only_on_error_or_reboot = false

[modules]
# Permanently disable selected module keys (run `sysupdate --list` to inspect keys)
# disable = ["snap", "docker", "antigravity"]

# Skip selected modules by default
# skip = ["brew"]

# Run only selected modules by default
# only = ["dnf", "flatpak"]

[categories]
# Run only selected categories by default (e.g. "system", "containers", "dev", "gaming")
# only = ["system", "dev"]

# Skip selected categories by default
# skip = ["gaming"]

[git]
# Local repositories to pull during an update run
# repos = ["~/dotfiles", "~/Projects/my-app"]

[pre_commands]
# Commands to run before update modules
# "Clean build cache" = "my-cleanup-command"

[commands]
# Additional update commands
# "Update custom tool" = "my-custom-cli update"

[post_commands]
# Commands to run after update modules
# "Refresh desktop database" = "update-desktop-database ~/.local/share/applications"
```

The `[commands]`, `[pre_commands]`, and `[post_commands]` tables accept a display name mapped to a shell command. Review custom commands carefully: they run with the permissions available to the `sysupdate` process.

## Reboot handling

SystemUpdater looks for reboot requirements reported by updated core packages (kernels, systemd, glibc, nvidia, microcode), firmware updates, and standard reboot marker files. When a component requires a reboot, it receives a distinct blue `[^]` marker in the live step output, run history, and `--show-log` views. A dedicated `── Reboot ──` section is displayed directly below the update summary detailing the exact components or packages that triggered the restart. `--reboot` requests a non-interactive `systemctl reboot` only when a reboot is required. The summary and run history are written before the reboot is requested. Without `--reboot`, the requirement is clearly reported and the machine is left running.

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
