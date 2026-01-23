#!/usr/bin/env bash
set -euo pipefail

# Starts backend (if not already running) and then runs Vite dev server.
# Used by Tauri `beforeDevCommand`.

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"

BACKEND_URL="${PDC_BACKEND_URL:-http://127.0.0.1:8000/health}"
BACKEND_PORT="${PDC_BACKEND_PORT:-8000}"

is_backend_up() {
  curl -fsS --max-time 0.5 "$BACKEND_URL" >/dev/null 2>&1
}

start_backend() {
  if is_backend_up; then
    echo "[tauri-dev] Backend already running."
    return 0
  fi

  echo "[tauri-dev] Starting backend on :${BACKEND_PORT} ..."

  # Reuse existing repo script. It will create venv & install deps if needed.
  # Run in background so this script can continue to start Vite.
  (cd "$ROOT_DIR" && bash ./scripts/dev-backend.sh) >/tmp/pdc-backend-dev.log 2>&1 &

  # Wait briefly for readiness.
  for i in {1..60}; do
    if is_backend_up; then
      echo "[tauri-dev] Backend is up."
      return 0
    fi
    sleep 0.5
  done

  echo "[tauri-dev] Backend failed to start. See /tmp/pdc-backend-dev.log" >&2
  return 1
}

start_backend

cd "$FRONTEND_DIR"
exec npm run dev
