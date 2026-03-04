# Session & Memory Architecture — BOMBA SR Runtime

> Complete map of session management, context assembly, memory read/write, and statefulness for every being.
> Generated 2026-03-04 from source code analysis.

---

## Table of Contents

1. [Part 1: Session Lifecycle](#part-1-session-lifecycle)
2. [Part 2: What Each Being Sees Every Turn](#part-2-what-each-being-sees-every-turn)
3. [Part 3: Memory Read/Write Map](#part-3-memory-readwrite-map)
4. [Part 4: Statefulness Gaps](#part-4-statefulness-gaps)

---

## Part 1: Session Lifecycle

### 1.1 Session ID Catalog

Every session in the system follows one of these patterns:

| Pattern | Format | Created By | File:Line |
|---|---|---|---|
| User direct chat | `mc-chat-{being_id}` | `DashboardService._route_to_being_sync()` | `dashboard/service.py:734` |
| Orchestration coordination | `orchestration:{task_id}` | `OrchestrationEngine.start()` | `orchestration/engine.py:28-29` |
| Orchestration subtask | `subtask:{task_id}:{being_id}` | `OrchestrationEngine._execute_subtask()` | `orchestration/engine.py:32-33` |
| Sub-agent run | `subagent-{run_id}` | `SubAgentWorkerFactory.create_worker()` | `subagents/worker.py:17` |
| Sister control | `sisters-control` | `SisterRegistry.spawn_sister()` | `runtime/sisters.py:75` |

Helper functions (engine.py:28-33):
```python
def orchestration_session_id(task_id: str) -> str:
    return f"orchestration:{task_id}"

def subtask_session_id(parent_task_id: str, being_id: str) -> str:
    return f"subtask:{parent_task_id}:{being_id}"
```

### 1.2 Tenant Isolation Model

Each being operates in its own **tenant**, which maps to a completely separate SQLite database:

```
.runtime/tenants/
  tenant-local/runtime/runtime.db       # Sai Prime (direct chat)
  tenant-prime/runtime/runtime.db       # Prime orchestration coordination
  tenant-athena/runtime/runtime.db      # Athena (Scholar)
  tenant-mylo/runtime/runtime.db        # Mylo
  tenant-callie/runtime/runtime.db      # Callie
  tenant-{being_id}/runtime/runtime.db  # Any being, auto-created
```

**Tenant isolation is absolute at the database level.** There is no cross-tenant query path. Each tenant gets its own `RuntimeDB`, `HybridMemoryStore`, `SubAgentProtocol`, `SubAgentOrchestrator`, skill registry, and policy engine.

Created in `RuntimeBridge._tenant_runtime()` at `runtime/bridge.py:2291`. A tenant is bound to a workspace root on first use and cannot be rebound.

### 1.3 Scenario A: "Research X" — Prime Delegates to Scholar and Forge

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ USER sends "research X" to Sai Prime via dashboard                          │
└──────────────────┬───────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Dashboard receives message                                          │
│   DashboardService._route_to_being_sync()  [service.py:690]                │
│   being_id = "prime"                                                        │
│   session_id = "mc-chat-prime"                                              │
│   tenant_id = "tenant-local"  (MC_TENANT)                                  │
│   _classify_message() → "full_task"                                        │
│   Intercept: classification == "full_task" AND being_id == "prime"          │
│   → _handle_orchestrated_task()  [service.py:859]                          │
│   → Sends ack message to user ("I'll coordinate this across beings...")     │
└──────────────────┬───────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Orchestration starts                                                │
│   OrchestrationEngine.start()  [engine.py:192]                             │
│   task_id_A = uuid4()  (e.g., "abc-123-...")                               │
│   orch_session_A = "orchestration:abc-123-..."                             │
│   Spawns background thread → _orchestrate(task_id_A)                       │
└──────────────────┬───────────────────────────────────────────────────────────┘
                   │
         ┌─────────┴─────────────────────────────────────┐
         ▼                                               │
┌──────────────────────────────────────┐                 │
│ STEP 3: Planning Phase               │                 │
│   _phase_plan()  [engine.py:314]     │                 │
│   bridge.handle_turn(                │                 │
│     tenant_id="tenant-prime",        │                 │
│     session_id="orch:abc-123",       │                 │
│     user_id="orchestrator",          │                 │
│     disable_tools=True               │                 │
│   )                                  │                 │
│   LLM produces JSON plan:           │                 │
│   {                                  │                 │
│     "strategy": "sequential",        │                 │
│     "sub_tasks": [                   │                 │
│       {being: "scholar", ...},       │                 │
│       {being: "forge", ...}          │                 │
│     ]                                │                 │
│   }                                  │                 │
│                                      │                 │
│   MEMORY WRITES:                     │                 │
│   • conversation_turns: 1 row in     │                 │
│     tenant-prime, session            │                 │
│     "orch:abc-123"                   │                 │
│   • markdown_notes: 1 working note   │                 │
│     under tenant-prime/memory/       │                 │
│     orchestrator/                    │                 │
│   • loop_executions: 1 row           │                 │
└──────────────────┬───────────────────┘                 │
                   │                                     │
                   ▼                                     │
┌──────────────────────────────────────┐                 │
│ STEP 4a: Scholar subtask             │                 │
│   _execute_subtask()  [engine.py:431]│                 │
│   bridge.handle_turn(                │                 │
│     tenant_id="tenant-athena"        │ ← FALLBACK:    │
│       (or being.get("tenant_id"))    │   f"tenant-     │
│     session_id=                      │   {being_id}"   │
│       "subtask:abc-123:scholar",     │                 │
│     user_id="prime->scholar",        │                 │
│     search_query=sub.title,          │                 │
│     disable_tools=False  ← TOOLS ON │                 │
│   )                                  │                 │
│                                      │                 │
│   CONTEXT:                           │                 │
│   • System prompt: Scholar's soul    │                 │
│     files from its workspace         │                 │
│   • Replay: EMPTY (subtask session)  │                 │
│   • Search: runs against sub.title   │                 │
│   • Memory: Scholar's own semantic   │                 │
│     memories for user "prime->       │                 │
│     scholar" (likely empty 1st time) │                 │
│   • Tools: FULL set available        │                 │
│                                      │                 │
│   MEMORY WRITES:                     │                 │
│   • conversation_turns: row in       │                 │
│     tenant-athena DB                 │                 │
│   • procedural_memories: tool chain  │                 │
│     hash for user "prime->scholar"   │                 │
│   • markdown_notes: working note in  │                 │
│     tenant-athena/memory/            │                 │
│     prime->scholar/                  │                 │
│   • learning_updates: if signals     │                 │
│     detected                         │                 │
│                                      │                 │
│   Output text → state["subtask_      │                 │
│     outputs"]["scholar"]             │                 │
└──────────────────┬───────────────────┘                 │
                   │ (sequential: waits for Scholar)     │
                   ▼                                     │
┌──────────────────────────────────────┐                 │
│ STEP 4b: Forge subtask               │                 │
│   bridge.handle_turn(                │                 │
│     tenant_id="tenant-forge",        │                 │
│     session_id=                      │                 │
│       "subtask:abc-123:forge",       │                 │
│     user_id="prime->forge",          │                 │
│   )                                  │                 │
│                                      │                 │
│   CONTEXT INJECTION (sequential):    │                 │
│   _collect_prior_outputs()           │                 │
│   [engine.py:718]                    │                 │
│   Scholar's output is injected into  │                 │
│   Forge's delegation message as:     │                 │
│   "Context from prior beings:        │                 │
│    scholar: {Scholar's full output}" │                 │
│                                      │                 │
│   Same memory writes as Scholar,     │                 │
│   but in tenant-forge DB.            │                 │
└──────────────────┬───────────────────┘                 │
                   │                                     │
         ┌─────────┴─────────────────────────────────────┘
         ▼
┌──────────────────────────────────────┐
│ STEP 5: Review Phase                 │
│   _phase_review()  [engine.py:527]   │
│   For each being's output:           │
│   bridge.handle_turn(                │
│     tenant_id="tenant-prime",        │
│     session_id="orch:abc-123",       │
│     user_id="orchestrator",          │
│     disable_tools=True               │
│   )                                  │
│   If revision needed: sends to being │
│   in SAME subtask session, up to     │
│   2 rounds [engine.py:580]           │
│                                      │
│   Writes: more turns in tenant-prime │
│   orch session + being's subtask     │
│   session if revised                 │
└──────────────────┬───────────────────┘
                   ▼
┌──────────────────────────────────────┐
│ STEP 6: Synthesis Phase              │
│   _phase_synthesize() [engine.py:626]│
│   bridge.handle_turn(                │
│     tenant_id="tenant-prime",        │
│     session_id="orch:abc-123",       │
│     user_id="orchestrator",          │
│     disable_tools=True               │
│   )                                  │
│   All outputs merged. Final result   │
│   posted to dashboard via            │
│   create_message() [engine.py:673]   │
│   Task marked "done" [engine.py:682] │
└──────────────────────────────────────┘
```

**Summary for Scenario A:**

| Entity | tenant_id | session_id | user_id |
|---|---|---|---|
| User→Prime chat | `tenant-local` | `mc-chat-prime` | user's actual ID |
| Orchestration coordination | `tenant-prime` | `orchestration:{task_A_id}` | `"orchestrator"` |
| Scholar execution | `tenant-athena` | `subtask:{task_A_id}:scholar` | `"prime->scholar"` |
| Forge execution | `tenant-forge` | `subtask:{task_A_id}:forge` | `"prime->forge"` |

### 1.4 Scenario B: "Now Research Y" — Prime Delegates to Scholar and Recovery

Immediately after Scenario A, the user sends another message.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ USER sends "now research Y" to Sai Prime via dashboard                      │
└──────────────────┬───────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Dashboard: session_id = "mc-chat-prime"  (SAME as Scenario A)              │
│ _classify_message() → "full_task"                                          │
│ → _handle_orchestrated_task()                                              │
│ NOTE: The original "research X" message was NOT recorded as a turn in      │
│ mc-chat-prime because it was intercepted before bridge.handle_turn().       │
│ The ack message ("I'll coordinate...") WAS posted to dashboard messages    │
│ but NOT recorded in conversation_turns.                                    │
└──────────────────┬───────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Orchestration starts with NEW task_id_B                                     │
│   task_id_B = uuid4()  (e.g., "def-456-...")                               │
│   orch_session_B = "orchestration:def-456-..."                             │
│   This is a DIFFERENT session from orch_session_A.                         │
│   Different task_id → different session → different DB rows.               │
│   Planning LLM call uses tenant-prime, so it SHARES the same DB as task A  │
│   but the session_id is different.                                         │
└──────────────────┬───────────────────────────────────────────────────────────┘
                   │
         ┌─────────┴──────────────────────────────────────┐
         ▼                                                ▼
┌────────────────────────────┐   ┌────────────────────────────────┐
│ Scholar: subtask:def-456   │   │ Recovery: subtask:def-456      │
│   :scholar                 │   │   :recovery                    │
│                            │   │                                │
│ tenant_id: tenant-athena   │   │ tenant_id: tenant-recovery     │
│ user_id: "prime->scholar"  │   │ user_id: "prime->recovery"     │
│                            │   │                                │
│ SAME tenant as Scenario A! │   │ Fresh tenant (if first time)   │
│ Scholar's DB has turns from│   │                                │
│ subtask:abc-123:scholar    │   │                                │
│ BUT: replay is EMPTY       │   │                                │
│ (subtask session detection)│   │                                │
│                            │   │                                │
│ Semantic memory: queried   │   │                                │
│ for user "prime->scholar"  │   │                                │
│ — MAY find memories from   │   │                                │
│ Scenario A if learn signals│   │                                │
│ were triggered             │   │                                │
│                            │   │                                │
│ Procedural memory: queried │   │                                │
│ for user "prime->scholar"  │   │                                │
│ — WILL find tool chains    │   │                                │
│ from Scenario A            │   │                                │
└────────────────────────────┘   └────────────────────────────────┘
```

### 1.5 Answers to Scenario Questions

#### Q: User↔Prime chat session — is it the same session_id across A and B?

**The `mc-chat-prime` session_id is the same.** However, because orchestration intercepts the message BEFORE `bridge.handle_turn()` is called, **no turns are recorded in `mc-chat-prime`** for orchestrated tasks. The user's messages and Prime's responses flow through the dashboard message system, not the conversation_turns table.

**Can Prime say "similar to what we did for X..."?** No — not through conversation history replay. The orchestration planning phase runs in `orchestration:{task_B_id}`, which is a fresh session with zero replay. Prime's planner has no visibility into task A's plan, delegation, or synthesis unless:
- The user explicitly mentions task A in their message
- Semantic memory in `tenant-prime` for `user_id="orchestrator"` captured something from task A (unlikely — planning phases don't trigger learning signals)

#### Q: Is `orchestration:{task_A_id}` different from `orchestration:{task_B_id}`?

**Yes, completely different sessions.** Each orchestration task gets a unique UUID task_id, producing a unique session_id. They share the same tenant (`tenant-prime`) and thus the same DB, but the session scope means no conversation replay crosses between them. The planning LLM for task B has zero visibility into how task A went.

#### Q: Do Scholar's subtask sessions carry over from A to B?

**Partially.** The sessions are different (`subtask:{task_A}:scholar` vs `subtask:{task_B}:scholar`), and conversation replay is always empty for subtask sessions. However, because both use `tenant-athena` with `user_id="prime->scholar"`:

- **Semantic memory:** If Scholar's work on task A triggered a learning signal (e.g., the user or delegation message contained "I prefer..." patterns), that semantic memory IS available during task B.
- **Procedural memory:** Tool-chain strategies from task A ARE available during task B. If Scholar used `pinecone_query → web_search → memory_store` successfully in task A, that pattern will be recalled for task B.
- **Markdown working notes:** The working note from task A exists in `tenant-athena/memory/prime->scholar/`. The recall function queries by `user_id + query` across all sessions, so task B CAN potentially find task A's notes if the query terms overlap.
- **Conversation turns:** Task A's turns exist in tenant-athena's DB but are scoped to session `subtask:{task_A}:scholar`. Task B cannot replay them (different session + subtask replay skip).

#### Q: If I chat directly with Scholar, does it know about sub-tasks?

**No.** Direct chat with Scholar (`@SaiScholar`) uses:
- `session_id = "mc-chat-scholar"` (dashboard/service.py:734)
- `tenant_id = being.get("tenant_id")` (e.g., `"tenant-athena"`)
- `user_id` = the actual user's ID (NOT `"prime->scholar"`)

The critical gap: **different user_id**. Semantic memory, procedural memory, and markdown notes are all scoped by `user_id`. Direct chat uses your actual user ID; orchestration uses `"prime->scholar"`. These are completely separate memory spaces within the same tenant DB.

Scholar in direct chat has **zero awareness** of its orchestration sub-tasks.

### 1.6 Session Lifecycle Diagram

```
USER
  │
  ├── Direct chat with Prime ──────────────── session: mc-chat-prime
  │     tenant: tenant-local                  user_id: <your_id>
  │     ✓ Conversation replay (last 5 turns)
  │     ✓ Session summary (every 5 turns)
  │     ✓ Semantic memory for <your_id>
  │
  ├── Direct chat with Scholar ────────────── session: mc-chat-scholar
  │     tenant: tenant-athena                 user_id: <your_id>
  │     ✓ Conversation replay (last 5 turns)
  │     ✓ Session summary
  │     ✗ NO visibility into orchestration work (different user_id)
  │
  └── Orchestrated task "research X" ──────── task_id: abc-123
        │
        ├── Planning ──── session: orchestration:abc-123
        │     tenant: tenant-prime            user_id: "orchestrator"
        │     ✗ NO replay (subtask session)
        │     ✗ NO tools (disable_tools=True)
        │
        ├── Scholar exec ── session: subtask:abc-123:scholar
        │     tenant: tenant-athena           user_id: "prime->scholar"
        │     ✗ NO replay (subtask session)
        │     ✓ Tools enabled
        │     ✓ Procedural + semantic memory for "prime->scholar"
        │
        ├── Forge exec ──── session: subtask:abc-123:forge
        │     tenant: tenant-forge            user_id: "prime->forge"
        │     Sequential: gets Scholar's output as context text
        │
        ├── Review ──────── session: orchestration:abc-123 (same as planning)
        │     tenant: tenant-prime            user_id: "orchestrator"
        │
        └── Synthesis ───── session: orchestration:abc-123 (same as planning)
              tenant: tenant-prime            user_id: "orchestrator"
```

---

## Part 2: What Each Being Sees Every Turn

### 2.1 Message Array Structure (Universal)

Every LLM call, regardless of context, receives this message structure:

```
┌─────────────────────────────────────────────────────────────────┐
│ Message[0]: SYSTEM                                              │
│   • Soul/Identity files (SOUL.md, IDENTITY.md, MISSION.md,     │
│     VISION.md, FORMULA.md, PRIORITIES.md)                      │
│   • Operational directive                                       │
│   • Skill index (XML listing of loaded skills)                 │
│   • cache_control: {"type": "ephemeral"}                       │
│                                                                 │
│ Message[1..N]: REPLAY (user/assistant pairs)                    │
│   • Last 5 turns from same session_id                          │
│   • Budget-capped at 30% of available input tokens             │
│   • EMPTY for subtask/orchestration sessions                   │
│                                                                 │
│ Message[N+1]: USER (assembled context)                          │
│   ## system_contract                                            │
│   ## user_message                                               │
│   ## explicit_constraints                                       │
│   ## task_state                                                 │
│   ## tool_provenance (search results with source tags)          │
│   ## working_memory (goal, pending approvals, diagnostics)      │
│   ## world_state (workspace root, persona summary)              │
│   ## semantic (memories + working notes + web snippets)          │
│   ## recent_history (session_id + session summary text)         │
│   ## procedural (tool-chain strategies with success ratios)     │
│   ## predictions (static: "User may request artifacts next")    │
│                                                                 │
│ Tool schemas: available tools (or empty if disable_tools=True)  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Context Assembly Detail

**File:** `context/policy.py`

#### Token Budget Calculation (line 83)

```
For a 200K context model:
  reserved_output_tokens = min(32000, 200000 * 0.20) = 32000
  reserved_safety_tokens = max(2000, 200000 * 0.03) = 6000
  available_input_tokens = 200000 - 32000 - 6000 = 162000
```

#### Required Blocks (always included, assembled first)

| Order | Block | Content |
|---|---|---|
| 1 | `system_contract` | `"Use cited evidence, respect explicit constraints, prefer local-first retrieval."` |
| 2 | `user_message` | The actual user message or delegation prompt |
| 3 | `explicit_constraints` | `"- Do not fabricate sources"` |
| 4 | `task_state` | `"Respond as a chat assistant while preserving memory and auditability."` + active project/task if set |
| 5 | `tool_provenance` | Source-tagged search result snippets: `[source: search://path#L42] code snippet` |

#### Optional Blocks (budget-weighted by TurnProfile)

Remaining tokens after required blocks are allocated by profile weights:

| Section | CHAT | TASK_EXECUTION | PLANNING | MEMORY_RECALL | SUBAGENT_ORCH |
|---|---|---|---|---|---|
| `working_memory` | **0.26** | 0.34 | 0.24 | 0.12 | 0.28 |
| `world_state` | 0.08 | 0.10 | 0.15 | 0.08 | 0.10 |
| `semantic` | **0.24** | 0.18 | 0.22 | **0.42** | 0.18 |
| `recent_history` | **0.34** | 0.20 | 0.17 | 0.26 | 0.14 |
| `procedural` | 0.05 | 0.12 | 0.18 | 0.06 | 0.12 |
| `predictions` | 0.03 | 0.06 | 0.04 | 0.06 | 0.18 |

Each section is packed greedily via `_pack_items()` (line 216). Items exceeding budget are head+tail truncated.

### 2.3 Context for: You Chatting with Sai Prime Directly

```
Session:    mc-chat-prime
Tenant:     tenant-local
User ID:    <your_actual_user_id>
Profile:    TurnProfile.CHAT

SYSTEM PROMPT (from tenant-local workspace):
├── <soul>     SOUL.md from workspaces/prime/
├── <identity> IDENTITY.md from workspaces/prime/
├── <mission>  MISSION.md (if exists)
├── <vision>   VISION.md (if exists)
├── <formula>  FORMULA.md (truncated 12000 chars)
├── <priorities> PRIORITIES.md (truncated 8000 chars)
├── Operational directive
└── Skill index XML

REPLAY MESSAGES:
├── Last 5 turns from mc-chat-prime in tenant-local DB
├── Budget: min(30% available, remaining after context)
└── Capped by _cap_recent_turn_messages() — newest first, skip if too large

CONTEXT ASSEMBLY:
├── Required:
│   ├── system_contract: "Use cited evidence..."
│   ├── user_message: your actual message
│   ├── explicit_constraints: "Do not fabricate sources"
│   ├── task_state: "Respond as chat assistant..."
│   └── tool_provenance: code search results for your message
│
├── Optional (CHAT weights):
│   ├── working_memory (26%): goal, pending approvals count, diagnostics
│   ├── world_state (8%): workspace_root, persona_summary
│   ├── semantic (24%): memories for <your_id> in tenant-local
│   │   Source: consolidator.retrieve() → lexical + recency scoring
│   │   Plus: markdown notes from tenant-local/memory/<your_id>/
│   ├── recent_history (34%): session_id + session_summary text
│   ├── procedural (5%): tool-chain strategies for <your_id>
│   └── predictions (3%): "User may request artifacts or code changes next."

TOOLS: Full set per BOMBA_TOOL_PROFILE (default: all registered tools)
```

### 2.4 Context for: Prime Delegating to Scholar via Orchestration

```
Session:    subtask:{task_id}:scholar
Tenant:     tenant-athena (Scholar's own DB)
User ID:    "prime->scholar"
Profile:    TurnProfile.CHAT (NOT overridden by orchestration engine)

SYSTEM PROMPT (from Scholar's workspace):
├── <soul>     SOUL.md from Scholar's workspace (if exists)
├── <identity> IDENTITY.md from Scholar's workspace (if exists)
├── (other soul files if present)
├── Operational directive
└── Skill index XML (Scholar's loaded skills)

REPLAY MESSAGES: EMPTY
└── Bridge detects "subtask:" in session_id → zero replay
    [bridge.py:521-527]

CONTEXT ASSEMBLY:
├── Required:
│   ├── system_contract: "Use cited evidence..."
│   ├── user_message: delegation message from orchestration engine
│   │   Contains: task title, instructions, acceptance criteria
│   │   If sequential: prior beings' outputs appended
│   │   [engine.py:460-476]
│   ├── explicit_constraints: "Do not fabricate sources"
│   ├── task_state: "Respond as chat assistant..."
│   └── tool_provenance: search results for sub.title (NOT full delegation text)
│       [engine.py:488: search_query=sub.title]
│
├── Optional (CHAT weights — not optimized for delegation):
│   ├── working_memory (26%): goal, approvals in tenant-athena
│   ├── world_state (8%): Scholar's workspace root
│   ├── semantic (24%): memories for "prime->scholar" in tenant-athena
│   │   First task: likely EMPTY
│   │   Subsequent tasks: may contain memories from prior delegations
│   ├── recent_history (34%): session_summary for subtask session (empty/None)
│   ├── procedural (5%): tool-chain strategies for "prime->scholar"
│   │   First task: fallback "Use local-first search then escalate..."
│   │   Subsequent: learned patterns from prior tool chains
│   └── predictions (3%): static text

TOOLS: Full set (disable_tools NOT set for subtask execution)
```

### 2.5 Context for: You Chatting with Scholar Directly

```
Session:    mc-chat-scholar
Tenant:     tenant-athena (SAME DB as orchestration Scholar!)
User ID:    <your_actual_user_id>  (DIFFERENT from "prime->scholar")
Profile:    TurnProfile.CHAT

SYSTEM PROMPT:
├── Scholar's soul/identity files (same as orchestration)
├── Operational directive
└── Skill index XML

REPLAY MESSAGES:
├── Last 5 turns from mc-chat-scholar in tenant-athena
├── Budget-capped at 30%
└── These are YOUR direct conversations with Scholar

CONTEXT ASSEMBLY:
├── Required blocks: same structure
│
├── Optional:
│   ├── semantic (24%): memories for <your_id> in tenant-athena
│   │   *** DIFFERENT user_id from orchestration ***
│   │   Scholar's direct-chat memories are SEPARATE from
│   │   Scholar's orchestration memories
│   ├── procedural (5%): tool chains for <your_id>
│   │   SEPARATE from orchestration tool chains
│   └── (other sections: same structure, different content)

TOOLS: Full set

KEY INSIGHT: Scholar has NO VISIBILITY into its orchestration work.
The user_id split ("prime->scholar" vs <your_id>) creates two
completely separate memory namespaces within the same tenant DB.
If you ask Scholar "what have you been working on?" — it has no idea.
```

### 2.6 Health Snapshot Injection (Agentic Loop)

Starting from iteration 2 of the agentic loop, a health status message is injected (loop.py:327):

```xml
<health_status>
  iteration: 3/25
  budget: $0.0123 / $2.00 (99% remaining)
  tool_calls: 5 total, 0 failed, 0 denied, 0 blocked
  loop_anomaly: False
  model: anthropic/claude-opus-4.6
</health_status>
```

This is injected as a `user` role message and **replaced in-place** each iteration (not appended).

### 2.7 Post-Turn Processing (What Gets Written)

After every LLM response, these operations run:

| Step | What | Where | Condition |
|---|---|---|---|
| 1 | Procedural learning | `procedural_memories` table | If tool calls were made |
| 2 | Artifact creation | Filesystem | If response looks like markdown/code |
| 3 | Working note | Markdown file + `markdown_notes` table | Always |
| 4 | Turn recording | `conversation_turns` table | Always |
| 5 | Session summary | `session_summaries` table | Every 5th turn |
| 6 | Learning signal | `learning_updates` → `memories` table | If user message matches signal patterns |
| 7 | Identity ingestion | User profile signals | If profile signals detected |
| 8 | Adaptation metrics | Metrics aggregation | Every N turns per config |
| 9 | Loop execution log | `loop_executions` table | Always |

---

## Part 3: Memory Read/Write Map

### 3.1 Storage Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│ PER-TENANT SQLITE DATABASE                                              │
│ Path: .runtime/tenants/{tenant_id}/runtime/runtime.db                  │
│                                                                         │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────┐     │
│ │ memories         │ │ memory_archive   │ │ procedural_memories  │     │
│ │ (semantic)       │ │ (contradictions) │ │ (tool chains)        │     │
│ │ scope: user_id   │ │ scope: user_id   │ │ scope: user_id       │     │
│ └──────────────────┘ └──────────────────┘ └──────────────────────┘     │
│                                                                         │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────┐     │
│ │ conversation_    │ │ session_         │ │ learning_updates     │     │
│ │   turns          │ │   summaries      │ │ (approval queue)     │     │
│ │ scope: tenant +  │ │ scope: tenant +  │ │ scope: tenant +      │     │
│ │   session_id     │ │   session_id     │ │   user_id            │     │
│ └──────────────────┘ └──────────────────┘ └──────────────────────┘     │
│                                                                         │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────┐     │
│ │ markdown_notes   │ │ memory_          │ │ loop_executions      │     │
│ │ (DB index)       │ │   embeddings     │ │ (telemetry)          │     │
│ │ scope: user_id   │ │ scope: user_id   │ │ scope: session_id    │     │
│ └──────────────────┘ └──────────────────┘ └──────────────────────┘     │
│                                                                         │
│ ┌──────────────────────────────────────────────────────────────────┐   │
│ │ SUBAGENT TABLES (only used by sub-agent system, not orch)       │   │
│ │ subagent_runs │ subagent_events │ shared_working_memory_writes  │   │
│ └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ PER-TENANT FILESYSTEM                                                    │
│ Path: .runtime/tenants/{tenant_id}/memory/{user_id}/YYYY/MM/DD/*.md    │
│                                                                          │
│ Markdown working notes (one per turn)                                   │
│ Format: YAML frontmatter + turn content                                  │
│ Scope: user_id + date hierarchy                                         │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ EXTERNAL: PINECONE (optional, gated by BOMBA_PINECONE_ENABLED)          │
│                                                                          │
│ Tools: pinecone_query, pinecone_list_indexes, pinecone_upsert           │
│ Default index: "ublib2"    Default namespace: "longterm"                 │
│ Embedding: OpenAI text-embedding-3-small                                │
│ Auth: PINECONE_API_KEY (+ optional PINECONE_API_KEY_STRATA)             │
│                                                                          │
│ NOT scoped by tenant or user_id — any being with the tool can           │
│ query any index/namespace. Scoping is by index and namespace only.      │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ WORKSPACE IDENTITY FILES (read-only, loaded at tenant init)             │
│                                                                          │
│ Path: {workspace_root}/SOUL.md, IDENTITY.md, MISSION.md,               │
│       VISION.md, FORMULA.md, PRIORITIES.md                              │
│                                                                          │
│ Loaded by: identity/soul.py:load_soul_from_workspace()                  │
│ Injected into: system prompt at every turn                              │
│ These are NOT memory — they are configuration/identity.                  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Per-Being Memory Map

#### Sai Prime (Direct Chat)

| Direction | What | Storage | Scope Key | Notes |
|---|---|---|---|---|
| **READ** | Semantic memories | `tenant-local` → `memories` | `user_id=<your_id>` | Lexical + recency-weighted |
| **READ** | Procedural memories | `tenant-local` → `procedural_memories` | `user_id=<your_id>` | Ranked by `lexical * success_ratio` |
| **READ** | Working notes | `tenant-local` → `markdown_notes` + filesystem | `user_id=<your_id>` | Top N by embedding/lexical score |
| **READ** | Conversation replay | `tenant-local` → `conversation_turns` | `session_id=mc-chat-prime` | Last 5 turns, budget-capped |
| **READ** | Session summary | `tenant-local` → `session_summaries` | `session_id=mc-chat-prime` | One row per session |
| **READ** | Soul/Identity | Filesystem: `workspaces/prime/*.md` | N/A | Loaded once at tenant init |
| **READ** | Pinecone | External API | index/namespace | If `BOMBA_PINECONE_ENABLED` + tool called |
| **WRITE** | Turn record | `tenant-local` → `conversation_turns` | `session_id=mc-chat-prime` | Every turn |
| **WRITE** | Working note | `tenant-local` → `markdown_notes` + `.md` file | `user_id=<your_id>` | Every turn |
| **WRITE** | Procedural memory | `tenant-local` → `procedural_memories` | `user_id=<your_id>` | If tool calls made |
| **WRITE** | Semantic memory | `tenant-local` → `memories` | `user_id=<your_id>` | If learning signal detected |
| **WRITE** | Session summary | `tenant-local` → `session_summaries` | `session_id=mc-chat-prime` | Every 5th turn |
| **WRITE** | Pinecone | External API | index/namespace | Via `pinecone_upsert` tool |

#### Sai Prime (Orchestration Coordination)

| Direction | What | Storage | Scope Key |
|---|---|---|---|
| **READ** | Semantic memories | `tenant-prime` → `memories` | `user_id="orchestrator"` |
| **READ** | Procedural memories | `tenant-prime` → `procedural_memories` | `user_id="orchestrator"` |
| **READ** | Conversation replay | **EMPTY** (subtask session detection) | N/A |
| **READ** | Soul/Identity | Filesystem: workspace for tenant-prime | N/A |
| **WRITE** | Turn record | `tenant-prime` → `conversation_turns` | `session_id=orchestration:{task_id}` |
| **WRITE** | Working note | `tenant-prime` → `markdown_notes` | `user_id="orchestrator"` |
| **WRITE** | Procedural memory | `tenant-prime` → `procedural_memories` | `user_id="orchestrator"` |

**Note:** `tenant-local` (direct chat) and `tenant-prime` (orchestration) are **different tenants with different databases**. Prime's direct-chat memories and Prime's orchestration memories are in different SQLite files.

#### Scholar (Orchestrated Sub-task)

| Direction | What | Storage | Scope Key |
|---|---|---|---|
| **READ** | Semantic memories | `tenant-athena` → `memories` | `user_id="prime->scholar"` |
| **READ** | Procedural memories | `tenant-athena` → `procedural_memories` | `user_id="prime->scholar"` |
| **READ** | Working notes | `tenant-athena` → `markdown_notes` + filesystem | `user_id="prime->scholar"` |
| **READ** | Conversation replay | **EMPTY** (subtask session detection) | N/A |
| **READ** | Prior being outputs | Injected as text in delegation message | N/A |
| **WRITE** | Turn record | `tenant-athena` → `conversation_turns` | `session_id=subtask:{task_id}:scholar` |
| **WRITE** | Working note | `tenant-athena` file: `memory/prime->scholar/...` | `user_id="prime->scholar"` |
| **WRITE** | Procedural memory | `tenant-athena` → `procedural_memories` | `user_id="prime->scholar"` |

#### Scholar (Direct Chat with User)

| Direction | What | Storage | Scope Key |
|---|---|---|---|
| **READ** | Semantic memories | `tenant-athena` → `memories` | `user_id=<your_id>` |
| **READ** | Procedural memories | `tenant-athena` → `procedural_memories` | `user_id=<your_id>` |
| **READ** | Conversation replay | `tenant-athena` → `conversation_turns` | `session_id=mc-chat-scholar` |
| **WRITE** | (same pattern as orchestrated, but scoped to `<your_id>`) | | |

**Critical gap:** Scholar direct-chat reads `user_id=<your_id>`. Scholar orchestrated reads `user_id="prime->scholar"`. **These are completely separate memory namespaces within the same SQLite database.**

### 3.3 Cross-Being Memory Visibility Matrix

```
Can Being B read what Being A wrote?

           Writer (A)
           ┌──────────┬──────────┬──────────┬──────────┬──────────┐
           │ Prime    │ Prime    │ Scholar  │ Scholar  │ Forge    │
           │ (chat)   │ (orch)   │ (orch)   │ (chat)   │ (orch)   │
Reader ────┼──────────┼──────────┼──────────┼──────────┼──────────┤
(B)        │          │          │          │          │          │
Prime      │          │          │          │          │          │
(chat)     │ ✓ SELF   │ ✗ diff   │ ✗ diff   │ ✗ diff   │ ✗ diff   │
           │          │ tenant   │ tenant   │ tenant   │ tenant   │
───────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
Prime      │ ✗ diff   │          │          │          │          │
(orch)     │ tenant   │ ✓ SELF   │ ✗ diff   │ ✗ diff   │ ✗ diff   │
           │          │          │ tenant   │ tenant   │ tenant   │
───────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
Scholar    │ ✗ diff   │ ✗ diff   │          │ ✗ diff   │ ✗ diff   │
(orch)     │ tenant   │ tenant   │ ✓ SELF   │ user_id  │ tenant   │
───────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
Scholar    │ ✗ diff   │ ✗ diff   │ ✗ diff   │          │ ✗ diff   │
(chat)     │ tenant   │ tenant   │ user_id  │ ✓ SELF   │ tenant   │
───────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
Forge      │ ✗ diff   │ ✗ diff   │ ✗ diff   │ ✗ diff   │          │
(orch)     │ tenant   │ tenant   │ tenant   │ tenant   │ ✓ SELF   │
───────────┴──────────┴──────────┴──────────┴──────────┴──────────┘

Legend:
  ✓ SELF       = same tenant + same user_id → full read access
  ✗ diff tenant = different SQLite database → zero access
  ✗ diff user_id = same database, different user_id → zero access
```

**Only exception: Pinecone.** Pinecone queries are NOT scoped by tenant or user_id. Any being with the `pinecone_query` tool can read from any index/namespace. This is the ONLY cross-being shared memory in the system.

### 3.4 Shared Working Memory (Sub-Agent System)

The sub-agent system (`subagents/protocol.py`) has a `shared_working_memory_writes` table:

```sql
CREATE TABLE IF NOT EXISTS shared_working_memory_writes (
    write_id TEXT PRIMARY KEY,
    run_id TEXT,                     -- FK to subagent_runs
    writer_agent_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL,         -- grouping key
    scope TEXT NOT NULL DEFAULT 'scratch',  -- scratch|proposal|committed
    confidence REAL NOT NULL DEFAULT 0.5,
    content TEXT NOT NULL,
    source_refs TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    merged_by_agent_id TEXT,
    merged_at TEXT
);
```

This table exists per-tenant. The `SubAgentWorkerFactory` writes to it after a sub-agent completes (worker.py:35-43) with `scope="proposal"` and `confidence=0.8`. The parent can then `promote_shared_write()` to `scope="committed"`.

**However:** The orchestration engine (`engine.py`) does NOT use the sub-agent system. It calls `bridge.handle_turn()` directly. Therefore, `shared_working_memory_writes` is **not populated** during orchestration. It's only used when beings spawn sub-agents via the `sessions_spawn` tool.

### 3.5 Session Summary Lifecycle

```
Turn 1:  Recorded in conversation_turns
Turn 2:  Recorded
Turn 3:  Recorded
Turn 4:  Recorded
Turn 5:  Recorded. Summary triggered (turn_number % 5 == 0, > 3).
         get_turns_for_summary() fetches turns 1-2 (turns 3-5 are "recent window")
         LLM generates summary → upserted into session_summaries
Turn 6-9: Recorded
Turn 10: Summary triggered again.
         get_turns_for_summary() fetches turns 3-7 (turns 8-10 are recent window)
         New summary = old summary + new turns → upserted (overwriting old)
```

Summary generation (hybrid.py:656):
- System prompt: `"Produce a compact session summary with only durable context. Max length: 200 tokens."`
- Input: previous summary + turn transcript (truncated to 24,000 chars)
- Output: capped at 8,000 chars
- One summary per session (upserted via `ON CONFLICT(tenant_id, session_id) DO UPDATE`)

---

## Part 4: Statefulness Gaps

### 4.1 Can a Being Remember What It Did Across Multiple Tasks?

**Partially, through two indirect channels:**

1. **Procedural memory persists across tasks.** If Scholar uses `pinecone_query → web_search` successfully in task A, that tool-chain strategy is recorded under `user_id="prime->scholar"` in `tenant-athena`. When task B arrives with a related query, the procedural memory recall (`recall_procedural()`, consolidation.py:313) will surface that strategy. Scholar's tool selection improves over time.

2. **Working notes persist across tasks.** Each turn creates a markdown file in `tenant-athena/memory/prime->scholar/YYYY/MM/DD/`. The `_recall_markdown()` function (hybrid.py:401) fetches the most recent 300 notes for the user_id and scores them against the current query. If task B's query overlaps with task A's content, relevant notes may surface.

**What's missing:**

- **No conversation replay across tasks.** Each task uses a different session_id, so conversation_turns from task A are invisible during task B.
- **Semantic memory requires explicit learning signals.** Unless the delegation message or being's response triggers a learning signal pattern (e.g., "I prefer...", "my name is..."), no semantic memory is created. Task-specific knowledge (e.g., "the user's competitor is Company X") is not automatically captured.
- **No explicit task result storage.** When Scholar completes a task, the output goes back to the orchestration engine as a string in `state["subtask_outputs"]`. It is NOT stored in any being-accessible memory table. The only trace is the working note.

### 4.2 Can Beings Build Up Expertise Over Time?

**Yes, for tool strategies. No, for domain knowledge.**

| Dimension | Accumulates? | Mechanism | Limitation |
|---|---|---|---|
| Tool selection | **Yes** | `procedural_memories` with success/failure ratios | Only captures tool chain signatures, not the query context |
| Research findings | **No** | Working notes exist but are only recalled by lexical/embedding overlap | No structured knowledge base; notes are raw turn transcripts |
| User preferences | **Partially** | `memories` table via learning signals | Only triggered by specific patterns; most delegation prompts don't trigger |
| Domain knowledge | **No** | No mechanism for a being to say "I learned that X is true" | Would need explicit `memory_store` tool calls during delegation |

### 4.3 Can Prime Reference Task A's Results When Planning Task B?

**No, through any automatic mechanism.**

The planning phase for task B:
- Uses `tenant-prime` with `user_id="orchestrator"`
- Session: `orchestration:{task_B_id}` — a fresh session, no replay
- Semantic memory for `"orchestrator"` — unlikely to contain task A results (no learning signals in planning prompts)
- Procedural memory for `"orchestrator"` — planning phases use `disable_tools=True`, so no tool chains are recorded
- Working notes for `"orchestrator"` — the planning turn notes exist, but the query might not overlap

**The only way Prime can reference task A** is if the user explicitly mentions it in their message for task B (e.g., "similar to what we did for X, now research Y").

### 4.4 Is There a "Being-Level Memory" That Persists Across All Contexts?

**No.** Memory is scoped by `(tenant_id, user_id)`, not by `being_id`. The same being (e.g., Scholar) has different memory namespaces depending on who's talking to it:

| Context | tenant_id | user_id | Memory Namespace |
|---|---|---|---|
| User chats directly | tenant-athena | `<your_id>` | Namespace A |
| Prime delegates task 1 | tenant-athena | `"prime->scholar"` | Namespace B |
| Prime delegates task 2 | tenant-athena | `"prime->scholar"` | Namespace B (same!) |
| Different user chats | tenant-athena | `<other_user_id>` | Namespace C |

Namespaces B are shared across orchestration tasks (because same tenant + same user_id), giving **partial cross-task continuity within the orchestration context.** But Namespace A (direct chat) is completely separate.

There is no concept of `being_id`-scoped memory that transcends both direct chat and orchestration.

### 4.5 What Would Need to Change for True Statefulness

#### Gap 1: Cross-Context Being Memory

**Problem:** Scholar-in-orchestration and Scholar-in-direct-chat are memory-siloed.

**Fix:** Introduce a `being_id`-scoped memory layer that all contexts can read/write. Options:
- Add a `being_id` column to `memories` table and query it alongside `user_id`
- Create a `being_memories` table with `(tenant_id, being_id)` as the scope key
- On direct chat, merge both `user_id`-scoped and `being_id`-scoped memories into semantic candidates

#### Gap 2: Cross-Task Orchestration Context

**Problem:** Prime's orchestration planner has no visibility into prior completed tasks.

**Fix:** After synthesis, write a structured task summary to a durable, queryable store:
```python
# After _phase_synthesize():
runtime.memory.learn_semantic(
    user_id="orchestrator",
    memory_key=f"task_result::{task_id}",
    content=f"Task '{goal}' completed. Beings: {beings}. Outcome: {summary[:500]}",
    confidence=0.9,
)
```
This would allow `recall()` during planning to surface prior task results.

#### Gap 3: Orchestration→Direct Chat Bridge

**Problem:** When a user asks Scholar "what have you been working on?", Scholar has no access to its orchestration work.

**Fix options:**
1. **Shared user_id:** Use the same user_id for both direct chat and orchestration (e.g., always use `<your_id>` instead of `"prime->scholar"`). Risk: orchestration noise polluting direct chat.
2. **Cross-namespace read:** On direct chat, also query memories for `user_id="prime->scholar"` and merge into semantic candidates. Requires a registry of "alternative user_ids for this being."
3. **Post-task sync:** After orchestration completes, copy key memories from `"prime->scholar"` namespace into the being's self-namespace (e.g., `being_id`-scoped).

#### Gap 4: Conversation Replay for Orchestration

**Problem:** Subtask and orchestration sessions get zero conversation replay.

**Why it exists:** Old `tool_use` blocks cause API errors when replayed (bridge.py:519-520 comment). This is a real constraint from the Anthropic API.

**Fix:** Strip tool_use/tool_result blocks from replayed messages for orchestration sessions, keeping only the text content. This would give the revision flow access to the being's prior work:
```python
if _is_subtask_session:
    recent_turn_messages = _strip_tool_blocks(
        runtime.memory.get_recent_turns(...)
    )
```

#### Gap 5: Structured Task Result Persistence

**Problem:** Orchestration outputs exist only as transient strings in `state["subtask_outputs"]`. Once the orchestration thread completes, they're gone.

**Fix:** Add a `task_results` table:
```sql
CREATE TABLE task_results (
    task_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    goal TEXT NOT NULL,
    strategy TEXT NOT NULL,     -- parallel, sequential, etc.
    beings_used TEXT NOT NULL,  -- JSON array
    outputs TEXT NOT NULL,      -- JSON object {being_id: output}
    synthesis TEXT NOT NULL,    -- final synthesized result
    created_at TEXT NOT NULL,
    INDEX(tenant_id, created_at DESC)
);
```

#### Gap 6: Explicit Knowledge Capture During Tasks

**Problem:** Beings learn tool strategies automatically (procedural memory) but not domain knowledge.

**Fix:** Two approaches:
1. **Automatic:** After each subtask, extract key facts from the being's output and write them as semantic memories:
   ```python
   # In _execute_subtask(), after getting output:
   facts = self._extract_key_facts(output)  # LLM call
   for fact in facts:
       being_memory.learn_semantic(
           user_id=f"prime->{sub.being_id}",
           memory_key=f"fact::{hash(fact)}",
           content=fact,
           confidence=0.7,
       )
   ```
2. **Tool-based:** Give beings a `remember_this` tool that explicitly writes to being-level memory during task execution.

#### Gap 7: Prime→Sister Knowledge Propagation

**Problem:** If Prime learns something during orchestration (e.g., user preference), sisters don't automatically know.

**Fix:** After orchestration, broadcast key learnings to relevant sister tenants:
```python
# Hypothetical: after synthesis
for being_id in plan.sub_tasks:
    sister_memory = get_memory_for_tenant(f"tenant-{being_id}")
    sister_memory.learn_semantic(
        user_id="system",
        memory_key=f"from_prime::{task_id}",
        content="Shared learning: ...",
        confidence=0.6,
    )
```

### 4.6 Summary: Current vs Ideal Statefulness

```
                           CURRENT STATE                    IDEAL STATE
                     ┌─────────────────────┐          ┌─────────────────────┐
Cross-task memory    │  Procedural: ✓      │          │  Procedural: ✓      │
(same being,         │  Semantic: ✗ (rare) │          │  Semantic: ✓ (auto) │
 same context)       │  Working notes: ~   │          │  Task results: ✓    │
                     │  Conv history: ✗    │          │  Conv history: ~    │
                     └─────────────────────┘          └─────────────────────┘

Cross-context memory │  Direct↔Orch: ✗     │          │  Direct↔Orch: ✓     │
(same being,         │  No being_id scope  │          │  Being-level memory │
 diff context)       │                     │          │  + cross-namespace  │
                     └─────────────────────┘          └─────────────────────┘

Cross-being memory   │  Pinecone: ✓ (shared│          │  Pinecone: ✓        │
(different beings)   │    but unstructured) │          │  Shared fact store:✓│
                     │  SQLite: ✗ (tenant  │          │  Broadcast channel:✓│
                     │    isolation)        │          │                     │
                     └─────────────────────┘          └─────────────────────┘

Cross-task orch      │  Plan→plan: ✗       │          │  Task result index:✓│
(Prime across        │  No task result DB  │          │  Prior task recall  │
 orchestrations)     │                     │          │  at planning time   │
                     └─────────────────────┘          └─────────────────────┘
```

---

## Appendix A: Key File Reference

| File | Key Functions | Purpose |
|---|---|---|
| `runtime/bridge.py:146` | `handle_turn()` | Universal entry point for all turns |
| `runtime/bridge.py:521` | `_is_subtask_session` check | Orchestration replay skip logic |
| `runtime/bridge.py:661` | Replay budget calculation | Token-capped history replay |
| `runtime/bridge.py:777` | LLM message assembly | Final message array construction |
| `runtime/bridge.py:882` | Post-turn writes | Working notes, turns, summaries |
| `runtime/bridge.py:2291` | `_tenant_runtime()` | Tenant creation and isolation |
| `runtime/bridge.py:2811` | `_cap_recent_turn_messages()` | Budget-aware replay capping |
| `orchestration/engine.py:28` | Session ID helpers | `orchestration:{id}`, `subtask:{id}:{being}` |
| `orchestration/engine.py:192` | `start()` | Orchestration lifecycle entry |
| `orchestration/engine.py:314` | `_phase_plan()` | Planning phase |
| `orchestration/engine.py:431` | `_execute_subtask()` | Being delegation |
| `orchestration/engine.py:527` | `_phase_review()` | Review + revision |
| `orchestration/engine.py:626` | `_phase_synthesize()` | Final synthesis |
| `orchestration/engine.py:718` | `_collect_prior_outputs()` | Sequential context injection |
| `context/policy.py:39` | `PROFILE_WEIGHTS` | Token allocation by turn type |
| `context/policy.py:83` | `calculate_budget()` | Token budget calculation |
| `context/policy.py:98` | `assemble()` | Context assembly engine |
| `memory/hybrid.py:61` | Schema creation | All memory table definitions |
| `memory/hybrid.py:141` | `append_working_note()` | Markdown note creation |
| `memory/hybrid.py:230` | `learn_semantic()` | Semantic memory creation |
| `memory/hybrid.py:359` | `learn_procedural()` | Tool-chain learning |
| `memory/hybrid.py:376` | `recall()` | Semantic + working note recall |
| `memory/hybrid.py:470` | `record_turn()` | Conversation turn persistence |
| `memory/hybrid.py:536` | `get_recent_turns()` | Turn replay fetch |
| `memory/hybrid.py:590` | `get_session_summary()` | Summary retrieval |
| `memory/hybrid.py:656` | `generate_session_summary()` | LLM summary generation |
| `memory/consolidation.py:57` | Schema for `memories` | Semantic memory table |
| `memory/consolidation.py:164` | `upsert()` | Contradiction detection + archival |
| `memory/consolidation.py:204` | `retrieve()` | Lexical + recency-weighted recall |
| `memory/consolidation.py:252` | `learn_procedural()` | Procedural memory upsert |
| `memory/consolidation.py:313` | `recall_procedural()` | Procedural recall with success ratio |
| `subagents/protocol.py:119` | `shared_working_memory_writes` | Sub-agent shared memory table |
| `subagents/worker.py:14` | `create_worker()` | Sub-agent session creation |
| `dashboard/service.py:734` | `mc-chat-{being_id}` | Direct chat session pattern |
| `dashboard/service.py:859` | `_handle_orchestrated_task()` | Orchestration intercept |
| `identity/soul.py:30` | `load_soul_from_workspace()` | Soul/identity file loading |
| `tools/builtin_pinecone.py:240` | `_pinecone_query_factory()` | Pinecone vector query |
| `tools/builtin_pinecone.py:502` | `builtin_pinecone_tools()` | Tool registration |

## Appendix B: Session ID Quick Reference

```
Direct chat:        mc-chat-{being_id}         e.g., mc-chat-prime, mc-chat-scholar
Orchestration:      orchestration:{uuid}        e.g., orchestration:abc-123-def-456
Subtask:            subtask:{uuid}:{being_id}   e.g., subtask:abc-123:scholar
Sub-agent:          subagent-{run_uuid}         e.g., subagent-xyz-789
Sister spawn:       sisters-control             (constant)
```

## Appendix C: user_id Quick Reference

```
Direct chat:        <actual_user_id>            e.g., user-local, user@email.com
Orchestration:      "orchestrator"              (constant for all orch coordination)
Subtask execution:  "prime->{being_id}"         e.g., prime->scholar, prime->forge
Sub-agent:          "agent-{run_id[:8]}"        e.g., agent-abc12345
```

## Appendix D: Tenant Quick Reference

```
Direct chat Prime:  tenant-local                (MC_TENANT constant)
Orchestration:      tenant-prime                (OrchestrationEngine.prime_tenant_id)
Scholar:            tenant-athena               (from being config or f"tenant-{being_id}")
Forge:              tenant-forge                (auto-generated fallback)
Recovery:           tenant-recovery             (auto-generated fallback)
Any being:          tenant-{being_id}           (fallback pattern)
```
