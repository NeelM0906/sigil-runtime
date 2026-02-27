from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bomba_sr.skills.descriptor import SkillDescriptor
from bomba_sr.storage.db import RuntimeDB


REQUIRED_FIELDS = {
    "skill_id",
    "version",
    "name",
    "description",
    "entrypoint",
    "intent_tags",
    "inputs",
    "outputs",
    "tools_required",
    "risk_level",
    "default_enabled",
}

VALID_STATUSES = {"draft", "validated", "active", "deprecated", "archived"}
VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


@dataclass(frozen=True)
class SkillRecord:
    skill_id: str
    version: str
    name: str
    description: str
    status: str
    source: str
    source_path: str | None
    manifest: dict[str, Any]
    created_at: str
    updated_at: str


class SkillRegistry:
    def __init__(self, db: RuntimeDB):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS skills (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              version TEXT NOT NULL,
              manifest_json TEXT NOT NULL,
              status TEXT NOT NULL,
              source TEXT NOT NULL DEFAULT 'database',
              source_path TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(tenant_id, skill_id, version)
            );

            CREATE TABLE IF NOT EXISTS skill_executions (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              skill_version TEXT NOT NULL,
              session_id TEXT,
              turn_id TEXT,
              status TEXT NOT NULL,
              input_json TEXT NOT NULL,
              output_json TEXT,
              tool_calls_json TEXT,
              error_detail TEXT,
              duration_ms INTEGER,
              created_at TEXT NOT NULL,
              ended_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_skills_tenant_skill
              ON skills(tenant_id, skill_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_skill_executions_tenant
              ON skill_executions(tenant_id, created_at DESC);
            """
        )
        self._ensure_column("skills", "source", "TEXT NOT NULL DEFAULT 'database'")
        self._ensure_column("skills", "source_path", "TEXT")
        self.db.commit()

    def register_skill(
        self,
        tenant_id: str,
        manifest: dict[str, Any],
        status: str = "validated",
        source: str = "database",
        source_path: str | None = None,
    ) -> SkillRecord:
        self._validate_manifest(manifest)
        if status not in VALID_STATUSES:
            raise ValueError("invalid skill status")

        now = self._now()
        skill_id = str(manifest["skill_id"])
        version = str(manifest["version"])

        self.db.execute(
            """
            INSERT INTO skills (
              id, tenant_id, skill_id, version, manifest_json, status, source, source_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id, skill_id, version) DO UPDATE SET
              manifest_json=excluded.manifest_json,
              status=excluded.status,
              source=excluded.source,
              source_path=excluded.source_path,
              updated_at=excluded.updated_at
            """,
            (
                str(uuid.uuid4()),
                tenant_id,
                skill_id,
                version,
                json.dumps(manifest, separators=(",", ":")),
                status,
                source,
                source_path,
                now,
                now,
            ),
        )
        self.db.commit()
        return self.get_skill(tenant_id, skill_id, version)

    def register_from_descriptor(
        self,
        tenant_id: str,
        descriptor: SkillDescriptor,
        status: str = "active",
    ) -> SkillRecord:
        manifest = {
            "skill_id": descriptor.skill_id,
            "version": descriptor.version,
            "name": descriptor.name,
            "description": descriptor.description,
            "entrypoint": {
                "type": "skill_doc",
                "source_path": descriptor.source_path,
                "body_text": descriptor.body_text,
            },
            "intent_tags": list(descriptor.intent_tags),
            "inputs": {},
            "outputs": {"text": "string"},
            "tools_required": list(descriptor.tools_required),
            "risk_level": descriptor.risk_level,
            "default_enabled": descriptor.default_enabled,
            "metadata": descriptor.metadata,
            "user_invocable": descriptor.user_invocable,
            "disable_model_invocation": descriptor.disable_model_invocation,
            "command_dispatch": descriptor.command_dispatch,
            "command_tool": descriptor.command_tool,
            "command_arg_mode": descriptor.command_arg_mode,
        }
        return self.register_skill(
            tenant_id=tenant_id,
            manifest=manifest,
            status=status,
            source=descriptor.source,
            source_path=descriptor.source_path,
        )

    def get_skill(self, tenant_id: str, skill_id: str, version: str | None = None) -> SkillRecord:
        if version is None:
            row = self.db.execute(
                """
                SELECT * FROM skills
                WHERE tenant_id = ? AND skill_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (tenant_id, skill_id),
            ).fetchone()
        else:
            row = self.db.execute(
                "SELECT * FROM skills WHERE tenant_id = ? AND skill_id = ? AND version = ?",
                (tenant_id, skill_id, version),
            ).fetchone()
        if row is None:
            raise ValueError(f"skill not found: {skill_id}")
        return self._row_to_skill(row)

    def list_skills(self, tenant_id: str, status: str | None = None) -> list[SkillRecord]:
        if status is None:
            rows = self.db.execute(
                "SELECT * FROM skills WHERE tenant_id = ? ORDER BY skill_id, created_at DESC",
                (tenant_id,),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM skills WHERE tenant_id = ? AND status = ? ORDER BY skill_id, created_at DESC",
                (tenant_id, status),
            ).fetchall()
        return [self._row_to_skill(row) for row in rows]

    def update_status(self, tenant_id: str, skill_id: str, version: str, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError("invalid skill status")
        self.db.execute(
            "UPDATE skills SET status = ?, updated_at = ? WHERE tenant_id = ? AND skill_id = ? AND version = ?",
            (status, self._now(), tenant_id, skill_id, version),
        )
        self.db.commit()

    def create_execution(
        self,
        tenant_id: str,
        skill_id: str,
        skill_version: str,
        session_id: str | None,
        turn_id: str | None,
        inputs: dict[str, Any],
    ) -> str:
        exec_id = str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO skill_executions (
              id, tenant_id, skill_id, skill_version, session_id, turn_id, status,
              input_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exec_id,
                tenant_id,
                skill_id,
                skill_version,
                session_id,
                turn_id,
                "accepted",
                json.dumps(inputs, separators=(",", ":")),
                self._now(),
            ),
        )
        self.db.commit()
        return exec_id

    def complete_execution(
        self,
        execution_id: str,
        status: str,
        output: dict[str, Any] | None,
        tool_calls: list[dict[str, Any]] | None,
        error_detail: str | None,
        duration_ms: int,
    ) -> None:
        self.db.execute(
            """
            UPDATE skill_executions
            SET status = ?, output_json = ?, tool_calls_json = ?, error_detail = ?, duration_ms = ?, ended_at = ?
            WHERE id = ?
            """,
            (
                status,
                json.dumps(output, separators=(",", ":")) if output is not None else None,
                json.dumps(tool_calls or [], separators=(",", ":")),
                error_detail,
                duration_ms,
                self._now(),
                execution_id,
            ),
        )
        self.db.commit()

    def list_executions(self, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM skill_executions WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "execution_id": str(row["id"]),
                    "tenant_id": str(row["tenant_id"]),
                    "skill_id": str(row["skill_id"]),
                    "skill_version": str(row["skill_version"]),
                    "session_id": str(row["session_id"]) if row["session_id"] is not None else None,
                    "turn_id": str(row["turn_id"]) if row["turn_id"] is not None else None,
                    "status": str(row["status"]),
                    "input": json.loads(str(row["input_json"])),
                    "output": json.loads(str(row["output_json"])) if row["output_json"] else None,
                    "tool_calls": json.loads(str(row["tool_calls_json"])) if row["tool_calls_json"] else [],
                    "error_detail": str(row["error_detail"]) if row["error_detail"] is not None else None,
                    "duration_ms": int(row["duration_ms"]) if row["duration_ms"] is not None else None,
                    "created_at": str(row["created_at"]),
                    "ended_at": str(row["ended_at"]) if row["ended_at"] is not None else None,
                }
            )
        return out

    @staticmethod
    def _validate_manifest(manifest: dict[str, Any]) -> None:
        missing = REQUIRED_FIELDS - set(manifest.keys())
        if missing:
            raise ValueError(f"skill manifest missing fields: {sorted(missing)}")
        if str(manifest["risk_level"]) not in VALID_RISK_LEVELS:
            raise ValueError("invalid skill risk_level")
        if not isinstance(manifest.get("entrypoint"), dict):
            raise ValueError("entrypoint must be object")

    @staticmethod
    def _row_to_skill(row) -> SkillRecord:
        manifest = json.loads(str(row["manifest_json"]))
        return SkillRecord(
            skill_id=str(row["skill_id"]),
            version=str(row["version"]),
            name=str(manifest.get("name", "")),
            description=str(manifest.get("description", "")),
            status=str(row["status"]),
            source=(str(row["source"]) if "source" in row.keys() and row["source"] is not None else "database"),
            source_path=(str(row["source_path"]) if "source_path" in row.keys() and row["source_path"] is not None else None),
            manifest=manifest,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _ensure_column(self, table: str, column: str, ddl: str) -> None:
        row = self.db.execute(
            "SELECT 1 FROM pragma_table_info(?) WHERE name = ?",
            (table, column),
        ).fetchone()
        if row is not None:
            return
        self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
