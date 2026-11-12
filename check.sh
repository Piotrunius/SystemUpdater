#!/usr/bin/env bash
#
# Unified quality, formatting, linting, and test runner for SystemUpdater.
#
set -euo pipefail

# ANSI color definitions
C_RESET="\033[0m"
C_DIM="\033[2m"
C_CYAN="\033[36m"
C_BOLD_CYAN="\033[1;36m"
C_BOLD_GREEN="\033[1;32m"
C_BOLD_RED="\033[1;31m"

FIX_MODE=0

show_help() {
	cat <<'EOF'
Usage: ./check.sh [OPTIONS]

Runs code style checks, linters, formatters, type checkers, and test suites
for both the core CLI tool and the web documentation portal.

Options:
  -f, --fix    Automatically apply formatters (shfmt, ruff, prettier, eslint)
  -h, --help   Display this help message and exit
EOF
	exit 0
}

# Parse command line options
while [[ $# -gt 0 ]]; do
	case "$1" in
	-f | --fix)
		FIX_MODE=1
		shift
		;;
	-h | --help)
		show_help
		;;
	*)
		echo -e "${C_BOLD_RED}Unknown option:${C_RESET} $1" >&2
		echo "Use -h or --help for usage information." >&2
		exit 1
		;;
	esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Ensure user binaries (~/.bun/bin, ~/.local/bin) are in PATH
if [[ -d "${HOME}/.bun/bin" && ":${PATH}:" != *":${HOME}/.bun/bin:"* ]]; then
	export PATH="${HOME}/.bun/bin:${PATH}"
fi
if [[ -d "${HOME}/.local/bin" && ":${PATH}:" != *":${HOME}/.local/bin:"* ]]; then
	export PATH="${HOME}/.local/bin:${PATH}"
fi

# Determine width matching SystemUpdater standard
TERM_WIDTH=$(tput cols 2>/dev/null || echo 80)
WIDTH=$((TERM_WIDTH < 80 ? TERM_WIDTH : 80))

print_divider() {
	local title="${1:-}"
	local line=""
	if [[ -z "${title}" ]]; then
		line=$(printf '─%.0s' $(seq 1 "${WIDTH}"))
		echo -e "${C_CYAN}${line}${C_RESET}"
	else
		local prefix="── ${title} "
		local prefix_len=${#prefix}
		local rem=$((WIDTH - prefix_len))
		if [[ ${rem} -lt 2 ]]; then
			rem=2
		fi
		local fill
		fill=$(printf '─%.0s' $(seq 1 "${rem}"))
		echo -e "${C_BOLD_CYAN}${prefix}${C_CYAN}${fill}${C_RESET}"
	fi
}

START_TIME=$(python3 -c 'import time; print(time.monotonic_ns())')

print_divider "Quality & Lint Checks"

FAILED_CHECKS=()

run_step() {
	local label="$1"
	shift
	local cmd=("$@")

	local step_start
	step_start=$(python3 -c 'import time; print(time.monotonic_ns())')

	local output
	local exit_code=0
	if output=$("${cmd[@]}" 2>&1); then
		exit_code=0
	else
		exit_code=$?
	fi

	local step_end
	step_end=$(python3 -c 'import time; print(time.monotonic_ns())')
	local duration_ms=$(((step_end - step_start) / 1000000))
	local duration_sec
	duration_sec=$(awk "BEGIN {printf \"%.1fs\", ${duration_ms}/1000}")

	if [[ ${exit_code} -eq 0 ]]; then
		echo -e "  ${C_DIM}[${C_RESET}${C_BOLD_GREEN}✓${C_RESET}${C_DIM}]${C_RESET} ${label} ${C_DIM}(${duration_sec})${C_RESET}"
	else
		echo -e "  ${C_DIM}[${C_RESET}${C_BOLD_RED}✗${C_RESET}${C_DIM}]${C_RESET} ${label} ${C_DIM}(${duration_sec})${C_RESET}"
		FAILED_CHECKS+=("${label}")
		if [[ -n "${output}" ]]; then
			# shellcheck disable=SC2001
			echo "${output}" | sed 's/^/      /'
		fi
	fi
}

# 1. Shell formatting check (shfmt)
SH_FILES=()
while IFS= read -r f; do
	[[ -n "${f}" ]] && SH_FILES+=("${f}")
done < <(find . -maxdepth 2 -name "*.sh" -not -path "*/.*")

if [[ ${#SH_FILES[@]} -gt 0 ]]; then
	if command -v shfmt >/dev/null 2>&1; then
		if [[ ${FIX_MODE} -eq 1 ]]; then
			run_step "Shell formatting (shfmt -w)" shfmt -w "${SH_FILES[@]}"
		else
			run_step "Shell formatting (shfmt -d)" shfmt -d "${SH_FILES[@]}"
		fi
	fi
	if command -v shellcheck >/dev/null 2>&1; then
		run_step "Shell linting (shellcheck)" shellcheck "${SH_FILES[@]}"
	fi
fi

# 2. Python linting (ruff check)
if command -v ruff >/dev/null 2>&1; then
	if [[ ${FIX_MODE} -eq 1 ]]; then
		run_step "Python linting (ruff check --fix)" ruff check --fix .
	else
		run_step "Python linting (ruff check)" ruff check .
	fi

	# 3. Python formatting (ruff format)
	if [[ ${FIX_MODE} -eq 1 ]]; then
		run_step "Python formatting (ruff format)" ruff format .
	else
		run_step "Python formatting (ruff format --check)" ruff format --check .
	fi
fi

# 4. Python type checking (basedpyright/pyright)
TYPE_CHECKER=""
if command -v basedpyright >/dev/null 2>&1; then
	TYPE_CHECKER="basedpyright"
elif [[ -x "${HOME}/.local/share/zed/languages/basedpyright/node_modules/.bin/basedpyright" ]]; then
	TYPE_CHECKER="${HOME}/.local/share/zed/languages/basedpyright/node_modules/.bin/basedpyright"
elif command -v pyright >/dev/null 2>&1; then
	TYPE_CHECKER="pyright"
fi

if [[ -n "${TYPE_CHECKER}" ]]; then
	run_step "Python type checking ($(basename "${TYPE_CHECKER}"))" "${TYPE_CHECKER}" .
fi

# 5. Full codebase formatting (prettier)
PRETTIER_CMD=()
if command -v prettier >/dev/null 2>&1; then
	PRETTIER_CMD=(prettier)
elif command -v bunx >/dev/null 2>&1; then
	PRETTIER_CMD=(bunx prettier)
elif command -v npx >/dev/null 2>&1; then
	PRETTIER_CMD=(npx prettier)
fi

if [[ ${#PRETTIER_CMD[@]} -gt 0 ]]; then
	if [[ ${FIX_MODE} -eq 1 ]]; then
		run_step "Codebase formatting (prettier --write)" "${PRETTIER_CMD[@]}" --write --log-level warn .
	else
		run_step "Codebase formatting (prettier --check)" "${PRETTIER_CMD[@]}" --check .
	fi
fi

# 6. Web portal checks (eslint, typescript, next build)
BUN_BIN=""
if command -v bun >/dev/null 2>&1; then
	BUN_BIN="bun"
elif [[ -x "${HOME}/.bun/bin/bun" ]]; then
	BUN_BIN="${HOME}/.bun/bin/bun"
fi

if [[ -d "web" && -f "web/package.json" && -n "${BUN_BIN}" ]]; then
	if [[ ${FIX_MODE} -eq 1 ]]; then
		run_step "Web portal linting (eslint --fix)" "${BUN_BIN}" run --cwd web lint:fix
	else
		run_step "Web portal linting (eslint)" "${BUN_BIN}" run --cwd web lint
	fi
	run_step "Web portal type checking (tsc)" "${BUN_BIN}" run --cwd web typecheck
	run_step "Web portal static build (next build)" "${BUN_BIN}" run --cwd web build
fi

# 7. Unit test suite (pytest)
if command -v pytest >/dev/null 2>&1; then
	run_step "Unit tests (pytest)" pytest -q
fi

END_TIME=$(python3 -c 'import time; print(time.monotonic_ns())')
TOTAL_MS=$(((END_TIME - START_TIME) / 1000000))
TOTAL_SEC=$(awk "BEGIN {printf \"%.1fs\", ${TOTAL_MS}/1000}")

echo ""
if [[ ${#FAILED_CHECKS[@]} -eq 0 ]]; then
	print_divider "Summary ─ ${TOTAL_SEC}"
	echo -e "  ${C_DIM}[${C_RESET}${C_BOLD_GREEN}✓${C_RESET}${C_DIM}]${C_RESET} All quality, style, and unit test checks passed"
	print_divider
	exit 0
else
	print_divider "Errors"
	echo -e "  ${C_DIM}[${C_RESET}${C_BOLD_RED}✗${C_RESET}${C_DIM}]${C_RESET} Failed components:"
	for check in "${FAILED_CHECKS[@]}"; do
		echo -e "    • ${check}: failed"
	done
	print_divider
	exit 1
fi
