# AUDIT_COMMUNICATION.md — Inter-Agent Communication Audit

> Generated: 2026-03-06 | Codebase: bomba-sr-runtime | Branch: main (d575f78)

---

## 1. System Overview

Two parallel communication systems exist:

- **Legacy channel** — `POST /chat` (`scripts/run_runtime_server.py:825`): raw API, caller supplies all session parameters. No routing intelligence, no SSE, no task creation.
- **Mission Control channel** — `POST /api/mc/chat/messages` (`run_runtime_server.py:1561`): full-featured path used by the React frontend. Message classification, task creation, orchestration intercept, SSE push, being status signals.

Both ultimately call `RuntimeBridge.handle_turn()` (`src/bomba_sr/runtime/bridge.py:173`).

---

## 2. User ↔ Being Communication

### 2.1 Dashboard Chat: Full Message Flow

**Entry:** `POST /api/mc/chat/messages` → `run_runtime_server.py:1561`

```
1. UI sends { content, sender, targets: ["prime"] }
2. create_message() → mc_messages table + _emit_event("chat_message") → SSE fan-out
3. for tid in targets: route_to_being(tid) → daemon thread (non-blocking)
4. HTTP 201 returned immediately

Background thread _route_to_being_sync() (service.py:748):
  a. lookup being from mc_beings
  b. check type (voice agents get stub reply), check status (offline → stub)
  c. _classify_message() → "not_task" | "light_task" | "full_task"
     - regex fast-path for greetings (_NOT_TASK_PATTERNS)
     - LLM call (gpt-4o-mini) for ambiguous messages
  d. full_task + being_id=="prime" + engine? → orchestration path (§3)
  e. else: bridge.handle_turn(TurnRequest(
       tenant_id    = being.tenant_id,
       session_id   = f"mc-chat-{being_id}",
       user_id      = sender,
       workspace_root = being's workspace,
       task_id      = auto-created task_id,
       project_id   = MC_PROJECT_ID,
     ))
  f. create_message(sender=being_id, content=reply) → mc_messages + SSE
```

### 2.2 @-Mention Routing

**There is no @-mention parser in the backend.** Routing is entirely determined by the `targets` array the frontend sends. `CommandParser` (`commands/parser.py:8`) only handles `/command` prefixes. The backend iterates `targets` and spawns one daemon thread per being_id. If `targets: []`, no being is routed and no error is returned.

### 2.3 Message Persistence

| Store | Table | Keyed by | Written by | Read via |
|-------|-------|----------|------------|---------|
| MC messages | `mc_messages` | id | `create_message()` | SSE only — no GET endpoint (**Bug 1**) |
| Turn history | `conversation_turns` | (tenant_id, session_id) | `memory.record_turn()` in `handle_turn()` | `get_recent_turns()` for LLM context replay |

The two stores are not foreign-key linked.

### 2.4 Legacy /chat

`POST /chat` → `run_runtime_server.py:825` → synchronous `bridge.handle_turn()` → full response dict. No classification, no SSE, no task creation.

---

## 3. Being ↔ Being — Orchestration Path

### 3.1 Trigger

```python
# service.py:809–817
if (
    classification == "full_task"
    and being_id == "prime"
    and self.orchestration_engine is not None
):
    self._handle_orchestrated_task(...)
```

Non-Prime beings never trigger orchestration.

### 3.2 Phase Plan (engine.py:428)

Session: `orchestration:{task_id}`, tenant: `"tenant-prime"`, user_id: `"orchestrator"`

```python
bridge.handle_turn(TurnRequest(
    session_id   = f"orchestration:{task_id}",
    user_id      = "orchestrator",
    user_message = "[SYSTEM: ORCHESTRATION MODE]\n" + PLAN_SYSTEM_PROMPT + prompt,
    disable_tools = True,
))
```

LLM returns JSON with `sub_tasks` array: `[{being_id, title, instructions, done_when}]` and `synthesis_strategy: "merge"|"sequential"|"compare"`. Auto-upgrade to "sequential" if instructions contain keywords like "combine", "summarize", "merge" (`engine.py:1353–1363`).

### 3.3 Phase Delegate (engine.py:527)

Session per being: `subtask:{task_id}:{being_id}`, user_id: `"prime->{being_id}"`

**Parallel** (non-sequential): daemon threads, 5-minute join timeout.
**Sequential**: beings run in plan order; prior outputs injected via `_collect_prior_outputs()`.

```python
bridge.handle_turn(TurnRequest(
    tenant_id    = being.tenant_id,
    session_id   = f"subtask:{task_id}:{being_id}",
    user_id      = f"prime->{being_id}",
    user_message = delegation_message,
    search_query = sub.title,   # short title, not full message
))
```

Delegation message structure:
```
[IDENTITY CONTEXT - ACT-I beings only]
You have been assigned a sub-task by SAI Prime.
TASK TITLE: {sub.title}
CONTEXT FROM OTHER BEINGS: [sequential only]
--- {prior_being_id}'s findings ---
{prior_output}
INSTRUCTIONS: {sub.instructions}
ACCEPTANCE CRITERIA: {sub.done_when}
```

### 3.4 _collect_prior_outputs (engine.py:1288)

```python
def _collect_prior_outputs(self, task_id, plan, current_being_id):
    state = self._get_state(task_id)
    prior = {}
    for sub in plan.sub_tasks:
        if sub.being_id == current_being_id:
            break   # beings before current only
        output = state["subtask_outputs"].get(sub.being_id, "")
        if output and not output.startswith("[Error"):
            prior[sub.being_id] = output
    return prior
```

Storage: `self._active[task_id]["subtask_outputs"]` — in-memory dict, `threading.Lock` protected. **No DB persistence. Server restart = total loss.**

### 3.5 Phase Review (engine.py:718)

Same orchestration session, `disable_tools=True`. Up to 2 revision rounds per being. Revisions go back to the being's same `subtask:{task_id}:{being_id}` session — conversation history replay provides continuity.

### 3.6 Phase Synthesize (engine.py:817)

Same orchestration session, `disable_tools=True`. Outputs truncated to token budget: `(200000 − 56000) / num_beings * 3.5` chars per being. Final output posted via `create_message(sender="prime")` → SSE → UI.

### 3.7 Direct Being-to-Being: sisters_message Tool

Only available in Prime's tenant. Full call chain:

```
AgenticLoop → ToolExecutor.execute("sisters_message")
  → bridge.message_sister()  [bridge.py:2073]
    → handle_turn(TurnRequest(
        session_id    = f"sister-chat-{sister_id}",
        user_id       = f"prime->{sister_id}",
        profile       = TASK_EXECUTION,
        workspace_root = sister.workspace_root,
      ))  [BLOCKING — no timeout]
    → returns {"sister_id", "response"}
```

Sisters cannot use this tool on each other. No peer-to-peer path exists.

---

## 4. Being ↔ Being — Non-Orchestration Paths

### 4.1 Cross-Being Memory via resolve_being_id

At every `handle_turn()` (`bridge.py:549`), `resolve_being_id(session_id, user_id)` extracts a being_id using:

```python
# hybrid.py:26–44
_BEING_PATTERNS = [
    (re.compile(r"^mc-chat-(.+)$"), 1),
    (re.compile(r"^subtask:[^:]+:(.+)$"), 1),
]
# Also: user_id.startswith("prime->") → strips prefix
```

Matched sessions get being-scoped recall (`recall_by_being()`). Sessions NOT matched: `orchestration:{task_id}`, `subagent-{run_id}`, `heartbeat-*`.

### 4.2 TEAM_CONTEXT.md

Injected read-only into every being's system prompt via SoulConfig (`bridge.py:659`), up to 3000 chars. No built-in write tool. Orchestration engine writes it via `_update_team_context_outcomes()`.

### 4.3 Dream Cycle Cross-Pollination

`DreamCycle.run_once()` (`dreaming.py`): gathers memories from all beings → LLM consolidate → LLM derive → writes high-confidence insights (≥0.5) directly into other beings' `learn_semantic()`. No approval step. Model: `minimax/minimax-m2-5`. Logs to `workspaces/sai-memory/dream_logs/`.

### 4.4 Sub-Agent Shared Working Memory

Session: `subagent-{run_id}`. Output written to `shared_working_memory_writes` table with scope `"proposal"`, promoted to `"committed"` via `promote_shared_write()`. `resolve_being_id()` returns None for this session pattern — no being-scoped memory.

---

## 5. Session Isolation

| Channel | session_id | user_id | tenant_id |
|---------|-----------|---------|-----------|
| MC dashboard chat | `mc-chat-{being_id}` | UI sender | `being.tenant_id` |
| Orchestration planning | `orchestration:{task_id}` | `"orchestrator"` | `"tenant-prime"` |
| Orchestration subtask | `subtask:{task_id}:{being_id}` | `"prime->{being_id}"` | `being.tenant_id` |
| Revision | `subtask:{task_id}:{being_id}` | `"prime->{being_id}"` | `being.tenant_id` |
| Synthesis | `orchestration:{task_id}` | `"orchestrator"` | `"tenant-prime"` |
| Sister message | `sister-chat-{sister_id}` | `"prime->{sister_id}"` | `sister.tenant_id` |
| Sub-agent | `subagent-{run_id}` | `"agent-{run_id[:8]}"` | `task.tenant_id` |

**Conversation history is isolated** by `(tenant_id, session_id)`. Orchestration sessions strip tool blocks from replay (`_strip_tool_blocks()`, `bridge.py:130`, applied when `"subtask:" in session_id or "orchestration:" in session_id`).

**Memory is NOT isolated by session** — the `memories` and `markdown_notes` tables are keyed by `tenant_id` (and `user_id`/`being_id`), not by `session_id`. Concurrent chat and orchestration sessions for the same being share the same memory pool.

**Tenant binding lock** (`bridge.py:2418`): once a tenant_id is bound to a workspace_root, any request with a different workspace_root for that tenant_id raises `ValueError`.

---

## 6. Real-Time Updates

**SSE endpoint:** `GET /api/mc/events` (`run_runtime_server.py:1681`). Persistent HTTP, `text/event-stream`. 20-second keepalive comment on idle. No WebSockets.

**Events pushed:**

| Event | Trigger |
|-------|---------|
| `chat_message` | Any `create_message()` call |
| `being_typing` | Before/after each LLM call in `_route_to_being_sync` |
| `being_status` | Being goes busy/online during orchestration |
| `orchestration_update` | Each orchestration phase transition |
| `task_created` / `task_updated` | Task lifecycle changes |
| `artifact_created` | ArtifactStore callback |

**Polling (not push):** sub-agent events (`GET /subagents/events?after_seq=N`), dashboard overview stats, orchestration status.

**Race condition:** Two simultaneous messages to the same being cause concurrent threads both setting `being.status`. The first to finish sets it to "online" while the second is still processing. No per-being message queue or mutex exists.

---

## 7. ASCII Diagrams

### 7.1 User ↔ Being (Mission Control)

```
  React UI
    │ POST /api/mc/chat/messages {content, targets:["prime"]}
    ▼
  run_runtime_server.py:1561
    ├── create_message() → mc_messages + SSE "chat_message"
    ├── for tid in targets: route_to_being(tid) → daemon thread
    └── HTTP 201

  [daemon thread _route_to_being_sync()]
    ├── _classify_message() → "full_task" / "light_task" / "not_task"
    ├── full_task + prime + engine → _handle_orchestrated_task() ──────►  §3
    └── else: bridge.handle_turn(session="mc-chat-{being_id}")
               └── create_message(being reply) → SSE "chat_message" → UI
```

### 7.2 Being ↔ Being — Orchestration

```
  PRIME (tenant-prime)
    │
    │ bridge.handle_turn(session="orchestration:{id}", disable_tools=True)
    ▼ PLAN: LLM → sub_tasks[], synthesis_strategy
    │
    ├── [parallel strategy] ────────────────────────────────────────────┐
    │   SCHOLAR: bridge.handle_turn(session="subtask:{id}:sai-scholar") │
    │   FORGE:   bridge.handle_turn(session="subtask:{id}:sai-forge")   │
    │   [daemon threads, 5-min timeout]                                 │
    │                                                                   │
    └── [sequential strategy] ──────────────────────────────────────────┘
        SCHOLAR first → output → _active[task_id]["subtask_outputs"]
        FORGE second  ← _collect_prior_outputs() injects Scholar's output
        (in-memory dict, no DB persistence)
    │
    │ bridge.handle_turn(session="orchestration:{id}", disable_tools=True)
    ▼ REVIEW: up to 2 revision rounds per being
    │
    │ bridge.handle_turn(session="orchestration:{id}", disable_tools=True)
    ▼ SYNTHESIZE: combine outputs within token budget
    │
    └── create_message(sender="prime") → SSE → UI
```

### 7.3 Sisters Message Tool

```
  Prime AgenticLoop
    └── sisters_message(sister_id, message)
          └── bridge.message_sister() [bridge.py:2073]
                └── handle_turn(session="sister-chat-{id}",
                                user_id="prime->{id}")
                    [BLOCKING — no timeout — hangs Prime on slow sister]
                    └── returns sister's text as tool result
```

### 7.4 Dream Cycle (Out-of-Band)

```
  DreamCycle.run_once()
    └── for each being:
          gather memories → LLM consolidate → LLM derive
          write cross-pollinated insights → other beings' learn_semantic()
          [no approval, no SSE notification, no rollback]
```

### 7.5 Session Isolation Boundaries

```
  ┌─── tenant-prime ─────────────────────────────────────────────────┐
  │  conversation_turns:                                              │
  │    mc-chat-prime          [isolated session]                      │
  │    orchestration:{task}   [isolated session]                      │
  │    sister-chat-{id}       [isolated session]                      │
  │                                                                   │
  │  memories / notes tables:  ← ALL sessions above share this pool   │
  │    being_id="prime", tenant_id="tenant-prime"                     │
  └───────────────────────────────────────────────────────────────────┘

  ┌─── tenant-scholar ───────────────────────────────────────────────┐
  │  conversation_turns:                                              │
  │    mc-chat-sai-scholar        [isolated from subtask session]     │
  │    subtask:{task}:sai-scholar [isolated from mc-chat session]     │
  │                                                                   │
  │  memories / notes tables:  ← BOTH sessions share this pool       │
  │  ⚠ RISK: semantic memory written during orchestration subtask    │
  │          is visible in the next mc-chat-sai-scholar session       │
  └───────────────────────────────────────────────────────────────────┘
```

---

## 8. Bugs, Dead Code, and Known Issues

### Bug 1 [HIGH] — No GET endpoint for chat message history
`GET /api/mc/chat/messages` does not exist in `_mc_get()` (`run_runtime_server.py:1236–1507`). Chat history is unrecoverable via HTTP after page refresh. Messages only live in the SSE stream.

### Bug 2 [MEDIUM] — SSE client queue memory leak
`_sse_clients` uses unbounded `queue.Queue()` (`service.py:182`). Disconnected clients are never cleaned up because `put_nowait()` never raises `Full` on unbounded queues. Grows indefinitely with reconnects.

### Bug 3 [HIGH] — Hardcoded absolute path in orchestration engine
`engine.py:595`: `str(Path("/Users/zidane/Downloads/PROJEKT") / ws)`. Breaks orchestration on any machine other than the dev machine.

### Bug 4 [HIGH] — Subtask outputs are in-memory only
`self._active[task_id]["subtask_outputs"]` (`engine.py:682`). Server restart during delegation/review loses all outputs. `_persist_task_result()` only runs after synthesis completes.

### Bug 5 [HIGH] — No @-mention routing in backend
Backend has no mention parser. `targets: []` → message stored, no being routed, HTTP 201 returned silently. The feature only works if the frontend sends the correct `targets` array.

### Bug 6 [MEDIUM] — `message_sister` is blocking with no timeout
`bridge.message_sister()` (`bridge.py:2086`) calls `handle_turn()` synchronously. No timeout. A slow or stuck sister blocks the calling being's entire turn indefinitely.

### Bug 7 [MEDIUM] — `resolve_being_id` does not match all session patterns
`orchestration:{task_id}`, `subagent-{run_id}`, `heartbeat-*` sessions return `being_id=None` — no being-scoped memory reads or writes during these phases.

### Bug 8 [LOW] — `_default_subagent_worker` is a stub
`run_runtime_server.py:83–102`: sleeps 0.02s and returns a fake summary. Direct HTTP `POST /subagents/spawn` calls use this stub. LLM-tool-spawned sub-agents use the real `SubAgentWorkerFactory` worker.

### Dead Code — `announce_with_retry`
`protocol.py:442–486`: webhook callback mechanism, never called by any orchestration or bridge code.

### Architectural Gap — No sister-to-sister messaging
`sisters_message` tool is registered only in Prime's tenant. Sisters cannot initiate messages to each other. All being-to-being communication requires Prime as intermediary.

### Architectural Gap — Memory contamination across concurrent sessions
A being's semantic memory (`memories` table, keyed by `tenant_id` + `being_id`) is shared across all sessions for that being. If Prime sends Scholar a subtask while a user is also chatting with Scholar directly, both sessions write to the same memory pool. No per-session isolation for memory writes.
