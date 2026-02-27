from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from bomba_sr.storage.db import RuntimeDB


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


class ArtifactStore:
    def __init__(self, db: RuntimeDB, artifacts_root: str | Path):
        self.db = db
        self.artifacts_root = Path(artifacts_root).resolve()
        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

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
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_artifacts_session
              ON artifacts(tenant_id, session_id, created_at DESC);
            """
        )
        existing_cols = {
            str(r["name"])
            for r in self.db.execute("PRAGMA table_info(artifacts)").fetchall()
        }
        if "project_id" not in existing_cols:
            self.db.execute("ALTER TABLE artifacts ADD COLUMN project_id TEXT")
        if "task_id" not in existing_cols:
            self.db.execute("ALTER TABLE artifacts ADD COLUMN task_id TEXT")
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(tenant_id, project_id, created_at DESC)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(tenant_id, task_id, created_at DESC)"
        )
        self.db.commit()

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
    ) -> ArtifactRecord:
        if artifact_type not in {"code", "markdown"}:
            raise ValueError("artifact_type must be code or markdown")

        ext = ".md" if artifact_type == "markdown" else ".txt"
        mime_type = "text/markdown" if artifact_type == "markdown" else "text/plain"

        artifact_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        folder = self.artifacts_root / session_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{turn_id}-{artifact_id[:8]}{ext}"
        path.write_text(content, encoding="utf-8")

        preview = content.strip()[:400]
        self.db.execute(
            """
            INSERT INTO artifacts (
              artifact_id, tenant_id, session_id, turn_id, project_id, task_id, artifact_type,
              title, path, preview, mime_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                tenant_id,
                session_id,
                turn_id,
                project_id,
                task_id,
                artifact_type,
                title,
                str(path),
                preview,
                mime_type,
                created_at,
            ),
        )
        self.db.commit()
        return ArtifactRecord(
            artifact_id=artifact_id,
            tenant_id=tenant_id,
            session_id=session_id,
            turn_id=turn_id,
            project_id=project_id,
            task_id=task_id,
            artifact_type=artifact_type,
            title=title,
            path=str(path),
            preview=preview,
            mime_type=mime_type,
            created_at=created_at,
        )

    def list_session_artifacts(self, tenant_id: str, session_id: str, limit: int = 50) -> list[ArtifactRecord]:
        rows = self.db.execute(
            """
            SELECT * FROM artifacts
            WHERE tenant_id = ? AND session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (tenant_id, session_id, limit),
        ).fetchall()
        return [
            ArtifactRecord(
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
            )
            for row in rows
        ]
