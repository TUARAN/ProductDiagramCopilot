#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source .venv/bin/activate
export PYTHONPATH=backend

alembic -c backend/alembic.ini upgrade head
