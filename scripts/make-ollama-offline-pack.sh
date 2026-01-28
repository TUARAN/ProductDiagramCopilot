#!/usr/bin/env bash
set -euo pipefail

# Build an offline "Ollama models" extension pack from an existing Ollama cache directory.
#
# Usage:
#   ./scripts/make-ollama-offline-pack.sh /path/to/.ollama/models
#
# Output:
#   dist/ollama-models-<os>-<arch>-YYYYMMDD.tar.gz

MODELS_DIR="${1:-}"
if [[ -z "${MODELS_DIR}" ]]; then
  echo "Usage: $0 /path/to/.ollama/models" >&2
  exit 2
fi

if [[ ! -d "${MODELS_DIR}" ]]; then
  echo "Models dir not found: ${MODELS_DIR}" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist"
mkdir -p "${OUT_DIR}"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
DATE="$(date +%Y%m%d)"
OUT_FILE="${OUT_DIR}/ollama-models-${OS}-${ARCH}-${DATE}.tar.gz"

# Pack the directory contents as "models/" so users can extract into ~/.ollama
# (i.e. ~/.ollama/models/<files...>)
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
mkdir -p "${TMP_DIR}/models"

# Copy rather than tar from original path so we control the top-level folder name.
# (This avoids embedding absolute paths into tar.)
cp -R "${MODELS_DIR}/." "${TMP_DIR}/models/"

tar -C "${TMP_DIR}" -czf "${OUT_FILE}" models

echo "Wrote: ${OUT_FILE}"

echo "\nInstall (official Ollama cache dir):"
echo "  macOS/Linux:  ~/.ollama/models"
echo "  Windows:      %USERPROFILE%\\.ollama\\models"
echo "\nExample (macOS/Linux):"
echo "  mkdir -p ~/.ollama && tar -xzf '${OUT_FILE}' -C ~/.ollama"
