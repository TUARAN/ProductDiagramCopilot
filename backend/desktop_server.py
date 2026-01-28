from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn


def main() -> int:
    # Ensure we can import backend package as `app.*`.
    backend_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(backend_dir))

    p = argparse.ArgumentParser(prog="pdc-backend", description="ProductDiagramCopilot bundled backend")
    p.add_argument("--host", default=os.getenv("PDC_BACKEND_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.getenv("PDC_BACKEND_PORT", "8000")))
    args = p.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        log_level=os.getenv("PDC_BACKEND_LOG_LEVEL", "info"),
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
