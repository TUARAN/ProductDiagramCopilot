from __future__ import annotations

import os
import sys


def main() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(root, "backend"))

    # Lazy import after sys.path tweak
    from celery.__main__ import main as celery_main  # type: ignore

    argv = [
        "celery",
        "-A",
        "app.jobs.celery_app.celery_app",
        "worker",
        "-l",
        os.environ.get("CELERY_LOGLEVEL", "info"),
    ]
    sys.argv = argv
    celery_main()


if __name__ == "__main__":
    main()
