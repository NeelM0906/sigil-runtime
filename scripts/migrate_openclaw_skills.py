#!/usr/bin/env python3
"""Audit and migrate skills from the old SAI/OpenClaw repo into Sigil workspaces.

Scans /Users/studio2/Downloads/SAI-main/skills/ for SKILL.md files,
parses each one, classifies it (knowledge-only vs executable), and
copies useful skills into the appropriate workspace.

Usage:
  PYTHONPATH=src python3 scripts/migrate_openclaw_skills.py --dry-run
  PYTHONPATH=src python3 scripts/migrate_openclaw_skills.py --execute
"""
from __future__ import annotations

import argparse
import logging
import re
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SOURCE_DIR = Path("/Users/studio2/Downloads/SAI-main/skills")
ALT_SOURCES = [
    Path.home() / "Downloads" / "SAI-main" / "skills",
    Path("/Users/studio2/SAI-main/skills"),
]

# Where to put skills based on their domain
ROUTING = {
    "recovery": "workspaces/recovery/skills",
    "legal": "workspaces/recovery/skills",
    "medical": "workspaces/recovery/skills",
    "compliance": "workspaces/recovery/skills",
    "billing": "workspaces/recovery/skills",
    "video": "workspaces/forge/skills",
    "creative": "workspaces/forge/skills",
    "design": "workspaces/forge/skills",
    "content": "workspaces/forge/skills",
    "default": "workspaces/prime/skills",
}

SKIP_LIST = {
    "test-skill", "example-skill", "hello-world",
}


def find_source_dir() -> Path | None:
    for d in [SOURCE_DIR] + ALT_SOURCES:
        if d.exists() and d.is_dir():
            return d
    return None


def parse_skill_frontmatter(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    match = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
    if not match:
        return {"body": content, "raw": True}
    import yaml
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except Exception:
        fm = {}
    fm["body"] = match.group(2).strip()
    fm["body_length"] = len(fm["body"])
    return fm


def classify_skill(fm: dict, skill_dir: Path) -> str:
    has_code = any(
        f.suffix in (".py", ".sh", ".js", ".ts")
        for f in skill_dir.iterdir()
        if f.is_file() and f.name != "SKILL.md"
    )
    tools_required = fm.get("tools_required") or fm.get("tools-required") or []
    if has_code:
        return "executable"
    if tools_required:
        return "hybrid"
    return "knowledge"


def route_skill(fm: dict) -> str:
    name = str(fm.get("name", "")).lower()
    desc = str(fm.get("description", "")).lower()
    text = f"{name} {desc}"
    for keyword, dest in ROUTING.items():
        if keyword == "default":
            continue
        if keyword in text:
            return dest
    return ROUTING["default"]


def audit(source_dir: Path) -> list[dict]:
    results = []
    for skill_dir in sorted(source_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        skill_id = skill_dir.name
        if skill_id in SKIP_LIST:
            continue
        fm = parse_skill_frontmatter(skill_md)
        skill_type = classify_skill(fm, skill_dir)
        destination = route_skill(fm)
        dest_path = Path(destination) / skill_id
        already_exists = dest_path.exists()
        supporting_files = [
            f.name for f in skill_dir.iterdir()
            if f.is_file() and f.name != "SKILL.md"
        ]
        results.append({
            "skill_id": skill_id,
            "name": fm.get("name", skill_id),
            "description": str(fm.get("description", ""))[:100],
            "type": skill_type,
            "destination": destination,
            "already_exists": already_exists,
            "body_length": fm.get("body_length", 0),
            "supporting_files": supporting_files,
            "source_path": str(skill_dir),
        })
    return results


def migrate(source_dir: Path, results: list[dict], dry_run: bool = True):
    migrated = 0
    skipped = 0
    for skill in results:
        if skill["already_exists"]:
            log.info("SKIP (exists): %s → %s", skill["skill_id"], skill["destination"])
            skipped += 1
            continue
        src = Path(skill["source_path"])
        dest = Path(skill["destination"]) / skill["skill_id"]
        if dry_run:
            log.info("WOULD COPY: %s → %s [%s, %d chars, %d files]",
                     skill["skill_id"], dest, skill["type"],
                     skill["body_length"], len(skill["supporting_files"]))
        else:
            dest.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                if f.is_file():
                    shutil.copy2(str(f), str(dest / f.name))
            log.info("COPIED: %s → %s", skill["skill_id"], dest)
        migrated += 1
    return migrated, skipped


def main():
    parser = argparse.ArgumentParser(description="Audit and migrate OpenClaw skills")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--source", type=str, default=None)
    args = parser.parse_args()
    dry_run = not args.execute
    source = Path(args.source) if args.source else find_source_dir()
    if not source or not source.exists():
        log.error("Source directory not found. Try --source /path/to/skills/")
        return 1
    log.info("Source: %s", source)
    log.info("Mode: %s", "DRY RUN" if dry_run else "EXECUTE")
    results = audit(source)

    print(f"\n{'='*60}")
    print(f"SKILL AUDIT: {len(results)} skills found")
    print(f"{'='*60}")

    by_type = {}
    for r in results:
        by_type.setdefault(r["type"], []).append(r)

    for stype in ["executable", "hybrid", "knowledge"]:
        skills = by_type.get(stype, [])
        if not skills:
            continue
        print(f"\n  {stype.upper()} ({len(skills)}):")
        for s in skills:
            exists = " [EXISTS]" if s["already_exists"] else ""
            files = f" +{len(s['supporting_files'])} files" if s["supporting_files"] else ""
            print(f"    {'→' if not s['already_exists'] else '·'} {s['skill_id']}: {s['description'][:60]}{files}{exists}")
            print(f"      dest: {s['destination']}")

    print(f"\n{'='*60}")
    migrated, skipped = migrate(source, results, dry_run=dry_run)
    print(f"\n  {'Would migrate' if dry_run else 'Migrated'}: {migrated}")
    print(f"  Skipped (already exist): {skipped}")

    if dry_run:
        print("\n  Run with --execute to actually copy the files.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
