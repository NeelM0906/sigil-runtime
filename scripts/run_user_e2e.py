#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from bomba_sr.context.policy import TurnProfile
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest
from bomba_sr.subagents.protocol import SubAgentTask


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run BOMBA runtime E2E user-flow demo")
    p.add_argument("--tenant-id", default="tenant-local")
    p.add_argument("--session-id", default=str(uuid.uuid4()))
    p.add_argument("--user-id", default="user-local")
    p.add_argument("--user-message", required=True, help="Simulated user message")
    p.add_argument("--workspace", default=".", help="Workspace directory")
    p.add_argument("--model-id", default=None, help="Optional model id override")
    p.add_argument(
        "--profile",
        default="task_execution",
        choices=[x.value for x in TurnProfile],
        help="Turn profile",
    )
    return p.parse_args()


def demo_worker(run_id: str, task: SubAgentTask, protocol) -> dict:
    protocol.progress(run_id, 35, summary="Gathered references")
    protocol.progress(run_id, 75, summary="Drafted result")
    write_id = protocol.write_shared_memory(
        run_id=run_id,
        writer_agent_id=str(uuid.uuid4()),
        ticket_id=task.ticket_id,
        scope="proposal",
        confidence=0.86,
        content=f"Sub-agent note: {task.goal}",
        source_refs=[task.task_id],
    )
    protocol.promote_shared_write(write_id, merged_by_agent_id=str(uuid.uuid4()))
    return {
        "summary": "sub-agent complete",
        "runtime_ms": 40,
        "token_usage": {"input": 120, "output": 60, "total": 180},
        "artifacts": {"status": "ok"},
    }


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        raise SystemExit(f"Workspace does not exist: {workspace}")

    bridge = RuntimeBridge()

    turn = bridge.handle_turn(
        TurnRequest(
            tenant_id=args.tenant_id,
            session_id=args.session_id,
            user_id=args.user_id,
            user_message=args.user_message,
            model_id=args.model_id,
            profile=TurnProfile(args.profile),
            workspace_root=str(workspace),
        )
    )

    task = SubAgentTask(
        tenant_id=args.tenant_id,
        task_id=str(uuid.uuid4()),
        ticket_id=str(uuid.uuid4()),
        idempotency_key=f"{turn['turn']['turn_id']}::demo-subagent",
        goal="Produce a concise summary of top search findings",
        done_when=("Summary ready", "Risks listed"),
        input_context_refs=(turn["turn"]["turn_id"],),
        output_schema={"summary": "string", "risks": "array"},
        priority="normal",
        run_timeout_seconds=120,
        cleanup="keep",
        workspace_root=str(workspace),
        model_id=args.model_id,
    )

    handle = bridge.spawn_subagent(
        tenant_id=args.tenant_id,
        task=task,
        parent_session_id=args.session_id,
        parent_turn_id=turn["turn"]["turn_id"],
        parent_agent_id=str(uuid.uuid4()),
        child_agent_id=str(uuid.uuid4()),
        worker=demo_worker,
        workspace_root=str(workspace),
    )

    handle.future.result(timeout=5)
    subagent_events = bridge.poll_subagent_events(args.tenant_id, handle.run_id, workspace_root=str(workspace))

    output = {
        "turn": turn,
        "subagent": {
            "run_id": handle.run_id,
            "events": subagent_events,
        },
        "artifacts": bridge.list_artifacts(args.tenant_id, args.session_id, workspace_root=str(workspace)),
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
