#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv-ecat"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CAPS="${CAPS:-cap_net_raw}"

echo "Repo root: ${REPO_ROOT}"
echo "Venv dir:  ${VENV_DIR}"
echo "Python:    ${PYTHON_BIN}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "error: Python interpreter not found: ${PYTHON_BIN}" >&2
    exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
    echo "Creating virtual environment"
    "${PYTHON_BIN}" -m venv --copies "${VENV_DIR}"
else
    echo "Using existing virtual environment"
fi

VENV_PYTHON="${VENV_DIR}/bin/python"

echo "Upgrading pip"
"${VENV_PYTHON}" -m pip install --upgrade pip

echo "Installing pysoem"
"${VENV_PYTHON}" -m pip install pysoem

cat <<EOF

Bootstrap complete.

This script uses \`python -m venv --copies\` so ${VENV_DIR}/bin/python3 is a
regular file. That is required for \`setcap\`; it will fail on symlink-based
venvs.

Activate it with:
  source "${VENV_DIR}/bin/activate"

Grant EtherCAT raw-socket capability to this venv interpreter with:
  sudo setcap ${CAPS}=eip "${VENV_DIR}/bin/python3"

Verify capabilities with:
  getcap "${VENV_DIR}/bin/python3"

Then run tests without sudo, for example:
  "${VENV_DIR}/bin/python" src/tools/scan_pysoem.py --iface enp47s0

If raw socket access still fails, rerun setcap with:
  sudo setcap cap_net_raw,cap_net_admin=eip "${VENV_DIR}/bin/python3"
EOF
