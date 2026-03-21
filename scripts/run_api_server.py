#!/usr/bin/env python3
"""FastAPI server for Bomba SR — runs alongside or instead of the legacy server."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

# Load .env before any bomba_sr imports
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw.startswith("export "):
            raw = raw[7:].strip()
        if "=" in raw:
            k, v = raw.split("=", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if k:
                os.environ.setdefault(k, v)


def main():
    parser = argparse.ArgumentParser(description="Run Bomba SR FastAPI server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(
        "bomba_sr.api.app:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
