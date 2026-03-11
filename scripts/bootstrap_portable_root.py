#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from bomba_sr.openclaw.integration import ensure_portable_openclaw_layout, portable_home_root


def main() -> int:
    portable_root = ensure_portable_openclaw_layout(REPO_ROOT)
    print(f"portable_openclaw_root={portable_root}")
    print(f"portable_home={portable_home_root(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
