# AUDIT_ORCHESTRATION.md

Multi-Agent Orchestration System — Comprehensive Audit
Codebase: /Users/zidane/Downloads/PROJEKT
Audit date: 2026-03-06
Audited by: Claude Sonnet 4.6

---

## 1. PIPELINE END-TO-END TRACE

### 1.1 Entry Point — Message to Orchestration Trigger

**File:** `src/bomba_sr/dashboard/service.py`

The orchestration pipeline is entered exclusively through `DashboardService._route_to_being_sync()` (line 748). This method is called asynchronously via `route_to_being()` (line 739) which spawns a daemon thread.

**Step 1: Message Classification** (`_classify_message`, line 1053)

Two-stage classifier:

1. **Regex fast-path** (line 1062): `_NOT_TASK_PATTERNS` matches greetings/casual phrases. If matched or `len(stripped) < 4`, returns `"not_task"` immediately — no LLM call.

2. **LLM classifier** (line 1066): Calls `provider.generate()` with `_CLASSIFY_MODEL` (env `BOMBA_CLASSIFY_MODEL`, default `openai/gpt-4o-mini`). System prompt `_CLASSIFY_SYSTEM_PROMPT` (line 47) requests JSON `{"classification": "not_task"|"light_task"|"full_task"}`.

   - `not_task` — casual chat, no task created
   - `light_task` — single-action task, direct to being
   - `full_task` — multi-step task that benefits from tracking

   On classifier failure or unrecognized value → safe default: `"not_task"` (line 1088).

**Step 2: Orchestration Gate** (line 809-817)

Intercept condition (all must be true):
```python
classification == "full_task"
and being_id == "prime"
and self.orchestration_engine is not None
and self.project_service is not None
```

If `being_id != "prime"` or engine not initialized → falls through to direct `handle_turn()` for the being.

**Step 3: Orchestration Start** (`_handle_orchestrated_task`, line 930)

1. Acknowledge immediately: `create_message(sender="prime", ...)` posts acknowledgment to user chat.
2. Updates Prime's status to `"busy"` in `mc_beings`.
3. Calls `orchestration_engine.start(goal=content, requester_session_id=session_id, sender=sender)`.
4. Returns. Orchestration background thread takes over.

---

### 1.2 Task Creation

**File:** `src/bomba_sr/orchestration/engine.py`, `start()`, line 268

```python
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
```

**BUG:** `parent_task.get("id")` always returns `None` — normalized task dict uses `"task_id"` key, not `"id"`.

**Task schema** (`project_tasks` table, `src/bomba_sr/projects/service.py`, line 35):
```sql
CREATE TABLE IF NOT EXISTS project_tasks (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  project_id TEXT NOT NULL,        -- always "mc-project"
  title TEXT NOT NULL,             -- goal[:120]
  description TEXT,                -- full goal text
  status TEXT NOT NULL,            -- "in_progress"
  priority TEXT NOT NULL,          -- "high"
  owner_agent_id TEXT,             -- "prime"
  parent_task_id TEXT DEFAULT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(tenant_id, task_id)
);
```

**In-memory state structure** (engine.py, line 293) — pure in-memory, NOT persisted:
```python
state = {
    "task_id": actual_task_id,
    "goal": goal,
    "orchestration_session": f"orchestration:{task_id}",
    "requester_session": requester_session_id,
    "sender": sender,
    "status": STATUS_PLANNING,
    "plan": None,
    "subtask_ids": {},        # being_id -> parent task_id (misleading — see Bug 6)
    "subtask_outputs": {},    # being_id -> output text
    "subtask_reviews": {},    # being_id -> review dict
    "created_at": datetime.now(timezone.utc).isoformat(),
}
```

---

### 1.3 Planning Phase

**File:** `src/bomba_sr/orchestration/engine.py`, `_phase_plan()`, line 428

**Beings gathered:** `dashboard.list_beings()` → filters out `status == "offline"` and `id == "prime"`. For each assignable being:
- Basic fields: `id`, `name`, `role`, `status`, `skills`
- ACT-I enrichment: `domain`, `top_clusters` (first 3 cluster names from `acti/loader.py`)
- REPRESENTATION.md: first 800 chars from `{workspace}/REPRESENTATION.md` if it exists

**System prompt** (`PLAN_SYSTEM_PROMPT`, line 146): Instructs Prime to respond with ONLY JSON:
```json
{
  "summary": "Brief plan summary",
  "synthesis_strategy": "merge|sequential|compare",
  "sub_tasks": [{"being_id":"...","title":"...","instructions":"...","done_when":"..."}]
}
```

**LLM call** (line 496): `bridge.handle_turn(TurnRequest(tenant_id="tenant-prime", session_id="orchestration:{task_id}", user_id="orchestrator", disable_tools=True))`

**Plan parsing** (`_parse_plan`, line 1302):
- Extracts JSON from response (handles markdown fences)
- Validates `being_id` — fuzzy match if not exact, fallback to first being
- Auto-upgrades to `"sequential"` if instructions contain keywords like `combine`, `summarize`, `synthesize` (line 1356)
- On JSON parse failure: single fallback sub-task to first available being (line 1312)

---

### 1.4 Sub-Task Creation / Delegation

**File:** `src/bomba_sr/orchestration/engine.py`, `_phase_delegate()`, line 527

Sub-tasks are **not stored as separate board entries** (line 538, explicit comment). Only `mc_task_history` logs are written per sub-task.

**Execution routing** (line 562):
- `strategy == "sequential"` → serial loop, each being receives prior outputs via `_collect_prior_outputs()`
- Otherwise → parallel `threading.Thread`, 5-minute join timeout per sub-task

---

### 1.5 Sub-Task Execution

**File:** `src/bomba_sr/orchestration/engine.py`, `_execute_subtask()`, line 581

**Session/tenant:** `session = "subtask:{task_id}:{being_id}"`, `tenant_id = being.get("tenant_id") or f"tenant-{sub.being_id}"`

**Delegation message** (line 627):
```
[IDENTITY CONTEXT]                    (ACT-I beings only)
You are operating as an ACT-I specialized being.
{acti_identity_text}
[END IDENTITY CONTEXT]

You have been assigned a sub-task by SAI Prime.
TASK TITLE: {sub.title}

CONTEXT FROM OTHER BEINGS:           (sequential mode only)
--- {prior_being_id}'s findings ---
{prior_output}

INSTRUCTIONS: {sub.instructions}
ACCEPTANCE CRITERIA: {sub.done_when}
```

**handle_turn call** (line 648):
```python
result = self.bridge.handle_turn(TurnRequest(
    tenant_id=tenant_id,
    session_id=f"subtask:{task_id}:{being_id}",
    user_id=f"prime->{sub.being_id}",
    user_message=delegation_message,
    workspace_root=workspace,
    search_query=sub.title,
    # profile defaults to TurnProfile.CHAT (not TASK_EXECUTION)
    # disable_tools NOT set — full tool access
))
```

**Result capture** (line 659): `output = (result.get("assistant") or {}).get("text", "")` — empty string stored on empty result, DEBUG log only.

**Post-execution:**
1. Being status restored to `"online"` (in `finally` — guaranteed)
2. Output stored in `self._active[parent_task_id]["subtask_outputs"][sub.being_id]`
3. If non-empty: semantic memory written to being's tenant store (`learn_semantic`, confidence=0.8, first 800 chars)
4. SSE event `"subtask_completed"` with first 200 chars preview

---

### 1.6 Review Phase

**File:** `src/bomba_sr/orchestration/engine.py`, `_phase_review()`, line 718

`max_revisions = 2` (hardcoded, line 727).

- If output empty or starts with `"[Error"` → auto-fail review, no LLM call.
- Otherwise: up to 3 iterations (review → revise → review):
  - Review truncates output to 8000 chars (line 746)
  - LLM call: `bridge.handle_turn(..., disable_tools=True)` using orchestration session
  - **On JSON parse failure:** `_parse_review` returns `{"approved": True, "quality_score": 0.6, "notes": "Review parsing failed — auto-approving"}` — **silent quality gate bypass**

---

### 1.7 Synthesis Phase

**File:** `src/bomba_sr/orchestration/engine.py`, `_phase_synthesize()`, line 817

Token budget (line 830):
```python
available_tokens = 200_000 - 40_000 - 16_000  # = 144,000 (HARDCODED — ignores actual model)
per_being_chars = int(max(144_000 // len(outputs), 2000) * 3.5)
```

**Synthesis attempts:**
1. **Stage 1:** `handle_turn(..., disable_tools=True)` using orchestration session
2. **Stage 2 fallback:** Per-being summarization via `provider.generate()` direct + re-synthesis via `handle_turn`
3. **Last resort:** Concatenate raw summaries with disclaimer

Final output: `create_message(sender="prime", content=final_output)` → `mc_messages` → SSE → UI.
`update_task(status="done")` → `project_tasks`.
`_update_task_result_synthesis()` → `task_results` UPDATE.

---

### 1.8 Final Delivery

```python
# engine.py:869
self.dashboard.create_message(sender="prime", content=final_output,
    targets=[state["sender"]], msg_type="direct", task_ref=task_id)
self.dashboard.update_task(self.project_svc, task_id, status="done")
self._set_status(task_id, STATUS_COMPLETED)
```

Post-delivery: dream cycle auto-triggered every `BOMBA_DREAM_TRIGGER_EVERY` (default 5) completed tasks (line 893).

---

## 2. FAILURE MODE ANALYSIS

### 2.1 Planning Phase

| Failure | What Happens |
|---|---|
| No online beings | `RuntimeError` line 472 → caught → `STATUS_FAILED` |
| LLM returns empty/bad JSON | `_parse_plan` fallback → single-being plan to first available being |
| LLM returns wrong being_id | Fuzzy match; if no match → first available being |
| API error (400/429/500) | Loop exception → empty plan → fallback single-being plan |
| ACT-I context load fails | Silently caught (line 476), continues without enrichment |
| REPRESENTATION.md unreadable | Silently caught (line 466), continues |

### 2.2 Delegation Phase

| Failure | What Happens |
|---|---|
| handle_turn raises exception | Caught line 669, `output = "[Error: {exc}]"`. Being status restored. |
| handle_turn returns empty | `output = ""`, stored. DEBUG log only. No retry. |
| Parallel thread times out (5 min) | Thread abandoned (keeps running in background), output stays `""` |
| Sequential being errors | Error output stored; next being gets empty prior_outputs for that being |

### 2.3 Review Phase

| Failure | What Happens |
|---|---|
| LLM returns bad JSON | **Auto-approve** (`quality_score=0.6`) — silent bypass |
| LLM returns empty | Same auto-approve path |
| max_revisions exhausted | Review stored with `approved=False`, proceeds to synthesis |

### 2.4 Synthesis Phase

| Failure | What Happens |
|---|---|
| Stage 1 empty/exception | Falls to Stage 2 |
| Stage 2 fails | Falls to concatenation last resort |
| task_results UPDATE fails | WARNING logged; synthesis still posted to chat |

### 2.5 Top-Level

| Failure | What Happens |
|---|---|
| Any unhandled exception | Caught line 387: `STATUS_FAILED`, partial persist, board marked failed, user notified |
| create_message in handler raises | Silently caught (line 425) |

**No retry. No resume. Task is terminal.**

**Timeout handling:** Per-subtask thread: 5-min join. Everything else (planning, review, synthesis LLM calls): **no timeout**.

---

## 3. STATE MACHINE

### 3.1 States (engine.py — in-memory only, not in project_tasks)

```
STATUS_PLANNING       = "planning"
STATUS_DELEGATING     = "delegating"
STATUS_AWAITING       = "awaiting_completion"
STATUS_REVIEWING      = "reviewing"
STATUS_REVISING       = "revising"
STATUS_SYNTHESIZING   = "synthesizing"
STATUS_COMPLETED      = "completed"
STATUS_FAILED         = "failed"
```

### 3.2 Transitions

| From | To | Trigger | Code |
|---|---|---|---|
| (new) | planning | `start()` called | engine.py:299 |
| planning | delegating | `_phase_plan()` completes | engine.py:529 |
| delegating | awaiting_completion | subtask threads started | engine.py:560 |
| awaiting_completion | reviewing | all threads complete (or timeout) | engine.py:718 |
| reviewing | revising | LLM review not approved | engine.py:768 |
| revising | reviewing | being revision complete | engine.py:815 |
| reviewing | synthesizing | all beings reviewed | engine.py:819 |
| synthesizing | completed | synthesis posted to chat | engine.py:879 |
| any | failed | unhandled exception in `_orchestrate()` | engine.py:388 |

### 3.3 Stuck States

- **`awaiting_completion` (parallel):** Abandoned threads at 5-min timeout keep running in background. No cancellation.
- **`planning`/`reviewing`/`synthesizing`:** Call `bridge.handle_turn()` with no wall-clock timeout. Hung LLM API = blocks indefinitely.
- **`failed`:** Terminal. Stays in `_active` until restart (then disappears entirely).
- **After restart:** All orchestrations gone. Board tasks stuck as `"in_progress"`. `cleanup_orphaned_tasks` does NOT clean them (only cleans `"Auto-created from chat message"` descriptions).

---

## 4. SUB-AGENT SYSTEM vs. ORCHESTRATION

### 4.1 SubAgentOrchestrator / SubAgentWorkerFactory

- **`SubAgentProtocol`** (`subagents/protocol.py`): Full DB-backed lifecycle — `subagent_runs`, `subagent_events`, `shared_working_memory_writes` tables. `spawn()`, `complete()`, `fail()`, `cascade_stop_session()`.
- **`SubAgentOrchestrator`** (`subagents/orchestrator.py`): `ThreadPoolExecutor`. `CrashStormDetector`. Enforces `max_spawn_depth` by walking `parent_run_id` chain.
- **`SubAgentWorkerFactory`** (`subagents/worker.py`): Calls `bridge.handle_turn(..., profile=TurnProfile.TASK_EXECUTION, ...)`. Output written to `shared_working_memory_writes`.

### 4.2 Comparison

| Dimension | SubAgentOrchestrator | OrchestrationEngine |
|---|---|---|
| State persistence | SQLite (`subagent_runs`) | **In-memory only** |
| State survives restart | Yes | **No** |
| Crash detection | Yes (`CrashStormDetector`) | **No** |
| Depth enforcement | Yes (walks `parent_run_id` chain) | **No** |
| Overall timeout | None | **None** |
| Per-subtask timeout | None | 5-min thread join |
| Shared memory | `shared_working_memory_writes` table | Being tenant semantic memories |
| `TurnProfile` | `TASK_EXECUTION` | **`CHAT` (default)** |
| Result capture | Formal artifact + DB record | Output text in `_active` dict |
| Cancellation | `Future.cancel()` on crash storm | **None** |
| Artifacts | Written to `artifacts` column | **Always `[]`** |
| Idempotency | Idempotency key enforced | **None** |

### 4.3 What Orchestration Is Missing

1. Persistence — task recovery after restart impossible
2. Crash detection — repeatedly crashing beings retried without backoff
3. Wall-clock timeout — hung LLM calls block forever
4. Cascade stop — no equivalent to `cascade_stop_session()`
5. Correct `TurnProfile` — uses `CHAT` instead of `TASK_EXECUTION`
6. Formal artifacts — always `[]`
7. Idempotency — `start()` called twice creates duplicate tasks

---

## 5. ASCII DIAGRAMS

### 5.1 Full Pipeline

```
User message → "prime"
      │
      ▼
DashboardService.route_to_being()  [daemon thread]
      │
      ├─► _classify_message()
      │       ├── regex fast-path → "not_task"
      │       └── LLM (gpt-4o-mini) → "not_task" | "light_task" | "full_task"
      │
      │  full_task + prime + engine ──► _handle_orchestrated_task()
      │                                      │
      │  else: direct handle_turn()          ├─► create_message("acknowledging...")
      │                                      ├─► update_being("prime", "busy")
      │                                      └─► engine.start() → background thread
      │
      └─── BACKGROUND THREAD ─────────────────────────────────────────────────┐
                                                                               │
      create_task(board) → project_tasks                                       │
      init _active[task_id] (in-memory)                                        │
             │                                                                 │
             ▼                                                                 │
       _phase_plan()                                                           │
       │ list_beings() + REPRESENTATION.md (800 chars each)                   │
       │ bridge.handle_turn(tenant="tenant-prime",                             │
       │   session="orchestration:{id}", disable_tools=True)                  │
       │ → JSON plan → OrchestrationPlan                                      │
             │                                                                 │
             ▼                                                                 │
       _phase_delegate()                                                       │
       │ sequential: serial loop                                               │
       │ parallel:   threading.Thread per being (5-min join timeout)           │
       │                                                                       │
       │ per being: bridge.handle_turn(                                        │
       │   tenant=being.tenant_id,                                             │
       │   session="subtask:{id}:{being_id}",                                  │
       │   user_id="prime->{being_id}",                                        │
       │   full tools, TurnProfile.CHAT)                                       │
       │ → output stored in _active["subtask_outputs"]                         │
             │                                                                 │
       _update_team_context_outcomes()  → TEAM_CONTEXT.md                     │
       _update_being_representations() → REPRESENTATION.md per being          │
             │                                                                 │
             ▼                                                                 │
       _phase_review()                                                         │
       │ per being: bridge.handle_turn(disable_tools=True) → review JSON      │
       │ on JSON failure: auto-approve (quality_score=0.6) ← BUG              │
       │ if not approved: revision → being (tools enabled)                    │
       │ max 2 revisions                                                       │
             │                                                                 │
             ▼                                                                 │
       _phase_synthesize()                                                     │
       │ _persist_task_result(synthesis="") → task_results                    │
       │ _truncate_outputs_to_budget()                                         │
       │ Stage 1: handle_turn(disable_tools=True)                              │
       │   if empty → Stage 2: summarize + synthesize                          │
       │     if empty → concatenate (last resort)                              │
       │ create_message(sender="prime") → mc_messages → SSE → UI              │
       │ update_task(status="done") → project_tasks                            │
       └── _trigger_dream_cycle() (every N tasks)                              │
                                                                               │
```

### 5.2 State Machine

```
       start()
          │
          ▼
     ┌─────────┐   _phase_plan() OK    ┌────────────┐
     │ planning │──────────────────────► delegating  │
     └─────────┘                       └────────────┘
                                             │ threads started
                                             ▼
                                   ┌──────────────────┐
                                   │awaiting_completion│  ← stuck if threads hang
                                   └──────────────────┘
                                             │ all join (5-min timeout)
                                             ▼
                                       ┌──────────┐
                               ┌───────│ reviewing │◄──────────────┐
                               │       └──────────┘               │
                               │            │ not approved         │
                               │            ▼                     │
                               │       ┌──────────┐               │
                               │       │ revising  │               │
                               │       └──────────┘               │
                               │          └───────────────────────┘ (max 2 rounds)
                               │ all reviewed
                               ▼
                        ┌─────────────┐
                        │ synthesizing │  ← stuck if LLM hangs (no timeout)
                        └─────────────┘
                               │
                   ┌───────────┴──────────┐
                   ▼                      ▼
            ┌───────────┐          ┌────────┐
            │ completed │          │ failed │  ← terminal, in-memory only
            └───────────┘          └────────┘    (gone after restart)

Exception at ANY phase ──────────────────────► failed
```

### 5.3 Parallel vs. Sequential Execution

```
PARALLEL (strategy != "sequential"):
Prime
  ├──[Thread]──► Scholar:  handle_turn → output_A ──┐
  ├──[Thread]──► Forge:    handle_turn → output_B ──┤ join(timeout=300s)
  └──[Thread]──► Recovery: handle_turn → output_C ──┘
                                                    └──► synthesis

SEQUENTIAL (strategy == "sequential"):
Prime
  ├──► Scholar:  handle_turn → output_A
  │    output_A injected as "CONTEXT FROM OTHER BEINGS"
  ├──► Forge:    handle_turn(prior={Scholar: A}) → output_B
  │    output_A + output_B injected
  └──► Recovery: handle_turn(prior={Scholar: A, Forge: B}) → output_C
                                                             └──► synthesis
```

### 5.4 Failure/Recovery Flow

```
_orchestrate() exception handler:
      exception raised
          │
          ▼
    1. _set_status(STATUS_FAILED)
    2. _persist_task_result("[FAILED...]")  [catches own exceptions]
    3. update_task("failed")               [catches own exceptions]
    4. _log_task_history("orchestration_failed")
    5. _emit_event("orchestration_update", failed)
    6. create_message("Orchestration failed...")   [catches own exceptions]
    
    NO retry. NO resume. Terminal.

Review failure recovery:
    LLM raises / bad JSON
        │
        ▼
    _parse_review() → auto-approve (quality_score=0.6)
    Orchestration CONTINUES with unverified output ← CRITICAL BUG

Synthesis failure recovery:
    Stage 1 empty/error
        │
        ▼
    Stage 2: per-being summarization + re-synthesis
        │ still fails
        ▼
    Concatenate summaries (always produces output)
        │
        ▼
    create_message(sender="prime") [posted even if DB update failed]
```

---

## 6. CONFIRMED BUGS AND GAPS

**Bug 1 [LOW]: `task_id` key mismatch in `start()` (engine.py:291)**
`parent_task.get("id")` always returns `None`. Dead check. Fallback to `"task_id"` works but this is fragile.

**Bug 2 [CRITICAL]: Silent auto-approve on review parse failure (`_parse_review`, engine.py:1371)**
Any LLM API error, JSON decode error, or empty response auto-approves with `quality_score=0.6`. Quality gate is not enforced when the reviewer itself fails.

**Bug 3 [CRITICAL]: All orchestration state is in-memory — no restart recovery (engine.py)**
`self._active` dict. Server restart = all in-progress orchestrations lost permanently. Board shows stuck `"in_progress"` tasks forever.

**Bug 4 [HIGH]: Hardcoded `/Users/zidane/Downloads/PROJEKT` (engine.py:462, 595, 787)**
Machine-specific path hardcoded. Breaks orchestration on any other deployment.

**Bug 5 [HIGH]: Tenant mismatch — `"tenant-prime"` vs `"tenant-local"` (engine.py:252, service.py:315)**
Prime registered under `"tenant-local"` in dashboard. All orchestration planning/synthesis calls go to `"tenant-prime"`. These are separate SQLite DBs. Prime's chat history and orchestration history are in different tenant contexts.

**Bug 6 [LOW]: `artifacts` always `[]` in `task_results` (engine.py:1144)**
```python
json.dumps([])  # artifacts — populated by future work
```
No artifacts from subtask execution are linked to orchestration results.

**Bug 7 [MEDIUM]: Prime status not restored after orchestration completion**
`_handle_orchestrated_task` sets Prime `"busy"`. Orchestration engine calls `update_task(status="done")` but NOT `update_being("prime", {"status": "online"})`. Prime stays `"busy"` indefinitely.

**Dead Code: `subtask_ids` dict**
Maps `being_id → parent_task_id` (not a unique subtask ID). Comment is incorrect. Field is returned by `get_status()` but is misleading.

**Dead Code: `TurnProfile.SUBAGENT_ORCHESTRATION`**
Exists in `context/policy.py` but never passed by the orchestration engine. All calls use `TurnProfile.CHAT`.

**Missing: No overall orchestration timeout.**
Hung LLM calls during planning/review/synthesis block indefinitely.

**Missing: No cancellation API.**
Once started, an orchestration cannot be cancelled without restarting the server.

**Missing: `cleanup_orphaned_tasks` does not clean stuck orchestration tasks (service.py:1330)**
Only cleans tasks with description `"Auto-created from chat message"`. Orchestration tasks have goal text as description and will never be cleaned up.

---

## 7. DATABASE SCHEMAS USED BY ORCHESTRATION

### `task_results` (engine.py:1095, prime tenant DB)
```sql
CREATE TABLE IF NOT EXISTS task_results (
    task_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    goal TEXT NOT NULL,
    strategy TEXT NOT NULL,
    beings_used TEXT NOT NULL,    -- JSON array of being_ids
    outputs TEXT NOT NULL,        -- JSON dict {being_id: output_text}
    synthesis TEXT NOT NULL,      -- final synthesis text (initially "")
    artifacts TEXT NOT NULL DEFAULT "[]",  -- always "[]" (bug)
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_task_results_created
    ON task_results(tenant_id, created_at DESC);
```

### `mc_task_history` (service.py:227, MC DB)
```sql
CREATE TABLE IF NOT EXISTS mc_task_history (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,                 -- JSON
    timestamp TEXT NOT NULL
);
```

---

## 8. CRITICAL RISKS SUMMARY

1. **Loss of orchestration state on restart.** In-progress orchestrations permanently lost. Board shows stuck tasks with no cleanup path.
2. **Silent auto-approve on review failure.** Quality gate bypassed when LLM reviewer fails — garbage output proceeds to synthesis.
3. **No orchestration timeout.** Hung LLM calls block the orchestration thread indefinitely.
4. **Hardcoded machine-specific paths.** Breaks on any deployment other than this exact dev machine.
5. **Prime stays `"busy"` after orchestration completes.** Status display permanently incorrect.
6. **Tenant mismatch.** Prime's chat history and orchestration history in separate tenant contexts.
7. **Two parallel multi-agent systems with incompatible state models.** The robust sub-agent infrastructure (DB-backed, crash-resilient) is not used by orchestration.
