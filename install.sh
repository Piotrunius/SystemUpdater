#!/usr/bin/env bash
set -euo pipefail

# SystemUpdater Installer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.local/bin"
CONFIG_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/sysupdate"

echo "Installing SystemUpdater..."

# 1. Verify Python 3.11+
if ! command -v python3 >/dev/null 2>&1; then
	echo "Error: python3 is required but not installed." >&2
	exit 1
fi

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="$(echo "${PY_VER}" | cut -d. -f1)"
PY_MINOR="$(echo "${PY_VER}" | cut -d. -f2)"

if [ "${PY_MAJOR}" -lt 3 ] || { [ "${PY_MAJOR}" -eq 3 ] && [ "${PY_MINOR}" -lt 11 ]; }; then
	echo "Error: Python 3.11 or newer is required (detected Python ${PY_VER})." >&2
	exit 1
fi

# 2. Make main.py executable
chmod +x "${SCRIPT_DIR}/main.py"

# 3. Create ~/.local/bin symlink
mkdir -p "${TARGET_DIR}"
ln -sf "${SCRIPT_DIR}/main.py" "${TARGET_DIR}/sysupdate"
chmod +x "${TARGET_DIR}/sysupdate"

# 4. Initialize config directory if not present
mkdir -p "${CONFIG_DIR}"
if [ ! -f "${CONFIG_DIR}/config.toml" ]; then
	cp "${SCRIPT_DIR}/config.example.toml" "${CONFIG_DIR}/config.toml"
	echo "Created default configuration at ${CONFIG_DIR}/config.toml"
fi

echo "Successfully installed SystemUpdater to ${TARGET_DIR}/sysupdate"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":${TARGET_DIR}:"* ]]; then
	echo "Notice: ${TARGET_DIR} is not currently in your PATH."
	echo "Add this line to your ~/.bashrc or ~/.zshrc:"
	echo '  export PATH="${HOME}/.local/bin:${PATH}"'
fi

echo "You can now run: sysupdate"
