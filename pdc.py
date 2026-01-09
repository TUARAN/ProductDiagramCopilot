#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"


def _env_with_backend_path() -> dict:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    backend_path = str(BACKEND_DIR)
    env["PYTHONPATH"] = backend_path + (os.pathsep + existing if existing else "")
    return env


def _exec(args: list) -> int:
    env = _env_with_backend_path()
    os.chdir(str(ROOT))
    os.execvpe(args[0], args, env)
    return 127


def run_api(host: str, port: int, reload: bool) -> int:
    args = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        args.append("--reload")
    return _exec(args)


def run_worker(loglevel: str) -> int:
    args = [
        sys.executable,
        "-m",
        "celery",
        "-A",
        "app.jobs.celery_app.celery_app",
        "worker",
        "-l",
        loglevel,
    ]
    return _exec(args)


def run_migrate() -> int:
    args = [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(BACKEND_DIR / "alembic.ini"),
        "upgrade",
        "head",
    ]
    return _exec(args)


def main() -> int:
    p = argparse.ArgumentParser(prog="pdc", description="Product Diagram Copilot dev entrypoint")
    sub = p.add_subparsers(dest="cmd", required=True)

    api = sub.add_parser("api", help="Run FastAPI server")
    api.add_argument("--host", default="0.0.0.0")
    api.add_argument("--port", default=8000, type=int)
    api.add_argument("--reload", action="store_true")

    worker = sub.add_parser("worker", help="Run Celery worker")
    worker.add_argument("--loglevel", default="info")

    sub.add_parser("migrate", help="Run Alembic migrations")

    args = p.parse_args()

    if args.cmd == "api":
        return run_api(args.host, args.port, args.reload)
    if args.cmd == "worker":
        return run_worker(args.loglevel)
    if args.cmd == "migrate":
        return run_migrate()

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
