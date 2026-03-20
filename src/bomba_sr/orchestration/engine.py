"""Being-to-being orchestration engine.

SAI Prime acts as orchestrator: plans complex tasks, delegates sub-tasks
to beings, reviews outputs, requests revisions, and synthesizes final results.

Orchestration state is persisted to SQLite (orchestration_state table) so
in-progress tasks survive server restarts.

Session ID patterns:
  orchestration:{task_id}    — Prime's coordination context
  subtask:{task_id}:{being_id} — each being's isolated work context
"""
from __future__ import annotations

import copy
import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bomba_sr.acti.loader import get_planning_context as get_acti_planning_context
from bomba_sr.subagents.orchestrator import SubAgentOrchestrator
from bomba_sr.subagents.protocol import SubAgentProtocol, SubAgentTask

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(
    os.environ.get("BOMBA_PROJECT_ROOT", str(Path(__file__).resolve().parents[3]))
)

_URL_RE = re.compile(r'https?://[^\s<>\'")\]]+')


def _build_message_metadata(
    content: str,
    subtasks: list[dict] | None = None,
    deliverable_files: list[str] | None = None,
) -> dict | None:
    """Build structured metadata (outputs + agents) for a dashboard message."""
    outputs: list[dict] = []
    agents: list[dict] = []

    # Extract links from content
    seen: set[str] = set()
    for url in _URL_RE.findall(content):
        url_clean = url.rstrip(".,;:!?")
        if url_clean not in seen:
            seen.add(url_clean)
            outputs.append({"type": "link", "title": url_clean[:80], "path": url_clean})

    # Deliverable files saved during orchestration
    for fp in (deliverable_files or []):
        ext = Path(fp).suffix.lstrip(".").lower()
        type_map = {"py": "code", "js": "code", "ts": "code", "md": "markdown",
                    "pdf": "pdf", "csv": "csv", "json": "json", "html": "html"}
        outputs.append({
            "type": type_map.get(ext, "file"),
            "title": Path(fp).name,
            "path": fp,
        })

    # Sub-tasks as agents
    for st in (subtasks or []):
        agents.append({
            "type": "sister",
            "agent_id": st.get("being_id"),
            "goal": st.get("title", ""),
            "status": st.get("status", "unknown"),
        })

    if not outputs and not agents:
        return None
    return {
        "outputs": outputs or None,
        "agents": agents or None,
    }

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
STATUS_REVIEWING = "reviewing"
STATUS_REVISING = "revising"
STATUS_SYNTHESIZING = "synthesizing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# ---------------------------------------------------------------------------
# Synthesis budget constants
# ---------------------------------------------------------------------------

# Reserve for system prompt, plan summary, and other overhead
SYNTHESIS_OVERHEAD_TOKENS = 40_000
# Reserve for the synthesis output itself
SYNTHESIS_OUTPUT_RESERVE = 16_000
# Default model max input (conservative — Claude Opus/Sonnet)
DEFAULT_MODEL_MAX_INPUT = 200_000
# Chars-per-token estimate (conservative)
CHARS_PER_TOKEN = 3.5
# Fallback summary word limit per being (stage A of two-stage fallback)
FALLBACK_SUMMARY_WORDS = 500

# Per-subtask execution timeout (seconds)
SUBTASK_TIMEOUT = int(os.environ.get("BOMBA_SUBTASK_TIMEOUT", "600"))


def _truncate_outputs_to_budget(
    outputs: dict[str, str],
    *,
    model_max_input: int = DEFAULT_MODEL_MAX_INPUT,
) -> dict[str, str]:
    """Truncate subtask outputs so they fit within the synthesis token budget.

    Budget = (model_max_input - overhead - output_reserve) / num_beings
    """
    if not outputs:
        return outputs
    available_tokens = model_max_input - SYNTHESIS_OVERHEAD_TOKENS - SYNTHESIS_OUTPUT_RESERVE
    per_being_tokens = max(available_tokens // len(outputs), 2000)
    per_being_chars = int(per_being_tokens * CHARS_PER_TOKEN)

    truncated: dict[str, str] = {}
    for being_id, text in outputs.items():
        if len(text) > per_being_chars:
            truncated[being_id] = text[:per_being_chars] + "\n\n[... output truncated to fit synthesis budget ...]"
        else:
            truncated[being_id] = text
    return truncated


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
    __slots__ = ("summary", "sub_tasks", "synthesis_strategy", "max_rounds")

    def __init__(
        self,
        summary: str,
        sub_tasks: list[SubTaskPlan],
        synthesis_strategy: str = "merge",
        max_rounds: int = 1,
    ):
        self.summary = summary
        self.sub_tasks = sub_tasks
        self.synthesis_strategy = synthesis_strategy
        self.max_rounds = min(max(max_rounds, 1), 4)  # clamp to [1, 4]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "sub_tasks": [st.to_dict() for st in self.sub_tasks],
            "synthesis_strategy": self.synthesis_strategy,
            "max_rounds": self.max_rounds,
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
  "synthesis_strategy": "merge|sequential|compare|critique",
  "max_rounds": 1,
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
- Beings with type "acti" are specialized ACT-I agents with domain expertise.
  Prefer assigning to the most specific ACT-I being when the task matches their domain.
  They run through their parent sister's runtime but have distinct capabilities.
- max_rounds (optional, 1-4): Number of collaboration rounds. Use 1 for straightforward tasks.
  Use 2-3 for tasks requiring beings to build on each other's work iteratively.
  Use 4 only for complex research synthesis.
- synthesis_strategy "critique": Each round after the first, every being sees all others' outputs
  and refines their own work. Best for tasks where cross-pollination improves quality.
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

REPRESENTATION_UPDATE_SYSTEM_PROMPT = """\
You are SAI Memory, the Central Memory Manager for the ACT-I ecosystem.
Your task is to update a being's REPRESENTATION.md profile based on new task data.

Being: {being_id}
Task completed: {goal}
This being's role in the task: {subtask_title}
Quality score: {quality_score}
Reviewer notes: {review_notes}
Synthesis summary (abbreviated): {synthesis_summary}

Current REPRESENTATION.md:
{current_representation}

Update the REPRESENTATION.md to reflect this new task data. Rules:
- Preserve the existing section structure exactly (Task History Summary, Performance Profile, Domain Expertise Map, Collaboration Profile, Evolution Log).
- Increment the task count.
- Add a one-line entry to Recent tasks.
- Update Strengths/Weaknesses/Most effective tool chains ONLY if the new data provides clear evidence.
- Add relevant topics to Domain Expertise Map if the task covered a new domain.
- Update Collaboration Profile if this being worked alongside others.
- Add a dated entry to the Evolution Log only for significant changes.
- Be concise. Do not invent data that is not supported by the task information provided.
- Return ONLY the updated markdown content — no fences, no explanation.
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
        subagent_orchestrator: SubAgentOrchestrator | None = None,
    ):
        self.bridge = bridge
        self.dashboard = dashboard_svc
        self.project_svc = project_svc
        # Resolve Prime's actual tenant from the being registry.
        # Falls back to the parameter default if Prime isn't registered yet.
        resolved = prime_tenant_id
        try:
            prime_being = dashboard_svc.get_being("prime") if dashboard_svc else None
            if prime_being and prime_being.get("tenant_id"):
                resolved = prime_being["tenant_id"]
                if resolved != prime_tenant_id:
                    log.info(
                        "Prime tenant resolved from registry: %s (overriding default %s)",
                        resolved, prime_tenant_id,
                    )
        except Exception:
            log.warning("Could not resolve Prime tenant from registry, using default: %s", prime_tenant_id)
        self.prime_tenant_id = resolved
        self._active: dict[str, dict[str, Any]] = {}  # task_id -> in-memory cache
        self._lock = threading.Lock()
        self._completed_task_count: int = 0
        self._dream_trigger_every: int = int(os.environ.get("BOMBA_DREAM_TRIGGER_EVERY", "5"))
        self.subagent_orch: SubAgentOrchestrator | None = None
        self.protocol: SubAgentProtocol | None = None
        self._orchestration_worker = None
        self._ensure_task_results_schema()
        self._ensure_orchestration_state_schema()
        self.cleanup_orphaned_orchestrations()

        # SubAgent protocol integration — passed in or auto-resolved from bridge
        if subagent_orchestrator is not None:
            self.subagent_orch = subagent_orchestrator
            self.protocol = subagent_orchestrator.protocol
            # Create a dashboard-aware worker for orchestration spawns
            from bomba_sr.subagents.worker import SubAgentWorkerFactory
            self._orchestration_worker = SubAgentWorkerFactory(
                self.bridge, dashboard_svc=self.dashboard,
            ).create_worker()
        else:
            try:
                runtime = self.bridge._tenant_runtime(
                    self.prime_tenant_id, self._prime_workspace(),
                )
                orch = getattr(runtime, "orchestrator", None)
                proto = getattr(runtime, "protocol", None)
                if isinstance(orch, SubAgentOrchestrator) and isinstance(proto, SubAgentProtocol):
                    self.subagent_orch = orch
                    self.protocol = proto
                    from bomba_sr.subagents.worker import SubAgentWorkerFactory
                    self._orchestration_worker = SubAgentWorkerFactory(
                        self.bridge, dashboard_svc=self.dashboard,
                    ).create_worker()
                else:
                    self.subagent_orch = None
                    self.protocol = None
                    self._orchestration_worker = None
            except Exception:
                log.debug("SubAgentOrchestrator not available — orchestration will use legacy path")
                self.subagent_orch = None
                self.protocol = None
                self._orchestration_worker = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        goal: str,
        requester_session_id: str,
        sender: str = "user",
        chat_session_id: str = "general",
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

        now = datetime.now(timezone.utc).isoformat()
        state = {
            "task_id": actual_task_id,
            "goal": goal,
            "orchestration_session": orch_session,
            "requester_session": requester_session_id,
            "sender": sender,
            "chat_session_id": chat_session_id,
            "status": STATUS_PLANNING,
            "plan": None,
            "subtask_ids": {},      # being_id -> subtask task_id
            "subtask_outputs": {},  # being_id -> output text
            "subtask_reviews": {},  # being_id -> review dict
            "created_at": now,
        }
        with self._lock:
            self._active[actual_task_id] = state

        # Persist to SQLite — source of truth for crash recovery
        self._db_insert_state(actual_task_id, state, now)

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
            if state is not None:
                # Snapshot fields under lock to avoid TOCTOU on mutable state
                plan = state["plan"]
                return {
                    "task_id": task_id,
                    "status": state["status"],
                    "plan": plan.to_dict() if plan else None,
                    "subtask_ids": dict(state.get("subtask_ids", {})),
                    "subtask_outputs": {k: v[:200] for k, v in state.get("subtask_outputs", {}).items()},
                    "subtask_reviews": dict(state.get("subtask_reviews", {})),
                }
        # Fallback to DB (immutable snapshot, no lock needed)
        state = self._db_load_state(task_id)
        if state is None:
            return None
        return {
            "task_id": task_id,
            "status": state["status"],
            "plan": state["plan"].to_dict() if state["plan"] else None,
            "subtask_ids": dict(state.get("subtask_ids", {})),
            "subtask_outputs": {k: v[:200] for k, v in state.get("subtask_outputs", {}).items()},
            "subtask_reviews": dict(state.get("subtask_reviews", {})),
        }

    def get_orchestration_log(self, task_id: str) -> list[dict[str, Any]]:
        """Read the orchestration session's conversation turns."""
        try:
            state = self._get_state(task_id)
        except RuntimeError:
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

            state = self._get_state(task_id)
            plan = state["plan"]
            max_rounds = plan.max_rounds if plan else 1

            for round_number in range(1, max_rounds + 1):
                if round_number == 1:
                    self._phase_delegate(task_id)
                else:
                    self._phase_delegate_iteration(task_id, round_number)

                # Fire representation + TEAM_CONTEXT updates after delegation
                state = self._get_state(task_id)
                self._update_team_context_outcomes(task_id, state)
                self._update_being_representations(task_id, state, "")

                self._phase_review(task_id)

                # Early stop if all reviews approved and more rounds remain
                if round_number < max_rounds:
                    if self._all_reviews_approved(task_id):
                        log.info(
                            "All reviews approved after round %d — skipping remaining rounds",
                            round_number,
                        )
                        break
                    else:
                        log.info(
                            "Round %d reviews mixed — proceeding to round %d",
                            round_number, round_number + 1,
                        )

            self._phase_synthesize(task_id)
        except Exception as exc:
            log.exception("Orchestration failed for task %s", task_id)
            self._set_status(task_id, STATUS_FAILED)

            # Cascade-stop any still-running subagent runs for this orchestration
            if self.protocol is not None:
                try:
                    orch_session = orchestration_session_id(task_id)
                    stopped = self.protocol.cascade_stop_session(
                        tenant_id=self.prime_tenant_id,
                        session_id=orch_session,
                        reason=f"orchestration failed: {exc}",
                    )
                    if stopped:
                        log.info("Cascade-stopped %d subagent runs for task %s", len(stopped), task_id[:8])
                except Exception as cs_exc:
                    log.warning("cascade_stop_session failed for task %s: %s", task_id[:8], cs_exc)

            # Persist partial results even on failure
            try:
                fail_state = self._get_state(task_id)
                self._persist_task_result(task_id, fail_state, f"[FAILED: {exc}]")
            except Exception:
                pass

            # Mark task as failed on the board
            try:
                self.dashboard.update_task(self.project_svc, task_id, status="failed")
            except Exception:
                pass

            self.dashboard._log_task_history(
                task_id, "orchestration_failed", {"error": str(exc)},
            )
            self.dashboard._emit_event("orchestration_update", {
                "task_id": task_id, "status": STATUS_FAILED, "error": str(exc),
            })

            # Notify the user so they don't wait forever
            try:
                fail_state = self._get_state(task_id)
                self.dashboard.create_message(
                    sender="prime",
                    content=(
                        f"Orchestration failed for task: {fail_state.get('goal', task_id)[:100]}\n\n"
                        f"Error: {str(exc)[:300]}\n\n"
                        f"Sub-task outputs were saved. You can retry or review partial results."
                    ),
                    targets=[fail_state.get("sender", "user")],
                    msg_type="direct",
                    session_id=fail_state.get("chat_session_id", "general"),
                    task_ref=task_id,
                )
            except Exception:
                pass
        finally:
            # Always restore Prime status — success or failure
            try:
                self.dashboard.update_being("prime", {"status": "online"})
            except Exception:
                log.warning("Failed to restore Prime status to online")

    def _phase_plan(self, task_id: str) -> None:
        """Use LLM to decompose the task into sub-tasks."""
        state = self._get_state(task_id)
        goal = state["goal"]
        orch_session = state["orchestration_session"]

        # Gather available beings
        beings = self.dashboard.list_beings() if self.dashboard else []
        assignable = []
        for b in beings:
            if b.get("status") == "offline" or b.get("id") == "prime":
                continue
            entry = {
                "id": b["id"],
                "name": b["name"],
                "role": b.get("role", ""),
                "status": b.get("status", "offline"),
                "skills": b.get("skills", ""),
            }
            # Enrich ACT-I beings with domain + cluster info
            if b.get("type") == "acti":
                entry["type"] = "acti"
                entry["parent_sister"] = b.get("tenant_id", "").replace("tenant-", "")
                try:
                    from bomba_sr.acti.loader import load_beings as _lb
                    acti_match = next((ab for ab in _lb() if ab["id"] == b["id"]), None)
                    if acti_match:
                        entry["domain"] = acti_match.get("domain", "")
                        entry["top_clusters"] = [c["name"] for c in acti_match.get("clusters", [])[:3]]
                except Exception:
                    pass
            # Enrich with representation data (truncated to 800 chars)
            ws = b.get("workspace")
            if ws and ws != ".":
                ws_path = Path(ws) if Path(ws).is_absolute() else _PROJECT_ROOT / ws
                rep_path = ws_path / "REPRESENTATION.md"
                if rep_path.exists():
                    try:
                        entry["representation"] = rep_path.read_text(encoding="utf-8")[:800]
                    except OSError:
                        pass
            assignable.append(entry)

        if not assignable:
            raise RuntimeError("No online beings available for delegation")

        acti_context = ""
        try:
            acti_context = get_acti_planning_context()
        except Exception:
            pass
        plan_prompt = (
            f"Task to decompose:\n{goal}\n\n"
            f"Assign sub-tasks to the available beings. "
            f"Each being should receive clear, self-contained instructions."
        )
        if acti_context:
            plan_prompt += (
                f"\n\n{acti_context}\n"
                f"Use the ACT-I architecture above to inform your delegation decisions. "
                f"Match tasks to the sister whose mapped beings best cover the required "
                f"skill clusters and levers."
            )

        # Call LLM via handle_turn in the orchestration session.
        # disable_tools=True prevents the LLM from calling code search
        # tools (which would pass this prompt to ripgrep and fail).
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
            disable_tools=True,
            include_representation=True,
        ))

        reply = (result.get("assistant") or {}).get("text", "")
        plan = self._parse_plan(reply, assignable)

        with self._lock:
            self._active[task_id]["plan"] = plan
        self._db_update_plan(task_id, plan)

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
        """Spawn sub-tasks via SubAgentProtocol and wait for all to complete."""
        self._set_status(task_id, STATUS_DELEGATING)
        state = self._get_state(task_id)
        plan = state["plan"]
        if plan is None:
            raise RuntimeError("No plan available for delegation")

        for sub in plan.sub_tasks:
            # Track sub-tasks internally — no separate board entries.
            self.dashboard._log_task_history(
                task_id, "subtask_created",
                {"being_id": sub.being_id, "title": sub.title},
            )

        if plan.synthesis_strategy == "sequential":
            # Sequential: spawn one at a time, wait for completion, collect output
            for sub in plan.sub_tasks:
                prior_outputs = self._collect_prior_outputs_from_shared_memory(
                    task_id, plan, sub.being_id,
                )
                run_id = self._execute_subtask(task_id, sub, prior_outputs=prior_outputs)
                run = self._await_run_completion(run_id, timeout=SUBTASK_TIMEOUT)
                self._on_subtask_completed(task_id, sub, run)
        else:
            # Parallel: spawn all, then await all
            run_ids: list[tuple[SubTaskPlan, str]] = []
            for sub in plan.sub_tasks:
                run_id = self._execute_subtask(task_id, sub)
                run_ids.append((sub, run_id))

            for sub, run_id in run_ids:
                run = self._await_run_completion(run_id, timeout=SUBTASK_TIMEOUT)
                self._on_subtask_completed(task_id, sub, run)

        # Persist subtask_ids to DB for crash recovery
        with self._lock:
            ids_snapshot = dict(self._active[task_id]["subtask_ids"])
        self._db_update_subtask_ids(task_id, ids_snapshot)

    def _phase_delegate_iteration(self, task_id: str, round_number: int) -> None:
        """Delegate a subsequent round where each being sees all prior outputs."""
        self._set_status(task_id, f"delegating_round_{round_number}")
        state = self._get_state(task_id)
        plan = state["plan"]
        if plan is None:
            raise RuntimeError("No plan available for iteration delegation")

        # Read all committed outputs from prior rounds
        all_outputs = self._read_all_committed_outputs(task_id)

        if plan.synthesis_strategy == "critique":
            # Critique: every being sees every other being's work
            run_ids: list[tuple[SubTaskPlan, str]] = []
            for sub in plan.sub_tasks:
                message = self._build_critique_round_message(sub, round_number, all_outputs)
                run_id = self._execute_subtask_with_message(
                    task_id, sub, message,
                    idempotency_suffix=f":round:{round_number}",
                )
                run_ids.append((sub, run_id))

            for sub, run_id in run_ids:
                run = self._await_run_completion(run_id, timeout=SUBTASK_TIMEOUT)
                self._on_subtask_completed(task_id, sub, run)

        elif plan.synthesis_strategy == "sequential":
            for sub in plan.sub_tasks:
                prior = self._collect_prior_outputs_from_shared_memory(
                    task_id, plan, sub.being_id,
                )
                message = self._build_iteration_message(sub, round_number, prior)
                run_id = self._execute_subtask_with_message(
                    task_id, sub, message,
                    idempotency_suffix=f":round:{round_number}",
                )
                run = self._await_run_completion(run_id, timeout=SUBTASK_TIMEOUT)
                self._on_subtask_completed(task_id, sub, run)
        else:
            # Parallel merge/compare: each being gets all outputs
            run_ids = []
            for sub in plan.sub_tasks:
                message = self._build_iteration_message(sub, round_number, all_outputs)
                run_id = self._execute_subtask_with_message(
                    task_id, sub, message,
                    idempotency_suffix=f":round:{round_number}",
                )
                run_ids.append((sub, run_id))

            for sub, run_id in run_ids:
                run = self._await_run_completion(run_id, timeout=SUBTASK_TIMEOUT)
                self._on_subtask_completed(task_id, sub, run)

        # Persist subtask_ids
        with self._lock:
            ids_snapshot = dict(self._active[task_id]["subtask_ids"])
        self._db_update_subtask_ids(task_id, ids_snapshot)

        log.info("Iteration round %d completed for %s", round_number, task_id[:8])

    def _read_all_committed_outputs(self, task_id: str) -> dict[str, str]:
        """Read all committed outputs from shared memory, newest per agent."""
        if self.protocol is None:
            return {}
        writes = self.protocol.read_shared_memory(
            ticket_id=task_id, scope="committed",
        )
        # Newest first — first write per agent wins
        outputs: dict[str, str] = {}
        for w in writes:
            agent = w["writer_agent_id"]
            if agent not in outputs:
                outputs[agent] = w["content"]
        return outputs

    def _execute_subtask_with_message(
        self,
        parent_task_id: str,
        sub: SubTaskPlan,
        message: str,
        idempotency_suffix: str = "",
    ) -> str:
        """Spawn a subtask with a custom message. Used for iteration rounds."""
        if self.subagent_orch is None:
            raise RuntimeError("SubAgentOrchestrator not available — cannot execute subtask")

        state = self._get_state(parent_task_id)
        being = self.dashboard.get_being(sub.being_id) or {}
        tenant_id = being.get("tenant_id") or f"tenant-{sub.being_id}"

        ws = being.get("workspace")
        if ws and ws != ".":
            workspace = str(_PROJECT_ROOT / ws)
        else:
            workspace = str(_PROJECT_ROOT)

        task = SubAgentTask(
            tenant_id=tenant_id,
            task_id=sub.being_id,
            ticket_id=parent_task_id,
            idempotency_key=f"{parent_task_id}:{sub.being_id}{idempotency_suffix}",
            goal=message,
            done_when=tuple(
                [sub.done_when] if sub.done_when else ["Complete the task as instructed"]
            ),
            input_context_refs=(),
            output_schema={},
            priority="high",
            run_timeout_seconds=SUBTASK_TIMEOUT,
            cleanup="archive",
            workspace_root=workspace,
        )

        orch_session = state["orchestration_session"]
        handle = self.subagent_orch.spawn_async(
            task=task,
            parent_session_id=orch_session,
            parent_turn_id=f"orch-{parent_task_id}-{sub.being_id}{idempotency_suffix}",
            parent_agent_id="prime",
            child_agent_id=sub.being_id,
            worker=self._orchestration_worker,
        )

        run_id = handle.run_id
        with self._lock:
            self._active[parent_task_id]["subtask_ids"][sub.being_id] = run_id

        return run_id

    def _build_critique_round_message(
        self,
        sub: SubTaskPlan,
        round_number: int,
        all_prior_outputs: dict[str, str],
    ) -> str:
        """Build delegation message for a critique round (N > 1)."""
        sections = [f"This is Round {round_number} of a collaborative task."]
        sections.append(f"\nYour original task: {sub.instructions}")
        sections.append("\nHere is what all beings produced in the previous round:")

        for being_id, output in all_prior_outputs.items():
            label = "YOUR PREVIOUS OUTPUT" if being_id == sub.being_id else f"{being_id}'s output"
            sections.append(f"\n--- {label} ---\n{output[:4000]}")

        sections.append("\nINSTRUCTIONS FOR THIS ROUND:")
        sections.append("1. Review all outputs from the previous round")
        sections.append("2. Identify gaps, contradictions, or areas that need deeper work")
        sections.append("3. Produce an improved version of YOUR contribution that addresses these issues")
        sections.append("4. Build on insights from other beings' work where relevant")

        return "\n".join(sections)

    def _build_iteration_message(
        self,
        sub: SubTaskPlan,
        round_number: int,
        prior_outputs: dict[str, str],
    ) -> str:
        """Build delegation message for a non-critique iteration round."""
        sections = [f"This is Round {round_number} of an iterative task."]
        sections.append(f"\nYour task: {sub.instructions}")

        if prior_outputs:
            sections.append("\nContext from previous round:")
            for being_id, output in prior_outputs.items():
                label = "Your previous output" if being_id == sub.being_id else f"{being_id}'s output"
                sections.append(f"\n--- {label} ---\n{output[:4000]}")

        sections.append(
            f"\nProduce an improved version building on the previous round's work. "
            f"Acceptance criteria: {sub.done_when or 'Complete the task as instructed'}"
        )

        return "\n".join(sections)

    def _all_reviews_approved(self, task_id: str) -> bool:
        """Check if all beings' reviews from the current round are approved."""
        state = self._get_state(task_id)
        reviews = state.get("subtask_reviews", {})
        if not reviews:
            return False
        return all(r.get("approved", False) for r in reviews.values())

    def _await_run_completion(
        self, run_id: str, timeout: int = 300,
    ) -> dict[str, Any] | None:
        """Poll subagent_runs until status is terminal or timeout."""
        if self.protocol is None:
            return None
        deadline = time.time() + timeout
        while time.time() < deadline:
            run = self.protocol.get_run(run_id)
            if run and run["status"] in ("completed", "failed", "timed_out"):
                return run
            time.sleep(2)

        # Timeout — cascade stop the run
        log.warning("Subagent run %s timed out after %ds", run_id, timeout)
        try:
            self.protocol.cascade_stop(run_id, reason="orchestration timeout")
        except Exception as exc:
            log.warning("Failed to cascade stop %s: %s", run_id, exc)
        return self.protocol.get_run(run_id)

    def _build_delegation_message(
        self,
        sub: SubTaskPlan,
        prior_outputs: dict[str, str] | None = None,
    ) -> str:
        """Build the delegation message for a subtask (ACT-I identity, context, instructions)."""
        being = self.dashboard.get_being(sub.being_id) or {}

        # Build ACT-I identity prefix for specialized beings
        acti_identity_prefix = ""
        if being.get("type") == "acti":
            try:
                from bomba_sr.acti.loader import get_being_identity_text
                identity_text = get_being_identity_text(sub.being_id)
                if identity_text:
                    acti_identity_prefix = (
                        f"[IDENTITY CONTEXT]\n"
                        f"You are operating as an ACT-I specialized being.\n"
                        f"{identity_text}\n"
                        f"[END IDENTITY CONTEXT]\n\n"
                    )
            except Exception:
                pass

        # Build context section from prior beings' outputs
        context_section = ""
        if prior_outputs:
            parts = []
            for bid, output in prior_outputs.items():
                parts.append(f"--- {bid}'s findings ---\n{output}")
            context_section = (
                f"\nCONTEXT FROM OTHER BEINGS:\n"
                + "\n\n".join(parts)
                + "\n\n"
            )

        return (
            acti_identity_prefix
            + f"You have been assigned a sub-task by SAI Prime.\n\n"
            f"TASK TITLE: {sub.title}\n\n"
            + (context_section if context_section else "")
            + f"INSTRUCTIONS:\n{sub.instructions}\n\n"
            f"ACCEPTANCE CRITERIA:\n{sub.done_when}\n\n"
            f"Complete this task using your available tools and skills. "
            f"When finished, provide your results as a clear response.\n\n"
            f"After completing your work, update your KNOWLEDGE.md with any "
            f"significant findings using the update_knowledge tool."
        )

    def _execute_subtask(
        self,
        parent_task_id: str,
        sub: SubTaskPlan,
        prior_outputs: dict[str, str] | None = None,
    ) -> str:
        """Spawn a subtask via SubAgentProtocol. Returns run_id."""
        if self.subagent_orch is None:
            raise RuntimeError("SubAgentOrchestrator not available — cannot execute subtask")

        state = self._get_state(parent_task_id)
        being = self.dashboard.get_being(sub.being_id) or {}
        tenant_id = being.get("tenant_id") or f"tenant-{sub.being_id}"

        ws = being.get("workspace")
        if ws and ws != ".":
            workspace = str(_PROJECT_ROOT / ws)
        else:
            workspace = str(_PROJECT_ROOT)

        delegation_message = self._build_delegation_message(sub, prior_outputs)

        # ── Log Point A: Prime sends delegation ──
        log.debug("[ORCH] ── Log Point A: Delegating to %s via SubAgentProtocol ──", sub.being_id)
        log.debug("[ORCH] Tenant: %s, Workspace: %s", tenant_id, workspace)
        log.debug("[ORCH] Message (first 300 chars): %s", delegation_message[:300])

        # Notify chat that this being is starting
        try:
            self.dashboard.create_message(
                sender=sub.being_id,
                content=f"Starting work on: **{sub.title}**",
                targets=[state.get("sender", "user")],
                msg_type="direct",
                task_ref=parent_task_id,
                session_id=state.get("chat_session_id", "general"),
            )
        except Exception:
            pass

        # Emit spawn event for live tracker
        try:
            _session_id = state.get("chat_session_id", "general")
            _session_name = self._resolve_session_name(_session_id)
            log.info("[ORCH-TRACKER] Emitting orchestration_spawn SPAWNING for %s (session=%s)", sub.being_id, _session_id)
            self.dashboard._emit_event("orchestration_spawn", {
                "task_id": parent_task_id,
                "being_id": sub.being_id,
                "being_name": being.get("name", sub.being_id),
                "being_type": being.get("type", "unknown"),
                "being_avatar": being.get("avatar", "?"),
                "being_color": being.get("color", "#666"),
                "title": sub.title,
                "status": "spawning",
                "goal": state.get("goal", "")[:100],
                "session_id": _session_id,
                "session_name": _session_name,
            })
        except Exception as exc:
            log.warning("[ORCH-TRACKER] Failed to emit spawn event: %s", exc)

        task = SubAgentTask(
            tenant_id=tenant_id,
            task_id=sub.being_id,
            ticket_id=parent_task_id,
            idempotency_key=f"{parent_task_id}:{sub.being_id}",
            goal=delegation_message,
            done_when=tuple(
                [sub.done_when] if sub.done_when else ["Complete the task as instructed"]
            ),
            input_context_refs=(),
            output_schema={},
            priority="high",
            run_timeout_seconds=SUBTASK_TIMEOUT,
            cleanup="archive",
            workspace_root=workspace,
        )

        orch_session = state["orchestration_session"]
        handle = self.subagent_orch.spawn_async(
            task=task,
            parent_session_id=orch_session,
            parent_turn_id=f"orch-{parent_task_id}-{sub.being_id}",
            parent_agent_id="prime",
            child_agent_id=sub.being_id,
            worker=self._orchestration_worker,
        )

        run_id = handle.run_id
        with self._lock:
            self._active[parent_task_id]["subtask_ids"][sub.being_id] = run_id

        return run_id

    def _on_subtask_completed(
        self,
        parent_task_id: str,
        sub: SubTaskPlan,
        run: dict[str, Any] | None,
    ) -> None:
        """Handle post-completion for a subtask: restore status, populate state, write memory, log."""
        being = self.dashboard.get_being(sub.being_id) or {}
        tenant_id = being.get("tenant_id") or f"tenant-{sub.being_id}"

        # Read output from shared working memory
        output = ""
        if run and run.get("status") == "completed" and self.protocol is not None:
            writes = self.protocol.read_shared_memory(
                ticket_id=parent_task_id, scope="committed",
            )
            being_writes = [w for w in writes if w["writer_agent_id"] == sub.being_id]
            if being_writes:
                output = being_writes[0]["content"]
            elif run.get("artifacts") and isinstance(run["artifacts"], dict):
                output = run["artifacts"].get("output", "")
        elif run:
            output = f"[Error: {run.get('error_detail', 'unknown error')}]"

        # ── Log Point E: Result returns to orchestration engine ──
        log.debug("[ORCH] ── Log Point E: Result from %s ──", sub.being_id)
        log.debug("[ORCH] Received from %s: status=%s, output_len=%d",
                  sub.being_id, run.get("status") if run else "none", len(output))

        # Being status (busy → online) is managed by the worker's finally block.
        state = self._get_state(parent_task_id)

        # Emit completion event for live tracker
        try:
            is_error = not output or output.startswith("[Error")
            _session_id = state.get("chat_session_id", "general")
            _session_name = self._resolve_session_name(_session_id)
            log.info("[ORCH-TRACKER] Emitting orchestration_spawn %s for %s",
                     "FAILED" if is_error else "COMPLETED", sub.being_id)
            self.dashboard._emit_event("orchestration_spawn", {
                "task_id": parent_task_id,
                "being_id": sub.being_id,
                "being_name": being.get("name", sub.being_id),
                "being_type": being.get("type", "unknown"),
                "being_avatar": being.get("avatar", "?"),
                "being_color": being.get("color", "#666"),
                "title": sub.title,
                "status": "failed" if is_error else "completed",
                "output_preview": (output or "")[:200],
                "session_id": _session_id,
                "session_name": _session_name,
            })
        except Exception as exc:
            log.warning("[ORCH-TRACKER] Failed to emit completion event: %s", exc)

        # Populate state["subtask_outputs"] for _phase_review backward compat
        with self._lock:
            self._active[parent_task_id]["subtask_outputs"][sub.being_id] = output

        # Extract deliverables from subtask output and notify chat
        try:
            _cs = state.get("chat_session_id", "general")
            if output and not output.startswith("[Error"):
                # Extract code blocks into deliverable files
                cleaned_output, _ = self._extract_and_save_deliverables(
                    parent_task_id, output, being_id=sub.being_id,
                )
                # Also detect file paths mentioned in output (tool-written files)
                self._register_mentioned_files(
                    parent_task_id, output, being_id=sub.being_id,
                )
                preview = cleaned_output[:1500] + ("..." if len(cleaned_output) > 1500 else "")
                _completion_content = f"Completed: **{sub.title}**\n\n{preview}"
                self.dashboard.create_message(
                    sender=sub.being_id,
                    content=_completion_content,
                    targets=[state.get("sender", "user")],
                    msg_type="direct",
                    task_ref=parent_task_id,
                    session_id=_cs,
                    metadata=_build_message_metadata(_completion_content),
                )
            else:
                self.dashboard.create_message(
                    sender=sub.being_id,
                    content=f"Failed on: **{sub.title}**\n\n{output[:500] if output else 'No output'}",
                    targets=[state.get("sender", "user")],
                    msg_type="direct",
                    task_ref=parent_task_id,
                    session_id=_cs,
                )
        except Exception:
            pass

        # Write semantic memory into the being's tenant
        if output and not output.startswith("[Error"):
            try:
                being_runtime = self.bridge._tenant_runtime(tenant_id)
                being_runtime.memory.learn_semantic(
                    tenant_id=tenant_id,
                    user_id=f"prime->{sub.being_id}",
                    memory_key=f"task_work::{parent_task_id}::{sub.being_id}",
                    content=(
                        f"Task: '{sub.title}'. "
                        f"My findings: {output[:800]}"
                    ),
                    confidence=0.8,
                    being_id=sub.being_id,
                )
            except Exception as exc:
                log.warning(
                    "Failed to write being memory for %s: %s",
                    sub.being_id, exc,
                )

        # Log the delegation exchange
        self.dashboard._log_task_history(
            parent_task_id, "being_responded",
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
                fail_review = {
                    "approved": False,
                    "feedback": "Sub-task failed or produced no output.",
                    "quality_score": 0.0,
                }
                with self._lock:
                    self._active[task_id]["subtask_reviews"][sub.being_id] = fail_review
                self._db_merge_subtask_review(task_id, sub.being_id, fail_review)
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
                    disable_tools=True,
                ))
                reply = (result.get("assistant") or {}).get("text", "")
                review = self._parse_review(reply)

                if review["approved"] or revision_round >= max_revisions:
                    with self._lock:
                        self._active[task_id]["subtask_reviews"][sub.being_id] = review
                    self._db_merge_subtask_review(task_id, sub.being_id, review)
                    self.dashboard._log_task_history(
                        task_id, "review_completed",
                        {"being_id": sub.being_id, "approved": review["approved"], "quality_score": review.get("quality_score", 0)},
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

                # Route revision through SubAgentProtocol for DB-backed state,
                # crash detection, and idempotency.
                being = self.dashboard.get_being(sub.being_id) or {}
                tenant_id = being.get("tenant_id") or self.prime_tenant_id
                ws = being.get("workspace")
                if ws and ws != ".":
                    workspace = str(_PROJECT_ROOT / ws)
                else:
                    workspace = str(_PROJECT_ROOT)

                revision_msg = (
                    f"[REVISION REQUEST FROM SAI PRIME — Round {revision_round + 1}]\n\n"
                    f"Your previous output needs revision.\n\n"
                    f"Feedback:\n{review['feedback']}\n\n"
                    f"Please revise your output addressing the feedback above."
                )

                if self.subagent_orch is not None:
                    # Spawn revision as a tracked subagent run
                    rev_task = SubAgentTask(
                        tenant_id=tenant_id,
                        task_id=f"{sub.being_id}-revision-{revision_round + 1}",
                        ticket_id=task_id,
                        idempotency_key=f"{task_id}:{sub.being_id}:revision:{revision_round + 1}",
                        goal=revision_msg,
                        done_when=("Revised output addressing feedback",),
                        input_context_refs=(),
                        output_schema={},
                        priority="high",
                        run_timeout_seconds=SUBTASK_TIMEOUT,
                        cleanup="archive",
                        workspace_root=workspace,
                    )
                    orch_session = state["orchestration_session"]
                    handle = self.subagent_orch.spawn_async(
                        task=rev_task,
                        parent_session_id=orch_session,
                        parent_turn_id=f"orch-{task_id}-{sub.being_id}-rev{revision_round + 1}",
                        parent_agent_id="prime",
                        child_agent_id=sub.being_id,
                        worker=self._orchestration_worker,
                    )
                    rev_run = self._await_run_completion(handle.run_id, timeout=SUBTASK_TIMEOUT)
                    # Read revised output from shared memory (worker writes it there)
                    if rev_run and rev_run.get("status") == "completed" and self.protocol is not None:
                        writes = self.protocol.read_shared_memory(
                            ticket_id=task_id, scope="committed",
                        )
                        being_writes = [w for w in writes if w["writer_agent_id"] == sub.being_id]
                        if being_writes:
                            output = being_writes[0]["content"]
                    elif rev_run:
                        log.warning("Revision run for %s failed: %s", sub.being_id, rev_run.get("error_detail"))
                    with self._lock:
                        self._active[task_id]["subtask_outputs"][sub.being_id] = output
                else:
                    # Fallback: direct handle_turn (no SubAgentProtocol available)
                    try:
                        rev_result = self.bridge.handle_turn(TurnRequest(
                            tenant_id=tenant_id,
                            session_id=subtask_session_id(task_id, sub.being_id),
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

                self._set_status(task_id, STATUS_REVIEWING)

    def _phase_synthesize(self, task_id: str) -> None:
        """Combine all outputs into a final result and post to user chat."""
        self._set_status(task_id, STATUS_SYNTHESIZING)
        state = self._get_state(task_id)
        plan = state["plan"]
        if plan is None:
            return

        # ── Step 1: Persist task_results BEFORE synthesis (with empty synthesis) ──
        self._persist_task_result(task_id, state, "")

        # ── Step 2: Truncate subtask outputs to fit within token budget ──
        # Read outputs from shared working memory (primary) or state fallback
        if self.protocol is not None:
            writes = self.protocol.read_shared_memory(
                ticket_id=task_id, scope="committed",
            )
            # writes are DESC by created_at — keep the newest per agent
            raw_outputs: dict[str, str] = {}
            for w in writes:
                agent = w["writer_agent_id"]
                if agent not in raw_outputs:
                    raw_outputs[agent] = w["content"]
        else:
            raw_outputs = dict(state["subtask_outputs"])
        truncated_outputs = _truncate_outputs_to_budget(raw_outputs)

        # Build sub-task outputs section from truncated outputs
        output_parts = []
        for sub in plan.sub_tasks:
            output = truncated_outputs.get(sub.being_id, "(no output)")
            review = state["subtask_reviews"].get(sub.being_id, {})
            output_parts.append(
                f"### {sub.title} (by {sub.being_id})\n"
                f"Quality: {review.get('quality_score', 'N/A')}\n"
                f"Approved: {review.get('approved', False)}\n\n"
                f"{output}\n"
            )

        # ── Log Point F: Context being passed to synthesis ──
        log.debug("[ORCH] ── Log Point F: Synthesis phase ──")
        for sub in plan.sub_tasks:
            out = truncated_outputs.get(sub.being_id, "(no output)")
            review = state["subtask_reviews"].get(sub.being_id, {})
            log.debug(
                "[ORCH] Being %s: output_len=%d (raw=%d), approved=%s, quality=%s",
                sub.being_id, len(out),
                len(raw_outputs.get(sub.being_id, "")),
                review.get("approved", "N/A"),
                review.get("quality_score", "N/A"),
            )

        # ── Step 3: Attempt synthesis with two-stage fallback ──
        final_output = self._attempt_synthesis(
            task_id, state, plan, output_parts, truncated_outputs,
        )

        # ── Step 4: Update task_results with actual synthesis ──
        self._update_task_result_synthesis(task_id, final_output)

        # Update representations again with synthesis context
        self._update_being_representations(task_id, state, final_output)

        # Extract code deliverables into files, replace with links in chat
        final_output, saved_files = self._extract_and_save_deliverables(
            task_id, final_output,
        )
        # Also detect file paths mentioned in synthesis output
        self._register_mentioned_files(task_id, final_output)

        # Post final output back to user's chat
        # Build metadata with all sub-tasks as agents + outputs from final text
        _plan = state.get("plan")
        _subtask_info = []
        if _plan and hasattr(_plan, "sub_tasks"):
            for _st in _plan.sub_tasks:
                _subtask_info.append({
                    "being_id": _st.being_id,
                    "title": _st.title,
                    "status": "completed",
                })
        self.dashboard.create_message(
            sender="prime",
            content=final_output,
            targets=[state["sender"]],
            msg_type="direct",
            task_ref=task_id,
            session_id=state.get("chat_session_id", "general"),
            metadata=_build_message_metadata(
                final_output,
                subtasks=_subtask_info,
                deliverable_files=[str(f) for f in (saved_files or [])],
            ),
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

        # Auto-trigger dream cycle every N completed tasks
        self._completed_task_count += 1
        if (
            self._dream_trigger_every > 0
            and self._completed_task_count % self._dream_trigger_every == 0
        ):
            self._trigger_dream_cycle()

    def _trigger_dream_cycle(self) -> None:
        """Fire off a dream cycle via the bridge (non-blocking)."""
        try:
            result = self.bridge.dream_cycle_run_once(
                dashboard_svc=self.dashboard,
            )
            log.info(
                "Auto-triggered dream cycle after %d tasks: %d beings processed",
                self._completed_task_count,
                len(result),
            )
        except Exception as exc:
            log.warning("Auto-triggered dream cycle failed: %s", exc)

    # ------------------------------------------------------------------
    # Synthesis helpers
    # ------------------------------------------------------------------

    def _attempt_synthesis(
        self,
        task_id: str,
        state: dict[str, Any],
        plan: OrchestrationPlan,
        output_parts: list[str],
        truncated_outputs: dict[str, str],
    ) -> str:
        """Try synthesis with truncated outputs; fall back to summarize-then-synthesize."""
        from bomba_sr.runtime.bridge import TurnRequest

        synthesis_prompt = SYNTHESIS_SYSTEM_PROMPT.format(
            original_goal=state["goal"],
            plan_summary=plan.summary,
            subtask_outputs="\n---\n".join(output_parts),
            strategy=plan.synthesis_strategy,
        )

        # Stage 1: Try with truncated outputs
        try:
            result = self.bridge.handle_turn(TurnRequest(
                tenant_id=self.prime_tenant_id,
                session_id=state["orchestration_session"],
                user_id="orchestrator",
                user_message=f"[SYNTHESIZE]\n\n{synthesis_prompt}",
                workspace_root=self._prime_workspace(),
                disable_tools=True,
            ))
            text = (result.get("assistant") or {}).get("text", "")
            if text:
                return text
        except Exception as exc:
            log.warning(
                "Synthesis stage 1 failed for task %s: %s — trying stage 2 (summarize first)",
                task_id[:8], exc,
            )

        # Stage 2: Summarize each being's output to ~500 words, then synthesize
        return self._fallback_summarize_then_synthesize(task_id, state, plan, truncated_outputs)

    def _fallback_summarize_then_synthesize(
        self,
        task_id: str,
        state: dict[str, Any],
        plan: OrchestrationPlan,
        outputs: dict[str, str],
    ) -> str:
        """Two-stage fallback: summarize each being's output, then synthesize from summaries."""
        from bomba_sr.runtime.bridge import TurnRequest
        from bomba_sr.llm.providers import ChatMessage, provider_from_env

        classify_model = os.environ.get("BOMBA_CLASSIFY_MODEL", os.environ.get("BOMBA_MODEL_ID", "anthropic/claude-opus-4.6"))
        provider = provider_from_env()

        summaries: dict[str, str] = {}
        for sub in plan.sub_tasks:
            raw = outputs.get(sub.being_id, "(no output)")
            if len(raw) < 800:
                summaries[sub.being_id] = raw
                continue
            try:
                resp = provider.generate(classify_model, [ChatMessage(
                    role="user",
                    content=(
                        f"Summarize the following output from {sub.being_id} in under {FALLBACK_SUMMARY_WORDS} words. "
                        f"Preserve all key findings, data points, and conclusions:\n\n{raw[:12000]}"
                    ),
                )])
                summaries[sub.being_id] = resp.text if hasattr(resp, "text") else str(resp)
            except Exception as exc:
                log.warning("Fallback summary failed for %s: %s", sub.being_id, exc)
                summaries[sub.being_id] = raw[:2000] + "\n[... truncated ...]"

        # Build compact synthesis prompt from summaries
        summary_parts = []
        for sub in plan.sub_tasks:
            summary_parts.append(
                f"### {sub.title} (by {sub.being_id})\n{summaries.get(sub.being_id, '(no output)')}\n"
            )
        fallback_prompt = SYNTHESIS_SYSTEM_PROMPT.format(
            original_goal=state["goal"],
            plan_summary=plan.summary,
            subtask_outputs="\n---\n".join(summary_parts),
            strategy=plan.synthesis_strategy,
        )

        try:
            result = self.bridge.handle_turn(TurnRequest(
                tenant_id=self.prime_tenant_id,
                session_id=state["orchestration_session"],
                user_id="orchestrator",
                user_message=f"[SYNTHESIZE-FALLBACK]\n\n{fallback_prompt}",
                workspace_root=self._prime_workspace(),
                disable_tools=True,
            ))
            text = (result.get("assistant") or {}).get("text", "")
            if text:
                log.info("Stage 2 synthesis succeeded for task %s", task_id[:8])
                return text
        except Exception as exc:
            log.error("Stage 2 synthesis also failed for task %s: %s", task_id[:8], exc)

        # Last resort: concatenate summaries directly
        log.warning("Both synthesis stages failed — returning concatenated summaries for task %s", task_id[:8])
        return (
            f"# Task Results: {state.get('goal', 'unknown')}\n\n"
            + "\n---\n".join(summary_parts)
            + "\n\n*Note: Automated synthesis was not available. These are the individual being outputs.*"
        )

    def _update_task_result_synthesis(self, task_id: str, synthesis_text: str) -> None:
        """Update the task_results row with the actual synthesis output and write semantic memory."""
        try:
            runtime = self.bridge._tenant_runtime(self.prime_tenant_id)
            runtime.db.execute_commit(
                "UPDATE task_results SET synthesis = ? WHERE task_id = ?",
                (synthesis_text, task_id),
            )
            # Now write the semantic memory for cross-task recall
            if synthesis_text and not synthesis_text.startswith("[FAILED"):
                # Read back the goal/beings from the task_results row
                row = runtime.db.execute(
                    "SELECT goal, beings_used, strategy FROM task_results WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
                if row:
                    beings_used = json.loads(row["beings_used"]) if row["beings_used"] else []
                    runtime.memory.learn_semantic(
                        tenant_id=self.prime_tenant_id,
                        user_id="orchestrator",
                        memory_key=f"task_result::{task_id}",
                        content=(
                            f"Completed task: '{row['goal']}'. "
                            f"Beings: {', '.join(beings_used)}. "
                            f"Strategy: {row['strategy']}. "
                            f"Outcome: {synthesis_text[:500]}"
                        ),
                        confidence=0.9,
                        being_id="prime",
                    )
        except Exception as exc:
            log.warning("Failed to update synthesis for task %s: %s", task_id[:8], exc)

    # ------------------------------------------------------------------
    # Deliverable extraction
    # ------------------------------------------------------------------

    _CODE_BLOCK_RE = re.compile(
        r"```(\w+)?\s*\n(.*?)```",
        re.DOTALL,
    )
    _LANG_EXT = {
        "html": ".html", "htm": ".html", "css": ".css", "js": ".js",
        "javascript": ".js", "typescript": ".ts", "tsx": ".tsx", "jsx": ".jsx",
        "python": ".py", "py": ".py", "json": ".json", "yaml": ".yaml",
        "yml": ".yaml", "sql": ".sql", "sh": ".sh", "bash": ".sh",
        "markdown": ".md", "md": ".md", "xml": ".xml", "svg": ".svg",
    }

    def _extract_and_save_deliverables(
        self, task_id: str, text: str, being_id: str | None = None,
    ) -> tuple[str, list[Path]]:
        """Extract large code blocks from output, save as files, register in DB.

        Returns (cleaned_text, list_of_saved_paths).
        Small code snippets (<30 lines) are left inline.
        """
        saved: list[Path] = []
        blocks = list(self._CODE_BLOCK_RE.finditer(text))
        if not blocks:
            return text, saved

        deliverables_dir = _PROJECT_ROOT / "projects" / "deliverables" / task_id[:12]
        file_counter = 0
        result = text

        # Process blocks in reverse so replacement indices stay valid
        for match in reversed(blocks):
            lang = (match.group(1) or "").lower()
            code = match.group(2)
            line_count = code.count("\n")

            # Skip small inline snippets
            if line_count < 30:
                continue

            ext = self._LANG_EXT.get(lang, ".txt")
            fname = self._detect_filename(code, lang) or f"deliverable-{file_counter}{ext}"
            file_counter += 1

            try:
                deliverables_dir.mkdir(parents=True, exist_ok=True)
                fpath = deliverables_dir / fname
                fpath.write_text(code, encoding="utf-8")
                saved.append(fpath)

                url = f"/deliverables/{task_id[:12]}/{fname}"
                byte_size = len(code.encode("utf-8"))

                # Register in DB
                self.dashboard.create_deliverable(
                    task_id=task_id,
                    filename=fname,
                    file_type=lang or ext.lstrip("."),
                    file_path=str(fpath),
                    url=url,
                    being_id=being_id,
                    line_count=line_count,
                    byte_size=byte_size,
                )

                # Replace code block with deliverable card marker
                replacement = (
                    f"\n\n[DELIVERABLE:{fname}:{url}:{lang or ext.lstrip('.')}:{line_count}:{byte_size}]\n"
                )
                result = result[:match.start()] + replacement + result[match.end():]

                log.info(
                    "[ORCH] Saved deliverable %s (%d lines) for task %s",
                    fname, line_count, task_id[:8],
                )
            except Exception as exc:
                log.warning("Failed to save deliverable %s: %s", fname, exc)

        return result, saved

    @staticmethod
    def _detect_filename(code: str, lang: str) -> str | None:
        """Try to detect a filename from code content."""
        if lang in ("html", "htm") and "<title>" in code.lower():
            m = re.search(r"<title>(.*?)</title>", code, re.IGNORECASE)
            if m:
                title = m.group(1).strip()
                safe = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "-").lower()
                if safe:
                    return f"{safe[:40]}.html"
        return None

    # Regex for absolute file paths (Windows and Unix)
    _FILE_PATH_RE = re.compile(
        r'(?:[A-Z]:\\[\w\\.\-/ ]+\.(?:html?|css|js|jsx|tsx?|py|json|md|txt|pdf|csv|sql|svg|png|jpg|yaml|yml))'
        r'|(?:/[\w/.\-]+\.(?:html?|css|js|jsx|tsx?|py|json|md|txt|pdf|csv|sql|svg|png|jpg|yaml|yml))',
        re.IGNORECASE,
    )

    # Regex for bare filenames like `hn_top5_summary.md` or "report.html"
    _BARE_FILENAME_RE = re.compile(
        r'(?<![/\\])(?:`|"|\'|\b)([\w.\-]+\.(?:html?|css|js|jsx|tsx?|py|json|md|txt|pdf|csv|sql|svg|png|jpg|jpeg|yaml|yml))(?:`|"|\'|\b)',
        re.IGNORECASE,
    )

    # Extensions worth serving via browser
    _SERVABLE_EXTS = {
        ".html", ".htm", ".css", ".js", ".jsx", ".tsx", ".ts",
        ".py", ".json", ".md", ".txt", ".pdf", ".csv", ".sql",
        ".svg", ".png", ".jpg", ".jpeg", ".yaml", ".yml",
    }

    def _register_mentioned_files(
        self, task_id: str, text: str, being_id: str | None = None,
    ) -> None:
        """Scan output text for file paths written by tools and register as deliverables."""
        import shutil

        existing = self.dashboard.list_deliverables(task_id)
        existing_paths = {d.get("file_path") for d in existing}
        existing_names = {d.get("filename") for d in existing}

        resolved_paths: list[Path] = []

        # 1) Absolute paths
        for raw_path in self._FILE_PATH_RE.findall(text):
            fpath = Path(raw_path.strip().strip('"').strip("'").rstrip("`"))
            if fpath.exists() and fpath.is_file():
                resolved_paths.append(fpath)

        # 2) Bare filenames — resolve against workspace dirs
        search_dirs = [
            _PROJECT_ROOT / "projects",
            _PROJECT_ROOT / "projects" / "screenshots",
            _PROJECT_ROOT / "projects" / "deliverables",
        ]
        # Add all workspace dirs
        ws_dir = _PROJECT_ROOT / "workspaces"
        if ws_dir.exists():
            for child in ws_dir.iterdir():
                if child.is_dir():
                    search_dirs.append(child)

        for m in self._BARE_FILENAME_RE.finditer(text):
            fname = m.group(1)
            for d in search_dirs:
                candidate = d / fname
                if candidate.exists() and candidate.is_file():
                    resolved_paths.append(candidate)
                    break
                # Also check one level deep
                for sub in d.iterdir() if d.exists() else []:
                    if sub.is_dir():
                        candidate = sub / fname
                        if candidate.exists() and candidate.is_file():
                            resolved_paths.append(candidate)
                            break

        # Deduplicate and register
        seen: set[str] = set()
        for fpath in resolved_paths:
            fpath = fpath.resolve()
            key = str(fpath)
            if key in seen:
                continue
            seen.add(key)

            if fpath.suffix.lower() not in self._SERVABLE_EXTS:
                continue
            if key in existing_paths or fpath.name in existing_names:
                continue

            # Copy to deliverables dir so it's servable via /deliverables/ URL
            deliverables_dir = _PROJECT_ROOT / "projects" / "deliverables" / task_id[:12]
            deliverables_dir.mkdir(parents=True, exist_ok=True)
            dest = deliverables_dir / fpath.name
            try:
                shutil.copy2(str(fpath), str(dest))
            except Exception as exc:
                log.warning("Failed to copy deliverable %s: %s", fpath, exc)
                continue

            url = f"/deliverables/{task_id[:12]}/{fpath.name}"
            byte_size = fpath.stat().st_size
            line_count = 0
            try:
                line_count = fpath.read_text(encoding="utf-8").count("\n")
            except Exception:
                pass

            ext = fpath.suffix.lstrip(".")
            self.dashboard.create_deliverable(
                task_id=task_id,
                filename=fpath.name,
                file_type=ext,
                file_path=str(fpath),
                url=url,
                being_id=being_id,
                line_count=line_count,
                byte_size=byte_size,
            )
            log.info("[ORCH] Registered tool-written deliverable %s for task %s", fpath.name, task_id[:8])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_session_name(self, session_id: str) -> str:
        """Look up a chat session's display name, falling back to the ID."""
        if not session_id or session_id == "general":
            return "General"
        try:
            s = self.dashboard.get_session(session_id)
            if s:
                return s.get("name") or session_id
        except Exception:
            pass
        return session_id

    def _get_state(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            state = self._active.get(task_id)
            if state is not None:
                # Return a deep copy so callers cannot mutate the canonical
                # state without going through lock-protected methods.
                return copy.deepcopy(state)
        # Fallback: load from DB
        state = self._db_load_state(task_id)
        if state is None:
            raise RuntimeError(f"No active orchestration for task {task_id}")
        with self._lock:
            # Use setdefault to avoid overwriting fresher state from a concurrent thread
            self._active.setdefault(task_id, state)
            return copy.deepcopy(self._active[task_id])

    def _set_status(self, task_id: str, status: str) -> None:
        with self._lock:
            if task_id in self._active:
                self._active[task_id]["status"] = status
        self._db_update_status(task_id, status)
        self.dashboard._emit_event("orchestration_update", {
            "task_id": task_id, "status": status,
        })

    def _prime_workspace(self) -> str:
        try:
            existing = getattr(self.bridge, "_tenants", {}).get(self.prime_tenant_id)
            existing_workspace = getattr(getattr(existing, "context", None), "workspace_root", None)
            if existing_workspace:
                return str(existing_workspace)
        except Exception:
            pass
        try:
            prime = self.dashboard.get_being("prime") if self.dashboard else None
            workspace = str((prime or {}).get("workspace") or "").strip()
            if workspace:
                path = Path(workspace)
                return str(path if path.is_absolute() else (_PROJECT_ROOT / path))
        except Exception:
            pass
        return str(_PROJECT_ROOT / "workspaces" / "prime")

    # ------------------------------------------------------------------
    # Task result persistence
    # ------------------------------------------------------------------

    def _ensure_task_results_schema(self) -> None:
        """Create the task_results table in the prime tenant DB if it doesn't exist."""
        try:
            runtime = self.bridge._tenant_runtime(
                self.prime_tenant_id,
                self._prime_workspace(),
            )
            runtime.db.script(
                """
                CREATE TABLE IF NOT EXISTS task_results (
                    task_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    beings_used TEXT NOT NULL,
                    outputs TEXT NOT NULL,
                    synthesis TEXT NOT NULL,
                    artifacts TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_task_results_created
                    ON task_results(tenant_id, created_at DESC);
                """
            )
        except Exception as exc:
            log.warning("Could not ensure task_results schema: %s", exc)

    def _ensure_orchestration_state_schema(self) -> None:
        """Create the orchestration_state table in the prime tenant DB."""
        try:
            runtime = self.bridge._tenant_runtime(
                self.prime_tenant_id,
                self._prime_workspace(),
            )
            runtime.db.script(
                """
                CREATE TABLE IF NOT EXISTS orchestration_state (
                    task_id           TEXT PRIMARY KEY,
                    goal              TEXT NOT NULL,
                    orch_session_id   TEXT NOT NULL,
                    requester_session TEXT NOT NULL,
                    sender            TEXT NOT NULL,
                    status            TEXT NOT NULL,
                    plan_json         TEXT,
                    subtask_ids       TEXT NOT NULL DEFAULT '{}',
                    subtask_reviews   TEXT NOT NULL DEFAULT '{}',
                    created_at        TEXT NOT NULL,
                    updated_at        TEXT NOT NULL
                );
                """
            )
            # Migration for existing databases: add subtask_ids column if missing
            try:
                runtime.db.execute(
                    "ALTER TABLE orchestration_state ADD COLUMN subtask_ids TEXT NOT NULL DEFAULT '{}'"
                )
                runtime.db.commit()
            except Exception:
                # Column already exists — expected on fresh databases
                pass
        except Exception as exc:
            log.warning("Could not ensure orchestration_state schema: %s", exc)

    # ------------------------------------------------------------------
    # Orchestration state DB helpers
    # ------------------------------------------------------------------

    def _db_insert_state(
        self, task_id: str, state: dict[str, Any], now: str,
    ) -> None:
        try:
            runtime = self.bridge._tenant_runtime(self.prime_tenant_id)
            runtime.db.execute_commit(
                """
                INSERT OR REPLACE INTO orchestration_state
                    (task_id, goal, orch_session_id, requester_session,
                     sender, status, plan_json, subtask_ids,
                     subtask_reviews, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    state["goal"],
                    state["orchestration_session"],
                    state["requester_session"],
                    state["sender"],
                    state["status"],
                    None,
                    json.dumps(state.get("subtask_ids", {})),
                    json.dumps({}),
                    now,
                    now,
                ),
            )
        except Exception as exc:
            log.warning("Failed to insert orchestration state for %s: %s", task_id[:8], exc)

    def _db_update_status(self, task_id: str, status: str) -> None:
        try:
            runtime = self.bridge._tenant_runtime(self.prime_tenant_id)
            runtime.db.execute_commit(
                "UPDATE orchestration_state SET status = ?, updated_at = ? WHERE task_id = ?",
                (status, datetime.now(timezone.utc).isoformat(), task_id),
            )
        except Exception as exc:
            log.warning("Failed to update orchestration status for %s: %s", task_id[:8], exc)

    def _db_update_plan(self, task_id: str, plan: OrchestrationPlan) -> None:
        try:
            runtime = self.bridge._tenant_runtime(self.prime_tenant_id)
            runtime.db.execute_commit(
                "UPDATE orchestration_state SET plan_json = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(plan.to_dict()), datetime.now(timezone.utc).isoformat(), task_id),
            )
        except Exception as exc:
            log.warning("Failed to update orchestration plan for %s: %s", task_id[:8], exc)

    def _db_update_subtask_ids(self, task_id: str, subtask_ids: dict[str, str]) -> None:
        try:
            runtime = self.bridge._tenant_runtime(self.prime_tenant_id)
            runtime.db.execute_commit(
                "UPDATE orchestration_state SET subtask_ids = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(subtask_ids), datetime.now(timezone.utc).isoformat(), task_id),
            )
        except Exception as exc:
            log.warning("Failed to update subtask_ids for %s: %s", task_id[:8], exc)

    def _db_merge_subtask_review(
        self, task_id: str, being_id: str, review: dict[str, Any],
    ) -> None:
        try:
            runtime = self.bridge._tenant_runtime(self.prime_tenant_id)
            now = datetime.now(timezone.utc).isoformat()
            with runtime.db.transaction() as conn:
                row = conn.execute(
                    "SELECT subtask_reviews FROM orchestration_state WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
                current = json.loads(row["subtask_reviews"]) if row else {}
                current[being_id] = review
                conn.execute(
                    "UPDATE orchestration_state SET subtask_reviews = ?, updated_at = ? WHERE task_id = ?",
                    (json.dumps(current), now, task_id),
                )
        except Exception as exc:
            log.warning("Failed to merge subtask review for %s/%s: %s", task_id[:8], being_id, exc)

    def _db_load_state(self, task_id: str) -> dict[str, Any] | None:
        """Load orchestration state from DB, reconstruct in-memory dict."""
        try:
            runtime = self.bridge._tenant_runtime(self.prime_tenant_id)
            row = runtime.db.execute(
                "SELECT * FROM orchestration_state WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                return None

            # Reconstruct plan from JSON
            plan = None
            if row["plan_json"]:
                try:
                    plan_data = json.loads(row["plan_json"])
                    plan = OrchestrationPlan(
                        summary=plan_data.get("summary", ""),
                        sub_tasks=[
                            SubTaskPlan(
                                being_id=st["being_id"],
                                title=st.get("title", ""),
                                instructions=st.get("instructions", ""),
                                done_when=st.get("done_when", ""),
                            )
                            for st in plan_data.get("sub_tasks", [])
                        ],
                        synthesis_strategy=plan_data.get("synthesis_strategy", "merge"),
                        max_rounds=int(plan_data.get("max_rounds", 1)),
                    )
                except (json.JSONDecodeError, KeyError) as exc:
                    log.error(
                        "Corrupt plan_json for task %s: %s",
                        task_id, row["plan_json"],
                    )
                    return None

            return {
                "task_id": task_id,
                "goal": row["goal"],
                "orchestration_session": row["orch_session_id"],
                "requester_session": row["requester_session"],
                "sender": row["sender"],
                "status": row["status"],
                "plan": plan,
                "subtask_ids": json.loads(row["subtask_ids"] or "{}"),
                "subtask_outputs": {},  # outputs now live in shared_working_memory_writes
                "subtask_reviews": json.loads(row["subtask_reviews"] or "{}"),
                "created_at": row["created_at"],
            }
        except Exception as exc:
            log.warning("Failed to load orchestration state for %s: %s", task_id[:8], exc)
            return None

    def cleanup_orphaned_orchestrations(self) -> int:
        """Recover or fail orphaned in-progress orchestrations on startup.

        Orchestrations younger than 24 hours are resumed.
        Orchestrations older than 24 hours are marked failed.

        Returns the number of orchestrations processed.
        """
        processed = 0
        try:
            runtime = self.bridge._tenant_runtime(
                self.prime_tenant_id,
                self._prime_workspace(),
            )
            terminal = (STATUS_COMPLETED, STATUS_FAILED)
            rows = runtime.db.execute(
                """
                SELECT task_id, goal, status, updated_at FROM orchestration_state
                WHERE status NOT IN (?, ?)
                """,
                terminal,
            ).fetchall()

            now = datetime.now(timezone.utc)
            for row in rows:
                task_id = row["task_id"]
                updated_at = row["updated_at"]
                try:
                    age_hours = (now - datetime.fromisoformat(updated_at)).total_seconds() / 3600
                except (ValueError, TypeError):
                    age_hours = 999.0

                if age_hours > 24:
                    log.warning(
                        "Orchestration %s is %.1fh old — marking failed (too stale to resume, goal: %s)",
                        task_id[:8], age_hours, (row["goal"] or "")[:80],
                    )
                    runtime.db.execute_commit(
                        "UPDATE orchestration_state SET status = ?, updated_at = ? WHERE task_id = ?",
                        (STATUS_FAILED, now.isoformat(), task_id),
                    )
                    try:
                        self.dashboard.update_task(self.project_svc, task_id, status="failed")
                    except Exception:
                        pass
                    self.dashboard._log_task_history(
                        task_id, "orchestration_cleanup",
                        {"reason": "Too stale to resume (>24h) — marked failed"},
                    )
                    processed += 1
                else:
                    log.info(
                        "Attempting resume for orchestration %s (age: %.1fh, status: %s)",
                        task_id[:8], age_hours, row["status"],
                    )
                    self.resume_orchestration(task_id)
                    processed += 1

            if processed:
                log.info("Processed %d orphaned orchestrations on startup", processed)
        except Exception as exc:
            log.warning("Failed to process orphaned orchestrations: %s", exc)
        return processed

    # ------------------------------------------------------------------
    # Orchestration resume (server restart recovery)
    # ------------------------------------------------------------------

    def resume_orchestration(self, task_id: str) -> None:
        """Resume an in-progress orchestration from its last persisted state.

        Called on startup for any orchestration_state with non-terminal status
        that is recent enough to attempt recovery (< 24h).
        """
        state = self._db_load_state(task_id)
        if not state:
            log.error("Cannot resume %s: state not found in DB", task_id[:8])
            return

        # Re-populate in-memory cache so the pipeline phases can operate
        with self._lock:
            self._active[task_id] = state

        log.info(
            "Resuming orchestration %s from status=%s (goal: %s)",
            task_id[:8], state["status"], (state.get("goal") or "")[:80],
        )

        # Notify user that we're resuming
        try:
            self.dashboard.create_message(
                sender="prime",
                content=(
                    f"System restarted. Resuming your task: "
                    f"{(state.get('goal') or task_id)[:100]}..."
                ),
                targets=[state.get("sender", "user")],
                msg_type="direct",
                task_ref=task_id,
                session_id=state.get("chat_session_id", "general"),
            )
        except Exception:
            pass

        t = threading.Thread(
            target=self._resume_from_status,
            args=(task_id, state),
            daemon=True,
            name=f"orch-resume-{task_id[:8]}",
        )
        t.start()

    def _resume_from_status(self, task_id: str, state: dict[str, Any]) -> None:
        """Re-enter the orchestration pipeline at the correct phase."""
        try:
            status = state["status"]

            # Parse round-specific delegating status (e.g. "delegating_round_2")
            resume_round = 0
            if status.startswith("delegating_round_"):
                try:
                    resume_round = int(status.split("_")[-1])
                except (ValueError, IndexError):
                    pass
                status = STATUS_DELEGATING  # normalize for routing

            if status == STATUS_PLANNING:
                # Plan never completed — restart from scratch
                self._phase_plan(task_id)
                self._phase_delegate(task_id)
                self._update_post_delegation(task_id)
                self._phase_review(task_id)
                self._phase_synthesize(task_id)

            elif status == STATUS_DELEGATING:
                if resume_round >= 2:
                    # Resume mid-iteration — re-enter at the correct round
                    self._reload_outputs_from_shared_memory(task_id, state)
                    plan = state["plan"]
                    max_rounds = plan.max_rounds if plan else 1
                    for rn in range(resume_round, max_rounds + 1):
                        self._phase_delegate_iteration(task_id, rn)
                        self._update_post_delegation(task_id)
                        self._phase_review(task_id)
                        if rn < max_rounds and self._all_reviews_approved(task_id):
                            break
                else:
                    self._resume_delegation(task_id, state)
                    self._update_post_delegation(task_id)
                    self._phase_review(task_id)
                self._phase_synthesize(task_id)

            elif status == STATUS_REVIEWING or status == STATUS_REVISING:
                # Re-populate subtask_outputs from shared memory for review
                self._reload_outputs_from_shared_memory(task_id, state)
                self._phase_review(task_id)
                self._phase_synthesize(task_id)

            elif status == STATUS_SYNTHESIZING:
                self._reload_outputs_from_shared_memory(task_id, state)
                self._phase_synthesize(task_id)

            else:
                log.warning("Cannot resume %s from status=%s", task_id[:8], status)
                self._set_status(task_id, STATUS_FAILED)
                return

        except Exception as exc:
            log.exception("Resume failed for %s", task_id[:8])
            self._set_status(task_id, STATUS_FAILED)

            if self.protocol is not None:
                try:
                    orch_session = orchestration_session_id(task_id)
                    self.protocol.cascade_stop_session(
                        tenant_id=self.prime_tenant_id,
                        session_id=orch_session,
                        reason=f"resume failed: {exc}",
                    )
                except Exception:
                    pass

            try:
                self.dashboard.update_task(self.project_svc, task_id, status="failed")
            except Exception:
                pass
        finally:
            try:
                self.dashboard.update_being("prime", {"status": "online"})
            except Exception:
                pass

    def _resume_delegation(self, task_id: str, state: dict[str, Any]) -> None:
        """Resume delegation phase — re-spawn only incomplete subtasks."""
        plan = state["plan"]
        if plan is None:
            raise RuntimeError("Cannot resume delegation: no plan in state")

        self._set_status(task_id, STATUS_DELEGATING)
        subtask_ids = state.get("subtask_ids") or {}

        completed_beings: set[str] = set()

        for being_id, run_id in subtask_ids.items():
            if self.protocol is None:
                break
            try:
                run = self.protocol.get_run(run_id)
                if run and run["status"] == "completed":
                    completed_beings.add(being_id)
                elif run and run["status"] not in ("completed", "failed", "timed_out"):
                    # Was running/accepted when server died — mark failed
                    try:
                        self.protocol.fail(
                            run_id,
                            reason="Server restart — run interrupted",
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        # Load outputs from already-completed subtasks into in-memory state
        self._reload_outputs_from_shared_memory(task_id, state)

        # Determine what needs to be (re-)spawned
        pending_subs = [
            s for s in plan.sub_tasks
            if s.being_id not in completed_beings
        ]

        if not pending_subs:
            log.info("All subtasks already completed for %s", task_id[:8])
            return

        log.info(
            "Resuming %d subtasks for %s (completed: %s)",
            len(pending_subs), task_id[:8], completed_beings,
        )

        if plan.synthesis_strategy == "sequential":
            for sub in pending_subs:
                prior = self._collect_prior_outputs_from_shared_memory(
                    task_id, plan, sub.being_id,
                )
                run_id = self._execute_subtask(task_id, sub, prior_outputs=prior)
                run = self._await_run_completion(run_id, timeout=SUBTASK_TIMEOUT)
                self._on_subtask_completed(task_id, sub, run)
        else:
            run_ids: list[tuple[SubTaskPlan, str]] = []
            for sub in pending_subs:
                run_id = self._execute_subtask(task_id, sub)
                run_ids.append((sub, run_id))
            for sub, run_id in run_ids:
                run = self._await_run_completion(run_id, timeout=SUBTASK_TIMEOUT)
                self._on_subtask_completed(task_id, sub, run)

        # Persist updated subtask_ids
        with self._lock:
            ids_snapshot = dict(self._active[task_id]["subtask_ids"])
        self._db_update_subtask_ids(task_id, ids_snapshot)

    def _reload_outputs_from_shared_memory(
        self, task_id: str, state: dict[str, Any],
    ) -> None:
        """Reload subtask outputs from shared_working_memory_writes into in-memory state."""
        if self.protocol is None:
            return
        plan = state.get("plan")
        if plan is None:
            return
        writes = self.protocol.read_shared_memory(
            ticket_id=task_id, scope="committed",
        )
        outputs_by_agent: dict[str, str] = {}
        for w in writes:
            agent = w["writer_agent_id"]
            if agent not in outputs_by_agent:
                outputs_by_agent[agent] = w["content"]
        with self._lock:
            for sub in plan.sub_tasks:
                if sub.being_id in outputs_by_agent:
                    self._active[task_id]["subtask_outputs"][sub.being_id] = (
                        outputs_by_agent[sub.being_id]
                    )

    def _update_post_delegation(self, task_id: str) -> None:
        """Run team context + representation updates after delegation."""
        try:
            state = self._get_state(task_id)
            self._update_team_context_outcomes(task_id, state)
            self._update_being_representations(task_id, state, "")
        except Exception as exc:
            log.warning("Post-delegation updates failed for %s: %s", task_id[:8], exc)

    def _persist_task_result(
        self,
        task_id: str,
        state: dict[str, Any],
        synthesis_text: str,
    ) -> None:
        """Write a permanent task result record after synthesis completes."""
        try:
            runtime = self.bridge._tenant_runtime(self.prime_tenant_id)
            plan: OrchestrationPlan | None = state.get("plan")
            beings_used = (
                [sub.being_id for sub in plan.sub_tasks] if plan else []
            )
            strategy = plan.synthesis_strategy if plan else "unknown"
            # Read outputs from shared memory (primary) or state fallback
            if self.protocol is not None:
                writes = self.protocol.read_shared_memory(
                    ticket_id=task_id, scope="committed",
                )
                outputs: dict[str, str] = {}
                for w in writes:
                    agent = w["writer_agent_id"]
                    if agent not in outputs:
                        outputs[agent] = w["content"]
            else:
                outputs = dict(state.get("subtask_outputs", {}))
            runtime.db.execute_commit(
                """
                INSERT OR REPLACE INTO task_results
                    (task_id, tenant_id, goal, strategy, beings_used,
                     outputs, synthesis, artifacts, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    self.prime_tenant_id,
                    state.get("goal", ""),
                    strategy,
                    json.dumps(beings_used),
                    json.dumps(outputs),
                    synthesis_text,
                    json.dumps([]),  # artifacts — populated by future work
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            log.info("Persisted task result for %s", task_id[:8])

            # Write a semantic memory so future planning phases can recall
            # past task outcomes via standard memory retrieval.
            # Skip if synthesis_text is empty (pre-synthesis persist).
            if synthesis_text and not synthesis_text.startswith("[FAILED"):
                goal = state.get("goal", "")
                runtime.memory.learn_semantic(
                    tenant_id=self.prime_tenant_id,
                    user_id="orchestrator",
                    memory_key=f"task_result::{task_id}",
                    content=(
                        f"Completed task: '{goal}'. "
                        f"Beings: {', '.join(beings_used)}. "
                        f"Strategy: {strategy}. "
                        f"Outcome: {synthesis_text[:500]}"
                    ),
                    confidence=0.9,
                    being_id="prime",
                )
        except Exception as exc:
            log.warning("Failed to persist task result for %s: %s", task_id[:8], exc)

    def _update_team_context_outcomes(
        self, task_id: str, state: dict[str, Any],
    ) -> None:
        """Append a one-line summary to TEAM_CONTEXT.md 'Recent Task Outcomes'."""
        try:
            from bomba_sr.tools.builtin_team_context import (
                TEAM_CONTEXT_MAX_CHARS,
                _TEAM_CONTEXT_TEMPLATE,
                _resolve_team_context_path,
            )
            import re as _re

            workspace = Path(self._prime_workspace())
            tc_path = _resolve_team_context_path(workspace)

            if tc_path.exists():
                text = tc_path.read_text(encoding="utf-8")
            else:
                text = _TEAM_CONTEXT_TEMPLATE

            goal = state.get("goal", "unknown task")
            plan: OrchestrationPlan | None = state.get("plan")
            beings = ", ".join(
                sub.being_id for sub in plan.sub_tasks
            ) if plan else "unknown"
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            new_line = f"- [{ts}] {goal[:100]} (by {beings})"

            # Find the Recent Task Outcomes section and prepend the new line
            pattern = _re.compile(
                r"(^## Recent Task Outcomes\s*\n)(.*?)(?=^## |\Z)",
                _re.MULTILINE | _re.DOTALL,
            )
            match = pattern.search(text)
            if match:
                existing = match.group(2).strip()
                # Keep only the most recent entries to stay under budget
                lines = [new_line]
                if existing:
                    lines.extend(existing.splitlines()[:9])  # keep last 9
                new_section = "\n".join(lines) + "\n\n"
                new_text = pattern.sub(rf"\g<1>{new_section}", text, count=1)
            else:
                new_text = text.rstrip() + f"\n\n## Recent Task Outcomes\n{new_line}\n"

            # Enforce size cap
            if len(new_text) > TEAM_CONTEXT_MAX_CHARS:
                new_text = new_text[:TEAM_CONTEXT_MAX_CHARS]

            tc_path.write_text(new_text, encoding="utf-8")
            log.info("Updated TEAM_CONTEXT.md with outcome for task %s", task_id[:8])
        except Exception as exc:
            log.warning("Failed to update TEAM_CONTEXT.md: %s", exc)

    def _update_being_representations(
        self,
        task_id: str,
        state: dict[str, Any],
        synthesis_text: str,
    ) -> None:
        """Have SAI Memory update each participating being's REPRESENTATION.md."""
        plan: OrchestrationPlan | None = state.get("plan")
        if plan is None:
            return

        import os
        classify_model = os.environ.get("BOMBA_CLASSIFY_MODEL", os.environ.get("BOMBA_MODEL_ID", "anthropic/claude-opus-4.6"))

        for sub in plan.sub_tasks:
            try:
                being = self.dashboard.get_being(sub.being_id) or {}
                ws = being.get("workspace")
                if ws and ws != ".":
                    ws_path = Path(ws) if Path(ws).is_absolute() else _PROJECT_ROOT / ws
                else:
                    ws_path = _PROJECT_ROOT

                rep_path = ws_path / "REPRESENTATION.md"
                current_rep = ""
                if rep_path.exists():
                    current_rep = rep_path.read_text(encoding="utf-8")

                review = state.get("subtask_reviews", {}).get(sub.being_id, {})
                quality_score = review.get("quality_score", "N/A")
                review_notes = review.get("notes", "")

                prompt = REPRESENTATION_UPDATE_SYSTEM_PROMPT.format(
                    being_id=sub.being_id,
                    goal=state.get("goal", "unknown task"),
                    subtask_title=sub.title,
                    quality_score=quality_score,
                    review_notes=review_notes,
                    synthesis_summary=synthesis_text[:500],
                    current_representation=current_rep[:3000],
                )

                # Use direct provider.generate() — lightweight, not handle_turn
                from bomba_sr.llm.providers import ChatMessage, provider_from_env
                provider = provider_from_env()
                messages = [ChatMessage(role="user", content=prompt)]
                resp = provider.generate(classify_model, messages)
                updated = resp.text if hasattr(resp, 'text') else str(resp)

                if updated and updated.strip():
                    # Cap at 3000 chars
                    final_text = updated.strip()[:3000]
                    rep_path.write_text(final_text, encoding="utf-8")
                    log.info(
                        "Updated REPRESENTATION.md for %s (task %s)",
                        sub.being_id, task_id[:8],
                    )
            except Exception as exc:
                log.warning(
                    "Failed to update REPRESENTATION.md for %s: %s",
                    sub.being_id, exc,
                )

    def _collect_prior_outputs_from_shared_memory(
        self, task_id: str, plan: OrchestrationPlan, current_being_id: str,
    ) -> dict[str, str]:
        """Read committed outputs from shared_working_memory_writes for prior beings."""
        if self.protocol is None:
            return {}
        prior: dict[str, str] = {}
        writes = self.protocol.read_shared_memory(
            ticket_id=task_id, scope="committed",
        )
        writes_by_agent = {w["writer_agent_id"]: w["content"] for w in writes}
        for sub in plan.sub_tasks:
            if sub.being_id == current_being_id:
                break  # only include beings that come before this one in the plan
            output = writes_by_agent.get(sub.being_id, "")
            if output and not output.startswith("[Error"):
                prior[sub.being_id] = output
        return prior

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

        strategy = data.get("synthesis_strategy", "merge")

        # Auto-detect sequential need: if any sub-task's instructions
        # reference other beings or mention combining/summarizing results,
        # upgrade to sequential so later beings get earlier outputs.
        if strategy != "sequential" and len(sub_tasks) > 1:
            _combine_keywords = {"combine", "combining", "summary", "summarize", "synthesize", "merge", "both results", "other beings", "receive"}
            for st in sub_tasks:
                instr_lower = st.instructions.lower()
                if any(kw in instr_lower for kw in _combine_keywords):
                    strategy = "sequential"
                    log.debug("[ORCH] Auto-upgraded strategy to 'sequential' — sub-task '%s' references combining results", st.title)
                    break

        max_rounds = int(data.get("max_rounds", 1))

        return OrchestrationPlan(
            summary=data.get("summary", ""),
            sub_tasks=sub_tasks,
            synthesis_strategy=strategy,
            max_rounds=max_rounds,
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
            log.warning(
                "Review parse failed — blocking approval. Raw response: %s",
                llm_reply[:500],
            )
            return {
                "approved": False,
                "feedback": "Review LLM returned unparseable response — revision required.",
                "quality_score": 0.0,
                "notes": "Review LLM returned unparseable response — blocking",
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
