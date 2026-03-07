from __future__ import annotations

import json
import logging

from bomba_sr.context.policy import TurnProfile
from bomba_sr.runtime.bridge import TurnRequest
from bomba_sr.subagents.orchestrator import SubAgentWorker

logger = logging.getLogger(__name__)


class SubAgentWorkerFactory:
    def __init__(self, bridge) -> None:  # bridge is RuntimeBridge; avoid import cycle in hints
        self.bridge = bridge

    def create_worker(self, max_iterations: int = 10) -> SubAgentWorker:
        def worker(run_id: str, task, protocol) -> dict:
            # Resolve run metadata (parent/child agent IDs, workspace, etc.)
            run = protocol.get_run(run_id)
            if run is None:
                raise RuntimeError(f"run {run_id} not found in protocol")

            parent_agent_id = run.get("parent_agent_id", "unknown")
            child_agent_id = run.get("child_agent_id", "unknown")

            session_id = f"subagent:{run_id}:{child_agent_id}"
            user_id = f"{parent_agent_id}->{child_agent_id}"

            protocol.progress(run_id, 10, summary="Sub-agent initializing")

            try:
                result = self.bridge.handle_turn(
                    TurnRequest(
                        tenant_id=task.tenant_id,
                        session_id=session_id,
                        user_id=user_id,
                        user_message=task.goal,
                        model_id=task.model_id or None,
                        profile=TurnProfile.TASK_EXECUTION,
                        workspace_root=task.workspace_root,
                        max_loop_iterations=max(1, int(max_iterations)),
                    )
                )
            except Exception:
                logger.exception("Sub-agent worker failed for run %s", run_id)
                raise

            output_text = result.get("assistant", {}).get("text", "")

            protocol.progress(run_id, 90, summary="Sub-agent completed work")

            # Write output to shared memory as committed (final result)
            if output_text.strip():
                protocol.write_shared_memory(
                    run_id=run_id,
                    writer_agent_id=child_agent_id,
                    ticket_id=task.ticket_id,
                    scope="committed",
                    confidence=0.9,
                    content=output_text,
                    source_refs=[task.task_id],
                )

            usage = result.get("assistant", {}).get("usage")
            if not isinstance(usage, dict):
                usage = {}

            return {
                "summary": str(output_text)[:500],
                "artifacts": {"output": str(output_text)[:2000]} if output_text.strip() else None,
                "runtime_ms": int(result.get("assistant", {}).get("loop_iterations", 1)) * 1000,
                "token_usage": usage,
            }

        return worker
