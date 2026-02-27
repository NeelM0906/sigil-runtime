from __future__ import annotations

import uuid
from typing import Any

from bomba_sr.subagents.orchestrator import SubAgentOrchestrator, SubAgentWorker
from bomba_sr.subagents.protocol import SubAgentProtocol, SubAgentTask
from bomba_sr.tools.base import ToolContext, ToolDefinition


def _default_worker(run_id: str, task: SubAgentTask, protocol: SubAgentProtocol) -> dict[str, Any]:
    protocol.progress(run_id, 35, summary="Sub-agent started")
    protocol.progress(run_id, 80, summary="Sub-agent completed work")
    return {
        "summary": f"Sub-agent completed task: {task.goal}",
        "runtime_ms": 1,
        "token_usage": {"input": 0, "output": 0, "total": 0},
    }


def _spawn_factory(orchestrator: SubAgentOrchestrator, default_worker: SubAgentWorker | None):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        goal = str(arguments.get("goal") or "").strip()
        if not goal:
            raise ValueError("goal is required")
        task = SubAgentTask(
            tenant_id=str(arguments.get("tenant_id") or context.tenant_id),
            task_id=str(arguments.get("task_id") or uuid.uuid4()),
            ticket_id=str(arguments.get("ticket_id") or uuid.uuid4()),
            idempotency_key=str(arguments.get("idempotency_key") or uuid.uuid4().hex),
            goal=goal,
            done_when=tuple(arguments.get("done_when") or ["Goal complete"]),
            input_context_refs=tuple(arguments.get("input_context_refs") or []),
            output_schema=dict(arguments.get("output_schema") or {"summary": "string"}),
            priority=str(arguments.get("priority") or "normal"),
            run_timeout_seconds=int(arguments.get("run_timeout_seconds") or 120),
            cleanup=str(arguments.get("cleanup") or "keep"),
            workspace_root=str(arguments.get("workspace_root") or context.workspace_root),
            model_id=(str(arguments.get("model_id")) if arguments.get("model_id") else None),
        )
        handle = orchestrator.spawn_async(
            task=task,
            parent_session_id=context.session_id,
            parent_turn_id=context.turn_id,
            parent_agent_id="parent-agent",
            child_agent_id=str(arguments.get("child_agent_id") or "subagent"),
            worker=default_worker or _default_worker,
            parent_run_id=(str(arguments.get("parent_run_id")) if arguments.get("parent_run_id") else None),
        )
        return {"run_id": handle.run_id}

    return run


def _poll_factory(protocol: SubAgentProtocol):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        run_id = str(arguments.get("run_id") or "").strip()
        if not run_id:
            raise ValueError("run_id is required")
        after_seq = int(arguments.get("after_seq") or 0)
        run_state = protocol.get_run(run_id)
        events = protocol.stream_events(run_id=run_id, after_seq=after_seq)
        return {"run": run_state, "events": events}

    return run


def _list_factory(protocol: SubAgentProtocol):
    def run(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 50)
        rows = protocol.db.execute(
            """
            SELECT run_id, task_id, ticket_id, parent_session_id, parent_turn_id, parent_agent_id,
                   child_agent_id, status, progress_pct, accepted_at, started_at, ended_at
            FROM subagent_runs
            WHERE tenant_id = ?
            ORDER BY accepted_at DESC
            LIMIT ?
            """,
            (context.tenant_id, limit),
        ).fetchall()
        return {
            "runs": [
                {
                    "run_id": str(row["run_id"]),
                    "task_id": str(row["task_id"]),
                    "ticket_id": str(row["ticket_id"]),
                    "parent_session_id": str(row["parent_session_id"]),
                    "parent_turn_id": str(row["parent_turn_id"]),
                    "parent_agent_id": str(row["parent_agent_id"]),
                    "child_agent_id": str(row["child_agent_id"]),
                    "status": str(row["status"]),
                    "progress_pct": (int(row["progress_pct"]) if row["progress_pct"] is not None else None),
                    "accepted_at": str(row["accepted_at"]),
                    "started_at": (str(row["started_at"]) if row["started_at"] is not None else None),
                    "ended_at": (str(row["ended_at"]) if row["ended_at"] is not None else None),
                }
                for row in rows
            ]
        }

    return run


def builtin_subagent_tools(
    orchestrator: SubAgentOrchestrator,
    protocol: SubAgentProtocol,
    default_worker: SubAgentWorker | None = None,
) -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="sessions_spawn",
            description="Spawn a sub-agent run asynchronously.",
            parameters={
                "type": "object",
                "properties": {
                    "goal": {"type": "string"},
                    "task_id": {"type": "string"},
                    "ticket_id": {"type": "string"},
                    "idempotency_key": {"type": "string"},
                    "done_when": {"type": "array", "items": {"type": "string"}},
                    "input_context_refs": {"type": "array", "items": {"type": "string"}},
                    "output_schema": {"type": "object"},
                    "priority": {"type": "string"},
                    "run_timeout_seconds": {"type": "integer"},
                    "cleanup": {"type": "string"},
                    "child_agent_id": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "workspace_root": {"type": "string"},
                    "model_id": {"type": "string"},
                },
                "required": ["goal"],
                "additionalProperties": False,
            },
            risk_level="high",
            action_type="execute",
            execute=_spawn_factory(orchestrator, default_worker),
            aliases=("spawn_subagent",),
        ),
        ToolDefinition(
            name="sessions_poll",
            description="Poll a sub-agent run and events.",
            parameters={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "after_seq": {"type": "integer"},
                },
                "required": ["run_id"],
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_poll_factory(protocol),
            aliases=("poll_subagent",),
        ),
        ToolDefinition(
            name="sessions_list",
            description="List sub-agent runs.",
            parameters={
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
                "additionalProperties": False,
            },
            risk_level="low",
            action_type="read",
            execute=_list_factory(protocol),
        ),
    ]
