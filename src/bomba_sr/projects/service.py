from __future__ import annotations

import uuid
from datetime import datetime, timezone

from bomba_sr.storage.db import RuntimeDB


PROJECT_STATUSES = {"active", "paused", "archived"}
TASK_STATUSES = {"backlog", "todo", "in_progress", "in_review", "blocked", "review", "done", "cancelled"}
TASK_PRIORITIES = {"low", "normal", "medium", "high", "critical"}


class ProjectService:
    def __init__(self, db: RuntimeDB):
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS projects (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              name TEXT NOT NULL,
              description TEXT,
              workspace_root TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(tenant_id, project_id)
            );

            CREATE TABLE IF NOT EXISTS project_tasks (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              task_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT,
              status TEXT NOT NULL,
              priority TEXT NOT NULL,
              owner_agent_id TEXT,
              parent_task_id TEXT DEFAULT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(tenant_id, task_id)
            );

            CREATE INDEX IF NOT EXISTS idx_projects_tenant
              ON projects(tenant_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_project_tasks_project
              ON project_tasks(project_id, updated_at DESC);
            """
        )
        self.db.commit()
        # Migrate existing databases: add parent_task_id column if missing.
        try:
            self.db.execute("SELECT parent_task_id FROM project_tasks LIMIT 0")
        except Exception:
            try:
                self.db.conn.rollback()
            except Exception:
                pass
            try:
                self.db.execute("ALTER TABLE project_tasks ADD COLUMN parent_task_id TEXT DEFAULT NULL")
                self.db.commit()
            except Exception:
                try:
                    self.db.conn.rollback()
                except Exception:
                    pass
        # Create the parent_task_id index AFTER the migration ensures the column exists.
        try:
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_project_tasks_parent ON project_tasks(parent_task_id)"
            )
            self.db.commit()
        except Exception:
            try:
                self.db.conn.rollback()
            except Exception:
                pass

    def create_project(
        self,
        tenant_id: str,
        name: str,
        workspace_root: str,
        description: str | None = None,
        project_id: str | None = None,
        status: str = "active",
    ) -> dict:
        if status not in PROJECT_STATUSES:
            raise ValueError("invalid project status")
        now = self._now()
        pid = project_id or str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO projects (
              id, tenant_id, project_id, name, description, workspace_root,
              status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                tenant_id,
                pid,
                name,
                description,
                workspace_root,
                status,
                now,
                now,
            ),
        )
        self.db.commit()
        return self.get_project(tenant_id, pid)

    def list_projects(self, tenant_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM projects WHERE tenant_id = ? ORDER BY updated_at DESC",
            (tenant_id,),
        ).fetchall()
        return [self._project_row(row) for row in rows]

    def get_project(self, tenant_id: str, project_id: str) -> dict:
        row = self.db.execute(
            "SELECT * FROM projects WHERE tenant_id = ? AND project_id = ?",
            (tenant_id, project_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"project not found: {project_id}")
        return self._project_row(row)

    def update_project_status(self, tenant_id: str, project_id: str, status: str) -> dict:
        if status not in PROJECT_STATUSES:
            raise ValueError("invalid project status")
        self.db.execute(
            "UPDATE projects SET status = ?, updated_at = ? WHERE tenant_id = ? AND project_id = ?",
            (status, self._now(), tenant_id, project_id),
        )
        self.db.commit()
        return self.get_project(tenant_id, project_id)

    def create_task(
        self,
        tenant_id: str,
        project_id: str,
        title: str,
        description: str | None = None,
        task_id: str | None = None,
        status: str = "todo",
        priority: str = "normal",
        owner_agent_id: str | None = None,
        parent_task_id: str | None = None,
    ) -> dict:
        if status not in TASK_STATUSES:
            raise ValueError("invalid task status")
        if priority not in TASK_PRIORITIES:
            raise ValueError("invalid task priority")

        self.get_project(tenant_id, project_id)

        now = self._now()
        tid = task_id or str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO project_tasks (
              id, tenant_id, task_id, project_id, title, description,
              status, priority, owner_agent_id, parent_task_id,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                tenant_id,
                tid,
                project_id,
                title,
                description,
                status,
                priority,
                owner_agent_id,
                parent_task_id,
                now,
                now,
            ),
        )
        self.db.commit()
        return self.get_task(tenant_id, tid)

    def get_task(self, tenant_id: str, task_id: str) -> dict:
        row = self.db.execute(
            "SELECT * FROM project_tasks WHERE tenant_id = ? AND task_id = ?",
            (tenant_id, task_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"task not found: {task_id}")
        return self._task_row(row)

    def list_tasks(
        self,
        tenant_id: str,
        project_id: str | None = None,
        status: str | None = None,
        top_level_only: bool = False,
    ) -> list[dict]:
        sql = "SELECT * FROM project_tasks WHERE tenant_id = ?"
        params: list = [tenant_id]
        if project_id is not None:
            sql += " AND project_id = ?"
            params.append(project_id)
        if status is not None:
            sql += " AND status = ?"
            params.append(status)
        if top_level_only:
            sql += " AND parent_task_id IS NULL"
        sql += " ORDER BY updated_at DESC"
        rows = self.db.execute(sql, tuple(params)).fetchall()
        return [self._task_row(row) for row in rows]

    def update_task(
        self,
        tenant_id: str,
        task_id: str,
        status: str | None = None,
        priority: str | None = None,
        owner_agent_id: str | None = None,
    ) -> dict:
        current = self.get_task(tenant_id, task_id)
        next_status = status or current["status"]
        next_priority = priority or current["priority"]
        next_owner = owner_agent_id if owner_agent_id is not None else current.get("owner_agent_id")

        if next_status not in TASK_STATUSES:
            raise ValueError("invalid task status")
        if next_priority not in TASK_PRIORITIES:
            raise ValueError("invalid task priority")

        self.db.execute(
            """
            UPDATE project_tasks
            SET status = ?, priority = ?, owner_agent_id = ?, updated_at = ?
            WHERE tenant_id = ? AND task_id = ?
            """,
            (next_status, next_priority, next_owner, self._now(), tenant_id, task_id),
        )
        self.db.commit()
        return self.get_task(tenant_id, task_id)

    @staticmethod
    def _project_row(row) -> dict:
        return {
            "project_id": str(row["project_id"]),
            "tenant_id": str(row["tenant_id"]),
            "name": str(row["name"]),
            "description": str(row["description"]) if row["description"] is not None else None,
            "workspace_root": str(row["workspace_root"]),
            "status": str(row["status"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    @staticmethod
    def _task_row(row) -> dict:
        return {
            "task_id": str(row["task_id"]),
            "tenant_id": str(row["tenant_id"]),
            "project_id": str(row["project_id"]),
            "title": str(row["title"]),
            "description": str(row["description"]) if row["description"] is not None else None,
            "status": str(row["status"]),
            "priority": str(row["priority"]),
            "owner_agent_id": str(row["owner_agent_id"]) if row["owner_agent_id"] is not None else None,
            "parent_task_id": str(row["parent_task_id"]) if row["parent_task_id"] is not None else None,
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
