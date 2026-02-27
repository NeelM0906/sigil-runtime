#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bomba_sr.memory.consolidation import MemoryCandidate, MemoryConsolidator
from bomba_sr.memory.hybrid import HybridMemoryStore
from bomba_sr.runtime.config import RuntimeConfig
from bomba_sr.runtime.tenancy import TenantRegistry
from bomba_sr.storage.db import RuntimeDB


DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
CALL_FILE_RE = re.compile(r"^call-\d{4}-\d{2}-\d{2}-[a-zA-Z0-9]+\.md$")


@dataclass
class ImportStats:
    daily_logs: int = 0
    call_transcripts: int = 0
    memory_index: int = 0
    semantic_memories: int = 0
    skipped: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "daily_logs": self.daily_logs,
            "call_transcripts": self.call_transcripts,
            "memory_index": self.memory_index,
            "semantic_memories": self.semantic_memories,
            "skipped": self.skipped,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SAI memory markdown into BOMBA SR runtime memory tables")
    parser.add_argument(
        "--source-dir",
        default=".sai-analysis/.openclaw/workspace",
        help="Source workspace directory containing memory/ and MEMORY.md",
    )
    parser.add_argument(
        "--tenant-id",
        default="tenant-prime",
        help="Tenant id for primary workspace import",
    )
    parser.add_argument(
        "--user-id",
        default="sai-prime",
        help="User id to attribute imported memory rows to",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be imported",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source_dir).expanduser().resolve()
    if not source_dir.exists():
        raise SystemExit(f"source dir not found: {source_dir}")

    print(f"Source workspace: {source_dir}")
    print(f"Primary tenant/user: {args.tenant_id}/{args.user_id}")
    print(f"Dry run: {bool(args.dry_run)}")
    print("")

    primary_stats = import_workspace_memory(
        source_workspace=source_dir,
        tenant_id=args.tenant_id,
        user_id=args.user_id,
        dry_run=bool(args.dry_run),
    )

    recovery_source = source_dir / "sisters" / "sai-recovery"
    recovery_stats = ImportStats()
    if recovery_source.exists():
        print("\nImporting recovery memory bundle...")
        recovery_stats = import_workspace_memory(
            source_workspace=recovery_source,
            tenant_id="tenant-recovery",
            user_id="sai-recovery",
            dry_run=bool(args.dry_run),
        )
    else:
        print("\nRecovery source not found, skipping tenant-recovery import.")

    print("\nSummary")
    print(f"  primary:  {json.dumps(primary_stats.as_dict(), ensure_ascii=True)}")
    print(f"  recovery: {json.dumps(recovery_stats.as_dict(), ensure_ascii=True)}")
    return 0


def import_workspace_memory(source_workspace: Path, tenant_id: str, user_id: str, dry_run: bool) -> ImportStats:
    cfg = RuntimeConfig()
    registry = TenantRegistry(cfg.runtime_home)
    context = registry.ensure_tenant(tenant_id=tenant_id, workspace_root=None)
    db = RuntimeDB(context.db_path)
    # Ensure schemas exist.
    HybridMemoryStore(db=db, memory_root=context.memory_root)
    consolidator = MemoryConsolidator(db=db)
    stats = ImportStats()

    memory_dir = source_workspace / "memory"
    print(f"[{tenant_id}] source={source_workspace}")
    print(f"[{tenant_id}] db={context.db_path}")
    if memory_dir.exists():
        for file_path in sorted(memory_dir.glob("*.md")):
            text = file_path.read_text(encoding="utf-8")
            created_at = _iso_from_mtime(file_path)
            filename = file_path.name

            if DATE_FILE_RE.match(filename):
                if _import_markdown_note(
                    db=db,
                    memory_root=context.memory_root,
                    user_id=user_id,
                    source_file=file_path,
                    title=file_path.stem,
                    note_type="daily_log",
                    tags=["daily_log", file_path.stem],
                    body_text=text,
                    created_at=created_at,
                    dry_run=dry_run,
                ):
                    stats.daily_logs += 1
                else:
                    stats.skipped += 1
                continue

            if CALL_FILE_RE.match(filename):
                meta_tags = _call_meta_tags(text)
                if _import_markdown_note(
                    db=db,
                    memory_root=context.memory_root,
                    user_id=user_id,
                    source_file=file_path,
                    title=file_path.stem,
                    note_type="call_transcript",
                    tags=["call_transcript", *meta_tags],
                    body_text=text,
                    created_at=created_at,
                    dry_run=dry_run,
                ):
                    stats.call_transcripts += 1
                else:
                    stats.skipped += 1
                continue

            memory_key = f"import::{source_workspace.name}::{file_path.stem}"
            if _import_semantic_memory(
                consolidator=consolidator,
                user_id=user_id,
                memory_key=memory_key,
                content=text,
                source_file=file_path,
                created_at=created_at,
                dry_run=dry_run,
            ):
                stats.semantic_memories += 1
            else:
                stats.skipped += 1

    index_path = source_workspace / "MEMORY.md"
    if index_path.exists():
        if _import_markdown_note(
            db=db,
            memory_root=context.memory_root,
            user_id=user_id,
            source_file=index_path,
            title="MEMORY index",
            note_type="memory_index",
            tags=["memory_index"],
            body_text=index_path.read_text(encoding="utf-8"),
            created_at=_iso_from_mtime(index_path),
            dry_run=dry_run,
        ):
            stats.memory_index += 1
        else:
            stats.skipped += 1

    if not dry_run:
        db.commit()
    db.close()
    print(f"[{tenant_id}] imported={json.dumps(stats.as_dict(), ensure_ascii=True)}")
    return stats


def _import_markdown_note(
    db: RuntimeDB,
    memory_root: Path,
    user_id: str,
    source_file: Path,
    title: str,
    note_type: str,
    tags: list[str],
    body_text: str,
    created_at: str,
    dry_run: bool,
) -> bool:
    relative_path = f"imports/{note_type}/{source_file.name}"
    existing = db.execute(
        "SELECT note_id FROM markdown_notes WHERE user_id = ? AND relative_path = ? LIMIT 1",
        (user_id, relative_path),
    ).fetchone()
    if existing is not None:
        return False
    if dry_run:
        print(f"  [dry-run] note:{note_type} -> {relative_path}")
        return True

    note_id = str(uuid.uuid4())
    note_frontmatter = {
        "note_id": note_id,
        "user_id": user_id,
        "session_id": "import-sai-memory",
        "title": title,
        "tags": tags,
        "confidence": 1.0,
        "created_at": created_at,
        "source_file": str(source_file),
    }
    out_path = memory_root / relative_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(
            [
                "---",
                json.dumps(note_frontmatter, ensure_ascii=True),
                "---",
                "",
                body_text.strip(),
                "",
            ]
        ),
        encoding="utf-8",
    )
    db.execute(
        """
        INSERT INTO markdown_notes (
          note_id, user_id, session_id, relative_path, title, tags, confidence, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            note_id,
            user_id,
            "import-sai-memory",
            relative_path,
            title,
            json.dumps(tags, ensure_ascii=True),
            1.0,
            created_at,
        ),
    )
    return True


def _import_semantic_memory(
    consolidator: MemoryConsolidator,
    user_id: str,
    memory_key: str,
    content: str,
    source_file: Path,
    created_at: str,
    dry_run: bool,
) -> bool:
    if dry_run:
        print(f"  [dry-run] semantic -> {memory_key}")
        return True
    consolidator.upsert(
        MemoryCandidate(
            user_id=user_id,
            key=memory_key,
            content=content.strip(),
            tier="semantic",
            entities=tuple(_tags_from_filename(source_file.stem)),
            evidence_refs=(str(source_file),),
            recency_ts=created_at,
        )
    )
    return True


def _call_meta_tags(content: str) -> list[str]:
    tags: list[str] = []
    date_match = re.search(r"^\s*-\s*\*\*Date:\*\*\s*(.+)$", content, flags=re.IGNORECASE | re.MULTILINE)
    duration_match = re.search(r"^\s*-\s*\*\*Duration:\*\*\s*(.+)$", content, flags=re.IGNORECASE | re.MULTILINE)
    turns_match = re.search(r"^\s*-\s*\*\*Turns:\*\*\s*(.+)$", content, flags=re.IGNORECASE | re.MULTILINE)
    if date_match:
        tags.append(f"date:{date_match.group(1).strip()}")
    if duration_match:
        tags.append(f"duration:{duration_match.group(1).strip()}")
    if turns_match:
        tags.append(f"turns:{turns_match.group(1).strip()}")
    return tags


def _tags_from_filename(stem: str) -> list[str]:
    return [part for part in re.split(r"[-_]+", stem.lower()) if part]


def _iso_from_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
