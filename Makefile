SHELL := /bin/bash

.PHONY: help venv install-backend install-frontend backend backend-pg frontend worker migrate \
	backend-script backend-pg-script frontend-script worker-script migrate-script

help:
	@echo "Targets:"
	@echo "  venv             Create .venv"
	@echo "  install-backend  Install backend deps"
	@echo "  backend          Run API (reload) via pdc.py"
	@echo "  backend-pg       One command: start Postgres(docker)+migrate+API"
	@echo "  migrate          Run Alembic migrations via pdc.py"
	@echo "  worker           Run Celery worker via pdc.py"
	@echo "  install-frontend Install frontend deps"
	@echo "  frontend         Run frontend dev server"
	@echo "  backend-script   Run ./scripts/dev-backend.sh"
	@echo "  backend-pg-script Run ./scripts/dev-backend-pg.sh"
	@echo "  migrate-script   Run ./scripts/migrate.sh"
	@echo "  worker-script    Run ./scripts/dev-worker.sh"
	@echo "  frontend-script  Run ./scripts/dev-frontend.sh"

venv:
	@test -d .venv || python3 -m venv .venv

install-backend: venv
	@source .venv/bin/activate && pip install -U pip && pip install -r backend/requirements.txt

backend: install-backend
	@source .venv/bin/activate && python pdc.py api --reload

backend-pg: install-backend
	./scripts/dev-backend-pg.sh

migrate: install-backend
	@source .venv/bin/activate && python pdc.py migrate

worker: install-backend
	@source .venv/bin/activate && python pdc.py worker

install-frontend:
	@cd frontend && npm i

frontend: install-frontend
	@cd frontend && npm run dev

backend-script:
	./scripts/dev-backend.sh

backend-pg-script:
	./scripts/dev-backend-pg.sh

frontend-script:
	./scripts/dev-frontend.sh

worker-script:
	./scripts/dev-worker.sh

migrate-script:
	./scripts/migrate.sh
