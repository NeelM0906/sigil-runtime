# Orchestration System Audit Report
# bomba-sr-runtime — Multi-Agent Orchestration Pipeline

**Date:** 2026-03-06
**Audited by:** Claude Sonnet 4.6 (automated code audit)
**Scope:** Full orchestration pipeline end-to-end, failure modes, state machine, sub-agent system comparison

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Pipeline End-to-End Trace](#2-pipeline-end-to-end-trace)
3. [Failure Modes by Phase](#3-failure-modes-by-phase)
4. [State Machine](#4-state-machine)
5. [Sub-Agent System vs Orchestration Engine](#5-sub-agent-system-vs-orchestration-engine)
6. [ASCII Diagrams](#6-ascii-diagrams)
7. [Key Findings and Risks](#7-key-findings-and-risks)

---

## 1. Executive Summary

The orchestration system has two parallel, **non-integrated** multi-agent mechanisms:

1. **OrchestrationEngine** (`src/bomba_sr/orchestration/engine.py`) — the "being-to-being" orchestrator. Prime receives a `full_task` classified message, decomposes it into sub-tasks, delegates each sub-task to a being via `bridge.handle_turn()`, reviews outputs, and synthesizes a final answer. State is stored only in an in-memory dict (`_active`) and conversational turns in SQLite. There are no new tables beyond `task_results`.

2. **SubAgentOrchestrator + SubAgentWorkerFactory** (`src/bomba_sr/subagents/`) — a general-purpose async sub-agent system with full protocol tracking in `subagent_runs` and `subagent_events` tables. Supports cascade stop, crash storm detection, shared memory, and parent-child lineage.

**These two systems are entirely independent.** The OrchestrationEngine does not use SubAgentOrchestrator at all. It spawns Python `threading.Thread` objects directly and tracks state in a plain Python dict.

Key risks identified:

- **Lost state on crash**: all active orchestration state lives in `_active` (in-memory dict). A process crash loses all in-flight orchestration with no recovery path.
- **No timeout on planning phase**: `_phase_plan` has no timeout guard. A hung LLM call blocks the orchestration thread indefinitely.
- **Hardcoded workspace path**: `_prime_workspace()` and `_execute_subtask()` contain literal `"/Users/zidane/Downloads/PROJEKT"` — not portable.
- **Empty-output silent failure**: if a being's `handle_turn` returns `assistant.text == ""`, the orchestration records that as a valid output string and proceeds through review/synthesis with no fallback.
- **Revision loop auto-approves on parse failure**: `_parse_review` returns `approved=True` when JSON parsing fails, meaning a malformed review response silently approves any output.
- **No cross-being result isolation**: all beings share the same `RuntimeDB` if they share `tenant_id`. A being's tool side-effects are not isolated from other beings running concurrently.
- **`task_id` confusion**: `start()` creates a parent task via `dashboard.create_task()`, but the actual `task_id` returned differs from the UUID generated inside `start()`. The `orchestration:{task_id}` session uses the board task ID, not the original UUID, but the `_active` dict key uses `actual_task_id`.

---

## 2. Pipeline End-to-End Trace

### 2.1 Entry Point: Message Routing

**File:** `src/bomba_sr/dashboard/service.py`

A user message arrives at `DashboardService.route_to_being(being_id, content, sender)` (line 739). This fires a background thread calling `_route_to_being_sync`.

```python
# service.py:739-746
def route_to_being(self, being_id: str, content: str, sender: str = "user") -> None:
    t = threading.Thread(
        target=self._route_to_being_sync,
        args=(being_id, content, sender),
        daemon=True,
    )
    t.start()
```

`route_to_being` returns immediately to the caller with no handle. There is no way for the caller to await the result or detect if the background thread crashes silently.

### 2.2 Message Classification

**File:** `src/bomba_sr/dashboard/service.py`, `_classify_message` (line 1053)

Classification is two-stage:

**Stage 1 — Regex fast-path (line 1062):**
```python
if len(stripped) < 4 or _NOT_TASK_PATTERNS.match(stripped):
    return "not_task"
```
The regex at line 66 matches common greetings and questions with up to 4 trailing words. No LLM call for these.

**Stage 2 — LLM call (line 1067):**
```
Model: BOMBA_CLASSIFY_MODEL env var, default "openai/gpt-4o-mini"
System prompt: _CLASSIFY_SYSTEM_PROMPT (line 47) — 3-category classifier
Input: first 500 chars of message
Expected output: {"classification": "not_task"|"light_task"|"full_task"}
```

On any exception, the classifier defaults to `"not_task"` (line 1088). This is intentional — "Creating spurious tasks is worse than missing a real one." (comment at line 1087). However it also means that if the LLM provider is unavailable, all messages to Prime silently fall through to direct LLM chat without orchestration.

**Classification outcomes (line 809-831):**
- `not_task` → direct `bridge.handle_turn()` chat, no task created
- `light_task` → task created, direct `bridge.handle_turn()` chat
- `full_task` to Prime (with orchestration_engine initialized) → `_handle_orchestrated_task()`
- `full_task` to any other being → task + steps created, direct `bridge.handle_turn()` chat

**Orchestration intercept condition (line 810-817):**
```python
if (
    classification == "full_task"
    and being_id == "prime"
    and self.orchestration_engine is not None
    and self.project_service is not None
):
    self._handle_orchestrated_task(...)
    return
```

Orchestration only fires for `being_id == "prime"`. All other beings always get direct handle_turn calls regardless of task complexity.

### 2.3 Orchestration Kickoff

**File:** `src/bomba_sr/dashboard/service.py`, `_handle_orchestrated_task` (line 930)

1. Posts an immediate "I'll orchestrate this" acknowledgment message to chat (line 940).
2. Sets Prime's status to "busy" (line 951).
3. Calls `orchestration_engine.start(goal, requester_session_id, sender)` (line 959).
4. `start()` returns immediately with `{"task_id", "orchestration_session", "status": "planning"}`.
5. The actual orchestration runs in a background thread (line 321-327).

**No error path**: if `orchestration_engine.start()` raises, the exception is caught at line 969, a failure message is posted to chat, and Prime's status is reset to "online". No partial state cleanup.

### 2.4 Phase 1: Planning

**File:** `src/bomba_sr/orchestration/engine.py`, `_phase_plan` (line 428)

**Step 1 — Gather assignable beings (line 435-469):**
- Calls `dashboard.list_beings()`.
- Excludes offline beings and Prime itself.
- For `type == "acti"` beings: loads domain + cluster info from `bomba_sr.acti.loader`.
- For beings with a workspace: reads `REPRESENTATION.md` (first 800 chars) to enrich the being entry.

**Step 2 — Build planning prompt (line 479-490):**
```
PLAN_SYSTEM_PROMPT (line 146) is NOT used as a system message.
It is concatenated into the user_message string along with beings JSON.
```
The full prompt structure:
```
"[SYSTEM: ORCHESTRATION MODE]\n"
+ PLAN_SYSTEM_PROMPT.format(beings_json=json.dumps(assignable, indent=2))
+ "\nTask to decompose:\n{goal}\n\n..."
+ optional ACT-I context
```

**Step 3 — LLM call via handle_turn (line 496-508):**
```python
result = self.bridge.handle_turn(TurnRequest(
    tenant_id=self.prime_tenant_id,      # "tenant-prime"
    session_id=orch_session,             # "orchestration:{task_id}"
    user_id="orchestrator",
    user_message=<full prompt>,
    workspace_root=self._prime_workspace(),  # HARDCODED path
    disable_tools=True,                  # no tools for planning
    include_representation=True,
))
```

`disable_tools=True` prevents the `handle_turn` bridge from running code-search on the prompt string (which contains ripgrep-incompatible characters). With tools disabled, `search_result` is set to a synthetic empty result at bridge.py:480-491.

`TurnProfile` is NOT specified — defaults to `TurnProfile.CHAT` (bridge.py:87). The SUBAGENT_ORCHESTRATION profile exists but is never used.

**Step 4 — Parse plan (line 511):**
```python
plan = self._parse_plan(reply, assignable)
```

`_parse_plan` (line 1302) extracts JSON from the LLM reply. On any parse failure, it falls back to a single-being plan using the first available being and the raw LLM reply as instructions (line 1312-1322). If the LLM hallucinates an unknown `being_id`, the parser fuzzy-matches or falls back to the first available being (line 1328-1334). **There is no validation that the plan is sensible — zero sub-tasks with a valid JSON response would trigger the empty fallback.**

Auto-upgrade to `sequential` strategy: if any sub-task's instructions contain keywords like "combine", "summarize", "merge", "both results", the strategy is upgraded from "merge" to "sequential" (line 1356-1363).

**Step 5 — Store plan (line 513-514):**
```python
with self._lock:
    self._active[task_id]["plan"] = plan
```

Plan is stored in the in-memory dict only. Not persisted to DB.

### 2.5 Phase 2: Delegation

**File:** `src/bomba_sr/orchestration/engine.py`, `_phase_delegate` (line 527)

**Sub-task tracking:** Unlike what the comment says, sub-tasks are not created as separate board entries. The only tracking is an entry in `mc_task_history` via `_log_task_history` and an update to `_active[task_id]["subtask_ids"]` (which maps `being_id -> task_id`, not to a unique subtask ID — this is a misleading dict name).

**Execution modes (line 562-579):**
- `sequential`: beings execute one at a time; each subsequent being receives prior beings' outputs as context via `_collect_prior_outputs`.
- Any other strategy (`merge`, `compare`): all beings execute in parallel via `threading.Thread`. Join timeout is `300 seconds` (5 minutes) per sub-task — but since all threads start simultaneously and are joined sequentially, the effective total timeout is also 5 minutes regardless of how many beings there are. If a thread hangs, `t.join(timeout=300)` returns but the thread continues running with no cancellation.

**Delegation message construction (line 627-638):**
```
[IDENTITY CONTEXT]           (ACT-I beings only)
You have been assigned a sub-task by SAI Prime.

TASK TITLE: {sub.title}

CONTEXT FROM OTHER BEINGS:  (sequential strategy only)
--- {prior_being}'s findings ---
{output}

INSTRUCTIONS:
{sub.instructions}

ACCEPTANCE CRITERIA:
{sub.done_when}

Complete this task using your available tools...
After completing your work, update your KNOWLEDGE.md...
```

**Delegation call (line 648-658):**
```python
result = self.bridge.handle_turn(TurnRequest(
    tenant_id=tenant_id,             # being's tenant_id from mc_beings
    session_id=session,              # "subtask:{task_id}:{being_id}"
    user_id=f"prime->{sub.being_id}",
    user_message=delegation_message,
    workspace_root=workspace,        # HARDCODED base path
    search_query=sub.title,          # short title as rg pattern
))
```

No `disable_tools`. The being gets full tool access. `TurnProfile` defaults to `CHAT`. The being's `workspace_root` is resolved as `Path("/Users/zidane/Downloads/PROJEKT") / ws` where `ws` is the being's workspace field from `mc_beings`.

**Result capture (line 659):**
```python
output = (result.get("assistant") or {}).get("text", "")
```

If `result["assistant"]` is None or if `text` is empty string, `output` is `""`. This is stored as a valid result. The empty string check at review phase (line 731) catches this: `if not output or output.startswith("[Error")` marks it as unapproved with feedback "Sub-task failed or produced no output." But this does NOT halt orchestration — it proceeds to synthesis with a zero-quality placeholder.

**Exception handling (line 669-673):**
```python
except Exception as exc:
    output = f"[Error: {exc}]"
```

The error is stored as the output string. The being's status is restored to "online" in the `finally` block regardless.

**Post-execution — semantic memory write (line 684-704):**
On non-empty, non-error output, the being's tenant runtime is accessed and `learn_semantic()` is called. This write persists domain knowledge across tasks. Failure is non-fatal (logged as warning only).

### 2.6 Phase 3: Review

**File:** `src/bomba_sr/orchestration/engine.py`, `_phase_review` (line 718)

**Per-being review loop (line 740):**
`max_revisions = 2` (hardcoded, line 727). For each being, up to 3 attempts total (initial + 2 revisions).

**Review prompt (line 741-746):**
```
REVIEW_SYSTEM_PROMPT.format(
    title=sub.title,
    instructions=sub.instructions,
    done_when=sub.done_when or "Complete the task as instructed",
    output=output[:8000],   # hard-truncated to 8000 chars
)
```

The output is truncated to 8000 chars for review regardless of actual length. The full output is used for synthesis.

**Review LLM call (line 747-754):**
```python
result = self.bridge.handle_turn(TurnRequest(
    tenant_id=self.prime_tenant_id,
    session_id=state["orchestration_session"],   # same session as planning
    user_id="orchestrator",
    user_message=f"[REVIEW] Being: {sub.being_id}\n\n{review_prompt}",
    workspace_root=self._prime_workspace(),
    disable_tools=True,
))
```

Reviews run in the `orchestration:{task_id}` session (Prime's session), not the subtask session. Planning context accumulates in this session.

**Review parsing (line 1371-1387):**
```python
def _parse_review(self, llm_reply: str) -> dict[str, Any]:
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
            "approved": True,          # BUG: auto-approves on parse failure
            "feedback": "",
            "quality_score": 0.6,
            "notes": "Review parsing failed — auto-approving",
        }
```

**IDENTIFIED BUG:** When the review LLM response cannot be parsed (malformed JSON, empty response, network error), the fallback returns `approved=True`. This silently accepts any output, including garbage or empty strings, when the reviewer itself fails.

**Revision flow (line 780-815):**
When not approved, a revision message is sent to the being in its subtask session:
```
[REVISION REQUEST FROM SAI PRIME — Round {N}]
Your previous output needs revision.
Feedback: {review["feedback"]}
Please revise your output addressing the feedback above.
```
The revised output replaces the stored output in `_active[task_id]["subtask_outputs"]`. If the revision call raises, the original output is kept (line 811). The being status is set to "busy" before revision and "online" after (finally block, line 813).

After `max_revisions` rounds, the review result (whether approved or not) is stored and the loop breaks.

### 2.7 Phase 4: Synthesis

**File:** `src/bomba_sr/orchestration/engine.py`, `_phase_synthesize` (line 817)

**Token budget handling (line 829-830):**
```python
raw_outputs = dict(state["subtask_outputs"])
truncated_outputs = _truncate_outputs_to_budget(raw_outputs)
```

`_truncate_outputs_to_budget` (line 69-90):
- `available_tokens = 200_000 - 40_000 - 16_000 = 144_000` (using `DEFAULT_MODEL_MAX_INPUT`)
- `per_being_tokens = available_tokens // len(outputs)` — equal budget per being
- `per_being_chars = int(per_being_tokens * 3.5)` — character estimate

The `DEFAULT_MODEL_MAX_INPUT = 200_000` is hardcoded and does not read the actual model's context window. For models with smaller context windows this will produce outputs that still exceed actual limits.

**Synthesis prompt (line 929-935):**
```
SYNTHESIS_SYSTEM_PROMPT.format(
    original_goal=state["goal"],
    plan_summary=plan.summary,
    subtask_outputs="\n---\n".join(output_parts),
    strategy=plan.synthesis_strategy,
)
```

**Two-stage fallback (line 858-956):**
1. Stage 1: synthesis with truncated outputs via handle_turn. If LLM returns empty string or raises, falls to stage 2.
2. Stage 2: each being's output is first summarized to ~500 words via direct `provider.generate()` call (not handle_turn), then synthesis is re-attempted via handle_turn.
3. Last resort (line 1020-1026): concatenate the summaries directly with a note that "Automated synthesis was not available."

All synthesis calls use `disable_tools=True` and the `orchestration:{task_id}` session.

**Pre-synthesis persist (line 826):**
`_persist_task_result(task_id, state, "")` is called with an empty synthesis string before the LLM synthesis runs. This creates a `task_results` row with blank synthesis. `_update_task_result_synthesis` is called after with the actual text (line 863). If synthesis fails entirely but the process crashes after the pre-persist, a row with empty synthesis remains in the DB.

**Final delivery (line 869-875):**
```python
self.dashboard.create_message(
    sender="prime",
    content=final_output,
    targets=[state["sender"]],
    msg_type="direct",
    task_ref=task_id,
)
```
The result is posted as a chat message. No return value is provided to the original caller (who got a non-blocking return from `_handle_orchestrated_task` long ago).

**Post-synthesis (line 866):**
`_update_being_representations()` is called to update each participating being's `REPRESENTATION.md` file using the `BOMBA_CLASSIFY_MODEL` (lightweight model, not handle_turn). This is a direct file write to the workspace.

**Dream cycle trigger (line 893-898):**
Every `BOMBA_DREAM_TRIGGER_EVERY` (default 5) completed tasks, a dream cycle is auto-triggered via `bridge.dream_cycle_run_once()`.

### 2.8 Sub-Task Context for Beings

**Session IDs used:**
- `orchestration:{task_id}` — Prime's planning/review/synthesis session. All three phases share this session, meaning planning context, review history, and synthesis all accumulate in one conversation thread.
- `subtask:{task_id}:{being_id}` — Each being's isolated work session. Revision rounds reuse the same subtask session, giving the being conversation continuity for revisions.

**Bridge behavior for orchestration sessions (bridge.py:572-589):**
Sessions matching `subtask:` or `orchestration:` get special treatment:
- Conversation history replay is limited to 3 turns (vs 5 for normal sessions).
- Tool blocks are stripped from replay messages via `_strip_tool_blocks()` to prevent API errors from stale tool schemas.

**Tool availability during delegation:**
- Planning, review, synthesis: `disable_tools=True` — no tools available.
- Delegation (being execution): tools fully available, governed by the being's tenant's `PolicyPipeline`.

---

## 3. Failure Modes by Phase

### 3.1 Classification Phase

| Failure | Behavior | Recovery |
|---|---|---|
| LLM API error | Returns `"not_task"` (line 1084-1089) | Message falls through to direct chat — no orchestration triggered |
| Empty LLM response | `_extract_json("")` returns None → returns `"not_task"` | Same as above |
| Model not found (404) | Exception caught → `"not_task"` | Same as above |
| Regex pattern match false positive | Returns `"not_task"` without LLM | Task that should be orchestrated goes to direct chat |

**Nothing is lost** in classification failures — the message is delivered to the being's LLM directly, just without the orchestration framework.

### 3.2 Planning Phase (`_phase_plan`)

| Failure | Behavior | Recovery |
|---|---|---|
| No online beings | `raise RuntimeError("No online beings available")` (line 472) | Caught at `_orchestrate` line 387. Sets status FAILED, persists empty result, posts failure message to chat, marks task failed. |
| LLM returns empty reply | `reply = ""` → `_parse_plan("")` raises JSONDecodeError → fallback single-being plan using raw reply as instructions (line 1313-1322) | Produces a degenerate plan delegating to one being with empty instructions |
| LLM API 400/429/500 | `handle_turn` logs `loop_error` and returns `{"assistant": {"text": "loop_error: ..."}}` (loop.py:147-148) | The error string becomes the "reply" — `_parse_plan` fails to parse JSON → fallback plan with error string as instructions |
| LLM hangs indefinitely | Thread blocks forever at `bridge.handle_turn()` | **NO TIMEOUT.** The orchestration thread hangs forever. The `_active` dict entry remains with status `planning`. |
| `_parse_plan` hallucinated being IDs | Fuzzy-matched or first-being fallback (line 1328-1334) | Being may receive wrong task type for their capabilities |
| Plan JSON has 0 sub_tasks | Empty `sub_tasks` triggers fallback (line 1342-1349) | Single-being plan to first available being |

**CRITICAL:** Planning has no timeout guard. A hung LLM call will block the orchestration thread indefinitely. The `_active` dict entry will remain in `STATUS_PLANNING` forever with no mechanism to unstick it.

### 3.3 Delegation Phase (`_execute_subtask`)

| Failure | Behavior | Recovery |
|---|---|---|
| `bridge.handle_turn()` raises | `output = f"[Error: {exc}]"` (line 670) | Being status restored to "online". Error string stored as output. Review phase marks this as unapproved with score 0.0. Synthesis proceeds with error placeholder. |
| Being offline (status check skipped) | No pre-check; `handle_turn` proceeds | Bridge has no being-availability gate — it will call the LLM regardless of the being's "online" status in `mc_beings`. |
| Empty output | `output = ""` stored | Review phase detects empty and marks unapproved. Synthesis gets "(no output)" placeholder. |
| Workspace path not found | `bridge.handle_turn` may fail on context search | Caught at line 669 as general exception |
| Parallel thread hangs (non-sequential mode) | `t.join(timeout=300)` returns after 5 min | Thread continues running. Being status is never reset to "online" (the `finally` block is in `_execute_subtask` which runs in the hung thread). Being stays "busy" forever. |
| Semantic memory write fails | Warning logged only (line 700-703) | Non-fatal. Task proceeds normally. |
| Sequential mode prior-output missing | `_collect_prior_outputs` returns only completed outputs (line 1288-1300) | Later beings get less context if earlier beings failed |

**IDENTIFIED BUG (being status on thread hang):** If a delegated thread hangs and `t.join(timeout=300)` times out, the thread's `finally` block has not run. The being's status remains "busy" in the dashboard with no cleanup mechanism.

### 3.4 Review Phase (`_phase_review`)

| Failure | Behavior | Recovery |
|---|---|---|
| Empty output from being | `not output` check at line 731 | Skips review loop, stores `approved=False, quality_score=0.0`. Synthesis proceeds. |
| Review LLM returns malformed JSON | `_parse_review` catches exception → returns `approved=True` (line 1382) | **BUG:** Silent auto-approval. Poor output accepted without revision. |
| Review LLM returns empty | `reply = ""` → same malformed JSON path | Same bug — auto-approval. |
| Revision `handle_turn` raises | Warning logged, original output kept (line 810-811) | Being retains its original output for synthesis. |
| max_revisions exhausted without approval | Review stored regardless of approval status (line 758) | Synthesis proceeds with unapproved output. No hard stop. |
| Review accumulates in orchestration session | All reviews share `orchestration:{task_id}` session | Session context grows unbounded across all review rounds for all beings. May cause context overflow on large tasks. |

### 3.5 Synthesis Phase (`_phase_synthesize`)

| Failure | Behavior | Recovery |
|---|---|---|
| Stage 1 synthesis empty | Falls to stage 2 (line 950-953) | Summarize-then-synthesize |
| Stage 1 synthesis raises | Falls to stage 2 (line 949-953) | Same |
| Stage 2 per-being summarization fails | Truncated raw output used (line 989) | `raw[:2000] + "[... truncated ...]"` |
| Stage 2 synthesis empty | Falls to concatenation (line 1020-1026) | Raw summaries joined with disclaimer |
| Stage 2 synthesis raises | Falls to concatenation (line 1018-1026) | Same |
| All fallbacks exhausted | Concatenated summaries returned | Functional but unpolished output delivered to user |
| Token budget underestimates actual usage | Truncation based on `DEFAULT_MODEL_MAX_INPUT=200_000` | May still overflow if actual model has smaller context window |
| `_persist_task_result` raises | Warning logged (line 1168-1169) | Task result lost from DB. Semantic memory not written. |
| `update_task` raises | Silent — board task remains "in_progress" | Task appears stuck on the board |

### 3.6 Delivery Phase

| Failure | Behavior | Recovery |
|---|---|---|
| `dashboard.create_message()` raises | Not caught — bubbles to `_orchestrate` line 387 | Sets status FAILED, posts failure message (which may also fail). |
| Representation update fails | Warning logged (line 1282-1285) | Non-fatal. REPRESENTATION.md not updated. |
| TEAM_CONTEXT.md update fails | Warning logged (line 1222-1223) | Non-fatal. |

### 3.7 Process-Level Failures

| Failure | Behavior | Recovery |
|---|---|---|
| Process crash during orchestration | All `_active` state is lost | **No recovery.** Tasks in `mc_task_history` and `task_results` may exist but there is no way to resume orchestration. |
| Multiple simultaneous orchestrations | All run concurrently — `_active` is a dict, `_lock` used for access | Safe for state reads/writes. But beings may receive concurrent delegations from different tasks. |
| Dream cycle fails | Warning logged (line 912) | Non-fatal. |

---

## 4. State Machine

### 4.1 Orchestration Task States

States are defined as module-level constants in `engine.py:44-51`:

```
STATUS_PLANNING    = "planning"
STATUS_DELEGATING  = "delegating"
STATUS_AWAITING    = "awaiting_completion"
STATUS_REVIEWING   = "reviewing"
STATUS_REVISING    = "revising"
STATUS_SYNTHESIZING = "synthesizing"
STATUS_COMPLETED   = "completed"
STATUS_FAILED      = "failed"
```

These exist ONLY in the `_active` in-memory dict. They are NOT stored in the database. `mc_task_history` gets event log entries but not the state enum directly.

### 4.2 State Transitions

```
[not started]
     |
     | orchestration_engine.start() called
     v
  PLANNING ─────────────────────────────────────────> FAILED
     |                                                    ^
     | _phase_plan() succeeds                             |
     v                                                    |
  DELEGATING ──────────────────────────────────────> FAILED
     |                                                    |
     | all subtasks registered (before actual execution)  |
     v                                                    |
  AWAITING_COMPLETION ─────────────────────────────> FAILED
     |                                                    |
     | all _execute_subtask() threads complete/join       |
     v                                                    |
  REVIEWING ───────────────────────────────────────> FAILED
     |  ^                                                 |
     |  | review round completes without approval         |
     |  |                                                 |
     v  |                                                 |
  REVISING (per-being, transient) ─────────────────> FAILED
     |                                                    |
     | all beings reviewed (approved or max_revisions)    |
     v                                                    |
  SYNTHESIZING ────────────────────────────────────> FAILED
     |
     | synthesis LLM call (with fallbacks)
     v
  COMPLETED
```

**Transition triggers:**

| From | To | Trigger | File:Line |
|---|---|---|---|
| (none) | PLANNING | `start()` called | engine.py:298 (implicit — state initialized in start()) |
| PLANNING | DELEGATING | `_set_status(task_id, STATUS_DELEGATING)` | engine.py:529 |
| DELEGATING | AWAITING | `_set_status(task_id, STATUS_AWAITING)` | engine.py:560 |
| AWAITING | REVIEWING | `_set_status(task_id, STATUS_REVIEWING)` | engine.py:720 |
| REVIEWING | REVISING | `_set_status(task_id, STATUS_REVISING)` | engine.py:768 |
| REVISING | REVIEWING | `_set_status(task_id, STATUS_REVIEWING)` | engine.py:815 |
| REVIEWING | SYNTHESIZING | `_set_status(task_id, STATUS_SYNTHESIZING)` | engine.py:819 |
| SYNTHESIZING | COMPLETED | `_set_status(task_id, STATUS_COMPLETED)` | engine.py:879 |
| (any) | FAILED | unhandled exception in `_orchestrate` | engine.py:389 |

### 4.3 Stuck States

| State | Stuck Condition | Mechanism to Unstick |
|---|---|---|
| PLANNING | LLM call hangs in `handle_turn` | **None.** Thread blocks forever. |
| AWAITING | Parallel delegated thread hangs (after `t.join(timeout=300)`) | 5-min join timeout releases the orchestration thread. The delegated thread may still run in background. |
| REVIEWING | Review LLM hangs | **None.** Thread blocks forever. |
| SYNTHESIZING | Synthesis LLM hangs | **None.** Thread blocks forever. |
| FAILED | Terminal state | No recovery. Must re-send the task. |
| COMPLETED | Terminal state | N/A |

**The only phase with a timeout is delegation (parallel mode, 5-min join timeout).** Planning, review, and synthesis phases can hang indefinitely if the LLM provider is unresponsive.

### 4.4 Project Task Board States (ProjectService)

Separate from orchestration states, the project task on the board (`mc_task_assignments`, `project_tasks`) uses statuses from `projects/service.py:10`:

```
backlog | todo | in_progress | in_review | blocked | review | done | cancelled
```

The orchestration engine only sets board statuses at two points:
- `start()`: creates task with `status="in_progress"` (dashboard.create_task)
- `_phase_synthesize()`: updates to `status="done"` (line 878)
- On failure: updates to `status="failed"` (line 400)

The board task never transitions through "in_review", "blocked", or "review" — those statuses are unused by orchestration.

### 4.5 Sub-Agent Protocol States (for reference)

The SubAgentProtocol (protocol.py:18-25) uses a different, richer state machine:

```
accepted -> in_progress -> completed
                        -> failed
                        -> timed_out
         -> blocked
```

These are persisted to `subagent_runs` table. Not used by OrchestrationEngine.

---

## 5. Sub-Agent System vs Orchestration Engine

### 5.1 SubAgentWorkerFactory / SubAgentOrchestrator

**Files:**
- `src/bomba_sr/subagents/orchestrator.py` — `SubAgentOrchestrator` (161 lines)
- `src/bomba_sr/subagents/worker.py` — `SubAgentWorkerFactory` (53 lines)
- `src/bomba_sr/subagents/protocol.py` — `SubAgentProtocol` (591 lines)

**How it works:**

1. A parent turn calls a tool (`sessions_spawn` via `builtin_subagents.py`) which calls `SubAgentOrchestrator.spawn_async()`.
2. `spawn_async` validates depth, records to `subagent_runs` table (via `SubAgentProtocol.spawn()`), and submits work to a `ThreadPoolExecutor`.
3. The worker is `SubAgentWorkerFactory.create_worker()` which calls `bridge.handle_turn()` with `TurnProfile.TASK_EXECUTION` and a `sub_session_id = f"subagent-{run_id}"`.
4. Progress events are recorded via `protocol.progress()`, `protocol.complete()`, `protocol.fail()`.
5. Results are written to `shared_working_memory_writes` table via `protocol.write_shared_memory()`.

**Key capabilities:**
- Full persistence: `subagent_runs`, `subagent_events`, `shared_working_memory_writes` tables
- Idempotency: `UNIQUE(parent_turn_id, idempotency_key)` prevents duplicate spawns
- Lineage tracking: `parent_run_id` chain supports depth enforcement
- Cascade stop: `SubAgentProtocol.cascade_stop()` recursively marks children as timed_out
- Crash storm detection: `CrashStormDetector` with configurable window/max/cooldown
- Event streaming: `stream_events()` for polling from the HTTP API
- Announcement with retry: `announce_with_retry()` for delivery guarantees

### 5.2 OrchestrationEngine

**File:** `src/bomba_sr/orchestration/engine.py` (1402 lines)

**How it works:**
1. Triggered by `DashboardService._handle_orchestrated_task()` — only for Prime + full_task.
2. Runs a deterministic pipeline: plan → delegate → review → synthesize in a single background thread.
3. Sub-tasks are executed as nested `bridge.handle_turn()` calls, either in sequence or in parallel Python threads.
4. State is in `self._active` (Python dict) and conversational turns in SQLite via normal memory storage.
5. Results are delivered via `dashboard.create_message()`.

**Key capabilities:**
- Multi-step pipeline with review/revision cycles
- Sequential vs parallel execution strategies (auto-detected)
- Two-stage synthesis fallback
- Representation file updates for beings
- TEAM_CONTEXT.md updates
- Dream cycle auto-trigger
- Task board integration (parent task only)

### 5.3 Where They Overlap

| Capability | SubAgentOrchestrator | OrchestrationEngine |
|---|---|---|
| Calls `bridge.handle_turn()` for sub-tasks | Yes (SubAgentWorkerFactory) | Yes (_execute_subtask) |
| Runs sub-tasks in threads | Yes (ThreadPoolExecutor) | Yes (threading.Thread) |
| State persistence | Full DB (subagent_runs table) | Partial (task_results table, memory turns) |
| Multi-being delegation | No (single sub-agent at a time per spawn) | Yes (plans across all beings) |
| Revision cycles | No | Yes (up to 2 rounds per being) |
| Synthesis | No | Yes (merge/sequential/compare strategies) |
| Cascade stop | Yes (SubAgentProtocol.cascade_stop) | No |
| Crash storm protection | Yes (CrashStormDetector) | No |
| Depth enforcement | Yes (max_spawn_depth) | No |
| Idempotency | Yes (idempotency_key) | No |
| Event streaming | Yes (subagent_events table) | No (SSE only via dashboard _emit_event) |
| Recovery from crash | Yes (state in DB) | **No** (state in memory only) |
| Timeout per sub-task | Yes (run_timeout_seconds in protocol) | 5 min join only (parallel mode) |
| Progress reporting | Yes (0-100% progress_pct) | No (SSE events only) |

### 5.4 Why Orchestration Does Not Use Sub-Agent Infrastructure

The code comment in `engine.py:1-11` states: "All orchestration context lives in regular conversation_turns with special session ID patterns — no new database tables." This design choice means:

- The orchestration session (`orchestration:{task_id}`) accumulates all planning, review, and synthesis turns in a single conversation thread, giving Prime conversational memory across phases.
- Each being's session (`subtask:{task_id}:{being_id}`) isolates their working context and supports revision by replaying prior turns.

The sub-agent system was designed for tool-invoked, non-deterministic sub-tasks (arbitrary depth, arbitrary goals, with the LLM deciding when to spawn). The orchestration engine is designed for a specific, structured workflow (plan, delegate, review, synthesize) where Prime is always the top-level orchestrator.

However, the two designs have drifted. The orchestration engine reimplements thread management, timeout logic, status tracking, and memory writing from scratch — all of which already exist in the sub-agent system with better guarantees.

### 5.5 What Orchestration Lacks by Not Using Sub-Agent Infrastructure

1. **State recovery**: Sub-agents persist to DB. OrchestrationEngine state is lost on process crash.
2. **Cascade stop**: When the parent budget is exhausted or Prime's AgenticLoop hits `max_iterations`, the loop triggers `cascade_stop_session()` (bridge.py:879-882). But this only stops `subagent_runs` entries — it has no effect on running OrchestrationEngine threads, which are not registered anywhere.
3. **Timeout enforcement per being**: The sub-agent protocol has `run_timeout_seconds` enforced in the protocol. OrchestrationEngine only has the 5-minute thread join in parallel mode.
4. **Idempotency**: Retrying an orchestrated task creates a new task. Sub-agent spawns with the same idempotency_key are deduplicated.
5. **Progress visibility**: Sub-agents emit structured events (0-100%). Orchestration emits coarse SSE events with no progress percentage.
6. **Depth enforcement**: Sub-agents cannot spawn sub-sub-agents beyond `max_spawn_depth`. An orchestration LLM could hallucinate instructions that cause a being to call `sessions_spawn` (since beings get full tool access), creating untracked sub-agent nesting.

---

## 6. ASCII Diagrams

### 6.1 Full Pipeline: Message to Final Delivery

```
User sends message
       |
       v
route_to_being(being_id, content)          [dashboard/service.py:739]
       |
       | (background thread)
       v
_route_to_being_sync()                      [service.py:748]
       |
       +-- being offline? --> post "offline" message, return
       +-- being is voice? --> post "use Voice panel" message, return
       +-- no bridge? --> post "offline" message, return
       |
       v
_classify_message(content)                  [service.py:1053]
       |
       +-- short/greeting regex match --> "not_task"
       +-- LLM call (gpt-4o-mini) --> "not_task" | "light_task" | "full_task"
       +-- LLM error --> "not_task" (safe default)
       |
       +---[not_task]---> direct bridge.handle_turn(), no task
       |
       +---[light_task]--> _auto_create_task()
       |                   -> bridge.handle_turn()
       |                   -> task -> done
       |
       +---[full_task, being_id != "prime"]---> _auto_create_task()
       |                                         _generate_task_steps()
       |                                         bridge.handle_turn()
       |                                         task -> done
       |
       +---[full_task, being_id == "prime", orchestration_engine set]
               |
               v
       _handle_orchestrated_task()           [service.py:930]
               |
               +--> post "I'll orchestrate" message to chat (immediate)
               +--> orchestration_engine.start(goal) [engine.py:268]
                       |
                       +--> create parent task on board (in_progress, owner=prime)
                       +--> init _active[task_id] state dict
                       +--> spawn background thread _orchestrate()
                       +--> return {task_id, status: "planning"} (immediate)

====== BACKGROUND THREAD ======

_orchestrate(task_id)                       [engine.py:373]
       |
       v
_phase_plan(task_id)                        [engine.py:428]
       |
       +--> list beings (exclude offline, exclude prime)
       +--> read REPRESENTATION.md for each being (800 chars)
       +--> build planning prompt (PLAN_SYSTEM_PROMPT + beings JSON + goal)
       +--> bridge.handle_turn(tenant=prime, session=orchestration:{task_id},
       |     disable_tools=True, include_representation=True)
       +--> _parse_plan(reply)
       |       +--> extract JSON
       |       +--> validate being IDs (fuzzy match if needed)
       |       +--> auto-detect sequential strategy
       |       +--> fallback: single-being plan if parse fails
       +--> store plan in _active[task_id]["plan"]
       |
       v
_phase_delegate(task_id)                    [engine.py:527]
       |
       +--> set status: DELEGATING
       +--> log subtask_created events
       +--> set each being's status: "busy"
       +--> set status: AWAITING
       |
       +---[sequential strategy]---
       |       for each sub:
       |         _collect_prior_outputs()
       |         _execute_subtask(sub, prior_outputs)
       |         (blocks until complete)
       |
       +---[merge/compare/other]---
               for each sub:
                 Thread(target=_execute_subtask).start()
               for each thread:
                 t.join(timeout=300)   # 5 min max
               (continues even if threads still running)

_execute_subtask(task_id, sub)              [engine.py:581]
       |
       +--> build delegation_message
       |     (identity prefix for ACT-I + title + context + instructions + criteria)
       +--> bridge.handle_turn(
       |     tenant=being.tenant_id,
       |     session=subtask:{task_id}:{being_id},
       |     user_id="prime->{being_id}",
       |     search_query=sub.title,
       |     full tools enabled
       |    )
       +--> capture output (may be empty or "[Error:...]")
       +--> store output in _active[task_id]["subtask_outputs"][being_id]
       +--> if non-error output: write semantic memory to being's tenant
       +--> restore being status: "online"
       |
       v
(after all sub-tasks complete)
       |
_update_team_context_outcomes()             [engine.py:1171]
_update_being_representations()            [engine.py:1225] (with empty synthesis)
       |
       v
_phase_review(task_id)                      [engine.py:718]
       |
       +--> set status: REVIEWING
       +--> for each sub:
       |     if empty/error output: skip, store approved=False, score=0.0
       |     for revision_round in 0..max_revisions:
       |       review_prompt = REVIEW_SYSTEM_PROMPT.format(output[:8000])
       |       bridge.handle_turn(tenant=prime, session=orchestration:{task_id},
       |                          disable_tools=True)
       |       review = _parse_review(reply)
       |       if approved or revision_round >= max_revisions: break
       |       else:
       |         set status: REVISING
       |         send revision message to being's subtask session
       |         bridge.handle_turn(being's session, full tools)
       |         update output in _active
       |         set status: REVIEWING
       +--> store review in _active[task_id]["subtask_reviews"]
       |
       v
_phase_synthesize(task_id)                  [engine.py:817]
       |
       +--> set status: SYNTHESIZING
       +--> _persist_task_result(..., synthesis="")  [pre-synthesis persist]
       +--> truncate outputs to token budget
       +--> _attempt_synthesis():
       |     Stage 1: bridge.handle_turn(disable_tools=True, synthesis prompt)
       |       --> if non-empty: done
       |     Stage 2: _fallback_summarize_then_synthesize()
       |       --> per-being: provider.generate(summarize to 500 words)
       |       --> bridge.handle_turn(disable_tools=True, summarized prompt)
       |         --> if non-empty: done
       |     Last resort: concatenate summaries
       +--> _update_task_result_synthesis(final_output)
       +--> _update_being_representations() (with synthesis text)
       +--> dashboard.create_message(sender=prime, content=final_output)
       +--> dashboard.update_task(status="done")
       +--> set status: COMPLETED
       +--> maybe trigger dream cycle
```

### 6.2 State Machine Diagram

```
                          +----------+
         start()          |          |
  ----------------------> | PLANNING |
                          |          |
                          +----+-----+
                               |
                 plan created  |   exception
                               |  +-------> FAILED (terminal)
                               v
                         +------------+
                         | DELEGATING |
                         +------+-----+
                                |
         subtasks registered    |   exception
                                |  +-------> FAILED (terminal)
                                v
                     +--------------------+
                     | AWAITING_COMPLETION|
                     +--------+-----------+
                              |
      all threads joined/     |   exception
      sequential done         |  +-------> FAILED (terminal)
                              v
                        +-----------+
                        | REVIEWING |  <-----+
                        +-----+-----+        |
                              |              |
                   approved   |   not approved, round < max
                  or max revs |  +---------> REVISING
                              |                   |
                              |   <---------------+
                              v
                      +-------------+
                      | SYNTHESIZING|
                      +------+------+
                             |
        synthesis done       |   exception
                             |  +-------> FAILED (terminal)
                             v
                        +-----------+
                        | COMPLETED |  (terminal)
                        +-----------+

FAILED: marks project task as "failed", posts error to chat, persists partial results.
COMPLETED: marks project task as "done", posts synthesis to chat.
Both are terminal — no resume path exists.
```

### 6.3 Parallel vs Sequential Execution

```
PARALLEL (merge/compare strategy):

  orchestration thread
       |
       +-- Thread 1: _execute_subtask(forge) -----> handle_turn -> output_forge
       |
       +-- Thread 2: _execute_subtask(scholar) ---> handle_turn -> output_scholar
       |
       +-- Thread 3: _execute_subtask(recovery) --> handle_turn -> output_recovery
       |
       | (t.join(timeout=300) for each thread)
       |
       v  (after all threads joined or timed out)
    _phase_review (all beings reviewed independently)
       |
       v
    _phase_synthesize (all outputs merged)


SEQUENTIAL (sequential strategy):

  orchestration thread
       |
       v
    _execute_subtask(being_1) --> handle_turn --> output_1
       |
       v (prior_outputs = {being_1: output_1})
    _execute_subtask(being_2) --> handle_turn(context includes output_1) --> output_2
       |
       v (prior_outputs = {being_1: output_1, being_2: output_2})
    _execute_subtask(being_3) --> handle_turn(context includes output_1, output_2) --> output_3
       |
       v
    _phase_review
       |
       v
    _phase_synthesize
```

### 6.4 Failure/Recovery Flow

```
Per-phase failure handling:

PLANNING failure:
  LLM error     -> "loop_error: ..." returned as text
                -> _parse_plan fails -> fallback single-being plan
                -> orchestration continues (degraded)

  No beings     -> RuntimeError raised
                -> caught at _orchestrate:387
                -> _persist_task_result(fail_state, "[FAILED: ...]")
                -> dashboard.update_task(status="failed")
                -> post failure message to chat
                -> done (no recovery)

  LLM hangs     -> orchestration thread blocks forever (NO RECOVERY)

DELEGATION failure:
  Exception in _execute_subtask:
                -> output = "[Error: exc]"
                -> being status restored
                -> continues to next subtask (no abort)

  Thread hangs (parallel):
                -> t.join(timeout=300) releases orchestration thread
                -> hanging thread continues running in background
                -> being status NEVER restored (finally not reached)
                -> orchestration continues with missing output

REVIEW failure:
  Parse failure -> auto-approve (BUG)
  LLM hangs    -> orchestration thread blocks forever (NO RECOVERY)

SYNTHESIS failure:
  Stage 1 fail -> Stage 2 (summarize + re-synthesize)
  Stage 2 fail -> concatenate summaries
  Result:      -> always returns something, even if degraded
  Exception in create_message -> bubbles to _orchestrate -> FAILED
```

### 6.5 Sub-Agent System Comparison

```
ORCHSTRATION ENGINE                    SUB-AGENT SYSTEM

dashboard.route_to_being()             bridge.handle_turn() [LLM calls sessions_spawn tool]
    |                                      |
    v                                      v
_handle_orchestrated_task()            SubAgentOrchestrator.spawn_async()
    |                                      |
    v                                      v
OrchestrationEngine.start()            SubAgentProtocol.spawn()
    |                                      |  (writes to subagent_runs DB)
    v                                      v
threading.Thread(_orchestrate)         ThreadPoolExecutor.submit(_run_worker)
    |                                      |
    v                                      v
_phase_plan/_phase_delegate/...        SubAgentWorkerFactory.worker()
    |                                      |
    v                                      v
bridge.handle_turn() for each being    bridge.handle_turn()
    |                                      |  (TurnProfile.TASK_EXECUTION)
    v                                      v
In-memory dict (_active)               subagent_runs table (persisted)
    |                                      |
    v                                      v
SSE events (transient)                 subagent_events table (persisted)
    |                                      |
    v                                      v
dashboard.create_message()             shared_working_memory_writes table
(final output to chat)                 (parent can poll and merge)

NO cascade stop                        SubAgentProtocol.cascade_stop()
NO crash recovery                      CrashStormDetector + DB state
NO idempotency                         UNIQUE(parent_turn_id, idempotency_key)
NO depth limit                         max_spawn_depth enforced
NO run timeout                         run_timeout_seconds per sub-agent
```

---

## 7. Key Findings and Risks

### 7.1 Critical Issues

**C1. In-memory state — no crash recovery (engine.py:258)**
The `_active` dict holds all active orchestration state. A Python process crash during orchestration leaves the board task stuck in `in_progress` with no way to resume. Tasks in `task_results` will have an empty `synthesis` field if the crash occurred before synthesis completed. Mitigation: persist orchestration state to a DB table at every phase transition.

**C2. No timeout on planning, review, and synthesis phases**
The `_phase_plan`, review LLM calls, and synthesis calls have no timeout. A hung LLM call blocks the orchestration thread indefinitely. Mitigation: wrap LLM calls in a thread with a timeout (e.g., `concurrent.futures.ThreadPoolExecutor` with `future.result(timeout=N)`).

**C3. Auto-approve on review parse failure (engine.py:1382)**
When `_parse_review` fails to parse the LLM response, it returns `approved=True` with no feedback. Any output — including errors, empty strings (though those are caught earlier), or garbage — is silently accepted. Mitigation: return `approved=False` on parse failure and log a warning. Use the raw reply as feedback.

**C4. Being status not restored on thread hang (engine.py:569-579)**
In parallel mode, if `_execute_subtask` hangs and `t.join(timeout=300)` returns, the thread's `finally` block has not executed. The being remains in "busy" status in the dashboard with no cleanup. Mitigation: move status restoration to the orchestration thread after the join.

**C5. Hardcoded absolute path (engine.py:595-597, 1081)**
```python
workspace = str(Path("/Users/zidane/Downloads/PROJEKT") / ws)
# and:
return "/Users/zidane/Downloads/PROJEKT/workspaces/prime"
```
This makes the codebase non-portable. It works only on the author's machine. Mitigation: use `Path(__file__).resolve().parent.parent.parent.parent` or read from a config variable.

### 7.2 Significant Issues

**S1. Orchestration session accumulates unbounded context (engine.py:747-754)**
All review calls for all beings share `orchestration:{task_id}` session. For a task with 4 beings, each reviewed twice, that is 8 review LLM calls in one growing session. Combined with planning and synthesis in the same session, this risks context overflow and performance degradation from turn replay.

**S2. Sub-task board tracking absent**
`_phase_delegate` logs to `mc_task_history` but does not create sub-task entries in `project_tasks`. The dashboard shows one task for the entire orchestration with no sub-task breakdown. The `subtask_ids` dict in `_active` maps `being_id -> parent_task_id` (all the same value), which is misleading.

**S3. PLAN_SYSTEM_PROMPT injected as user message, not system message (engine.py:502)**
The planning prompt is embedded in the `user_message` field with a `[SYSTEM: ORCHESTRATION MODE]` prefix. It is not a proper system message. It goes through the context assembly pipeline (`ContextPolicyEngine.assemble`) where it may be compressed, truncated, or dropped if it exceeds the token budget. For a complex planning prompt with large beings JSON, this is a real risk.

**S4. Review output truncated to 8000 chars (engine.py:746)**
The output passed to the review prompt is `output[:8000]`. If a being produced a long, high-quality 50,000-character report, the reviewer only sees the first 8000 characters. The review verdict is based on an incomplete view of the output.

**S5. `task_id` identity ambiguity (engine.py:291)**
```python
actual_task_id = parent_task.get("id") or parent_task.get("task_id") or task_id
```
The board task has both `id` (row PK) and `task_id` (domain ID). The `actual_task_id` used to key `_active` may differ from the UUID generated in `start()`. The `orchestration:{task_id}` session uses `actual_task_id` (line 279), and `start()` returns `actual_task_id` (line 331), so this is consistent — but the initial UUID is discarded.

**S6. Synthesis token budget uses hardcoded model max (engine.py:62)**
`DEFAULT_MODEL_MAX_INPUT = 200_000` is used for truncation regardless of the actual model. If the configured model has a 100k context window, the synthesized prompt may still exceed it and get a context-exceeded API error.

**S7. `_phase_plan` TurnProfile defaults to CHAT**
`TurnProfile` is not set in the planning TurnRequest, so it defaults to `TurnProfile.CHAT` (bridge.py:87). The `TurnProfile.SUBAGENT_ORCHESTRATION` profile (context/policy.py:72-80) exists and has context weight allocations specifically tuned for orchestration (`working_memory: 0.28, predictions: 0.18`) but is never used.

### 7.3 Minor Issues

**M1. Sequential mode `_collect_prior_outputs` uses plan order, not completion order (engine.py:1295)**
```python
for sub in plan.sub_tasks:
    if sub.being_id == current_being_id:
        break
    output = state["subtask_outputs"].get(sub.being_id, "")
```
This assumes the plan order matches execution order, which is correct for sequential mode but would be incorrect if ever called in parallel mode.

**M2. `_active` is not pruned (engine.py:258)**
Completed and failed orchestrations remain in `_active` indefinitely. For long-running servers with many orchestrations, this is a memory leak.

**M3. Step-based progress for direct handle_turn tasks (service.py:849-853)**
The `_on_loop_iteration` callback advances `mc_task_steps` once per loop iteration. For a 5-step task and a 25-iteration agentic loop, steps advance faster than meaningful progress checkpoints.

**M4. `init_orchestration` must be called explicitly (service.py:911)**
If the server is started without calling `DashboardService.init_orchestration(project_svc)`, `orchestration_engine` remains `None` and all `full_task` messages to Prime fall through to direct chat silently.

---

## 8. File Reference Index

| File | Purpose | Key Lines Audited |
|---|---|---|
| `src/bomba_sr/orchestration/engine.py` | OrchestrationEngine — full pipeline | 1-1402 |
| `src/bomba_sr/dashboard/service.py` | DashboardService — classification, routing, task steps | 44-113, 748-990, 1053-1110 |
| `src/bomba_sr/runtime/bridge.py` | RuntimeBridge.handle_turn — LLM routing, context assembly | 130-260, 457-895, 960-1183 |
| `src/bomba_sr/runtime/loop.py` | AgenticLoop — tool-call iteration loop | 1-470 |
| `src/bomba_sr/subagents/orchestrator.py` | SubAgentOrchestrator — thread pool, crash detection | 1-161 |
| `src/bomba_sr/subagents/worker.py` | SubAgentWorkerFactory — bridge-backed sub-agent worker | 1-53 |
| `src/bomba_sr/subagents/protocol.py` | SubAgentProtocol — DB schema, state transitions, events | 1-591 |
| `src/bomba_sr/projects/service.py` | ProjectService — task board schema and CRUD | 1-275 |
| `src/bomba_sr/context/policy.py` | ContextPolicyEngine — context assembly, TurnProfile weights | 1-311 |
| `src/bomba_sr/storage/db.py` | RuntimeDB — SQLite WAL, thread-safe RLock | 1-80 |
