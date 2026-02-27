from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bomba_sr.subagents.orchestrator import SubAgentHandle, SubAgentOrchestrator
from bomba_sr.subagents.protocol import SubAgentProtocol, SubAgentTask


@dataclass(frozen=True)
class SisterConfig:
    sister_id: str
    display_name: str
    emoji: str
    tenant_id: str
    workspace_root: Path
    model_id: str
    role: str
    auto_start: bool
    heartbeat_enabled: bool
    cron_tasks: list[dict[str, Any]]


class SisterRegistry:
    def __init__(
        self,
        config_path: Path,
        orchestrator: SubAgentOrchestrator,
        protocol: SubAgentProtocol,
        parent_agent_id: str = "prime",
    ) -> None:
        self.config_path = Path(config_path).expanduser().resolve()
        self.orchestrator = orchestrator
        self.protocol = protocol
        self.parent_agent_id = parent_agent_id
        self._sisters: dict[str, SisterConfig] = self._load_configs(self.config_path)
        self._handles: dict[str, SubAgentHandle] = {}

    def list_sisters(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for sister in sorted(self._sisters.values(), key=lambda item: item.sister_id):
            status = self._status_for_sister(sister.sister_id)
            out.append(
                {
                    "sister_id": sister.sister_id,
                    "display_name": sister.display_name,
                    "emoji": sister.emoji,
                    "tenant_id": sister.tenant_id,
                    "workspace_root": str(sister.workspace_root),
                    "model_id": sister.model_id,
                    "role": sister.role,
                    "auto_start": sister.auto_start,
                    "heartbeat_enabled": sister.heartbeat_enabled,
                    "cron_tasks": sister.cron_tasks,
                    **status,
                }
            )
        return out

    def get_sister(self, sister_id: str) -> SisterConfig | None:
        return self._sisters.get(sister_id)

    def spawn_sister(
        self,
        sister_id: str,
        *,
        parent_session_id: str = "sisters-control",
        parent_turn_id: str | None = None,
        worker=None,
    ) -> dict[str, Any]:
        sister = self._require_sister(sister_id)
        current_status = self._status_for_sister(sister_id)
        if current_status["running"]:
            return {
                "started": False,
                "sister_id": sister_id,
                "run_id": current_status.get("run_id"),
                "status": current_status.get("status"),
                "reason": "already_running",
            }

        task = SubAgentTask(
            tenant_id=sister.tenant_id,
            task_id=f"sister-{sister.sister_id}",
            ticket_id=str(uuid.uuid4()),
            idempotency_key=uuid.uuid4().hex,
            goal=f"Sister bootstrap: {sister.role}",
            done_when=("Sister initialized and ready for delegated tasks",),
            input_context_refs=(f"sister:{sister.sister_id}", f"workspace:{sister.workspace_root}"),
            output_schema={"summary": "string", "status": "string"},
            priority="normal",
            run_timeout_seconds=24 * 60 * 60,
            cleanup="keep",
            workspace_root=str(sister.workspace_root),
            model_id=sister.model_id,
        )
        handle = self.orchestrator.spawn_async(
            task=task,
            parent_session_id=parent_session_id,
            parent_turn_id=parent_turn_id or str(uuid.uuid4()),
            parent_agent_id=self.parent_agent_id,
            child_agent_id=f"sister-{sister.sister_id}",
            worker=worker,
            parent_run_id=None,
        )
        self._handles[sister_id] = handle
        return {
            "started": True,
            "sister_id": sister_id,
            "run_id": handle.run_id,
            "status": "accepted",
        }

    def stop_sister(self, sister_id: str) -> dict[str, Any]:
        sister = self._require_sister(sister_id)
        status = self._status_for_sister(sister_id)
        run_id = status.get("run_id")
        if not run_id:
            return {"stopped": False, "sister_id": sister.sister_id, "reason": "not_running"}
        stopped = self.protocol.cascade_stop(run_id, reason="sister_stop_requested")
        self._handles.pop(sister_id, None)
        return {
            "stopped": bool(stopped),
            "sister_id": sister.sister_id,
            "run_id": run_id,
            "stopped_run_ids": stopped,
        }

    def _status_for_sister(self, sister_id: str) -> dict[str, Any]:
        handle = self._handles.get(sister_id)
        if handle is not None:
            run = self.protocol.get_run(handle.run_id)
            if run is not None and run.get("status") not in {"failed", "timed_out", "completed"}:
                return {
                    "running": True,
                    "run_id": handle.run_id,
                    "status": run.get("status"),
                    "last_activity": run.get("ended_at") or run.get("started_at") or run.get("accepted_at"),
                }
        latest = self._latest_run_for_sister(sister_id)
        if latest is None:
            return {"running": False, "run_id": None, "status": "never_started", "last_activity": None}
        status = str(latest["status"])
        return {
            "running": status not in {"failed", "timed_out", "completed"},
            "run_id": str(latest["run_id"]),
            "status": status,
            "last_activity": (
                (str(latest["ended_at"]) if latest["ended_at"] is not None else None)
                or (str(latest["started_at"]) if latest["started_at"] is not None else None)
                or str(latest["accepted_at"])
            ),
        }

    def _latest_run_for_sister(self, sister_id: str):
        return self.protocol.db.execute(
            """
            SELECT run_id, status, accepted_at, started_at, ended_at
            FROM subagent_runs
            WHERE child_agent_id = ?
            ORDER BY accepted_at DESC
            LIMIT 1
            """,
            (f"sister-{sister_id}",),
        ).fetchone()

    def _require_sister(self, sister_id: str) -> SisterConfig:
        sister = self._sisters.get(sister_id)
        if sister is None:
            raise ValueError(f"sister not found: {sister_id}")
        return sister

    @staticmethod
    def _load_configs(config_path: Path) -> dict[str, SisterConfig]:
        if not config_path.exists():
            return {}
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        raw_sisters = payload.get("sisters") if isinstance(payload, dict) else None
        if not isinstance(raw_sisters, list):
            return {}
        out: dict[str, SisterConfig] = {}
        for item in raw_sisters:
            if not isinstance(item, dict):
                continue
            sister_id = str(item.get("sister_id") or "").strip()
            if not sister_id:
                continue
            raw_workspace = str(item.get("workspace_root") or "").strip()
            if not raw_workspace:
                continue
            workspace_root = Path(raw_workspace).expanduser()
            if not workspace_root.is_absolute():
                workspace_root = (Path.cwd() / workspace_root).resolve()
            out[sister_id] = SisterConfig(
                sister_id=sister_id,
                display_name=str(item.get("display_name") or sister_id),
                emoji=str(item.get("emoji") or ""),
                tenant_id=str(item.get("tenant_id") or f"tenant-{sister_id}"),
                workspace_root=workspace_root,
                model_id=str(item.get("model_id") or ""),
                role=str(item.get("role") or ""),
                auto_start=bool(item.get("auto_start", False)),
                heartbeat_enabled=bool(item.get("heartbeat_enabled", False)),
                cron_tasks=list(item.get("cron_tasks") or []),
            )
        return out
