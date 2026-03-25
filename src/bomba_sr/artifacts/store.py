from __future__ import annotations

import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bomba_sr.storage.db import RuntimeDB


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Artifact type registry ───────────────────────────────────
# Extensible map: artifact_type → (extension, mime_type, is_binary)

ARTIFACT_TYPES: dict[str, tuple[str, str, bool]] = {
    # Text types
    "markdown": (".md", "text/markdown", False),
    "code": (".txt", "text/plain", False),
    # Document types
    "pdf": (".pdf", "application/pdf", True),
    "docx": (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", True),
    # Image types
    "image": (".png", "image/png", True),
    "video": (".mp4", "video/mp4", True),
    "gif": (".gif", "image/gif", True),
    "svg": (".svg", "image/svg+xml", False),
    # Data types
    "json": (".json", "application/json", False),
    "csv": (".csv", "text/csv", False),
    "html": (".html", "text/html", False),
}


def register_artifact_type(
    artifact_type: str, extension: str, mime_type: str, is_binary: bool = False,
) -> None:
    """Register a new artifact type at runtime."""
    ARTIFACT_TYPES[artifact_type] = (extension, mime_type, is_binary)


def get_artifact_type_info(artifact_type: str) -> tuple[str, str, bool]:
    """Return (extension, mime_type, is_binary) for a type. Defaults to text/plain."""
    return ARTIFACT_TYPES.get(artifact_type, (".bin", "application/octet-stream", True))


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    tenant_id: str
    session_id: str
    turn_id: str
    project_id: str | None
    task_id: str | None
    artifact_type: str
    title: str
    path: str
    preview: str
    mime_type: str
    created_at: str
    file_size: int = 0
    created_by: str | None = None
    skill_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArtifactStore:
    def __init__(self, db: RuntimeDB, artifacts_root: str | Path):
        self.db = db
        self.artifacts_root = Path(artifacts_root).resolve()
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        self._on_created: Any = None
        self._ensure_schema()

    def set_on_created(self, callback: Any) -> None:
        """Set callback invoked after each artifact is created. Receives ArtifactRecord."""
        self._on_created = callback

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
              artifact_id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              session_id TEXT NOT NULL,
              turn_id TEXT NOT NULL,
              project_id TEXT,
              task_id TEXT,
              artifact_type TEXT NOT NULL,
              title TEXT NOT NULL,
              path TEXT NOT NULL,
              preview TEXT NOT NULL,
              mime_type TEXT NOT NULL,
              created_at TEXT NOT NULL,
              file_size INTEGER DEFAULT 0,
              created_by TEXT,
              skill_id TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_artifacts_session
              ON artifacts(tenant_id, session_id, created_at DESC);
            """
        )
        for col, col_type in [
            ("project_id", "TEXT"),
            ("task_id", "TEXT"),
            ("file_size", "INTEGER DEFAULT 0"),
            ("created_by", "TEXT"),
            ("skill_id", "TEXT"),
        ]:
            try:
                self.db.execute(f"ALTER TABLE artifacts ADD COLUMN {col} {col_type}")
                self.db.commit()
            except Exception:
                try:
                    self.db.conn.rollback()
                except Exception:
                    pass
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(tenant_id, project_id, created_at DESC)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(tenant_id, task_id, created_at DESC)"
        )
        self.db.commit()

    # ------------------------------------------------------------------
    # Create artifacts
    # ------------------------------------------------------------------

    def create_text_artifact(
        self,
        tenant_id: str,
        session_id: str,
        turn_id: str,
        project_id: str | None,
        task_id: str | None,
        artifact_type: str,
        title: str,
        content: str,
        created_by: str | None = None,
        skill_id: str | None = None,
    ) -> ArtifactRecord:
        ext, mime_type, _ = get_artifact_type_info(artifact_type)

        artifact_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        safe_session = session_id.replace(":", "_")
        folder = self.artifacts_root / safe_session
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{turn_id}-{artifact_id[:8]}{ext}"
        path.write_text(content, encoding="utf-8")
        file_size = path.stat().st_size

        preview = content.strip()[:400]
        return self._insert_record(
            artifact_id, tenant_id, session_id, turn_id, project_id, task_id,
            artifact_type, title, str(path), preview, mime_type, created_at,
            file_size, created_by, skill_id,
        )

    def create_binary_artifact(
        self,
        tenant_id: str,
        session_id: str,
        turn_id: str,
        project_id: str | None,
        task_id: str | None,
        artifact_type: str,
        title: str,
        data: bytes,
        created_by: str | None = None,
        skill_id: str | None = None,
        filename: str | None = None,
    ) -> ArtifactRecord:
        ext, mime_type, _ = get_artifact_type_info(artifact_type)

        artifact_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        safe_session = session_id.replace(":", "_")
        folder = self.artifacts_root / safe_session
        folder.mkdir(parents=True, exist_ok=True)
        fname = filename or f"{turn_id}-{artifact_id[:8]}{ext}"
        path = folder / fname
        path.write_bytes(data)
        file_size = len(data)

        preview = f"[{artifact_type} file: {title} ({file_size:,} bytes)]"
        return self._insert_record(
            artifact_id, tenant_id, session_id, turn_id, project_id, task_id,
            artifact_type, title, str(path), preview, mime_type, created_at,
            file_size, created_by, skill_id,
        )

    def create_file_artifact(
        self,
        tenant_id: str,
        session_id: str,
        turn_id: str,
        project_id: str | None,
        task_id: str | None,
        artifact_type: str,
        title: str,
        source_path: str | Path,
        created_by: str | None = None,
        skill_id: str | None = None,
    ) -> ArtifactRecord:
        """Register an existing file on disk as an artifact (no copy)."""
        src = Path(source_path)
        if not src.is_file():
            raise FileNotFoundError(f"artifact source not found: {source_path}")

        _, mime_type, is_binary = get_artifact_type_info(artifact_type)
        artifact_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        file_size = src.stat().st_size

        if is_binary:
            preview = f"[{artifact_type} file: {title} ({file_size:,} bytes)]"
        else:
            preview = src.read_text(encoding="utf-8", errors="replace")[:400]

        return self._insert_record(
            artifact_id, tenant_id, session_id, turn_id, project_id, task_id,
            artifact_type, title, str(src), preview, mime_type, created_at,
            file_size, created_by, skill_id,
        )

    def _insert_record(
        self,
        artifact_id: str, tenant_id: str, session_id: str, turn_id: str,
        project_id: str | None, task_id: str | None, artifact_type: str,
        title: str, path: str, preview: str, mime_type: str, created_at: str,
        file_size: int, created_by: str | None, skill_id: str | None,
    ) -> ArtifactRecord:
        self.db.execute(
            """
            INSERT INTO artifacts (
              artifact_id, tenant_id, session_id, turn_id, project_id, task_id,
              artifact_type, title, path, preview, mime_type, created_at,
              file_size, created_by, skill_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id, tenant_id, session_id, turn_id, project_id, task_id,
                artifact_type, title, path, preview, mime_type, created_at,
                file_size, created_by, skill_id,
            ),
        )
        self.db.commit()
        record = ArtifactRecord(
            artifact_id=artifact_id, tenant_id=tenant_id, session_id=session_id,
            turn_id=turn_id, project_id=project_id, task_id=task_id,
            artifact_type=artifact_type, title=title, path=path, preview=preview,
            mime_type=mime_type, created_at=created_at, file_size=file_size,
            created_by=created_by, skill_id=skill_id,
        )
        if self._on_created is not None:
            try:
                self._on_created(record)
            except Exception:
                pass
        return record

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_session_artifacts(self, tenant_id: str, session_id: str, limit: int = 50) -> list[ArtifactRecord]:
        rows = self.db.execute(
            """
            SELECT * FROM artifacts
            WHERE tenant_id = ? AND session_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (tenant_id, session_id, limit),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_task_artifacts(self, tenant_id: str, task_id: str, limit: int = 50) -> list[ArtifactRecord]:
        rows = self.db.execute(
            """
            SELECT * FROM artifacts
            WHERE tenant_id = ? AND task_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (tenant_id, task_id, limit),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_recent_artifacts(self, tenant_id: str, limit: int = 50) -> list[ArtifactRecord]:
        rows = self.db.execute(
            """
            SELECT * FROM artifacts
            WHERE tenant_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (tenant_id, limit),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        row = self.db.execute(
            "SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    @staticmethod
    def _row_to_record(row) -> ArtifactRecord:
        return ArtifactRecord(
            artifact_id=str(row["artifact_id"]),
            tenant_id=str(row["tenant_id"]),
            session_id=str(row["session_id"]),
            turn_id=str(row["turn_id"]),
            project_id=str(row["project_id"]) if row["project_id"] is not None else None,
            task_id=str(row["task_id"]) if row["task_id"] is not None else None,
            artifact_type=str(row["artifact_type"]),
            title=str(row["title"]),
            path=str(row["path"]),
            preview=str(row["preview"]),
            mime_type=str(row["mime_type"]),
            created_at=str(row["created_at"]),
            file_size=int(row["file_size"]) if row["file_size"] else 0,
            created_by=str(row["created_by"]) if row["created_by"] else None,
            skill_id=str(row["skill_id"]) if row["skill_id"] else None,
        )
