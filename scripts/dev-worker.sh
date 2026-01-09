#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source .venv/bin/activate

export PYTHONPATH=backend
celery -A app.jobs.celery_app.celery_app worker -l info
