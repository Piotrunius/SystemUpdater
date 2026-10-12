"""Terminal ANSI escape codes for SystemUpdater."""


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"

    BOLD_GREEN = "\033[1;32m"
    BOLD_RED = "\033[1;31m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_MAGENTA = "\033[1;35m"
    BOLD_CYAN = "\033[1;36m"


# Standard status markers: exactly 6 symbols with unique, consistent styling
# Allowed symbols: "!", "✗", "✓", "—", ":", "~"
STATUS_MARKERS: dict[str, str] = {
    "✓": f"{Colors.DIM}[{Colors.RESET}{Colors.BOLD_GREEN}✓{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
    "!": f"{Colors.DIM}[{Colors.RESET}{Colors.BOLD_YELLOW}!{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
    "✗": f"{Colors.DIM}[{Colors.RESET}{Colors.BOLD_RED}✗{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
    "—": f"{Colors.DIM}[—]{Colors.RESET}",
    ":": f"{Colors.DIM}[{Colors.RESET}{Colors.BOLD_CYAN}:{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
    "~": f"{Colors.DIM}[{Colors.RESET}{Colors.BOLD_MAGENTA}~{Colors.RESET}{Colors.DIM}]{Colors.RESET}",
}

STATUS_SYMBOL_MAP: dict[str, str] = {
    "ok": "✓",
    "updated": "✓",
    "warning": "!",
    "error": "✗",
    "failed": "✗",
    "interrupted": "~",
    "cancelled": "~",
    "running": ":",
    "unchanged": "—",
    "up-to-date": "—",
    "skipped": "—",
}


def get_status_marker(status_or_symbol: str, plain: bool = False) -> str:
    """Return the styled status marker for any status or symbol."""
    sym = STATUS_SYMBOL_MAP.get(status_or_symbol, status_or_symbol)
    if plain:
        return f"[{sym}]"
    return STATUS_MARKERS.get(sym, f"{Colors.DIM}[{sym}]{Colors.RESET}")
