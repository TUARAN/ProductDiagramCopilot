from __future__ import annotations

import os
import sys

from alembic import command
from alembic.config import Config


def main() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(root, "backend"))

    cfg = Config(os.path.join(root, "backend", "alembic.ini"))
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    main()
