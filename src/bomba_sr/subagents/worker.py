from __future__ import annotations

import json

from bomba_sr.context.policy import TurnProfile
from bomba_sr.runtime.bridge import TurnRequest
from bomba_sr.subagents.orchestrator import SubAgentWorker


class SubAgentWorkerFactory:
    def __init__(self, bridge) -> None:  # bridge is RuntimeBridge; avoid import cycle in hints
        self.bridge = bridge

    def create_worker(self, max_iterations: int = 10) -> SubAgentWorker:
        _ = max_iterations

        def worker(run_id, task, protocol):
            protocol.progress(run_id, 10, summary="Sub-agent initializing")
            sub_session_id = f"subagent-{run_id}"
            result = self.bridge.handle_turn(
                TurnRequest(
                    tenant_id=task.tenant_id,
                    session_id=sub_session_id,
                    user_id=f"agent-{run_id[:8]}",
                    user_message=(
                        f"Goal: {task.goal}\n"
                        f"Done when: {json.dumps(list(task.done_when), ensure_ascii=True)}\n"
                        f"Context: {json.dumps(list(task.input_context_refs), ensure_ascii=True)}"
                    ),
                    model_id=task.model_id or None,
                    profile=TurnProfile.TASK_EXECUTION,
                    workspace_root=task.workspace_root,
                )
            )
            protocol.progress(run_id, 90, summary="Sub-agent completed work")
            protocol.write_shared_memory(
                run_id=run_id,
                writer_agent_id=f"agent-{run_id[:8]}",
                ticket_id=task.ticket_id,
                scope="proposal",
                confidence=0.8,
                content=result.get("assistant", {}).get("text", ""),
                source_refs=[task.task_id],
            )
            usage = result.get("assistant", {}).get("usage")
            if not isinstance(usage, dict):
                usage = {}
            return {
                "summary": str(result.get("assistant", {}).get("text", ""))[:500],
                "runtime_ms": int(result.get("assistant", {}).get("loop_iterations", 1)) * 1000,
                "token_usage": usage,
            }

        return worker
