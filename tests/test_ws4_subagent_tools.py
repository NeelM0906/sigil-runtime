from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from bomba_sr.storage.db import RuntimeDB
from bomba_sr.subagents.orchestrator import SubAgentOrchestrator
from bomba_sr.subagents.protocol import SubAgentProtocol, SubAgentTask
from bomba_sr.tools.base import ToolContext
from bomba_sr.tools.builtin_subagents import builtin_subagent_tools


def _guard(root: Path):
    def guard(path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        root_real = root.resolve()
        if candidate != root_real and root_real not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    return guard


def _task(tenant_id: str, task_suffix: str) -> SubAgentTask:
    return SubAgentTask(
        tenant_id=tenant_id,
        task_id=f"task-{task_suffix}",
        ticket_id=f"ticket-{task_suffix}",
        idempotency_key=f"turn-{task_suffix}::hash-{uuid.uuid4().hex[:12]}",
        goal="Test goal",
        done_when=("done",),
        input_context_refs=(),
        output_schema={"summary": "string"},
        priority="normal",
        run_timeout_seconds=60,
        cleanup="keep",
        workspace_root=None,
        model_id=None,
    )


class SubAgentToolTenantIsolationTests(unittest.TestCase):
    def test_sessions_list_filters_by_context_tenant(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = RuntimeDB(root / "runtime.db")
            protocol = SubAgentProtocol(db)
            orchestrator = SubAgentOrchestrator(protocol)
            tools = builtin_subagent_tools(orchestrator=orchestrator, protocol=protocol)
            list_tool = next(t for t in tools if t.name == "sessions_list")

            protocol.spawn(
                task=_task("tenant-a", "a"),
                parent_session_id="s-a",
                parent_turn_id="t-a",
                parent_agent_id="p-a",
                child_agent_id="c-a",
            )
            protocol.spawn(
                task=_task("tenant-b", "b"),
                parent_session_id="s-b",
                parent_turn_id="t-b",
                parent_agent_id="p-b",
                child_agent_id="c-b",
            )

            context = ToolContext(
                tenant_id="tenant-a",
                session_id="session-test",
                turn_id="turn-test",
                user_id="user-test",
                workspace_root=root,
                db=db,
                guard_path=_guard(root),
            )
            payload = list_tool.execute({"limit": 50}, context)
            runs = payload.get("runs", [])
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["task_id"], "task-a")


if __name__ == "__main__":
    unittest.main()
