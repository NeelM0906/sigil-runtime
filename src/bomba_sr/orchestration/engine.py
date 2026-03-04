"""Being-to-being orchestration engine.

SAI Prime acts as orchestrator: plans complex tasks, delegates sub-tasks
to beings, reviews outputs, requests revisions, and synthesizes final results.

All orchestration context lives in regular conversation_turns with
special session ID patterns — no new database tables.

Session ID patterns:
  orchestration:{task_id}    — Prime's coordination context
  subtask:{task_id}:{being_id} — each being's isolated work context
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Session ID helpers
# ---------------------------------------------------------------------------

def orchestration_session_id(task_id: str) -> str:
    return f"orchestration:{task_id}"


def subtask_session_id(parent_task_id: str, being_id: str) -> str:
    return f"subtask:{parent_task_id}:{being_id}"


# ---------------------------------------------------------------------------
# Orchestration statuses
# ---------------------------------------------------------------------------

STATUS_PLANNING = "planning"
STATUS_DELEGATING = "delegating"
STATUS_AWAITING = "awaiting_completion"
STATUS_REVIEWING = "reviewing"
STATUS_REVISING = "revising"
STATUS_SYNTHESIZING = "synthesizing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# ---------------------------------------------------------------------------
# Plan model
# ---------------------------------------------------------------------------

class SubTaskPlan:
    __slots__ = ("being_id", "title", "instructions", "done_when")

    def __init__(
        self,
        being_id: str,
        title: str,
        instructions: str,
        done_when: str = "",
    ):
        self.being_id = being_id
        self.title = title
        self.instructions = instructions
        self.done_when = done_when

    def to_dict(self) -> dict[str, str]:
        return {
            "being_id": self.being_id,
            "title": self.title,
            "instructions": self.instructions,
            "done_when": self.done_when,
        }


class OrchestrationPlan:
    __slots__ = ("summary", "sub_tasks", "synthesis_strategy")

    def __init__(
        self,
        summary: str,
        sub_tasks: list[SubTaskPlan],
        synthesis_strategy: str = "merge",
    ):
        self.summary = summary
        self.sub_tasks = sub_tasks
        self.synthesis_strategy = synthesis_strategy

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "sub_tasks": [st.to_dict() for st in self.sub_tasks],
            "synthesis_strategy": self.synthesis_strategy,
        }


# ---------------------------------------------------------------------------
# Orchestration Engine
# ---------------------------------------------------------------------------

PLAN_SYSTEM_PROMPT = """\
You are SAI Prime, the orchestrator of a team of specialized AI beings.
You must decompose a complex task into sub-tasks and assign each to the best-suited being.

Available beings:
{beings_json}

Respond with ONLY a JSON object (no markdown fences):
{{
  "summary": "Brief plan summary",
  "synthesis_strategy": "merge|sequential|compare",
  "sub_tasks": [
    {{
      "being_id": "the being's id",
      "title": "short sub-task title",
      "instructions": "detailed instructions for this being",
      "done_when": "acceptance criteria"
    }}
  ]
}}

Rules:
- Assign each sub-task to exactly one being based on their role and strengths.
- Each being should get at most one sub-task unless the task truly requires multiple from the same being.
- Instructions must be self-contained — the being has no access to the parent task context.
- Keep sub-tasks focused and achievable in a single turn.
"""

REVIEW_SYSTEM_PROMPT = """\
You are SAI Prime reviewing a being's output for a delegated sub-task.

Sub-task: {title}
Instructions given: {instructions}
Acceptance criteria: {done_when}

Being's output:
{output}

Evaluate:
1. Does the output satisfy the acceptance criteria?
2. Is the quality sufficient?
3. Are there factual errors or missing elements?

Respond with ONLY a JSON object (no markdown fences):
{{
  "approved": true/false,
  "feedback": "If not approved, specific revision instructions. If approved, empty string.",
  "quality_score": 0.0-1.0,
  "notes": "Brief assessment notes"
}}
"""

SYNTHESIS_SYSTEM_PROMPT = """\
You are SAI Prime synthesizing the outputs from your team of beings into a final deliverable.

Original task: {original_goal}

Plan summary: {plan_summary}

Sub-task outputs:
{subtask_outputs}

Synthesis strategy: {strategy}

Produce the final consolidated output. Attribute insights to the relevant beings where appropriate.
Do not mention internal orchestration mechanics — present a unified result to the user.
"""


class OrchestrationEngine:
    """Coordinates multi-being task execution via Prime."""

    def __init__(
        self,
        bridge: Any,
        dashboard_svc: Any,
        project_svc: Any,
        prime_tenant_id: str = "tenant-prime",
    ):
        self.bridge = bridge
        self.dashboard = dashboard_svc
        self.project_svc = project_svc
        self.prime_tenant_id = prime_tenant_id
        self._active: dict[str, dict[str, Any]] = {}  # task_id -> state
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        goal: str,
        requester_session_id: str,
        sender: str = "user",
    ) -> dict[str, Any]:
        """Kick off an orchestrated task. Returns immediately with task info.

        The actual orchestration runs in a background thread.
        """
        task_id = str(uuid.uuid4())
        orch_session = orchestration_session_id(task_id)

        # Create parent task on the board
        parent_task = self.dashboard.create_task(
            self.project_svc,
            title=goal[:120],
            description=goal,
            status="in_progress",
            priority="high",
            assignees=["prime"],
            owner_agent_id="prime",
        )
        actual_task_id = parent_task.get("id") or parent_task.get("task_id") or task_id

        state = {
            "task_id": actual_task_id,
            "goal": goal,
            "orchestration_session": orch_session,
            "requester_session": requester_session_id,
            "sender": sender,
            "status": STATUS_PLANNING,
            "plan": None,
            "subtask_ids": {},      # being_id -> subtask task_id
            "subtask_outputs": {},  # being_id -> output text
            "subtask_reviews": {},  # being_id -> review dict
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._active[actual_task_id] = state

        # Log orchestration start
        self.dashboard._log_task_history(
            actual_task_id, "orchestration_started",
            {"goal": goal, "session": orch_session},
        )
        self.dashboard._emit_event("orchestration_update", {
            "task_id": actual_task_id,
            "status": STATUS_PLANNING,
            "goal": goal,
        })

        # Run the full orchestration flow in background
        t = threading.Thread(
            target=self._orchestrate,
            args=(actual_task_id,),
            daemon=True,
            name=f"orch-{actual_task_id[:8]}",
        )
        t.start()

        return {
            "task_id": actual_task_id,
            "orchestration_session": orch_session,
            "status": STATUS_PLANNING,
        }

    def get_status(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            state = self._active.get(task_id)
            if state is None:
                return None
            return {
                "task_id": task_id,
                "status": state["status"],
                "plan": state["plan"].to_dict() if state["plan"] else None,
                "subtask_ids": dict(state["subtask_ids"]),
                "subtask_outputs": {k: v[:200] for k, v in state["subtask_outputs"].items()},
                "subtask_reviews": dict(state["subtask_reviews"]),
            }

    def get_orchestration_log(self, task_id: str) -> list[dict[str, Any]]:
        """Read the orchestration session's conversation turns."""
        with self._lock:
            state = self._active.get(task_id)
        if state is None:
            return []
        session = state["orchestration_session"]
        try:
            from bomba_sr.memory.hybrid import HybridMemoryStore
            runtime = self.bridge._tenant_runtime(self.prime_tenant_id)
            records = runtime.memory.get_recent_turn_records(
                tenant_id=self.prime_tenant_id,
                session_id=session,
                limit=100,
            )
            return records
        except Exception as exc:
            log.warning("Failed to read orchestration log: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Background orchestration flow
    # ------------------------------------------------------------------

    def _orchestrate(self, task_id: str) -> None:
        """Full orchestration lifecycle — runs in background thread."""
        try:
            self._phase_plan(task_id)
            self._phase_delegate(task_id)
            self._phase_review(task_id)
            self._phase_synthesize(task_id)
        except Exception as exc:
            log.exception("Orchestration failed for task %s", task_id)
            self._set_status(task_id, STATUS_FAILED)
            self.dashboard._log_task_history(
                task_id, "orchestration_failed", {"error": str(exc)},
            )
            self.dashboard._emit_event("orchestration_update", {
                "task_id": task_id, "status": STATUS_FAILED, "error": str(exc),
            })

    def _phase_plan(self, task_id: str) -> None:
        """Use LLM to decompose the task into sub-tasks."""
        state = self._get_state(task_id)
        goal = state["goal"]
        orch_session = state["orchestration_session"]

        # Gather available beings
        beings = self.dashboard.list_beings() if self.dashboard else []
        assignable = [
            {
                "id": b["id"],
                "name": b["name"],
                "role": b.get("role", ""),
                "status": b.get("status", "offline"),
                "skills": b.get("skills", ""),
            }
            for b in beings
            if b.get("status") != "offline" and b.get("id") != "prime"
        ]

        if not assignable:
            raise RuntimeError("No online beings available for delegation")

        plan_prompt = (
            f"Task to decompose:\n{goal}\n\n"
            f"Assign sub-tasks to the available beings. "
            f"Each being should receive clear, self-contained instructions."
        )

        # Call LLM via handle_turn in the orchestration session
        from bomba_sr.runtime.bridge import TurnRequest
        result = self.bridge.handle_turn(TurnRequest(
            tenant_id=self.prime_tenant_id,
            session_id=orch_session,
            user_id="orchestrator",
            user_message=(
                f"[SYSTEM: ORCHESTRATION MODE]\n"
                f"{PLAN_SYSTEM_PROMPT.format(beings_json=json.dumps(assignable, indent=2))}\n\n"
                f"{plan_prompt}"
            ),
            workspace_root=self._prime_workspace(),
        ))

        reply = (result.get("assistant") or {}).get("text", "")
        plan = self._parse_plan(reply, assignable)

        with self._lock:
            self._active[task_id]["plan"] = plan

        self.dashboard._log_task_history(
            task_id, "plan_created",
            {"summary": plan.summary, "sub_task_count": len(plan.sub_tasks)},
        )
        self.dashboard._emit_event("orchestration_update", {
            "task_id": task_id,
            "status": STATUS_PLANNING,
            "plan": plan.to_dict(),
        })
        log.info("Orchestration plan for %s: %d sub-tasks", task_id[:8], len(plan.sub_tasks))

    def _phase_delegate(self, task_id: str) -> None:
        """Send sub-tasks to beings and wait for all to complete."""
        self._set_status(task_id, STATUS_DELEGATING)
        state = self._get_state(task_id)
        plan = state["plan"]
        if plan is None:
            raise RuntimeError("No plan available for delegation")

        from bomba_sr.runtime.bridge import TurnRequest

        for sub in plan.sub_tasks:
            # Create child task on the board
            child_task = self.dashboard.create_task(
                self.project_svc,
                title=sub.title,
                description=sub.instructions,
                status="in_progress",
                priority="high",
                assignees=[sub.being_id],
                owner_agent_id=sub.being_id,
            )
            child_id = child_task.get("id") or child_task.get("task_id")

            # Store parent-child relationship in task history
            self.dashboard._log_task_history(
                task_id, "subtask_created",
                {"child_task_id": child_id, "being_id": sub.being_id, "title": sub.title},
            )
            self.dashboard._log_task_history(
                child_id, "delegated_from",
                {"parent_task_id": task_id, "being_id": sub.being_id},
            )

            with self._lock:
                self._active[task_id]["subtask_ids"][sub.being_id] = child_id

            # Update being status
            self.dashboard.update_being(sub.being_id, {"status": "busy"})
            self.dashboard._emit_event("being_status", {
                "being_id": sub.being_id,
                "status": "busy",
                "task_name": sub.title,
                "task_id": child_id,
            })

        # Now execute all sub-tasks (sequentially for now, could be parallelized)
        self._set_status(task_id, STATUS_AWAITING)
        threads: list[threading.Thread] = []
        for sub in plan.sub_tasks:
            t = threading.Thread(
                target=self._execute_subtask,
                args=(task_id, sub),
                daemon=True,
                name=f"subtask-{sub.being_id[:12]}",
            )
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join(timeout=300)  # 5 min per sub-task max

    def _execute_subtask(self, parent_task_id: str, sub: SubTaskPlan) -> None:
        """Execute a single sub-task by calling handle_turn for the being."""
        session = subtask_session_id(parent_task_id, sub.being_id)
        being = self.dashboard.get_being(sub.being_id) or {}
        tenant_id = being.get("tenant_id") or self.prime_tenant_id

        ws = being.get("workspace")
        if ws and ws != ".":
            from pathlib import Path
            workspace = str(Path("/Users/zidane/Downloads/PROJEKT") / ws)
        else:
            workspace = "/Users/zidane/Downloads/PROJEKT"

        delegation_message = (
            f"[DELEGATED TASK FROM SAI PRIME]\n\n"
            f"Task: {sub.title}\n\n"
            f"Instructions:\n{sub.instructions}\n\n"
            f"Acceptance criteria:\n{sub.done_when}\n\n"
            f"Complete this task to the best of your abilities. "
            f"Focus on quality and thoroughness."
        )

        try:
            from bomba_sr.runtime.bridge import TurnRequest
            result = self.bridge.handle_turn(TurnRequest(
                tenant_id=tenant_id,
                session_id=session,
                user_id=f"prime->{sub.being_id}",
                user_message=delegation_message,
                workspace_root=workspace,
            ))
            output = (result.get("assistant") or {}).get("text", "")
        except Exception as exc:
            output = f"[Error: {exc}]"
            log.exception("Subtask execution failed for being %s", sub.being_id)
        finally:
            # Restore being status
            self.dashboard.update_being(sub.being_id, {"status": "online"})
            self.dashboard._emit_event("being_status", {
                "being_id": sub.being_id, "status": "online",
            })

        with self._lock:
            self._active[parent_task_id]["subtask_outputs"][sub.being_id] = output

        # Log the delegation exchange
        child_id = self._active[parent_task_id]["subtask_ids"].get(sub.being_id)
        if child_id:
            self.dashboard._log_task_history(
                child_id, "being_responded",
                {"being_id": sub.being_id, "output_length": len(output)},
            )
        self.dashboard._emit_event("orchestration_update", {
            "task_id": parent_task_id,
            "event": "subtask_completed",
            "being_id": sub.being_id,
            "output_preview": output[:200],
        })

    def _phase_review(self, task_id: str) -> None:
        """Review each being's output. Request revisions if needed."""
        self._set_status(task_id, STATUS_REVIEWING)
        state = self._get_state(task_id)
        plan = state["plan"]
        if plan is None:
            return

        from bomba_sr.runtime.bridge import TurnRequest
        max_revisions = 2

        for sub in plan.sub_tasks:
            output = state["subtask_outputs"].get(sub.being_id, "")
            if not output or output.startswith("[Error"):
                with self._lock:
                    self._active[task_id]["subtask_reviews"][sub.being_id] = {
                        "approved": False,
                        "feedback": "Sub-task failed or produced no output.",
                        "quality_score": 0.0,
                    }
                continue

            for revision_round in range(max_revisions + 1):
                review_prompt = REVIEW_SYSTEM_PROMPT.format(
                    title=sub.title,
                    instructions=sub.instructions,
                    done_when=sub.done_when or "Complete the task as instructed",
                    output=output[:8000],
                )
                result = self.bridge.handle_turn(TurnRequest(
                    tenant_id=self.prime_tenant_id,
                    session_id=state["orchestration_session"],
                    user_id="orchestrator",
                    user_message=f"[REVIEW] Being: {sub.being_id}\n\n{review_prompt}",
                    workspace_root=self._prime_workspace(),
                ))
                reply = (result.get("assistant") or {}).get("text", "")
                review = self._parse_review(reply)

                if review["approved"] or revision_round >= max_revisions:
                    with self._lock:
                        self._active[task_id]["subtask_reviews"][sub.being_id] = review
                    child_id = state["subtask_ids"].get(sub.being_id)
                    if child_id:
                        final_status = "done" if review["approved"] else "in_review"
                        self.dashboard.update_task(
                            self.project_svc, child_id, status=final_status,
                        )
                        self.dashboard._log_task_history(
                            child_id, "review_completed",
                            {"approved": review["approved"], "quality_score": review.get("quality_score", 0)},
                        )
                    break

                # Request revision
                self._set_status(task_id, STATUS_REVISING)
                self.dashboard._log_task_history(
                    task_id, "revision_requested",
                    {"being_id": sub.being_id, "feedback": review["feedback"][:500]},
                )
                self.dashboard._emit_event("orchestration_update", {
                    "task_id": task_id,
                    "event": "revision_requested",
                    "being_id": sub.being_id,
                    "round": revision_round + 1,
                })

                # Send revision back to being in same subtask session
                session = subtask_session_id(task_id, sub.being_id)
                being = self.dashboard.get_being(sub.being_id) or {}
                tenant_id = being.get("tenant_id") or self.prime_tenant_id
                ws = being.get("workspace")
                if ws and ws != ".":
                    from pathlib import Path
                    workspace = str(Path("/Users/zidane/Downloads/PROJEKT") / ws)
                else:
                    workspace = "/Users/zidane/Downloads/PROJEKT"

                revision_msg = (
                    f"[REVISION REQUEST FROM SAI PRIME — Round {revision_round + 1}]\n\n"
                    f"Your previous output needs revision.\n\n"
                    f"Feedback:\n{review['feedback']}\n\n"
                    f"Please revise your output addressing the feedback above."
                )
                self.dashboard.update_being(sub.being_id, {"status": "busy"})
                try:
                    rev_result = self.bridge.handle_turn(TurnRequest(
                        tenant_id=tenant_id,
                        session_id=session,
                        user_id=f"prime->{sub.being_id}",
                        user_message=revision_msg,
                        workspace_root=workspace,
                    ))
                    output = (rev_result.get("assistant") or {}).get("text", "")
                    with self._lock:
                        self._active[task_id]["subtask_outputs"][sub.being_id] = output
                except Exception as exc:
                    log.warning("Revision failed for %s: %s", sub.being_id, exc)
                    output = state["subtask_outputs"].get(sub.being_id, "")
                finally:
                    self.dashboard.update_being(sub.being_id, {"status": "online"})

                self._set_status(task_id, STATUS_REVIEWING)

    def _phase_synthesize(self, task_id: str) -> None:
        """Combine all outputs into a final result and post to user chat."""
        self._set_status(task_id, STATUS_SYNTHESIZING)
        state = self._get_state(task_id)
        plan = state["plan"]
        if plan is None:
            return

        # Build sub-task outputs section
        output_parts = []
        for sub in plan.sub_tasks:
            output = state["subtask_outputs"].get(sub.being_id, "(no output)")
            review = state["subtask_reviews"].get(sub.being_id, {})
            output_parts.append(
                f"### {sub.title} (by {sub.being_id})\n"
                f"Quality: {review.get('quality_score', 'N/A')}\n"
                f"Approved: {review.get('approved', False)}\n\n"
                f"{output}\n"
            )

        synthesis_prompt = SYNTHESIS_SYSTEM_PROMPT.format(
            original_goal=state["goal"],
            plan_summary=plan.summary,
            subtask_outputs="\n---\n".join(output_parts),
            strategy=plan.synthesis_strategy,
        )

        from bomba_sr.runtime.bridge import TurnRequest
        result = self.bridge.handle_turn(TurnRequest(
            tenant_id=self.prime_tenant_id,
            session_id=state["orchestration_session"],
            user_id="orchestrator",
            user_message=f"[SYNTHESIZE]\n\n{synthesis_prompt}",
            workspace_root=self._prime_workspace(),
        ))
        final_output = (result.get("assistant") or {}).get("text", "")

        # Post final output back to user's chat
        self.dashboard.create_message(
            sender="prime",
            content=final_output,
            targets=[state["sender"]],
            msg_type="direct",
            task_ref=task_id,
        )

        # Mark parent task as done
        self.dashboard.update_task(self.project_svc, task_id, status="done")
        self._set_status(task_id, STATUS_COMPLETED)

        self.dashboard._log_task_history(
            task_id, "orchestration_completed",
            {"output_length": len(final_output), "sub_tasks_completed": len(state["subtask_outputs"])},
        )
        self.dashboard._emit_event("orchestration_update", {
            "task_id": task_id,
            "status": STATUS_COMPLETED,
            "output_preview": final_output[:300],
        })
        log.info("Orchestration completed for task %s", task_id[:8])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_state(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            state = self._active.get(task_id)
        if state is None:
            raise RuntimeError(f"No active orchestration for task {task_id}")
        return state

    def _set_status(self, task_id: str, status: str) -> None:
        with self._lock:
            if task_id in self._active:
                self._active[task_id]["status"] = status
        self.dashboard._emit_event("orchestration_update", {
            "task_id": task_id, "status": status,
        })

    def _prime_workspace(self) -> str:
        return "/Users/zidane/Downloads/PROJEKT/workspaces/prime"

    def _parse_plan(
        self,
        llm_reply: str,
        assignable_beings: list[dict],
    ) -> OrchestrationPlan:
        """Parse LLM plan response into OrchestrationPlan."""
        valid_ids = {b["id"] for b in assignable_beings}
        try:
            data = self._extract_json(llm_reply)
        except Exception:
            # Fallback: single sub-task to the first available being
            fallback_id = assignable_beings[0]["id"] if assignable_beings else "prime"
            return OrchestrationPlan(
                summary="Single-being fallback plan",
                sub_tasks=[SubTaskPlan(
                    being_id=fallback_id,
                    title="Complete the task",
                    instructions=llm_reply[:2000],
                    done_when="Task completed",
                )],
            )

        sub_tasks = []
        for st in data.get("sub_tasks", []):
            bid = st.get("being_id", "")
            if bid not in valid_ids:
                # Try to find closest match
                for vid in valid_ids:
                    if bid.lower() in vid.lower() or vid.lower() in bid.lower():
                        bid = vid
                        break
                else:
                    bid = assignable_beings[0]["id"]
            sub_tasks.append(SubTaskPlan(
                being_id=bid,
                title=st.get("title", "Sub-task"),
                instructions=st.get("instructions", ""),
                done_when=st.get("done_when", ""),
            ))

        if not sub_tasks:
            fallback_id = assignable_beings[0]["id"]
            sub_tasks = [SubTaskPlan(
                being_id=fallback_id,
                title="Complete the task",
                instructions="Complete the full task as described.",
                done_when="Task completed",
            )]

        return OrchestrationPlan(
            summary=data.get("summary", ""),
            sub_tasks=sub_tasks,
            synthesis_strategy=data.get("synthesis_strategy", "merge"),
        )

    def _parse_review(self, llm_reply: str) -> dict[str, Any]:
        """Parse LLM review response."""
        try:
            data = self._extract_json(llm_reply)
            return {
                "approved": bool(data.get("approved", False)),
                "feedback": str(data.get("feedback", "")),
                "quality_score": float(data.get("quality_score", 0.5)),
                "notes": str(data.get("notes", "")),
            }
        except Exception:
            return {
                "approved": True,
                "feedback": "",
                "quality_score": 0.6,
                "notes": "Review parsing failed — auto-approving",
            }

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract JSON from LLM response, handling markdown fences."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            start = 1
            end = len(lines)
            for i in range(1, len(lines)):
                if lines[i].strip() == "```":
                    end = i
                    break
            cleaned = "\n".join(lines[start:end])
        return json.loads(cleaned)
