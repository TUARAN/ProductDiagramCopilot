#!/usr/bin/env bash
set -euo pipefail

# Build a self-contained backend executable for macOS using PyInstaller,
# and copy it into Tauri sidecar bins.
#
# Output:
#   frontend/src-tauri/binaries/pdc-backend-aarch64-apple-darwin
#
# Prereqs:
#   - Python venv at .venv (created by dev scripts)
#   - backend deps installed
#   - pyinstaller installed

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${PY}" ]]; then
  echo "Missing venv python: ${PY}" >&2
  echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt pyinstaller" >&2
  exit 2
fi

TAURI_BIN_DIR="${ROOT_DIR}/frontend/src-tauri/binaries"
mkdir -p "${TAURI_BIN_DIR}"

# Build in an isolated temp dir to avoid polluting repo.
BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "${BUILD_DIR}"' EXIT

cd "${ROOT_DIR}"

# Ensure imports resolve during build.
export PYTHONPATH="backend"

"${PY}" -m PyInstaller \
  --clean \
  --noconfirm \
  --onefile \
  --name pdc-backend \
  --collect-submodules app \
  backend/desktop_server.py \
  --distpath "${BUILD_DIR}/dist" \
  --workpath "${BUILD_DIR}/build" \
  --specpath "${BUILD_DIR}"

SRC_BIN="${BUILD_DIR}/dist/pdc-backend"
if [[ ! -x "${SRC_BIN}" ]]; then
  echo "PyInstaller output missing: ${SRC_BIN}" >&2
  exit 2
fi

DST="${TAURI_BIN_DIR}/pdc-backend-aarch64-apple-darwin"
cp -f "${SRC_BIN}" "${DST}"
chmod +x "${DST}"

echo "[build-backend-sidecar-macos] Wrote: ${DST}"
