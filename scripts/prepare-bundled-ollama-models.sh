#!/usr/bin/env bash
set -euo pipefail

# Prepare Scheme A: bundle Ollama models into the Tauri installer.
#
# Copies an existing Ollama models cache into:
#   frontend/src-tauri/resources/ollama_models/
#
# Usage:
#   ./scripts/prepare-bundled-ollama-models.sh [SOURCE_MODELS_DIR]
#
# Default SOURCE_MODELS_DIR:
#   macOS/Linux: ~/.ollama/models

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_DIR="${1:-$HOME/.ollama/models}"
DST_DIR="${ROOT_DIR}/frontend/src-tauri/resources/ollama_models"

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "Source models dir not found: ${SRC_DIR}" >&2
  exit 2
fi

mkdir -p "${DST_DIR}"

echo "[prepare-bundled-ollama-models] Source: ${SRC_DIR}"
echo "[prepare-bundled-ollama-models] Dest:   ${DST_DIR}"

# Use rsync for speed and progress on large directories.
# --delete keeps destination exactly equal to source.
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "${SRC_DIR}/" "${DST_DIR}/"
else
  rm -rf "${DST_DIR}" && mkdir -p "${DST_DIR}"
  cp -R "${SRC_DIR}/." "${DST_DIR}/"
fi

echo "[prepare-bundled-ollama-models] Done. NOTE: this directory is intentionally gitignored."
