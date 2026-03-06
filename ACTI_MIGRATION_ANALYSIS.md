# ACT-I Migration Analysis — BOMBA SR Runtime

**Date:** 2026-03-06
**Standard:** "How We Build Masterful ACT-I Beings" (March 2026)
**Scope:** Full codebase audit across all beings, context assembly, memory management, orchestration, and tier handling

---

## Part 1: Identity File Compliance Audit

### ACT-I Required Files (6 per Being)

| # | File | Purpose | Character Limit |
|---|------|---------|-----------------|
| 1 | DESCRIPTION | What the being causes (3-5 sentences) | None specified |
| 2 | AGENTS.md | Operating rules, boot sequence, memory management | None specified |
| 3 | TOOLS.md | Lean per-being tool set | None specified |
| 4 | SOUL.md | Voice, personality, Formula | **< 4,000 chars** |
| 5 | IDENTITY.md | Name, role, creature level, levers | **< 2,000 chars** |
| 6 | USER.md | Who it serves, zone actions | None specified |

### What SoulConfig Actually Loads Into the System Prompt

Source: `src/bomba_sr/identity/soul.py` + `src/bomba_sr/runtime/bridge.py` (lines 636-695)

| File | XML Tag | Truncation Limit | Loaded Every Turn? |
|------|---------|------------------|--------------------|
| `SOUL.md` | `<soul>` | **NONE** | Yes |
| `IDENTITY.md` | `<identity>` | **NONE** | Yes |
| `MISSION.md` | `<mission>` | **NONE** | Yes |
| `VISION.md` | `<vision>` | **NONE** | Yes |
| `FORMULA.md` | `<formula>` | 12,000 chars | Yes |
| `PRIORITIES.md` | `<priorities>` | 8,000 chars | Yes |
| `KNOWLEDGE.md` | `<knowledge>` | 4,000 chars | Yes |
| `TEAM_CONTEXT.md` | `<team-context>` | 3,000 chars | Yes |
| `REPRESENTATION.md` | `<representation>` | 3,000 chars | Conditional |

**Critical:** SOUL.md and IDENTITY.md are injected with NO truncation. Oversized files consume tokens on every single turn.

**Not loaded by SoulConfig:** DESCRIPTION, AGENTS.md, TOOLS.md, USER.md — these must be read manually by the agent during boot.

---

### Core Sisters Compliance

#### SAI Prime (`workspaces/prime/`)

| File | Status | Chars | Limit | Compliant? |
|------|--------|-------|-------|------------|
| SOUL.md | EXISTS | 6,390 | 4,000 | **OVER by 60%** |
| IDENTITY.md | EXISTS | 7,482 | 2,000 | **OVER by 274%** |
| DESCRIPTION | MISSING | — | Required | **MISSING** |
| USER.md | EXISTS | 3,177 | — | OK |
| AGENTS.md | EXISTS | 7,863 | — | Has boot sequence + memory management |
| TOOLS.md | EXISTS | 4,211 | — | Has per-being tool defs |

Additional payload: MISSION.md (9,220), VISION.md (3,290), FORMULA.md (6,380), PRIORITIES.md (1,135), KNOWLEDGE.md (1,122), TEAM_CONTEXT.md (672), REPRESENTATION.md (1,019)

**Total system prompt payload: ~36,690 chars (~9,173 tokens)**
**Compliance Score: 4/6**

---

#### SAI Forge (`workspaces/forge/`)

| File | Status | Chars | Limit | Compliant? |
|------|--------|-------|-------|------------|
| SOUL.md | EXISTS | 1,567 | 4,000 | OK |
| IDENTITY.md | EXISTS | 1,628 | 2,000 | OK |
| DESCRIPTION | MISSING | — | Required | **MISSING** |
| USER.md | EXISTS | 1,498 | — | OK |
| AGENTS.md | EXISTS | 1,159 | — | No boot sequence, has memory rules |
| TOOLS.md | EXISTS | 3,217 | — | Has per-being tool defs |

**Total system prompt payload: ~6,828 chars (~1,707 tokens)**
**Compliance Score: 4/6**

---

#### SAI Scholar (`workspaces/scholar/`)

| File | Status | Chars | Limit | Compliant? |
|------|--------|-------|-------|------------|
| SOUL.md | EXISTS | 2,332 | 4,000 | OK |
| IDENTITY.md | EXISTS | 1,650 | 2,000 | OK |
| DESCRIPTION | MISSING | — | Required | **MISSING** |
| USER.md | EXISTS | 1,498 | — | OK |
| AGENTS.md | EXISTS | 743 | — | **Skeletal — no boot, no memory mgmt** |
| TOOLS.md | EXISTS | 4,479 | — | Has per-being tool defs |

**Total system prompt payload: ~8,556 chars (~2,139 tokens)**
**Compliance Score: 4/6**

---

#### SAI Recovery (`workspaces/recovery/`)

| File | Status | Chars | Limit | Compliant? |
|------|--------|-------|-------|------------|
| SOUL.md | EXISTS | 6,455 | 4,000 | **OVER by 61%** |
| IDENTITY.md | EXISTS | 5,447 | 2,000 | **OVER by 172%** |
| DESCRIPTION | MISSING | — | Required | **MISSING** |
| USER.md | MISSING | — | Required | **MISSING** |
| AGENTS.md | MISSING | — | Required | **MISSING** |
| TOOLS.md | MISSING | — | Required | **MISSING** |

**Total system prompt payload: ~17,696 chars (~4,424 tokens)**
**Compliance Score: 2/6** — Severely non-compliant

---

#### SAI Memory (`workspaces/sai-memory/`)

| File | Status | Chars | Limit | Compliant? |
|------|--------|-------|-------|------------|
| SOUL.md | EXISTS | 8,271 | 4,000 | **OVER by 107%** |
| IDENTITY.md | EXISTS | 6,377 | 2,000 | **OVER by 219%** |
| DESCRIPTION | MISSING | — | Required | **MISSING** |
| USER.md | EXISTS | 7,998 | — | OK |
| AGENTS.md | EXISTS | 12,969 | — | Has boot sequence + memory mgmt |
| TOOLS.md | MISSING | — | Required | **MISSING** |

**Total system prompt payload: ~16,752 chars (~4,188 tokens)**
**Compliance Score: 3/6**

---

### 17 ACT-I Beings Compliance

All 17 operational beings exist ONLY as architectural spec files (634–1,326 chars each) in `workspaces/acti-architecture/beings/`. None have individual workspace directories. None have any of the 6 required files.

| Being | Parent Sister | Spec File Chars | Has Own Workspace? | Compliance Score |
|-------|--------------|-----------------|--------------------|-|
| The Writer | forge | 1,088 | No | **0/6** |
| The Visual Architect | forge | 1,326 | No | **0/6** |
| The Filmmaker | forge | 961 | No | **0/6** |
| The Sound Engineer | forge | 745 | No | **0/6** |
| The Media Buyer | forge | 677 | No | **0/6** |
| The Voice | forge | 875 | No | **0/6** |
| The Technologist | forge | 734 | No | **0/6** |
| The Messenger | forge | 792 | No | **0/6** |
| The Stage Director | forge | 974 | No | **0/6** |
| The Analyst | scholar | 1,085 | No | **0/6** |
| The Researcher | scholar | 638 | No | **0/6** |
| The Connector | recovery | 949 | No | **0/6** |
| The Agreement Maker | recovery | 843 | No | **0/6** |
| The Keeper | recovery | 665 | No | **0/6** |
| The Multiplier | recovery | 678 | No | **0/6** |
| The Operator | prime | 1,033 | No | **0/6** |
| The Strategist | prime | 634 | No | **0/6** |

---

### Compliance Summary Matrix

| Being | SOUL.md | IDENTITY.md | DESC | USER.md | AGENTS.md | TOOLS.md | Score | Worst Issue |
|-------|---------|-------------|------|---------|-----------|----------|-------|-------------|
| **Prime** | 6,390 (**OVER**) | 7,482 (**OVER**) | MISS | OK | OK | OK | **4/6** | IDENTITY 274% over |
| **Forge** | 1,567 (OK) | 1,628 (OK) | MISS | OK | PARTIAL | OK | **4/6** | No boot sequence |
| **Scholar** | 2,332 (OK) | 1,650 (OK) | MISS | OK | WEAK | OK | **4/6** | AGENTS skeletal |
| **Recovery** | 6,455 (**OVER**) | 5,447 (**OVER**) | MISS | MISS | MISS | MISS | **2/6** | 4 files missing |
| **Memory** | 8,271 (**OVER**) | 6,377 (**OVER**) | MISS | OK | OK | MISS | **3/6** | SOUL 107% over |
| **17 ACT-I** | MISS | MISS | MISS | MISS | MISS | MISS | **0/6** | No workspaces |

**System-wide: 0 beings have a DESCRIPTION file. This is a universal gap.**

---

## Part 2: Context Assembly Audit

### System Prompt Components (What Gets Loaded Per Turn)

Source: `src/bomba_sr/runtime/bridge.py` lines 636-695

| Component | Source File | Truncation | Est. Tokens (Prime) |
|-----------|-----------|------------|---------------------|
| `<soul>` | SOUL.md | **NONE** | ~1,597 |
| `<identity>` | IDENTITY.md | **NONE** | ~1,870 |
| `<mission>` | MISSION.md | **NONE** | ~2,305 |
| `<vision>` | VISION.md | **NONE** | ~822 |
| `<formula>` | FORMULA.md | 12,000 chars | ~1,595 |
| `<priorities>` | PRIORITIES.md | 8,000 chars | ~283 |
| `<knowledge>` | KNOWLEDGE.md | 4,000 chars | ~280 |
| `<team-context>` | TEAM_CONTEXT.md | 3,000 chars | ~168 |
| `<representation>` | REPRESENTATION.md | 3,000 chars | ~255 |
| Operational guideline | Hardcoded | Fixed | ~25 |
| Skill index XML | SkillDisclosure | Variable | ~200 |
| Selected skill context | Command routing | Variable | ~0-2,000 |
| **Subtotal: Identity** | | | **~9,400** |
| Tool schemas (78 tools) | builtin_*.py | **NONE** | **~15,600** |
| Context assembly (memory+history) | ContextPolicyEngine | Budget-capped | ~5,000-30,000 |
| Replay messages (30% cap) | Recent turns | Budget-capped | ~10,000-30,000 |
| **TOTAL PER TURN (Prime)** | | | **~40,000-85,000** |

### Total System Prompt by Being Type

| Being | Identity Tokens | Tool Tokens | Context Tokens | Total Per Turn |
|-------|----------------|-------------|----------------|----------------|
| **Prime** | ~9,400 | ~15,600 | ~15,000-30,000 | **~40,000-55,000** |
| **Forge** | ~1,700 | ~15,600 | ~5,000-15,000 | **~22,000-32,000** |
| **Scholar** | ~2,100 | ~15,600 | ~5,000-15,000 | **~23,000-33,000** |
| **Recovery** | ~4,400 | ~15,600 | ~5,000-15,000 | **~25,000-35,000** |
| **Memory** | ~4,200 | ~15,600 | ~5,000-15,000 | **~25,000-35,000** |

### Tool Count: 78 Total Tools

Source: `src/bomba_sr/tools/builtin_*.py`

| Category | Count | Examples |
|----------|-------|---------|
| Filesystem | 6 | read, write, edit, apply_patch, glob, grep |
| Memory | 3 | memory_search, memory_get, memory_store |
| Sub-agents | 3 | sessions_spawn, sessions_poll, sessions_list |
| Web | 2 | web_search, web_fetch |
| Pinecone | 4 | pinecone_query, pinecone_list_indexes, pinecone_upsert, pinecone_multi_query |
| Voice | 4 | voice_list_calls, voice_get_transcript, voice_make_call, voice_list_pathways |
| Colosseum | 5 | colosseum_run_round, colosseum_leaderboard, etc. |
| Prove-Ahead | 4 | prove_ahead_competitors, prove_ahead_matrix, etc. |
| Sisters | 5 | sisters_list, sisters_spawn, sisters_stop, etc. |
| Team Manager | 19 | team_graph_create, team_deploy, team_schedule_*, etc. |
| Projects | 5 | project_create, task_create, task_list, etc. |
| Scheduler | 4 | schedule_task, list_schedules, etc. |
| Skills | 4 | skill_create, skill_update, skill_install_* |
| Model/Discovery | 3 | switch_model, enable_tools, compact_context |
| Execution | 2 | exec, process |
| Code search | 1 | code_search |
| Knowledge | 1 | update_knowledge |
| Approvals | 2 | list_approvals, decide_approval |

**At ~200 tokens per schema, 78 tools = ~15,600 tokens just for tool definitions.**

### Per-Being Tool Filtering

Source: `src/bomba_sr/governance/tool_profiles.py` lines 70-83, `src/bomba_sr/runtime/config.py` lines 67-69

**FINDING: NO per-being tool filtering exists.**

- Default profile: `FULL` (all 78 tools)
- Profiles available: `MINIMAL` (1 tool), `CODING` (~30), `RESEARCH` (~8), `FULL` (all)
- Profiles are **process-wide env vars**, not per-being
- Tool registration is **per-tenant, not per-being** (`bridge.py` lines 2568-2666)
- A Scholar being that only needs `web_search` + `memory_search` gets all 78 tools

**ACT-I says:** "Only include tools the being actually needs. Every unnecessary tool reference eats tokens."

**Token waste:** A Scholar being burns ~13,000 tokens on tool schemas it will never use (voice, colosseum, team manager, prove-ahead, etc.)

### Context Window Self-Monitoring

Source: `src/bomba_sr/runtime/health.py` lines 1-55, `src/bomba_sr/runtime/loop.py` lines 327-336

**FINDING: No token-level monitoring.**

The `HealthSnapshot` (injected from iteration 2 onward) shows:
- Budget: `$1.20 / $2.00 (40% remaining)` — cost-based
- Iterations: `14/25` — count-based
- Tool stats: total/failed/denied

**Missing:** `context_window: 85,000/200,000 tokens (42% remaining)` — the being CANNOT see how much context it's consuming.

### Offload-at-50% Protocol

**FINDING: Does not exist.**

- `should_trigger_pre_compaction_flush()` defined in `context/policy.py` line 207 — **DEAD CODE, never called**
- `compact_context` tool exists but is manual-only (LLM must invoke it)
- No automatic threshold trigger at any capacity percentage

### Write-As-You-Go

**FINDING: Does not exist in the loop.**

Source: `src/bomba_sr/runtime/loop.py` lines 98-250

- All persistence happens AFTER the loop completes (`bridge.py` lines 898-1092)
- If loop crashes at iteration 24 of 25, ALL in-memory state is lost
- Tool results, partial text, accumulated messages — none persisted mid-loop
- `WorkspaceRescue` (`rescue.py`) saves git stash for filesystem changes only

### Context Assembly Compliance Matrix

| ACT-I Requirement | Status | Evidence |
|-------------------|--------|----------|
| Lean startup (only 5 ACT-I files) | **PARTIAL FAIL** | Loads 7-9 identity files, no 100K dump but ~9K tokens for Prime |
| Per-being tool filtering | **FAIL** | All beings get all 78 tools, ~15,600 token overhead |
| Context window self-monitoring | **FAIL** | HealthSnapshot has budget/iterations, NOT tokens |
| Offload-at-50% | **FAIL** | `should_trigger_pre_compaction_flush` is dead code |
| Write-as-you-go | **FAIL** | No mid-loop persistence; all writes are post-loop |
| No 100K+ token dump | **PASS** | Per-file caps exist; total identity < 15K tokens |

---

## Part 3: Memory Management Audit

### Automatic Persistence (Where We're Better Than ACT-I)

ACT-I says beings must manually write to memory. Our framework does it automatically at 6 levels:

| Channel | Trigger | Storage | Source |
|---------|---------|---------|--------|
| Working notes | Every turn | `memory/*.md` + SQLite `markdown_notes` | `bridge.py:959-967` |
| Conversation turns | Every turn | SQLite `conversation_turns` | `bridge.py:968-975` |
| Procedural learning | After tool chains | SQLite `procedural_memories` | `bridge.py:898-930` |
| Semantic learning | On user signals | SQLite `memories` | `bridge.py:1006-1019` |
| Session summaries | Every 5th turn | SQLite `session_summaries` | `bridge.py:976-1004` |
| Loop execution logs | Every turn | SQLite `loop_executions` | `bridge.py:1071-1092` |

**Verdict: SUPERIOR to ACT-I.** ACT-I relies on beings remembering to write. We persist automatically.

### On-Demand Retrieval

| Tool | Purpose | On-Demand? | Source |
|------|---------|------------|--------|
| `memory_search` | Search semantic + markdown memory | Yes | `builtin_memory.py` |
| `memory_get` | Retrieve specific memory items | Yes | `builtin_memory.py` |
| `memory_store` | Store new semantic memory | Yes | `builtin_memory.py` |
| `pinecone_query` | Embed + retrieve from Pinecone | Yes | `builtin_pinecone.py` |
| `pinecone_multi_query` | Parallel multi-index query | Yes | `builtin_pinecone.py` |
| `pinecone_upsert` | Write to Pinecone | Yes | `builtin_pinecone.py` |

**Gap:** No Supabase integration (ACT-I specifies "Pinecone + Supabase").

### Preloading vs On-Demand

Source: `src/bomba_sr/runtime/bridge.py` lines 544-593

**Every turn preloads:**
- `runtime.memory.recall()` — semantic + markdown memory retrieval
- `runtime.memory.recall_by_being()` — cross-context memory
- `runtime.memory.recall_procedural()` — tool-chain strategies
- Recent conversation turns (3-5)
- Session summary
- Code search results
- Full SoulConfig identity text

**ACT-I says:** "Beings must be able to call for memory and context ON DEMAND, not force-fed at startup."

**Reality:** We do both. Heavy preloading PLUS on-demand tools. The preloading is budget-aware (via `ContextPolicyEngine`) but cannot be opted out of.

### Context Overflow Protection

| Mechanism | Source | What It Does | Token-Aware? |
|-----------|--------|-------------|--------------|
| Budget hard stop | `loop.py:168-171` | Breaks at 90% of USD budget | No (cost-based) |
| Max iterations | `loop.py:114` | 25 iterations max | No |
| Loop detection | `loop.py:440-451` | Detects repeating tool calls | No |
| Context assembly compression | `policy.py:97-204` | Head+tail truncation of sections | Yes |
| Replay history cap | `bridge.py:737-745` | 30% of available tokens | Yes |
| Pre-compaction flush | `policy.py:207` | **DEAD CODE — never called** | Yes |

**Synthesis overflow structural risk:** The `state.messages` list in `LoopState` grows unboundedly during the loop. Each iteration adds assistant + tool result messages. No automatic compaction trigger exists.

### Conversation History Management

**FULLY COMPLIANT** with good implementation:

1. **Every turn recorded** in `conversation_turns` with token estimates
2. **Last 3-5 turns replayed** as full ChatMessage pairs (budget-capped at 30%)
3. **Older turns summarized** every 5th turn via LLM-generated digests
4. **Summaries injected** into context assembly as `recent_history`
5. **Budget-aware replay** — `_cap_recent_turn_messages()` iterates from most recent backward

### Memory Compliance Matrix

| ACT-I Requirement | Status | Evidence |
|-------------------|--------|----------|
| Automatic memory persistence | **EXCEEDS** | 6 automatic channels vs ACT-I's manual approach |
| On-demand Pinecone query | **PASS** | 4 Pinecone tools available |
| On-demand Supabase | **FAIL** | No Supabase anywhere in codebase |
| Write findings as you work | **FAIL** | All writes post-loop; no mid-loop persistence |
| Offload at 50% capacity | **FAIL** | Dead code exists but is not wired |
| Crash survival | **PARTIAL** | Previous turns safe; current turn lost if loop crashes |
| Conversation history mgmt | **PASS** | Sliding window + summaries + budget-capped replay |
| Graceful degradation | **PARTIAL** | Budget-aware compression exists but mid-loop unbounded |

---

## Part 4: Agent Tier Handling Audit

### ACT-I Three-Tier Model

| Tier | Purpose | Context Budget | Key Rules |
|------|---------|---------------|-----------|
| **Being** | Persistent sessions | Full | Lean startup, fetch on demand, offload at 50% |
| **Contractor** | Multi-step sub-agent | Medium | Pre-inject 3-5 Pinecone results, give fetch tool, output path, additive-only |
| **Baby** | Single-task sub-agent | Minimal | One task/one output/one file, <1000 word prompt, write-as-you-go, never naked |

### Current Implementation: No Tier Differentiation

**FINDING: The system treats ALL delegated work uniformly.**

#### `SubTaskPlan` has no tier field
Source: `src/bomba_sr/orchestration/engine.py` line 97-118

```python
class SubTaskPlan:
    __slots__ = ("being_id", "title", "instructions", "done_when")
```

No `tier`, no `output_path`, no `prompt_budget`, no `context_injection`.

#### Uniform delegation message
Source: `src/bomba_sr/orchestration/engine.py` lines 627-638

Every sub-task gets the same template:
```
[IDENTITY CONTEXT] (if ACT-I being)
You have been assigned a sub-task by SAI Prime.
TASK TITLE: ...
INSTRUCTIONS: ...
ACCEPTANCE CRITERIA: ...
Complete this task using your available tools...
```

**Missing per ACT-I:**
- No output path (`"write your output to reports/writer-email-sequence-v1.md"`)
- No write-as-you-go instruction (`"Write incrementally, don't hold in memory"`)
- No fetch tool instruction (`"If you need context: python3 tools/context_fetch.py"`)
- No pre-loaded Pinecone results
- No tier-specific prompt budget

#### Orchestration does NOT use SubAgentWorkerFactory
Source: `src/bomba_sr/orchestration/engine.py` — zero references to `SubAgent`, `subagent`, `sessions_spawn`, or `worker`.

| System | Entry Point | How It Delegates | Missing |
|--------|-------------|-----------------|---------|
| **Orchestration Engine** | `engine.py:_execute_subtask()` | Direct `bridge.handle_turn()` | Crash recovery, depth enforcement, event streaming |
| **Sub-Agent System** | `orchestrator.py:spawn_async()` | Via `SubAgentWorkerFactory` | Used by sisters, not orchestration |
| **Sister System** | `sisters.py:spawn_sister()` | Via `SubAgentOrchestrator` | Correctly uses sub-agent infra |

**Critical gap:** Orchestrated sub-tasks miss crash recovery, depth enforcement, and event streaming because they bypass the sub-agent protocol entirely.

#### Wrong TurnProfile default
Source: `engine.py` line 648 — `TurnRequest` uses default `TurnProfile.CHAT`, not `TASK_EXECUTION`.

Sub-tasks get chat-optimized context weights (34% recent history) instead of task-optimized weights (34% working memory).

#### No tier-based context budgeting
Source: `src/bomba_sr/context/policy.py`

Available profiles: `CHAT`, `TASK_EXECUTION`, `PLANNING`, `MEMORY_RECALL`, `SUBAGENT_ORCHESTRATION`

**Missing:** No `CONTRACTOR` or `BABY` profiles. A baby-tier agent gets the same context budget as a full being.

### Tier Compliance Matrix

| ACT-I Requirement | Status | Details |
|-------------------|--------|---------|
| Tier differentiation (Being/Contractor/Baby) | **NOT IMPLEMENTED** | No tier field anywhere |
| Contractors: pre-injected Pinecone results | **NOT IMPLEMENTED** | No Pinecone in orchestration |
| Contractors: given fetch tool instructions | **NOT IMPLEMENTED** | Not in delegation message |
| Contractors: clear output path | **NOT IMPLEMENTED** | "Provide results as a clear response" |
| Contractors: additive-only | **NOT IMPLEMENTED** | No write-mode restriction |
| Babies: lean prompt (<1000 words) | **NOT IMPLEMENTED** | Full context assembly for all |
| Babies: write-as-you-go instruction | **NOT IMPLEMENTED** | Not mentioned |
| Babies: never sent naked | **NOT IMPLEMENTED** | Missing: files, mission, output path, context_fetch |
| Orchestration uses sub-agent infra | **NOT IMPLEMENTED** | Separate codepaths |
| Task TurnProfile | **WRONG** | Defaults to CHAT, should be TASK_EXECUTION |

---

## Part 5: Gap Analysis & Migration Plan

### MISSING — Things ACT-I Requires That We Don't Have

| # | Gap | Impact | Where to Build | Complexity |
|---|-----|--------|----------------|------------|
| M1 | **DESCRIPTION files** (0/22 beings) | No causal north star for any being | Create `DESCRIPTION.md` in each workspace | Easy |
| M2 | **Per-being tool filtering** | ~13,000 wasted tokens/turn for non-Prime beings | `bridge.py` tool registration, per-being profile map | Medium |
| M3 | **Context window token monitoring** | Beings can't see context consumption | `health.py` + `loop.py` — add token tracking | Medium |
| M4 | **Offload-at-50% auto-trigger** | No proactive memory offload | Wire `should_trigger_pre_compaction_flush` (dead code) into loop | Medium |
| M5 | **Write-as-you-go in loop** | Current turn lost on crash | `loop.py` — checkpoint after each iteration | Medium |
| M6 | **Tier-differentiated delegation** | All tasks get same bloated treatment | `engine.py` — tier field + templates | Hard |
| M7 | **Contractor pre-injection** | No Pinecone results pre-loaded | `engine.py:_execute_subtask()` — add Pinecone fetch | Medium |
| M8 | **Baby lean prompt** | Babies get full 30K+ token context | New `BABY` TurnProfile, slim delegation template | Medium |
| M9 | **Output path in delegation** | Sub-tasks have nowhere to write to | `SubTaskPlan` + delegation message | Easy |
| M10 | **Orchestration → SubAgent integration** | No crash recovery for orchestrated tasks | Refactor `_execute_subtask()` to use `spawn_async()` | Hard |
| M11 | **Creature scale scoring** | No quality measurement framework | New module + Kai integration | Hard |
| M12 | **Kai refinement loop** | No automated being quality check | New tool/workflow | Hard |

### WHERE WE'RE BETTER — Things Our Framework Does That ACT-I Doesn't Address

| # | Advantage | Evidence | ACT-I Equivalent |
|---|-----------|----------|-----------------|
| B1 | **Automatic 6-channel memory persistence** | `bridge.py:898-1092` — working notes, turns, procedural, semantic, summaries, loop logs | ACT-I: manual `memory/*.md` writes |
| B2 | **Budget-aware context assembly** | `policy.py:83-204` — profile-weighted allocation with compression pipeline | ACT-I: manual context management |
| B3 | **Conversation history sliding window + LLM summaries** | `bridge.py:573-1004` — 5-turn replay, 5-turn summary cycle, budget-capped | ACT-I: not specified |
| B4 | **Procedural memory learning** | `bridge.py:898-930` — automatic tool-chain success/failure tracking | ACT-I: not specified |
| B5 | **Self-correcting adaptation** | `adaptation/runtime_adaptation.py` — metrics-based policy correction every N turns | ACT-I: not specified |
| B6 | **SoulConfig multi-file identity** | SOUL + IDENTITY + MISSION + VISION + FORMULA + PRIORITIES + KNOWLEDGE | ACT-I: only SOUL.md + IDENTITY.md |
| B7 | **Loop detection** | `loop.py:440-451` — repeating tool-call detection | ACT-I: not specified |
| B8 | **Semantic contradiction detection** | `consolidation.py` — archives old belief, promotes new | ACT-I: not specified |
| B9 | **Crash storm detection** | `orchestrator.py:26-52` — window/max/cooldown for sub-agents | ACT-I: not specified |
| B10 | **Governance pipeline** | `governance/policy_pipeline.py` — tool visibility + per-call risk/confidence | ACT-I: not specified |

### WHERE WE FALL SHORT — Things Both Address But ACT-I Does Better

| # | Area | ACT-I Standard | Our Reality | Code Path to Fix |
|---|------|---------------|-------------|-----------------|
| S1 | **SOUL.md size** | < 4,000 chars | Prime: 6,390, Recovery: 6,455, Memory: 8,271 | Rewrite SOUL.md files; apply soul-upgrades |
| S2 | **IDENTITY.md size** | < 2,000 chars | Prime: 7,482, Recovery: 5,447, Memory: 6,377 | Rewrite IDENTITY.md; facts only |
| S3 | **Tool bloat** | Only needed tools | 78 tools for everyone (~15,600 tokens) | Per-being tool profiles in `bridge.py` |
| S4 | **Lean startup** | 5 files only | 7-9 files + all tools preloaded | Identity payload truncation in `bridge.py` |
| S5 | **Sub-agent context** | Contractors get 3-5 results + output path | Uniform full-context delegation | `engine.py:_execute_subtask()` |
| S6 | **Memory offload** | Proactive at 50% | Reactive (LLM must call compact_context) | Wire dead code in `policy.py:207` |
| S7 | **Boot sequence** | Every session reads SOUL → IDENTITY → USER → memory/ | Only SoulConfig auto-loads; no AGENTS.md protocol | `bridge.py` startup hook |

---

### MIGRATION PLAN (Ordered by Impact × Feasibility)

#### Phase 1: Quick Wins — Identity Compliance (Est. savings: ~5,000 tokens/turn for Prime)

| # | Change | Files | Token Savings | Complexity |
|---|--------|-------|---------------|------------|
| 1.1 | **Trim Prime SOUL.md to < 4,000 chars** | `workspaces/prime/SOUL.md` | ~597 tokens | Easy |
| 1.2 | **Trim Prime IDENTITY.md to < 2,000 chars** | `workspaces/prime/IDENTITY.md` | ~1,370 tokens | Easy |
| 1.3 | **Apply soul-upgrades for Recovery** | `workspaces/recovery/SOUL.md` (use `soul-upgrades/RECOVERY-SOUL.md`) | ~643 tokens | Easy |
| 1.4 | **Trim Recovery IDENTITY.md to < 2,000** | `workspaces/recovery/IDENTITY.md` | ~862 tokens |Easy |
| 1.5 | **Trim Memory SOUL.md to < 4,000** | `workspaces/sai-memory/SOUL.md` | ~1,068 tokens | Easy |
| 1.6 | **Trim Memory IDENTITY.md to < 2,000** | `workspaces/sai-memory/IDENTITY.md` | ~1,094 tokens | Easy |
| 1.7 | **Create DESCRIPTION.md for all 5 sisters** | `workspaces/*/DESCRIPTION.md` | 0 (new file) | Easy |
| 1.8 | **Create missing Recovery files** | `workspaces/recovery/{USER,AGENTS,TOOLS}.md` | 0 (new files) | Easy |

#### Phase 2: Per-Being Tool Filtering (Est. savings: ~8,000-13,000 tokens/turn for non-Prime)

| # | Change | Files | Token Savings | Complexity |
|---|--------|-------|---------------|------------|
| 2.1 | **Define per-being tool profiles** | New: `src/bomba_sr/governance/being_tool_profiles.py` | — | Medium |
| 2.2 | **Load tool profile from being config** | `src/bomba_sr/runtime/bridge.py` (tool registration) | ~8,000-13,000/turn | Medium |
| 2.3 | **Annotate sister configs with tool profile** | `workspaces/prime/sisters.json` | — | Easy |

Suggested profiles:
```
Prime:    full (78 tools)
Forge:    coding + web + memory + pinecone + skills (30 tools, ~6,000 tokens)
Scholar:  research + web + memory + pinecone (15 tools, ~3,000 tokens)
Recovery: coding + web + memory + voice (20 tools, ~4,000 tokens)
Memory:   memory + pinecone (8 tools, ~1,600 tokens)
```

#### Phase 3: Context Window Monitoring + Offload (Est. savings: prevents crash at capacity)

| # | Change | Files | Impact | Complexity |
|---|--------|-------|--------|------------|
| 3.1 | **Add token tracking to HealthSnapshot** | `src/bomba_sr/runtime/health.py` | Beings see consumption | Medium |
| 3.2 | **Wire `should_trigger_pre_compaction_flush` into loop** | `src/bomba_sr/runtime/loop.py` | Auto-offload at threshold | Medium |
| 3.3 | **Add auto-compact trigger at 60% capacity** | `src/bomba_sr/runtime/loop.py` | Proactive memory offload | Medium |
| 3.4 | **Write-as-you-go: checkpoint after every 5 iterations** | `src/bomba_sr/runtime/loop.py` | Crash survival | Medium |

#### Phase 4: Tier-Differentiated Orchestration (Est. savings: ~15,000 tokens for baby tasks)

| # | Change | Files | Impact | Complexity |
|---|--------|-------|--------|------------|
| 4.1 | **Add `tier` field to SubTaskPlan** | `src/bomba_sr/orchestration/engine.py` | Tier classification | Easy |
| 4.2 | **Update PLAN_SYSTEM_PROMPT with tier classification** | `engine.py` lines 146-175 | LLM classifies tasks | Easy |
| 4.3 | **Add CONTRACTOR and BABY TurnProfiles** | `src/bomba_sr/context/policy.py` | Tier-specific context budgets | Medium |
| 4.4 | **Baby delegation: lean prompt template** | `engine.py:_execute_subtask()` | <1000 word prompts | Medium |
| 4.5 | **Contractor delegation: pre-inject Pinecone** | `engine.py:_execute_subtask()` | Pre-loaded context | Medium |
| 4.6 | **Add output_path to delegation message** | `engine.py:_execute_subtask()` | Clear deliverable location | Easy |
| 4.7 | **Add write-as-you-go instruction to delegation** | `engine.py:_execute_subtask()` | Crash survival | Easy |
| 4.8 | **Fix TurnProfile default** | `engine.py` line 648 | Use TASK_EXECUTION | Easy |

#### Phase 5: Architectural Integration (Enables full ACT-I compliance)

| # | Change | Files | Impact | Complexity |
|---|--------|-------|--------|------------|
| 5.1 | **Route orchestration through SubAgentOrchestrator** | `engine.py`, `orchestrator.py` | Crash recovery + depth enforcement | Hard |
| 5.2 | **ACT-I being workspaces** | `workspaces/{being-id}/` directories | Per-being identity files | Hard |
| 5.3 | **Creature scale scoring module** | New: `src/bomba_sr/acti/scoring.py` | Quality measurement | Hard |
| 5.4 | **Kai refinement integration** | New: workflow/tool | Automated quality checks | Hard |

---

### Context Budget: Current vs Target

```
CURRENT STATE — Prime Being (per turn)
┌─────────────────────────────────────────────────────────────────┐
│ 200,000 token context window                                    │
├──────────────────────────────────┬──────────────────────────────┤
│ IDENTITY PAYLOAD     9,400 (5%) │                              │
│ ████████░░░░░░░░░░░░░░░░░░░░░░░ │                              │
├──────────────────────────────────┤                              │
│ TOOL SCHEMAS        15,600 (8%) │   OUTPUT RESERVED            │
│ ████████████████░░░░░░░░░░░░░░░ │   40,000 (20%)              │
├──────────────────────────────────┤   ████████████████           │
│ CONTEXT ASSEMBLY    20,000 (10%)│                              │
│ ████████████████████░░░░░░░░░░░ │                              │
├──────────────────────────────────┤                              │
│ REPLAY HISTORY      30,000 (15%)│   SAFETY MARGIN              │
│ ██████████████████████████████░░ │   6,000 (3%)                │
├──────────────────────────────────┤   ██████                     │
│ AVAILABLE FOR WORK  78,000 (39%)│                              │
│ (agentic loop messages)         │                              │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │                              │
└──────────────────────────────────┴──────────────────────────────┘
  Fixed overhead: ~75,000 tokens (38%)
  Available for actual work: ~78,000 tokens (39%)

TARGET STATE — Prime Being (after migration)
┌─────────────────────────────────────────────────────────────────┐
│ 200,000 token context window                                    │
├──────────────────────────────────┬──────────────────────────────┤
│ IDENTITY PAYLOAD     4,000 (2%) │  Savings: -5,400 tokens      │
│ ████░░░░░░░░░░░░░░░░░░░░░░░░░░ │  (trim SOUL+IDENTITY)       │
├──────────────────────────────────┤                              │
│ TOOL SCHEMAS         8,000 (4%) │   OUTPUT RESERVED            │
│ ████████░░░░░░░░░░░░░░░░░░░░░░░ │   40,000 (20%)              │
├──────────────────────────────────┤   ████████████████           │
│ CONTEXT ASSEMBLY    15,000 (8%) │  Savings: -5,000 tokens      │
│ ███████████████░░░░░░░░░░░░░░░░ │  (demand-driven)            │
├──────────────────────────────────┤                              │
│ REPLAY HISTORY      25,000 (13%)│   SAFETY MARGIN              │
│ █████████████████████████░░░░░░ │   6,000 (3%)                │
├──────────────────────────────────┤   ██████                     │
│ AVAILABLE FOR WORK 102,000 (51%)│  +24,000 tokens recovered!   │
│ (agentic loop messages)         │                              │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │                              │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │                              │
└──────────────────────────────────┴──────────────────────────────┘
  Fixed overhead: ~52,000 tokens (26%)
  Available for actual work: ~102,000 tokens (51%)
  NET GAIN: +24,000 tokens per turn (31% more working space)

TARGET STATE — Scholar Being (after per-being tool filtering)
┌─────────────────────────────────────────────────────────────────┐
│ 200,000 token context window                                    │
├──────────────────────────────────┬──────────────────────────────┤
│ IDENTITY PAYLOAD     2,100 (1%) │                              │
│ ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │                              │
├──────────────────────────────────┤                              │
│ TOOL SCHEMAS         3,000 (2%) │   OUTPUT RESERVED            │
│ ███░░░░░░░░░░░░░░░░░░░░░░░░░░░ │   40,000 (20%)              │
├──────────────────────────────────┤   ████████████████           │
│ CONTEXT + REPLAY    30,000 (15%)│                              │
│ ██████████████████████████████░░ │   SAFETY MARGIN              │
├──────────────────────────────────┤   6,000 (3%)                │
│ AVAILABLE FOR WORK 119,000 (60%)│   ██████                     │
│ (agentic loop messages)         │                              │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │                              │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │                              │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │                              │
└──────────────────────────────────┴──────────────────────────────┘
  vs CURRENT Scholar: ~33,000 token overhead → ~35,000 token overhead
  Scholar gains ~12,600 tokens from tool filtering alone
```

---

### Migration Priority Score

| Phase | Est. Token Savings/Turn | Effort | Priority |
|-------|------------------------|--------|----------|
| **Phase 1: Identity trim** | ~5,600 (Prime only) | 1-2 hours | **P0 — Do First** |
| **Phase 2: Tool filtering** | ~8,000-13,000 (per non-Prime being) | 4-6 hours | **P0 — Do First** |
| **Phase 3: Context monitoring** | Prevents crashes | 4-6 hours | **P1 — Do Soon** |
| **Phase 4: Tier orchestration** | ~15,000 (baby tasks) | 8-12 hours | **P1 — Do Soon** |
| **Phase 5: Architecture** | Enables full ACT-I | 16-24 hours | **P2 — Plan** |

**Total estimated token recovery:** ~24,000 tokens/turn for Prime, ~12,600/turn for each non-Prime being.

---

*Generated by comprehensive codebase audit against "How We Build Masterful ACT-I Beings" (March 2026)*
