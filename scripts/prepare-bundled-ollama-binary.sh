#!/usr/bin/env bash
set -euo pipefail

# Prepare a real Ollama sidecar binary for Tauri bundling (macOS).
#
# This replaces the development shim under frontend/src-tauri/binaries/ with the
# actual Ollama executable from the official macOS app install.
#
# Usage:
#   ./scripts/prepare-bundled-ollama-binary.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TAURI_BIN_DIR="${ROOT_DIR}/frontend/src-tauri/binaries"

SRC="/Applications/Ollama.app/Contents/Resources/ollama"

if [[ ! -x "${SRC}" ]]; then
  echo "Ollama macOS app not found (or not executable): ${SRC}" >&2
  echo "Install Ollama for macOS first, then re-run this script." >&2
  exit 2
fi

mkdir -p "${TAURI_BIN_DIR}"

# The Ollama binary is universal on macOS, so we can copy the same file to both names.
DST_AARCH64="${TAURI_BIN_DIR}/ollama-aarch64-apple-darwin"
DST_X86_64="${TAURI_BIN_DIR}/ollama-x86_64-apple-darwin"

cp -f "${SRC}" "${DST_AARCH64}"
cp -f "${SRC}" "${DST_X86_64}"
chmod +x "${DST_AARCH64}" "${DST_X86_64}"

echo "[prepare-bundled-ollama-binary] Copied: ${SRC}"
echo "[prepare-bundled-ollama-binary] -> ${DST_AARCH64}"
echo "[prepare-bundled-ollama-binary] -> ${DST_X86_64}"

echo "NOTE: This is intended for local packaging. Review Ollama's license/redistribution policy before distributing widely."
