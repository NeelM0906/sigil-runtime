#!/usr/bin/env python3
"""Run the FastAPI server (Phase 1 — coexists with the legacy ThreadingHTTPServer)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Load .env before any bomba_sr imports
def _load_dotenv_early(path: Path, *, override: bool = True) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw.startswith("export "):
            raw = raw[len("export "):].strip()
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and (override or key not in os.environ or not os.environ.get(key)):
            os.environ[key] = value

_load_dotenv_early(Path(__file__).resolve().parent.parent / ".env")

import uvicorn

from bomba_sr.api.app import create_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Sigil Runtime FastAPI server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
