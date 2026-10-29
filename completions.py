"""
Shell completion generators for SystemUpdater.
Supports Bash, Zsh, and Fish with dynamic module and category resolution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.base import BaseModule

CATEGORIES = [
    "system",
    "protection",
    "apps",
    "gaming",
    "containers",
    "dev",
    "editors",
]

OPTIONS = [
    ("-h", "--help", "Show command help"),
    ("", "--version", "Show installed version and latest available version"),
    ("-f", "--force", "Force execution (bypass snapshot cooldown)"),
    (
        "-q",
        "--quiet",
        "Suppress live step progress, display only summary and errors",
    ),
    ("-v", "--verbose", "Stream update command output live"),
    ("", "--notify", "Send a desktop notification on completion"),
    (
        "",
        "--only",
        "Comma-separated list of module keys or aliases to run",
    ),
    ("", "--skip", "Comma-separated list of module keys to skip"),
    (
        "-c",
        "--category",
        "Comma-separated list of categories to run",
    ),
    (
        "",
        "--no-sudo",
        "Skip all modules requiring administrator (sudo) privileges",
    ),
    ("", "--no-snapshot", "Skip protective Btrfs snapshot"),
    ("", "--config", "Path to custom configuration TOML file"),
    ("", "--edit-config", "Open configuration file in $EDITOR"),
    (
        "-l",
        "--list",
        "List all registered modules and check their availability",
    ),
    (
        "-r",
        "--reboot",
        "Reboot the system after updates if required by any module",
    ),
    (
        "",
        "--history",
        "List the most recent update runs (default: 10, maximum: 30)",
    ),
    ("", "--show-log", "Show the saved command output for a run listed by --history"),
    ("", "--no-history", "Do not record this run or its command logs in history"),
    (
        "",
        "--generate-completion",
        "Generate shell completion script (bash, zsh, fish)",
    ),
    (
        "",
        "--generate-completions",
        "Alias for --generate-completion",
    ),
]


def _collect_module_identifiers(modules: list[BaseModule]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for m in modules:
        for ident in [m.key, *getattr(m, "aliases", [])]:
            ident_clean = ident.strip().lower()
            if ident_clean and ident_clean not in seen:
                seen.add(ident_clean)
                result.append(ident_clean)
    return sorted(result)


def generate_bash_completion(modules: list[BaseModule]) -> str:
    module_keys = " ".join(_collect_module_identifiers(modules))
    categories = " ".join(CATEGORIES)
    all_flags = " ".join(
        sorted(
            {
                flag
                for short, long, _ in OPTIONS
                for flag in (short, long)
                if flag.strip()
            }
        )
    )

    return f"""# bash completion for sysupdate
_sysupdate() {{
    local cur prev words cword
    _init_completion -n : || return

    local all_flags="{all_flags}"
    local module_keys="{module_keys}"
    local categories="{categories}"

    case "$prev" in
        --generate-completion|--generate-completions)
            COMPREPLY=($(compgen -W "bash zsh fish" -- "$cur"))
            return 0
            ;;
        --only|--skip)
            local prefix=""
            local query="$cur"
            if [[ "$cur" == *,* ]]; then
                prefix="${{cur%,*}},"
                query="${{cur##*,}}"
            fi
            local matches=($(compgen -W "$module_keys" -- "$query"))
            COMPREPLY=()
            for m in "${{matches[@]}}"; do
                COMPREPLY+=("${{prefix}}${{m}}")
            done
            return 0
            ;;
        -c|--category)
            local prefix=""
            local query="$cur"
            if [[ "$cur" == *,* ]]; then
                prefix="${{cur%,*}},"
                query="${{cur##*,}}"
            fi
            local matches=($(compgen -W "$categories" -- "$query"))
            COMPREPLY=()
            for c in "${{matches[@]}}"; do
                COMPREPLY+=("${{prefix}}${{c}}")
            done
            return 0
            ;;
        --config)
            _filedir toml
            return 0
            ;;
        --show-log)
            local hist_dir="${{XDG_STATE_HOME:-$HOME/.local/state}}/sysupdate/history"
            if [[ -d "$hist_dir" ]]; then
                local ids=$(find "$hist_dir" -maxdepth 1 -name "*.json" -printf "%f\\n" 2>/dev/null | sed -e 's/\\.json$//')
                COMPREPLY=($(compgen -W "$ids" -- "$cur"))
                return 0
            fi
            ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W "$all_flags" -- "$cur"))
        return 0
    fi
}}

complete -F _sysupdate sysupdate
"""


def generate_zsh_completion(modules: list[BaseModule]) -> str:
    module_keys = _collect_module_identifiers(modules)
    keys_formatted = " ".join(f"'{k}'" for k in module_keys)
    categories_formatted = " ".join(f"'{c}'" for c in CATEGORIES)

    return f"""#compdef sysupdate

_sysupdate() {{
    local -a options
    local -a module_keys
    local -a categories

    module_keys=({keys_formatted})
    categories=({categories_formatted})

    options=(
        '(-h --help)'{{-h,--help}}'[Show command help]'
        '--version[Show installed version and latest available version]'
        '(-f --force)'{{-f,--force}}'[Force execution (bypass snapshot cooldown)]'
        '(-q --quiet)'{{-q,--quiet}}'[Suppress live step progress, display only summary and errors]'
        '(-v --verbose)'{{-v,--verbose}}'[Stream update command output live]'
        '--notify[Send a desktop notification on completion]'
        '--only=[Comma-separated list of module keys or aliases to run]:module:_values -s , "module" $module_keys'
        '--skip=[Comma-separated list of module keys to skip]:module:_values -s , "module" $module_keys'
        '(-c --category)'{{-c,--category}}'=[Comma-separated list of categories to run]:category:_values -s , "category" $categories'
        '--no-sudo[Skip all modules requiring administrator (sudo) privileges]'
        '--no-snapshot[Skip protective Btrfs snapshot]'
        '--config=[Path to custom configuration TOML file]:file:_files -g "*.toml"'
        '--edit-config[Open configuration file in $EDITOR]'
        '(-l --list)'{{-l,--list}}'[List all registered modules and check their availability]'
        '(-r --reboot)'{{-r,--reboot}}'[Reboot the system after updates if required by any module]'
        '--history=[List the most recent update runs]:count:'
        '--show-log=[Show the saved command output for a run listed by --history]:run_id:'
        '--no-history[Do not record this run or its command logs in history]'
        '--generate-completion=[Generate shell completion script]:shell:(bash zsh fish)'
        '--generate-completions=[Generate shell completion script]:shell:(bash zsh fish)'
    )

    _arguments -s -S $options
}}

_sysupdate "$@"
"""


def generate_fish_completion(modules: list[BaseModule]) -> str:
    module_keys = " ".join(_collect_module_identifiers(modules))
    categories = " ".join(CATEGORIES)

    lines = [
        "# fish completion for sysupdate",
        "complete -c sysupdate -f",
        "complete -c sysupdate -s h -l help -d 'Show command help'",
        ("complete -c sysupdate -l version -d 'Show installed and latest version'"),
        ("complete -c sysupdate -s f -l force -d 'Bypass snapshot safeguards'"),
        (
            "complete -c sysupdate -s q -l quiet -d 'Hide live progress, show"
            " summary only'"
        ),
        (
            "complete -c sysupdate -s v -l verbose -d 'Stream update command"
            " output live'"
        ),
        (
            "complete -c sysupdate -l notify -d 'Send desktop notification on"
            " completion'"
        ),
        (
            f"complete -c sysupdate -l only -x -a '{module_keys}' -d 'Run only"
            " specified modules'"
        ),
        (
            f"complete -c sysupdate -l skip -x -a '{module_keys}' -d 'Skip"
            " specified modules'"
        ),
        (
            f"complete -c sysupdate -s c -l category -x -a '{categories}' -d"
            " 'Run specified categories'"
        ),
        (
            "complete -c sysupdate -l no-sudo -d 'Skip modules requiring root"
            " privileges'"
        ),
        ("complete -c sysupdate -l no-snapshot -d 'Skip protective Btrfs snapshot'"),
        ("complete -c sysupdate -l config -r -d 'Path to custom config file'"),
        ("complete -c sysupdate -l edit-config -d 'Open configuration in $EDITOR'"),
        (
            "complete -c sysupdate -s l -l list -d 'List registered modules"
            " and availability'"
        ),
        ("complete -c sysupdate -s r -l reboot -d 'Reboot after updates if required'"),
        (
            "complete -c sysupdate -l history -x -d 'List recent update runs"
            " (default: 10)'"
        ),
        ("complete -c sysupdate -l show-log -x -d 'Show saved details for a run ID'"),
        ("complete -c sysupdate -l no-history -d 'Do not save run record in history'"),
        (
            "complete -c sysupdate -l generate-completion -x -a 'bash zsh"
            " fish' -d 'Generate shell completion script'"
        ),
        (
            "complete -c sysupdate -l generate-completions -x -a 'bash zsh"
            " fish' -d 'Generate shell completion script'"
        ),
    ]

    return "\n".join(lines) + "\n"
