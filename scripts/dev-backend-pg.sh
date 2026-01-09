#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PG_PORT="${PDC_PG_PORT:-5433}"

# 1) Start Postgres (Docker)
docker compose up -d postgres

# 2) Wait until Postgres is reachable on the host port
for i in {1..60}; do
  if nc -z 127.0.0.1 "$PG_PORT" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
  if [[ $i -eq 60 ]]; then
    echo "Postgres not reachable on 127.0.0.1:${PG_PORT}." >&2
    echo "Hint: check docker compose ps/logs, or change PDC_PG_PORT." >&2
    exit 1
  fi
done

# 3) Ensure venv + deps
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -U pip >/dev/null
pip install -r backend/requirements.txt >/dev/null

# 4) Run migrations (uses DATABASE_URL from .env)
python pdc.py migrate

# 5) Start API (reload)
python pdc.py api --reload
