#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


IDENTITY_FILES = (
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "MISSION.md",
    "VISION.md",
    "FORMULA.md",
    "PRIORITIES.md",
    "SECURITY.md",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SAI identity files into BOMBA workspaces")
    parser.add_argument(
        "--source-root",
        default=".sai-analysis/.openclaw",
        help="Path to the source SAI .openclaw root directory",
    )
    parser.add_argument(
        "--dest-root",
        default="workspaces",
        help="Destination root containing prime/forge/scholar/recovery workspaces",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing files",
    )
    return parser.parse_args()


def copy_identity_bundle(source_dir: Path, dest_dir: Path, dry_run: bool) -> dict[str, list[str]]:
    copied: list[str] = []
    missing: list[str] = []
    if not source_dir.exists():
        return {"copied": copied, "missing": list(IDENTITY_FILES)}
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
    for filename in IDENTITY_FILES:
        src = source_dir / filename
        dst = dest_dir / filename
        if not src.exists():
            missing.append(filename)
            continue
        if not dry_run:
            shutil.copy2(src, dst)
        copied.append(filename)
    return {"copied": copied, "missing": missing}


def main() -> int:
    args = parse_args()
    source_root = Path(args.source_root).expanduser().resolve()
    dest_root = Path(args.dest_root).expanduser().resolve()

    workspace_map = {
        "prime": source_root / "workspace",
        "forge": source_root / "workspace-forge",
        "scholar": source_root / "workspace-scholar",
        "recovery": source_root / "workspace" / "sisters" / "sai-recovery",
    }

    print(f"SAI identity import source: {source_root}")
    print(f"BOMBA workspace destination: {dest_root}")
    print(f"Dry run: {bool(args.dry_run)}")
    print("")

    total_copied = 0
    total_missing = 0
    for workspace, source_dir in workspace_map.items():
        dest_dir = dest_root / workspace
        result = copy_identity_bundle(source_dir=source_dir, dest_dir=dest_dir, dry_run=bool(args.dry_run))
        total_copied += len(result["copied"])
        total_missing += len(result["missing"])
        print(f"[{workspace}] source={source_dir}")
        print(f"  copied ({len(result['copied'])}): {', '.join(result['copied']) if result['copied'] else '-'}")
        print(f"  missing ({len(result['missing'])}): {', '.join(result['missing']) if result['missing'] else '-'}")

    print("")
    print(f"Import complete. copied={total_copied}, missing={total_missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
