# Memory Architecture Audit — bomba-sr-runtime
**Date:** 2026-03-06
**Auditor:** Claude Sonnet 4.6
**Scope:** All storage locations, scope boundaries, cross-being pathways, and lifecycle mechanics

---

## Table of Contents
1. [Storage Topology Overview](#1-storage-topology-overview)
2. [Every Storage Location — Full Schema](#2-every-storage-location--full-schema)
3. [Filesystem Storage](#3-filesystem-storage)
4. [External Storage — Pinecone](#4-external-storage--pinecone)
5. [Scope Boundaries and Isolation Model](#5-scope-boundaries-and-isolation-model)
6. [Cross-Being Memory Pathways](#6-cross-being-memory-pathways)
7. [Scenario Traces](#7-scenario-traces)
8. [Memory Lifecycle — End-to-End Trace](#8-memory-lifecycle--end-to-end-trace)
9. [Dream Cycle — Deep Trace](#9-dream-cycle--deep-trace)
10. [Gaps, Dead Code, and Known Risks](#10-gaps-dead-code-and-known-risks)
11. [ASCII Diagrams](#11-ascii-diagrams)

---

## 1. Storage Topology Overview

The runtime uses a **per-tenant SQLite database** as its canonical store. Every tenant gets its own database file at:

```
{BOMBA_RUNTIME_HOME}/tenants/{tenant_id}/runtime/runtime.db
```

Default: `.runtime/tenants/{tenant_id}/runtime/runtime.db`

All services (memory, subagents, adaptation, governance, skills, artifacts) share a single `RuntimeDB` instance per tenant. This means all tables described below co-exist in one SQLite file per tenant, with WAL mode enabled (`PRAGMA journal_mode = WAL`) and a 5-second busy timeout.

The `RuntimeDB` class (`src/bomba_sr/storage/db.py:10`) wraps all operations in `threading.RLock()`, making it safe for concurrent reads and writes from the agentic loop thread, heartbeat thread, cron thread, sub-agent threads, and dream cycle thread.

**Key layout:**

```
.runtime/
  tenants/
    {tenant_id}/
      runtime/
        runtime.db          <-- All SQLite tables for this tenant
      memory/               <-- Markdown note files (working memory)
        {user_id}/
          {year}/{month}/{day}/
            {HHMMSS}-{slug}-{uuid8}.md
      artifacts/            <-- Artifact files (code, markdown, PDFs)
        {session_id}/
          {turn_id}-{uuid8}.{ext}
      tenant.json           <-- Workspace binding

workspaces/
  {being_id}/
    SOUL.md, IDENTITY.md, MISSION.md, VISION.md
    FORMULA.md, PRIORITIES.md, KNOWLEDGE.md, REPRESENTATION.md
    TEAM_CONTEXT.md         <-- Shared (read from parent dir if absent locally)
    memory/                 <-- Hand-curated static memory files (NOT auto-written)
    sisters.json            <-- Sister config (Prime tenant only)

  sai-memory/
    dream_logs/
      {YYYY-MM-DD-HH:MM}.md  <-- Dream cycle reports
    memory/                 <-- Static memory documents (NOT auto-written by runtime)
    SOUL.md, IDENTITY.md, etc.

External:
  Pinecone indexes          <-- Long-term vector store (optional, gated by BOMBA_PINECONE_ENABLED)
```

---

## 2. Every Storage Location — Full Schema

All tables are created via `_ensure_schema()` calls in each service constructor. The per-tenant DB is opened in `_tenant_runtime()` at `bridge.py:2429`.

---

### 2.1 `markdown_notes` — Working/Episodic Memory

**File:** `src/bomba_sr/memory/hybrid.py:82`

```sql
CREATE TABLE IF NOT EXISTS markdown_notes (
  note_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  session_id TEXT,
  relative_path TEXT NOT NULL,
  title TEXT NOT NULL,
  tags TEXT NOT NULL,          -- JSON array
  confidence REAL NOT NULL,
  created_at TEXT NOT NULL,
  being_id TEXT               -- added via ALTER TABLE migration at hybrid.py:165
);

CREATE INDEX idx_markdown_notes_user_created
  ON markdown_notes(user_id, created_at DESC);
```

**Written by:**
- `HybridMemoryStore.append_working_note()` at `hybrid.py:175` — called every turn from `bridge.py:959` immediately after LLM response is received
- Write triggers: unconditionally after every handle_turn() call, including command routes and skill-nl routes (`bridge.py:209-213` for command bypass path, `bridge.py:959` for main path)

**Read by:**
- `HybridMemoryStore._recall_markdown()` at `hybrid.py:471` — called from `hybrid.py:423` (recall by user_id)
- `HybridMemoryStore._recall_markdown_by_being()` at `hybrid.py:518` — called from `hybrid.py:449` (recall by being_id)
- `DreamCycle._phase_gather()` at `dreaming.py:259` — queries `WHERE user_id = ? OR being_id = ?`

**Scope keys:** `user_id` (primary partition) + `being_id` (secondary, cross-context access)

**Retention:** Grows forever. No pruning. The filesystem `.md` file and the DB index row are both permanent.

**Note:** The actual content lives as a `.md` file on disk (at `memory_root / relative_path`). The DB row is a metadata index only. If the file is deleted, `_read_note_body()` at `hybrid.py:819` silently returns `""`.

---

### 2.2 `memory_embeddings` — Vector Index for Working Notes

**File:** `src/bomba_sr/memory/hybrid.py:99`

```sql
CREATE TABLE IF NOT EXISTS memory_embeddings (
  id TEXT PRIMARY KEY,
  note_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  model TEXT NOT NULL,
  vector_json TEXT NOT NULL,   -- JSON-encoded float array (OpenAI embedding)
  created_at TEXT NOT NULL,
  FOREIGN KEY(note_id) REFERENCES markdown_notes(note_id) ON DELETE CASCADE
);

CREATE INDEX idx_memory_embeddings_user
  ON memory_embeddings(user_id, created_at DESC);
```

**Written by:** `HybridMemoryStore.append_working_note()` at `hybrid.py:238` — only when `embedding_provider` is set (requires `OPENAI_API_KEY`)

**Read by:** `HybridMemoryStore._embedding_scores()` at `hybrid.py:560` — used during recall to compute cosine similarity instead of lexical scoring

**Scope keys:** `user_id`

**Retention:** Grows forever. Cascades on note deletion (but notes are never deleted).

**Gap:** No being_id column. Embedding recall only works by user_id, not being_id. The `_recall_markdown_by_being()` path falls back to lexical scoring only (`hybrid.py:535-538`).

---

### 2.3 `learning_updates` — Learning Approval Queue

**File:** `src/bomba_sr/memory/hybrid.py:112`

```sql
CREATE TABLE IF NOT EXISTS learning_updates (
  update_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  memory_key TEXT NOT NULL,
  content TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL,        -- 'pending' | 'applied' | 'rejected'
  evidence_refs TEXT NOT NULL, -- JSON array of note_id strings
  memory_id TEXT,              -- FK to memories.id if applied
  reason TEXT,
  created_at TEXT NOT NULL,
  decided_at TEXT
);

CREATE INDEX idx_learning_updates_user
  ON learning_updates(tenant_id, user_id, created_at DESC);
```

**Written by:**
- `HybridMemoryStore.learn_semantic()` at `hybrid.py:266` — called from:
  - `bridge.py:1010` when `_learning_signal()` detects a high-confidence user preference signal
  - `DreamCycle._phase_derive()` at `dreaming.py:498` for derived insights (confidence=0.6)
  - `DreamCycle._phase_cross_pollinate()` at `dreaming.py:614` for cross-pollinated insights (confidence=0.5)
  - `orchestration/engine.py:1155` for task result summaries (confidence=0.9)

**Read by:**
- `HybridMemoryStore.pending_approvals()` at `hybrid.py:375` — returned in every turn response and checked in context assembly
- `HybridMemoryStore.approve_learning()` at `hybrid.py:325` — manual approval path

**Scope keys:** `tenant_id`, `user_id`

**Retention:** Grows forever. Applied/rejected records are never pruned.

---

### 2.4 `conversation_turns` — Per-Session Conversation History

**File:** `src/bomba_sr/memory/hybrid.py:130`

```sql
CREATE TABLE IF NOT EXISTS conversation_turns (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  turn_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  user_message TEXT NOT NULL,
  assistant_message TEXT NOT NULL,
  turn_number INTEGER NOT NULL,
  token_estimate INTEGER NOT NULL,  -- (len(user)+len(assistant))/4
  created_at TEXT NOT NULL
);

CREATE INDEX idx_conv_turns_session
  ON conversation_turns(tenant_id, session_id, turn_number DESC);
```

**Written by:**
- `HybridMemoryStore.record_turn()` at `hybrid.py:582` — called from `bridge.py:968` after every turn (main path) and `bridge.py:209` (command bypass path)

**Read by:**
- `HybridMemoryStore.get_recent_turns()` at `hybrid.py:648` → called from `bridge.py:578-589` to build replay messages (last 3 turns for orchestration sessions, last 5 for regular sessions)
- `HybridMemoryStore.get_turns_for_summary()` at `hybrid.py:655` → called from `bridge.py:983` to gather turns for LLM summarization (every 5th turn)

**Scope keys:** `tenant_id`, `session_id`

**Retention:** Grows indefinitely per session. No pruning. Summarization happens separately. Old turns are never deleted even after summarization.

---

### 2.5 `session_summaries` — Session Digest

**File:** `src/bomba_sr/memory/hybrid.py:146`

```sql
CREATE TABLE IF NOT EXISTS session_summaries (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  summary_text TEXT NOT NULL,
  covers_through_turn INTEGER NOT NULL,
  token_estimate INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(tenant_id, session_id)      -- only one summary per session (upserted)
);

CREATE INDEX idx_session_summaries
  ON session_summaries(tenant_id, session_id, covers_through_turn DESC);
```

**Written by:**
- `HybridMemoryStore.update_session_summary()` at `hybrid.py:723` — called from `bridge.py:998` when `turn_number % 5 == 0` (every 5th turn, if there are turns to summarize beyond the recent window of 3)

**Read by:**
- `HybridMemoryStore.get_session_summary()` at `hybrid.py:702` — called from `bridge.py:590`, injected into context as `session_summary` in the `recent_history` input

**Scope keys:** `tenant_id`, `session_id`

**Trigger:** Every 5th turn within a session, covering turns not already in the summary and not in the recent 3-turn window.

**Retention:** One row per session, updated in place. Old summary text is replaced. There is no archive of old summaries.

**Gap:** The `covers_through_turn` field means gaps can exist. If a session is created fresh with a session_id that was previously used in another tenant, the `UNIQUE(tenant_id, session_id)` constraint prevents conflicts.

---

### 2.6 `memories` — Semantic Long-Term Memory

**File:** `src/bomba_sr/memory/consolidation.py:56`

```sql
CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  memory_key TEXT NOT NULL,
  tier TEXT NOT NULL,          -- always 'semantic' in practice
  content TEXT NOT NULL,
  entities TEXT NOT NULL,      -- JSON array (usually empty)
  evidence_refs TEXT NOT NULL, -- JSON array of note_ids
  recency_ts TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,   -- 0 = archived
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  being_id TEXT,               -- added via ALTER TABLE at consolidation.py:107
  UNIQUE(user_id, memory_key, version)
);

CREATE INDEX idx_memories_active_user
  ON memories(user_id, tier, active, updated_at DESC);
```

**Written by:**
- `MemoryConsolidator.upsert()` at `consolidation.py:118` — via `HybridMemoryStore.learn_semantic()` at `hybrid.py:289`
  - On identical content: updates `recency_ts` and `evidence_refs` only
  - On changed content: archives old row, inserts new row at `version+1`
- `DreamCycle._phase_prune()` at `dreaming.py:561` — sets `active=0` for excess memories
- `DreamCycle._phase_consolidate()` via `_archive_memory_by_key()` at `dreaming.py:714` — sets `active=0`

**Read by:**
- `MemoryConsolidator.retrieve()` at `consolidation.py:218` — by `user_id`, active=1, tier='semantic'
- `MemoryConsolidator.retrieve_by_being()` at `consolidation.py:372` — by `being_id`, active=1, tier='semantic'
- `DreamCycle._phase_gather()` at `dreaming.py:284` — queries `user_id = ? OR being_id = ?`
- `DreamCycle._phase_prune()` at `dreaming.py:524` — counts active memories per being

**Scope keys:** `user_id` (primary) + `being_id` (secondary, cross-context)

**Retention:** Active=0 rows are never deleted. The archive path creates a record in `memory_archive` and sets `active=0`. Prune sets `active=0` when count exceeds 200 (`MEMORY_PRUNE_THRESHOLD` at `dreaming.py:33`).

---

### 2.7 `memory_archive` — Superseded Semantic Beliefs

**File:** `src/bomba_sr/memory/consolidation.py:74`

```sql
CREATE TABLE IF NOT EXISTS memory_archive (
  id TEXT PRIMARY KEY,
  memory_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  memory_key TEXT NOT NULL,
  old_content TEXT NOT NULL,
  archived_at TEXT NOT NULL,
  reason TEXT NOT NULL,        -- 'contradiction_or_update' | 'dream_duplicate' | 'dream_stale' | 'dream_contradiction_resolved' | 'dream_prune'
  FOREIGN KEY(memory_id) REFERENCES memories(id)
);
```

**Written by:**
- `MemoryConsolidator.upsert()` at `consolidation.py:179` — when content changes (contradiction/update path)
- `DreamCycle._archive_memory_by_key()` at `dreaming.py:705` — for dream consolidation actions
- `DreamCycle._phase_prune()` at `dreaming.py:554` — for pruned memories

**Read by:** Never read in normal operation. Used only for `dashboard_overview()` counts at `bridge.py:2193`.

**Scope keys:** `user_id`

**Retention:** Never deleted.

---

### 2.8 `procedural_memories` — Tool-Chain Strategy Store

**File:** `src/bomba_sr/memory/consolidation.py:88`

```sql
CREATE TABLE IF NOT EXISTS procedural_memories (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  strategy_key TEXT NOT NULL,   -- 'toolchain_{sha1_12hex}' computed at bridge.py:911
  content TEXT NOT NULL,         -- 'Use tool chain: {tools}. Observed stop_reason=...'
  success_count INTEGER NOT NULL DEFAULT 0,
  failure_count INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  being_id TEXT,                -- added via ALTER TABLE at consolidation.py:108
  UNIQUE(user_id, strategy_key)
);

CREATE INDEX idx_procedural_memories_user
  ON procedural_memories(user_id, active, updated_at DESC);
```

**Written by:**
- `MemoryConsolidator.learn_procedural()` at `consolidation.py:266` — via `HybridMemoryStore.learn_procedural()` at `hybrid.py:397`
  - Called from `bridge.py:918` after every agentic loop that executed at least one tool call
  - `strategy_key` = `toolchain_{sha1(comma_joined_tool_names)[:12]}`
  - `success` = all tool statuses are "executed" with no failures

**Read by:**
- `MemoryConsolidator.recall_procedural()` at `consolidation.py:336` — by `user_id`, scores = `lexical_score * success_ratio`
- `MemoryConsolidator.recall_procedural_by_being()` at `consolidation.py:412` — by `being_id`
- `DreamCycle._phase_gather()` at `dreaming.py:308` — queries `user_id = ? OR being_id = ?`

**Scope keys:** `user_id` (primary) + `being_id` (secondary)

**Retention:** Never deleted. Success/failure counts grow cumulatively. `active` flag unused (always 1 in practice — no code path sets it to 0 for procedural memories except the dead `backfill_being_id` helper at `consolidation.py:449`).

---

### 2.9 `subagent_runs` — Sub-Agent Lifecycle Records

**File:** `src/bomba_sr/subagents/protocol.py:68`

```sql
CREATE TABLE IF NOT EXISTS subagent_runs (
  run_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL DEFAULT '',
  task_id TEXT NOT NULL,
  ticket_id TEXT NOT NULL,
  parent_run_id TEXT,
  parent_session_id TEXT NOT NULL,
  parent_turn_id TEXT NOT NULL,
  parent_agent_id TEXT NOT NULL,
  child_agent_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  goal TEXT NOT NULL,
  done_when TEXT NOT NULL,         -- JSON array
  input_context_refs TEXT NOT NULL,-- JSON array
  output_schema TEXT NOT NULL,     -- JSON object
  priority TEXT NOT NULL,
  run_timeout_seconds INTEGER NOT NULL,
  cleanup TEXT NOT NULL,           -- 'keep' | 'archive'
  workspace_root TEXT,
  model_id TEXT,
  status TEXT NOT NULL,            -- 'accepted'|'in_progress'|'blocked'|'failed'|'timed_out'|'completed'
  progress_pct INTEGER,
  accepted_at TEXT NOT NULL,
  started_at TEXT,
  ended_at TEXT,
  runtime_ms INTEGER,
  token_usage TEXT,                -- JSON object
  error_detail TEXT,
  artifacts TEXT,                  -- JSON object
  UNIQUE(parent_turn_id, idempotency_key),
  FOREIGN KEY(parent_run_id) REFERENCES subagent_runs(run_id)
);

CREATE INDEX idx_subagent_runs_parent
  ON subagent_runs(parent_run_id, status, accepted_at DESC);
CREATE INDEX idx_subagent_runs_tenant_session
  ON subagent_runs(tenant_id, parent_session_id, accepted_at DESC);
```

**Written by:** `SubAgentProtocol.spawn()` at `protocol.py:153`, then `start()`, `progress()`, `block()`, `fail()`, `timeout()`, `complete()` — all in `protocol.py`

**Read by:**
- `SubAgentProtocol.get_run()` at `protocol.py:488`
- `SubAgentProtocol.cascade_stop()` at `protocol.py:410`
- `bridge.py:2237` for dashboard overview

**Scope keys:** `tenant_id`, `parent_session_id`

**Retention:** Never deleted. The `cleanup` field is stored but not currently acted upon (`"keep"` vs `"archive"` has no runtime effect — dead code gap).

---

### 2.10 `subagent_events` — Sub-Agent Event Stream

**File:** `src/bomba_sr/subagents/protocol.py:103`

```sql
CREATE TABLE IF NOT EXISTS subagent_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  run_id TEXT NOT NULL,
  ticket_id TEXT NOT NULL,
  event_type TEXT NOT NULL,   -- 'accepted'|'started'|'progress'|'blocked'|'failed'|'timed_out'|'completed'|'announced'
  status TEXT NOT NULL,
  progress_pct INTEGER,
  summary TEXT,
  artifacts TEXT,             -- JSON object
  runtime_ms INTEGER,
  token_usage TEXT,           -- JSON object
  created_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES subagent_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX idx_subagent_events_run
  ON subagent_events(run_id, seq ASC);
```

**Written by:** `SubAgentProtocol._add_event()` at `protocol.py:524` — called internally from every state transition

**Read by:** `SubAgentProtocol.stream_events()` at `protocol.py:403` — polled via `GET /subagents/events`

**Scope keys:** `run_id` (derived from subagent_runs)

**Retention:** Cascades on run deletion (but runs are never deleted).

---

### 2.11 `shared_working_memory_writes` — Cross-Agent Scratch Pad

**File:** `src/bomba_sr/subagents/protocol.py:119`

```sql
CREATE TABLE IF NOT EXISTS shared_working_memory_writes (
  write_id TEXT PRIMARY KEY,
  run_id TEXT,
  writer_agent_id TEXT NOT NULL,
  ticket_id TEXT NOT NULL,
  scope TEXT NOT NULL,         -- 'scratch' | 'proposal' | 'committed'
  confidence REAL NOT NULL,
  content TEXT NOT NULL,
  source_refs TEXT NOT NULL,   -- JSON array
  merged_by_agent_id TEXT,
  merged_at TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES subagent_runs(run_id) ON DELETE SET NULL
);

CREATE INDEX idx_shared_writes_ticket
  ON shared_working_memory_writes(ticket_id, created_at DESC);
```

**Written by:** `SubAgentProtocol.write_shared_memory()` at `protocol.py:352` — exposed via `builtin_subagents.py` tools

**Read by:** Only via `promote_shared_write()` at `protocol.py:392`. There is **no automatic read path** into the main context assembly. The LLM must explicitly call the tool to read it, and no tool currently exposes a "read shared memory" function.

**Scope keys:** `ticket_id`

**Gap/Dead code:** The `promote_shared_write()` function exists but there is no tool that calls it. The shared memory mechanism is a stub — writes accumulate but are never automatically surfaced to the parent agent. This is a known incomplete implementation.

---

### 2.12 `loop_executions` — Agentic Loop Telemetry

**File:** `src/bomba_sr/runtime/bridge.py:2431`

```sql
CREATE TABLE IF NOT EXISTS loop_executions (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  turn_id TEXT NOT NULL,
  iterations INTEGER NOT NULL,
  tool_calls_json TEXT NOT NULL,  -- JSON array of tool call records
  stopped_reason TEXT,
  total_input_tokens INTEGER,
  total_output_tokens INTEGER,
  duration_ms INTEGER,
  created_at TEXT NOT NULL
);

CREATE INDEX idx_loop_exec_tenant
  ON loop_executions(tenant_id, created_at DESC);
```

**Written by:** `bridge.py:1071` — written at the end of every `handle_turn()` call

**Read by:**
- `SelfEvaluator.evaluate()` — reads recent loop_executions to assess tool efficiency
- `bridge.py:2150,2167` for dashboard token counts and average iterations

**Scope keys:** `tenant_id`, `session_id`

**Retention:** Grows forever. No pruning.

---

### 2.13 `raw_search_metrics`, `raw_subagent_metrics`, `raw_prediction_metrics`, `raw_loop_incidents` — Adaptation Inputs

**File:** `src/bomba_sr/adaptation/runtime_adaptation.py:33`

```sql
CREATE TABLE IF NOT EXISTS raw_search_metrics (
  id TEXT PRIMARY KEY,
  escalated INTEGER NOT NULL,    -- 0|1
  precision_at_k REAL,
  execution_ms INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_subagent_metrics (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  runtime_ms INTEGER,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_prediction_metrics (
  id TEXT PRIMARY KEY,
  brier_score REAL,
  ece REAL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_loop_incidents (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL
);
```

**Written by:**
- `RuntimeAdaptationEngine.ingest_search_metric()` at `runtime_adaptation.py:95` — called from `bridge.py:1031` every turn
- `RuntimeAdaptationEngine.ingest_subagent_metric()` — called in subagent worker completion path
- `RuntimeAdaptationEngine.ingest_prediction_metric()` — no call site found (dead write path)
- `RuntimeAdaptationEngine.ingest_loop_incident()` — called from loop detection logic

**Scope keys:** Implicitly tenant-scoped (one DB per tenant), no explicit tenant_id column.

**Retention:** Grows forever. No pruning.

---

### 2.14 `runtime_metrics_rollup` — Aggregated Adaptation Metrics

**File:** `src/bomba_sr/adaptation/runtime_adaptation.py:62`

```sql
CREATE TABLE IF NOT EXISTS runtime_metrics_rollup (
  id TEXT PRIMARY KEY,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  retrieval_precision_at_k REAL,
  search_escalation_rate REAL,
  subagent_success_rate REAL,
  subagent_p95_latency_ms INTEGER,
  loop_detector_incidents INTEGER NOT NULL DEFAULT 0,
  prediction_brier_score REAL,
  prediction_ece REAL,
  created_at TEXT NOT NULL,
  UNIQUE(period_start, period_end)
);
```

**Written by:** `RuntimeAdaptationEngine.aggregate_period()` at `runtime_adaptation.py:123` — called from `bridge.py:1037` every turn with a 5-minute window

**Read by:** `bridge.py:2219` for dashboard

**Retention:** Grows forever (one row per 5-minute window, after first write per window).

---

### 2.15 `policy_versions` — Adaptation Policy History

**File:** `src/bomba_sr/adaptation/runtime_adaptation.py:77`

```sql
CREATE TABLE IF NOT EXISTS policy_versions (
  id TEXT PRIMARY KEY,
  policy_name TEXT NOT NULL,
  version INTEGER NOT NULL,
  policy_json TEXT NOT NULL,
  diff_json TEXT NOT NULL,
  reason TEXT,
  rolled_back_from INTEGER,
  created_at TEXT NOT NULL,
  UNIQUE(policy_name, version)
);

CREATE INDEX idx_policy_versions_name_ver
  ON policy_versions(policy_name, version DESC);
```

**Written by:** `RuntimeAdaptationEngine.update_policy()` — called from `bridge.py:1059` when LLM self-evaluation suggests changes, and from `check_and_correct()` on metrics regression

**Scope keys:** `policy_name` (always "default" in practice)

**Retention:** Grows forever.

---

### 2.16 `tool_governance_policies`, `approval_queue`, `tool_audit_logs`

**File:** `src/bomba_sr/governance/tool_policy.py:42`

```sql
CREATE TABLE IF NOT EXISTS tool_governance_policies (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  policy_name TEXT NOT NULL,
  version INTEGER NOT NULL,
  policy_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(tenant_id, policy_name, version)
);

CREATE TABLE IF NOT EXISTS approval_queue (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  session_id TEXT,
  turn_id TEXT,
  action_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  risk_class TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL,        -- 'pending'|'approved'|'rejected'|'expired'|'cancelled'
  reason TEXT,
  decided_by TEXT,
  requested_at TEXT NOT NULL,
  decided_at TEXT,
  expires_at TEXT
);

CREATE TABLE IF NOT EXISTS tool_audit_logs (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  session_id TEXT,
  turn_id TEXT,
  action_type TEXT NOT NULL,
  tool_name TEXT,
  backend TEXT,
  risk_class TEXT,
  confidence REAL,
  policy_action TEXT,
  payload_hash TEXT,
  outcome_json TEXT,
  created_at TEXT NOT NULL
);
```

**Scope keys:** `tenant_id`

**Retention:** All three grow forever. Approval records are never deleted.

---

### 2.17 `user_profiles`, `user_profile_signals`

**File:** `src/bomba_sr/identity/profile.py:29`

```sql
CREATE TABLE IF NOT EXISTS user_profiles (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  display_name TEXT,
  preferences_json TEXT NOT NULL,
  constraints_json TEXT NOT NULL,
  goals_json TEXT NOT NULL,
  communication_style_json TEXT NOT NULL DEFAULT '{}',
  contact_info_json TEXT NOT NULL DEFAULT '{}',
  relationship_notes TEXT NOT NULL DEFAULT '',
  persona_summary TEXT NOT NULL,
  profile_version INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS user_profile_signals (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  signal_key TEXT NOT NULL,
  signal_value TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL,
  source_ref TEXT,
  created_at TEXT NOT NULL,
  decided_at TEXT
);
```

**Written by:** `UserIdentityService.ingest_turn()` — called from `bridge.py:1021` every turn

**Scope keys:** `tenant_id`, `user_id`

**Retention:** Profile grows forever (upserted in place). Signals accumulate forever.

---

### 2.18 `skills`, `skill_executions`, `skill_telemetry`, `skill_install_requests`

**File:** `src/bomba_sr/skills/registry.py:50`

```sql
CREATE TABLE IF NOT EXISTS skills (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  skill_id TEXT NOT NULL,
  version TEXT NOT NULL,
  manifest_json TEXT NOT NULL,
  status TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'database',
  source_path TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(tenant_id, skill_id, version)
);
```

**Scope keys:** `tenant_id`

---

### 2.19 `projects`, `project_tasks`

**File:** `src/bomba_sr/projects/service.py:19`

```sql
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  workspace_root TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(tenant_id, project_id)
);

CREATE TABLE IF NOT EXISTS project_tasks (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL,
  priority TEXT NOT NULL,
  owner_agent_id TEXT,
  parent_task_id TEXT DEFAULT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(tenant_id, task_id)
);
```

**Scope keys:** `tenant_id`

---

### 2.20 `artifacts`

**File:** `src/bomba_sr/artifacts/store.py:83`

```sql
CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  turn_id TEXT NOT NULL,
  project_id TEXT,
  task_id TEXT,
  artifact_type TEXT NOT NULL,
  title TEXT NOT NULL,
  path TEXT NOT NULL,         -- absolute filesystem path
  preview TEXT NOT NULL,      -- first 400 chars of content
  mime_type TEXT NOT NULL,
  created_at TEXT NOT NULL,
  file_size INTEGER DEFAULT 0,
  created_by TEXT,
  skill_id TEXT
);
```

**Written by:** `ArtifactStore.create_text_artifact()` at `store.py:133` — called from `bridge.py:934` when the user message triggers markdown/code artifact creation

**Scope keys:** `tenant_id`, `session_id`

**Files:** Stored at `{artifacts_root}/{session_id}/{turn_id}-{uuid8}.{ext}`

---

### 2.21 `scheduled_tasks`

**File:** `src/bomba_sr/autonomy/scheduler.py:199`

```sql
CREATE TABLE IF NOT EXISTS scheduled_tasks (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  cron_expression TEXT NOT NULL,
  task_goal TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  last_run_at TEXT,
  next_run_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX idx_scheduled_tasks_due
  ON scheduled_tasks(tenant_id, user_id, enabled, next_run_at);
```

**Scope keys:** `tenant_id`, `user_id`

---

### 2.22 `model_capabilities_cache`

**File:** `src/bomba_sr/models/capabilities.py:48`

```sql
CREATE TABLE IF NOT EXISTS model_capabilities_cache (
  model_id TEXT PRIMARY KEY,
  context_length INTEGER NOT NULL,
  max_completion_tokens INTEGER NOT NULL,
  supports_tools INTEGER NOT NULL,
  supports_json_mode INTEGER NOT NULL,
  provider_context_length INTEGER,
  raw_metadata TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
```

**Scope:** Global within the tenant DB (not tenant-gated by column).

---

### 2.23 `task_results` — Orchestration Task Outcomes

**File:** `src/bomba_sr/orchestration/engine.py:1096`

```sql
CREATE TABLE IF NOT EXISTS task_results (
  task_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  goal TEXT NOT NULL,
  strategy TEXT NOT NULL,
  beings_used TEXT NOT NULL,    -- JSON array of being_ids
  outputs TEXT NOT NULL,        -- JSON dict of subtask_id -> output
  synthesis TEXT NOT NULL,
  artifacts TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL
);

CREATE INDEX idx_task_results_created
  ON task_results(tenant_id, created_at DESC);
```

**Written by:**
- `OrchestrationEngine._persist_task_result()` at `engine.py:1114` — called from `engine.py:826` (before synthesis) and `_update_task_result_synthesis()` at `engine.py:1028` (after synthesis)
- After synthesis: also calls `memory.learn_semantic()` at `engine.py:1155` to write a semantic memory of the outcome with `user_id="orchestrator"` and `being_id="prime"`

**Read by:**
- `DreamCycle._phase_gather()` at `dreaming.py:344` — queries `WHERE beings_used LIKE '%"being_id"%'`

**Written to:** Prime tenant DB only (`self.prime_tenant_id` at `engine.py:1122`)

---

## 3. Filesystem Storage

### 3.1 Working Memory Notes — Markdown Files

**Path pattern:** `{tenant_home}/memory/{user_id}/{YYYY}/{MM}/{DD}/{HHMMSS}-{slug}-{uuid8}.md`

**Written by:** `HybridMemoryStore.append_working_note()` at `hybrid.py:196` — every turn writes one file

**Format:**
```
---
{"note_id": "uuid", "user_id": "...", "session_id": "...", "title": "...", "tags": [...], "confidence": 1.0, "created_at": "..."}
---

{content}
```

Content = `"User: {message}\n\nAssistant: {response}"`

**Retention:** Never deleted. Grows indefinitely.

### 3.2 Workspace Identity Files — Read-Only (not auto-written)

**Paths:** `{workspace_root}/SOUL.md`, `IDENTITY.md`, `MISSION.md`, `VISION.md`, `FORMULA.md`, `PRIORITIES.md`, `KNOWLEDGE.md`, `REPRESENTATION.md`, `TEAM_CONTEXT.md`

**Read by:** `load_soul_from_workspace()` at `identity/soul.py:33` — called once per tenant initialization in `_tenant_runtime()` at `bridge.py:2428`

**TEAM_CONTEXT.md special case:** `soul.py:46-47` — if not found in workspace root, falls back to `workspace_root.parent / "TEAM_CONTEXT.md"`. This means beings in `workspaces/{being_id}/` inherit from `workspaces/TEAM_CONTEXT.md`.

**Written by:** KNOWLEDGE.md and REPRESENTATION.md are updated by `builtin_knowledge_tools()` and `builtin_team_context_tools()` tool calls. They are NOT auto-written by the memory system.

**Being workspace locations:**
```
workspaces/prime/       -> SOUL.md, IDENTITY.md, KNOWLEDGE.md, etc.
workspaces/forge/       -> SOUL.md, IDENTITY.md, KNOWLEDGE.md, etc.
workspaces/scholar/     -> SOUL.md, IDENTITY.md, KNOWLEDGE.md, etc.
workspaces/recovery/    -> SOUL.md, IDENTITY.md, KNOWLEDGE.md, etc.
workspaces/sai-memory/  -> SOUL.md, IDENTITY.md (SAI Memory being)
```

### 3.3 Artifact Files

**Path pattern:** `{tenant_home}/artifacts/{session_id}/{turn_id}-{uuid8}.{ext}`

**Written by:** `ArtifactStore.create_text_artifact()` at `store.py:152`

**Retention:** Never deleted.

### 3.4 Dream Cycle Logs — Markdown Reports

**Path:** `workspaces/sai-memory/dream_logs/{YYYY-MM-DD-HH:MM}.md`

**Written by:** `DreamCycle._write_dream_log()` at `dreaming.py:639` — after each dream cycle run

**Read by:** `DreamCycle.list_dream_logs()` at `dreaming.py:681` — for dashboard display

**Hardcoded path:** Uses `os.environ.get("BOMBA_PROJECT_ROOT", "/Users/zidane/Downloads/PROJEKT")` — this is a hardcoded fallback to the developer's local path.

### 3.5 Static Memory Documents (workspaces/{being}/memory/)

**Path:** `workspaces/{being_id}/memory/*.md`

These are NOT written by the runtime memory system. They are hand-curated documents. There is no automatic write path here. The runtime's `HybridMemoryStore` writes to `{tenant_home}/memory/` (under `.runtime/`), not to `workspaces/`. These files are unrelated to the `markdown_notes` table.

**Exception:** `sai-memory/memory/` contains ~30+ manually-created documents and dream logs. The SAI Memory dream cycle reports go to `sai-memory/dream_logs/` (auto-written). The `sai-memory/memory/*.md` files are hand-placed.

---

## 4. External Storage — Pinecone

**Tool registration:** `bridge.py:2580` — gated by `BOMBA_PINECONE_ENABLED`

**Tools defined:** `src/bomba_sr/tools/builtin_pinecone.py`
- `pinecone_query` — read, embeds query via OpenAI, queries one index
- `pinecone_list_indexes` — read, lists all accessible indexes
- `pinecone_upsert` — write, embeds texts and upserts vectors
- `pinecone_multi_query` — read, queries multiple indexes in parallel

**Key indexes (from env vars):**
- Default: `ublib2` / namespace `longterm` (via `BOMBA_PINECONE_DEFAULT_INDEX` / `BOMBA_PINECONE_DEFAULT_NAMESPACE`)
- STRATA indexes: `oracleinfluencemastery`, `ultimatestratabrain` — use separate `PINECONE_API_KEY_STRATA`

**Host resolution:** Control-plane discovery via `https://api.pinecone.io/indexes`, cached for 300 seconds. Falls back to `BOMBA_PINECONE_INDEX_HOSTS` JSON env var.

**Scope:** None. Pinecone is **not tenant-scoped**. All tenants using the same API key share the same Pinecone indexes. There is no per-tenant namespace enforced — the agent specifies the namespace freely in the tool call.

**Write path:** `pinecone_upsert` is a direct tool call. Vectors include `{"text": "...", ...metadata}`. No being_id or tenant_id is embedded in vector metadata by default. The LLM must explicitly include identifying metadata via the `metadata` argument.

**Gap:** Pinecone access is completely unmediated by tenant or being identity. Any being that has the `pinecone_upsert` tool available can write to any namespace of any accessible index. This is a significant cross-contamination risk.

---

## 5. Scope Boundaries and Isolation Model

### 5.1 Tenant Isolation

Each tenant gets its own SQLite DB at a distinct filesystem path. The `TenantRegistry.guard_path()` at `tenancy.py:65` enforces that filesystem tool calls (read_file, write_file, etc.) cannot escape the tenant's workspace root. All memory tables are partitioned by `tenant_id` column where present.

**Binding is permanent per process:** `_tenant_runtime()` at `bridge.py:2415-2424` caches the tenant runtime and enforces that the workspace_root cannot change once bound. A second call with a different workspace_root raises `ValueError`.

### 5.2 Being Identity Resolution

`being_id` is derived from `session_id` or `user_id` patterns — it is NOT a first-class auth token:

```python
# hybrid.py:26-44
_BEING_PATTERNS = [
    (re.compile(r"^mc-chat-(.+)$"), 1),          # direct chat
    (re.compile(r"^subtask:[^:]+:(.+)$"), 1),    # orchestration subtask
]

def resolve_being_id(session_id, user_id=None):
    if session_id:
        for pattern, group in _BEING_PATTERNS:
            if m := pattern.match(session_id):
                return m.group(group)
    if user_id and user_id.startswith("prime->"):
        return user_id[len("prime->"):]          # "prime->scholar" -> "scholar"
    return None
```

`_being_id_for_write` is computed at `bridge.py:177` and attached to:
- `markdown_notes.being_id` (`bridge.py:966`)
- `memories.being_id` via `learn_semantic()` (`bridge.py:1018`)
- `procedural_memories.being_id` via `learn_procedural()` (`bridge.py:923`)

### 5.3 Memory Query Scope Rules

| Query method | Scope key used | Returns memories for |
|---|---|---|
| `recall(user_id, query)` | `user_id` | All notes/memories written as this user_id |
| `recall_by_being(being_id, query)` | `being_id` column | All notes/memories tagged with this being_id |
| `retrieve(user_id, query)` | `user_id` | Active semantic memories for user_id |
| `retrieve_by_being(being_id, query)` | `being_id` column | Active semantic for this being_id |
| `recall_procedural(user_id, query)` | `user_id` | Procedural memories for user_id |
| `recall_procedural_by_being(being_id, query)` | `being_id` | Procedural for being_id |

**Dual-path during a turn (bridge.py:544-567):**
```python
recall = runtime.memory.recall(user_id=request.user_id, ...)
_being_id = resolve_being_id(request.session_id, request.user_id)
if _being_id:
    _being_recall = runtime.memory.recall_by_being(being_id=_being_id, ...)
    # merge, dedup by memory_id
```

This means a being can read both its `user_id`-scoped memories AND its `being_id`-scoped memories on every turn.

### 5.4 Cross-Tenant Access

Blocked by design. Each service constructor takes a `RuntimeDB` instance that is already bound to one tenant's file. There is no query path that crosses tenant DB files.

**Exception:** The dream cycle (`dreaming.py:253`) calls `self.bridge._tenant_runtime(tenant_id)` for each being — it can reach any tenant's DB by constructing the tenant_id. This is an intentional cross-tenant read for consolidation purposes.

**Exception 2:** Sister messaging (`bridge.py:2086`) calls `handle_turn()` with the sister's `tenant_id` and `workspace_root`. This creates/accesses a second tenant's runtime.

---

## 6. Cross-Being Memory Pathways

### 6.1 Direct Pathways (same DB, different being_id)

When beings share a tenant (e.g., all sub-agents spawned under `tenant-prime`):

1. **being_id column reads** — any agent in the same tenant DB can call `recall_by_being(being_id="scholar")` and read Scholar's tagged memories. There is no access control on being_id column queries.

2. **task_results table** — written to the prime tenant DB by orchestrator. All beings whose being_id appears in `beings_used` can have their past task results read during dream cycles.

3. **shared_working_memory_writes** — keyed by `ticket_id`. Any agent that knows the ticket_id can write. No agent can read it via a tool (read tool is missing — dead code gap).

### 6.2 Indirect Pathways

1. **TEAM_CONTEXT.md** — a shared filesystem file at `workspaces/TEAM_CONTEXT.md`. Updated by `builtin_team_context_tools()` which is registered only for prime-like tenants (`bridge.py:2616-2617`: `if "prime" in tenant_id.lower() or tenant_id == "tenant-local"`). Read by `load_soul_from_workspace()` for any being whose workspace is under `workspaces/`. All beings in subdirectory workspaces inherit the parent `TEAM_CONTEXT.md`.

2. **Dream cycle cross-pollination** — `DreamCycle._phase_cross_pollinate()` at `dreaming.py:580` writes derived insights from being A's memory to being B's tenant runtime as `learn_semantic()` with `user_id="prime->{target_bid}"` and `being_id=target_bid`. This creates a direct write cross-beam between tenant DBs.

3. **Session replay** — a parent agent that orchestrates Scholar will read the `conversation_turns` from Scholar's session (which uses Scholar's tenant DB). But there is no automatic cross-session replay — each agent only replays its own session_id.

4. **KNOWLEDGE.md** — per-being workspace file, read at tenant initialization. Updated by `knowledge_update` tool. Persistent across sessions as part of soul config (re-read on next tenant init). Functions as a durable, persistent memory layer outside SQLite.

### 6.3 Blocked Pathways

- A being cannot query another being's `markdown_notes` by user_id (different user_ids)
- A being cannot query another being's `conversation_turns` (different session_ids and different tenant DBs if beings have separate tenants)
- A being cannot read another being's `learning_updates` approval queue
- Pinecone: NOT blocked — any being with the tool can read/write any namespace

---

## 7. Scenario Traces

### Scenario A: User chats with Prime

**Request:** `TurnRequest(tenant_id="tenant-prime", session_id="sess-1", user_id="user-local", ...)`

1. `bridge.handle_turn()` calls `_tenant_runtime("tenant-prime")` → opens `.runtime/tenants/tenant-prime/runtime/runtime.db`
2. `_being_id_for_write = resolve_being_id("sess-1", "user-local")` → returns `None` (no pattern match)
3. Memory recall: `runtime.memory.recall(user_id="user-local", query=..., limit=8)` → reads `markdown_notes` and `memories` WHERE `user_id="user-local"`
4. Being recall: skipped (`_being_id` is None)
5. Procedural recall: `recall_procedural(user_id="user-local", query=...)`
6. Recent turns: `get_recent_turns(tenant_id="tenant-prime", session_id="sess-1", limit=5)`
7. Session summary: `get_session_summary(tenant_id="tenant-prime", session_id="sess-1")`
8. Soul/identity: loaded from `workspaces/prime/SOUL.md`, `IDENTITY.md`, `KNOWLEDGE.md`, `TEAM_CONTEXT.md`
9. After LLM response:
   - `append_working_note(user_id="user-local", session_id="sess-1", being_id=None)` → writes `.md` file, DB row with `being_id=NULL`
   - `record_turn(tenant_id="tenant-prime", session_id="sess-1", ...)` → writes `conversation_turns`
   - `learn_procedural(user_id="user-local", ..., being_id=None)` if tools were called
   - `learn_semantic(tenant_id="tenant-prime", user_id="user-local", ..., being_id=None)` if pattern matched
   - `loop_executions` row written

**What is NOT written:** No being_id tag on any memory, since session "sess-1" does not match any being pattern.

---

### Scenario B: Prime orchestrates → Scholar executes sub-task

**Parent (Prime):** `TurnRequest(tenant_id="tenant-prime", session_id="sess-1", user_id="user-local")`
Prime calls `sessions_spawn` tool → `SubAgentOrchestrator.spawn_async()` → creates run record → `SubAgentWorkerFactory` creates worker → spawns thread calling `bridge.handle_turn()` with:

**Child (Scholar):** `TurnRequest(tenant_id="tenant-scholar", session_id="subtask:{task_id}:scholar", user_id="prime->scholar")`

Scholar's turn:
1. `_being_id_for_write = resolve_being_id("subtask:{task_id}:scholar", "prime->scholar")` → `"scholar"` (matched by `_BEING_PATTERNS[1]`)
2. Memory recall:
   - `recall(user_id="prime->scholar", query=...)` → reads `markdown_notes` WHERE `user_id="prime->scholar"` in Scholar's tenant DB
   - `recall_by_being(being_id="scholar", query=...)` → reads `markdown_notes` WHERE `being_id="scholar"` in Scholar's tenant DB
3. After response:
   - `append_working_note(user_id="prime->scholar", being_id="scholar")` → DB row tagged with `being_id="scholar"`
   - `record_turn(tenant_id="tenant-scholar", session_id="subtask:{task_id}:scholar", ...)`
   - `learn_semantic(user_id="prime->scholar", being_id="scholar")` if pattern matched

**Cross-DB:** Prime writes `subagent_runs` to its own DB (`tenant-prime`). Scholar writes memory to its own DB (`tenant-scholar`). The sub-agent protocol DB is Prime's DB.

**What Prime cannot directly read from Scholar's memory:** Prime has no automatic read path into `tenant-scholar`'s DB during the parent turn. The synthesized output flows back only as the LLM text of Scholar's response, surfaced via the sub-agent events poll mechanism.

---

### Scenario C: User chats with Scholar directly

**Request:** `TurnRequest(tenant_id="tenant-scholar", session_id="mc-chat-scholar", user_id="user-local")`

1. `_being_id_for_write = resolve_being_id("mc-chat-scholar", "user-local")` → `"scholar"` (matched by `_BEING_PATTERNS[0]`)
2. Memory recall:
   - `recall(user_id="user-local", query=...)` → reads notes from Scholar's tenant DB where `user_id="user-local"` (this is the human user's notes in Scholar's DB)
   - `recall_by_being(being_id="scholar", query=...)` → reads notes tagged `being_id="scholar"` in Scholar's tenant DB
3. After response: all writes go to Scholar's tenant DB with `being_id="scholar"`

**What IS visible vs invisible from orchestration context:**
- Visible: Any note/memory from a prior orchestration run where Scholar wrote with `being_id="scholar"` — these appear via `recall_by_being()`
- Invisible: Orchestration session turns from `session_id="subtask:{task_id}:scholar"` — those are in a different session_id and only surfaced if the session_id matches. Since the session_id is `"mc-chat-scholar"`, only turns from THAT session are replayed.
- Invisible: Prime's `task_results` table (different DB, different tenant)

**Confusion point:** The `user_id` is `"user-local"` in both direct chat and orchestration. Notes written during orchestration with `user_id="prime->scholar"` are NOT visible during direct chat (`recall(user_id="user-local")` does not match `"prime->scholar"`). They ARE visible via `recall_by_being("scholar")` if tagged with `being_id="scholar"`.

---

### Scenario D: Dream cycle runs for Scholar

1. `DreamCycle.run_cycle()` at `dreaming.py:161`
2. `_dream_for_being("scholar")` at `dreaming.py:200`
3. Gets being config from dashboard service (workspace, tenant_id)
4. Calls `self.bridge._tenant_runtime("tenant-scholar")` → gets Scholar's runtime
5. **Phase 1 — Gather:**
   - `SELECT ... FROM markdown_notes WHERE user_id = 'scholar' OR being_id = 'scholar'` — gets notes where either field matches
   - `SELECT ... FROM memories WHERE (user_id = 'scholar' OR being_id = 'scholar') AND active = 1`
   - `SELECT ... FROM procedural_memories WHERE (user_id = 'scholar' OR being_id = 'scholar') AND active = 1`
   - Reads `workspaces/scholar/KNOWLEDGE.md` and `REPRESENTATION.md`
   - `SELECT ... FROM task_results WHERE beings_used LIKE '%"scholar"%'` — reads from prime tenant DB if `self.bridge._tenant_runtime(tenant_id)` resolves to prime's DB
6. **Phase 2 — Consolidate:** LLM call with gathered data, archives duplicate/stale memories
7. **Phase 3 — Derive:** LLM call, stores derived insights via `learn_semantic(tenant_id="tenant-scholar", user_id="scholar", being_id="scholar", confidence=0.6)`
8. **Phase 4 — Prune:** Archives memories beyond threshold of 200 for Scholar's being_id
9. **Phase 5 — Cross-pollinate:** If Scholar's derived insights are `relevance_to_others=["forge"]`, writes to Forge's tenant DB:
   ```python
   target_runtime.memory.learn_semantic(
       tenant_id="tenant-forge",
       user_id="prime->forge",
       being_id="forge",
       content="[From Scholar's dream cycle] {insight}",
       confidence=0.5,
   )
   ```

**Gap in dream Phase 1:** `task_results` is read by calling `self.bridge._tenant_runtime(tenant_id)` where `tenant_id = being.get("tenant_id") or f"tenant-{being_id}"`. If scholar's tenant is `"tenant-scholar"` but `task_results` is in `"tenant-prime"`, this query returns nothing. The dream cycle will only find task results if they are in the same DB as the being's tenant.

---

## 8. Memory Lifecycle — End-to-End Trace

**Scenario:** User says "I prefer short reports"

### Step 1: Entry
`bridge.handle_turn()` receives the message. `_learning_signal("I prefer short reports")` at `bridge.py:2967` matches `r"\bi prefer\b"` → returns `("user_signal::{sha256_12hex}", "I prefer short reports", 0.72, "explicit_user_profile_signal")`.

### Step 2: Storage — Immediate Write
At `bridge.py:1010-1019`:
```python
decision = runtime.memory.learn_semantic(
    tenant_id=request.tenant_id,
    user_id=request.user_id,
    memory_key="user_signal::{digest}",
    content="I prefer short reports",
    confidence=0.72,
    evidence_refs=[note["note_id"]],
    reason="explicit_user_profile_signal",
    being_id=_being_id_for_write,  # None if Prime session, "prime" if Prime being
)
```

Since `0.72 >= 0.4` (auto_apply_confidence), `learn_semantic()` at `hybrid.py:287` immediately calls `consolidator.upsert()`. This inserts a row into `memories` with `active=1`.

The `learning_updates` row is also written with `status="applied"`.

Also at `bridge.py:959`: `append_working_note()` writes the full conversation to `markdown_notes` and a `.md` file.

### Step 3: Recall
On the **next turn**, `bridge.handle_turn()` calls `runtime.memory.recall(user_id=..., query="report format", limit=8)`. This calls:
- `consolidator.retrieve()` at `consolidation.py:218` → fetches all active semantic memories for this user_id → computes `lexical_score("report format", "I prefer short reports")` + `recency_boost(ts, 14 days half-life, 0.15 weight)` → returns ranked list
- The result is injected into `semantic_candidates` in context assembly at `bridge.py:594`

### Step 4: Update / Contradiction
If the user later says "actually I prefer detailed reports", `_learning_signal()` matches again → `learn_semantic()` with key `"user_signal::{new_digest}"` (different key since SHA256 of different text). This creates a NEW memory entry — it does not automatically resolve the contradiction with the old one.

**Contradiction resolution only happens if:** The same `memory_key` is used. Since `_learning_signal()` computes the key from SHA256 of the content, two different preference statements get different keys. The dream cycle's LLM-based consolidation is the only mechanism to detect and resolve these cross-key contradictions.

If the same text is submitted again → `upsert()` detects identical content → updates `recency_ts` only (no contradiction path).

If the key is the same but content differs → contradiction path at `consolidation.py:177`: old memory is archived in `memory_archive` with `reason="contradiction_or_update"`, new memory inserted at `version+1`.

### Step 5: Forgetting
- **Active pruning:** Dream cycle `_phase_prune()` at `dreaming.py:516` — only triggers when active semantic memory count for this being exceeds 200. Archives oldest, lowest-version memories. Sets `active=0`. Never deletes.
- **Natural decay in recall:** `_recency_boost()` at `consolidation.py:489` uses 14-day half-life, weight 0.15. After 14 days, the recency boost drops to ~0.075. After 60 days, it's effectively 0. The memory is still returned but ranks lower than recent ones.
- **No hard expiry.** No memory is ever hard-deleted. The `active=0` flag is the closest to forgetting.

---

## 9. Dream Cycle — Deep Trace

**Trigger:** Background thread in `DreamCycle._run_loop()` at `dreaming.py:146`, sleeping for `interval_seconds` (default from `BOMBA_DREAM_INTERVAL_SECONDS` env var, if set). Also triggerable on-demand via `bridge.dream_cycle_run_once()`.

**Model used:** `DREAM_MODEL = os.environ.get("BOMBA_DREAM_MODEL", "minimax/minimax-m2.5")` at `dreaming.py:33`

**What each phase reads and writes:**

| Phase | Reads From | Writes To |
|---|---|---|
| Gather | `markdown_notes`, `memories`, `procedural_memories`, KNOWLEDGE.md, REPRESENTATION.md, `task_results` | Nothing |
| Consolidate | Gathered data (in-memory) | `memory_archive` (archive entries), `memories.active=0` |
| Derive | Gathered data (in-memory) | `memories` (new derived insights via learn_semantic) |
| Prune | `memories` count | `memory_archive` (insert), `memories.active=0` |
| Cross-pollinate | Derived insights (in-memory), dashboard being list | `memories` in TARGET being's tenant DB |
| Log | Results (in-memory) | `workspaces/sai-memory/dream_logs/{timestamp}.md` |

**Cross-pollination write path (critical):**
```python
# dreaming.py:612-621
target_runtime.memory.learn_semantic(
    tenant_id=target_tenant,
    user_id=f"prime->{target_bid}",  # e.g., "prime->forge"
    memory_key=f"cross_pollinate::{source_being_id}::{uuid8}",
    content=f"[From {source_name}'s dream cycle] {content}",
    confidence=0.5,
    being_id=target_bid,
)
```

This write goes into `learning_updates` with `status="applied"` (confidence 0.5 >= 0.4 threshold) and creates a new `memories` row in the target tenant's DB, tagged with `being_id=target_bid`.

---

## 10. Gaps, Dead Code, and Known Risks

### Dead Code / Incomplete Implementations

1. **`shared_working_memory_writes` read tool missing** (`protocol.py:352`): `write_shared_memory()` exists and is exposed via tools, but no tool exposes `read_shared_memory()` or `promote_shared_write()`. Writes accumulate permanently but are never surfaced to the parent agent automatically.

2. **`subagent_runs.cleanup` field unused** (`protocol.py:101`): The `cleanup` field is stored (`"keep"` vs `"archive"`) but no code path acts on it. Both values result in identical behavior.

3. **`raw_prediction_metrics` has no write callers**: `ingest_prediction_metric()` exists at `runtime_adaptation.py:109` but no code in the codebase calls it. The `prediction_brier_score` and `prediction_ece` columns in `runtime_metrics_rollup` will always be NULL.

4. **`procedural_memories.active` never set to 0**: The `active` column exists on `procedural_memories` but no code path archives procedural memories. The dream cycle gathers them but does not prune them. The `backfill_being_id()` function at `consolidation.py:449` is a maintenance utility, not called automatically.

5. **`memory_embeddings` lacks `being_id`**: The `_recall_markdown_by_being()` path (`hybrid.py:518`) uses lexical scoring only — it cannot use embeddings because there is no `being_id` column in `memory_embeddings` and the query is not by `user_id`.

6. **Dream cycle `task_results` query uses wrong tenant**: `dreaming.py:344` queries `task_results` from `runtime.db` where `runtime = self.bridge._tenant_runtime(tenant_id)` and `tenant_id = being.get("tenant_id") or f"tenant-{being_id}"`. But `task_results` is always written to the prime tenant DB (`engine.py:1122`). If `tenant_id` for a being (e.g., Scholar) differs from the prime tenant, the query returns nothing.

7. **`backfill_being_id()` never called automatically** (`consolidation.py:449`): Backfill of `being_id` from old `user_id="prime->X"` pattern records requires manual invocation.

8. **Hardcoded project root path in dream log writer** (`dreaming.py:641`): `os.environ.get("BOMBA_PROJECT_ROOT", "/Users/zidane/Downloads/PROJEKT")` — falls back to a developer machine path. Will silently fail on any other deployment.

### Known Risks

1. **Pinecone is tenant-blind**: All beings share Pinecone indexes. A being with `pinecone_upsert` can contaminate any namespace. No per-tenant or per-being namespace enforcement exists.

2. **being_id is not authenticated**: `resolve_being_id()` derives identity from session_id string patterns. Any caller that crafts a session_id like `"mc-chat-scholar"` will write memories tagged as Scholar, and read Scholar's being_id-scoped memories, regardless of actual identity.

3. **Infinite growth on all core tables**: `conversation_turns`, `markdown_notes`, `learning_updates`, `loop_executions`, `raw_search_metrics`, `tool_audit_logs`, `approval_queue` — none have retention policies. Long-running deployments will accumulate unbounded data.

4. **Dream cycle LLM dependency**: All 5 dream phases are optional gracefully (errors caught and logged), but Phases 2-3 rely on an LLM call to `DREAM_MODEL` (default `minimax/minimax-m2.5`). If the model is unavailable, consolidation and derivation silently return empty results.

5. **Session summary overwrites history**: `session_summaries` has `UNIQUE(tenant_id, session_id)` with upsert. The previous summary text is permanently lost on each update. There is no summary version history.

6. **Cross-pollination creates unattributed memories**: Cross-pollinated insights are written with `user_id="prime->target_bid"` and `memory_key="cross_pollinate::source::uuid"`. These can accumulate indefinitely (one new key per cross-pollination event). They are never deduplicated because the UUID-suffix ensures no key collision.

---

## 11. ASCII Diagrams

### 11.1 Full Storage Topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        RUNTIME PROCESS                                    │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  RuntimeBridge  (bridge.py)                                       │    │
│  │  _tenants: dict[tenant_id -> _TenantRuntime]                     │    │
│  └───────────────┬──────────────────────────────────────────────────┘    │
│                  │ _tenant_runtime(tenant_id)                             │
│          ┌───────┴───────┐                                                │
│          ▼               ▼                                                │
│  ┌───────────────┐  ┌───────────────┐  ... (one per tenant)              │
│  │ tenant-prime  │  │ tenant-scholar │                                    │
│  │  runtime.db   │  │  runtime.db   │                                    │
│  │  memory/      │  │  memory/      │                                    │
│  │  artifacts/   │  │  artifacts/   │                                    │
│  └──────┬────────┘  └───────┬───────┘                                    │
│         │                   │                                             │
│  .runtime/tenants/          │                                             │
└─────────┼───────────────────┼─────────────────────────────────────────── │
          │                   │
          ▼                   ▼
  ┌───────────────────────────────────────────────────────────────────────┐
  │  SQLite Tables in runtime.db (per tenant)                             │
  │                                                                       │
  │  Working/Episodic:                                                    │
  │    markdown_notes          (index only; files on disk)                │
  │    memory_embeddings       (vector cache for notes)                   │
  │    conversation_turns      (raw turn history)                         │
  │    session_summaries       (LLM-generated digests, 1 per session)    │
  │                                                                       │
  │  Semantic/Long-term:                                                  │
  │    memories                (beliefs, versioned, active/archived)      │
  │    memory_archive          (superseded beliefs)                       │
  │    learning_updates        (approval queue + applied log)             │
  │                                                                       │
  │  Procedural:                                                          │
  │    procedural_memories     (tool-chain strategies + success counts)   │
  │                                                                       │
  │  Sub-agents:                                                          │
  │    subagent_runs           (run lifecycle)                            │
  │    subagent_events         (event stream)                             │
  │    shared_working_memory_writes  (stub - no read tool)               │
  │                                                                       │
  │  Orchestration (prime only):                                          │
  │    task_results            (completed orchestration outcomes)         │
  │                                                                       │
  │  Adaptation:                                                          │
  │    loop_executions         (telemetry per turn)                       │
  │    raw_search_metrics      (search quality signals)                   │
  │    raw_subagent_metrics    (sub-agent perf)                           │
  │    raw_prediction_metrics  (dead - never written)                     │
  │    raw_loop_incidents      (loop detector triggers)                   │
  │    runtime_metrics_rollup  (aggregated metrics per 5-min window)      │
  │    policy_versions         (adaptation policy history)                │
  │                                                                       │
  │  Governance:                                                          │
  │    tool_governance_policies                                           │
  │    approval_queue                                                     │
  │    tool_audit_logs                                                    │
  │                                                                       │
  │  Identity:                                                            │
  │    user_profiles                                                      │
  │    user_profile_signals                                               │
  │                                                                       │
  │  Skills:                                                              │
  │    skills, skill_executions, skill_telemetry, skill_install_requests  │
  │                                                                       │
  │  Projects:                                                            │
  │    projects, project_tasks                                            │
  │                                                                       │
  │  Artifacts:                                                           │
  │    artifacts               (index; files in artifacts/)              │
  │                                                                       │
  │  Autonomy:                                                            │
  │    scheduled_tasks                                                    │
  │                                                                       │
  │  Capabilities:                                                        │
  │    model_capabilities_cache                                           │
  └───────────────────────────────────────────────────────────────────────┘

  Filesystem (alongside SQLite):
  ┌──────────────────────────────────────────────────────────┐
  │  .runtime/tenants/{tenant_id}/memory/                    │
  │    {user_id}/{YYYY}/{MM}/{DD}/{HHMMSS}-{slug}-{uuid8}.md │
  │                                                          │
  │  .runtime/tenants/{tenant_id}/artifacts/                 │
  │    {session_id}/{turn_id}-{uuid8}.{ext}                  │
  └──────────────────────────────────────────────────────────┘

  Workspace Identity (read-only by runtime):
  ┌──────────────────────────────────────────────────────────┐
  │  workspaces/{being}/SOUL.md, IDENTITY.md, KNOWLEDGE.md  │
  │  workspaces/TEAM_CONTEXT.md  (shared)                    │
  │  workspaces/sai-memory/dream_logs/{timestamp}.md         │
  └──────────────────────────────────────────────────────────┘

  External:
  ┌──────────────────────────────────────────────────────────┐
  │  Pinecone (optional, BOMBA_PINECONE_ENABLED=true)        │
  │    index: ublib2  namespace: longterm  (defaults)        │
  │    No tenant/being isolation enforced                    │
  └──────────────────────────────────────────────────────────┘
```

---

### 11.2 Scope Isolation Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TENANT BOUNDARY  (hard, different SQLite files)                         │
│                                                                           │
│  ┌─────────────────────────┐    ┌─────────────────────────┐             │
│  │   tenant-prime DB       │    │   tenant-scholar DB      │             │
│  │                         │    │                          │             │
│  │  user_id="user-local"   │    │  user_id="prime->scholar"│             │
│  │  being_id=NULL          │    │  being_id="scholar"      │             │
│  │  (direct chat to prime) │    │  (orchestration subtask) │             │
│  │                         │    │                          │             │
│  │  user_id="orchestrator" │    │  user_id="user-local"    │             │
│  │  being_id="prime"       │    │  being_id="scholar"      │             │
│  │  (task_results writes)  │    │  (direct chat to scholar)│             │
│  │                         │    │                          │             │
│  │  ┌───────────────────┐  │    │  ┌───────────────────┐  │             │
│  │  │ task_results      │  │    │  │ memories           │  │             │
│  │  │ (prime only)      │  │    │  │ (scholar's beliefs)│  │             │
│  │  └───────────────────┘  │    │  └───────────────────┘  │             │
│  └─────────────────────────┘    └─────────────────────────┘             │
│                                                                           │
│  Cross-tenant reads:  dream cycle only (explicit bridge._tenant_runtime) │
│  Cross-tenant writes: dream cycle cross-pollination                      │
│  Cross-tenant access: sister messaging (via handle_turn)                 │
│                                                                           │
│  PINECONE: crosses ALL tenant boundaries (no isolation)                  │
└─────────────────────────────────────────────────────────────────────────┘

BEING SCOPE (within a tenant DB):

  Query by user_id:   returns rows WHERE user_id = ?
  Query by being_id:  returns rows WHERE being_id = ?
  Dual query:         returns rows WHERE user_id = ? OR being_id = ? (dream cycle)

  being_id is a DERIVED SECONDARY KEY:
    - mc-chat-{being}      → being_id="{being}"
    - subtask:{id}:{being} → being_id="{being}"
    - user_id="prime->X"   → being_id="X" (from user_id prefix)
    - No auth — derivable by anyone crafting the right session_id
```

---

### 11.3 Memory Flow for a Single Orchestrated Task

```
User → Prime → handle_turn()
          │
          ├─ 1. READ: memories, markdown_notes, procedural_memories (Prime's user_id)
          ├─ 2. READ: session_summaries for Prime's session
          ├─ 3. LLM generates response + calls sessions_spawn tool
          │
          ▼
  SubAgentOrchestrator.spawn_async()
          │
          ├─ WRITE: subagent_runs (accepted) → tenant-prime DB
          │
          ▼
  SubAgentWorker.run() [background thread]
          │
          ▼
  bridge.handle_turn() for Scholar
          │
          ├─ 4. READ: memories WHERE being_id="scholar" (scholar's tenant DB)
          ├─ 5. READ: markdown_notes WHERE being_id="scholar"
          ├─ 6. LLM runs Scholar's task
          │
          ├─ 7. WRITE: markdown_notes (user_id="prime->scholar", being_id="scholar")
          ├─ 8. WRITE: conversation_turns (tenant-scholar, session="subtask:...")
          ├─ 9. WRITE: memories if learn_semantic triggered (being_id="scholar")
          ├─ 10. WRITE: procedural_memories (being_id="scholar")
          │
          ├─ WRITE: subagent_events (progress/completed) → tenant-prime DB
          ├─ WRITE: subagent_runs (status=completed) → tenant-prime DB
          │
          ▼
  [Parent Prime polls events, reads Scholar's final response text]
          │
          ▼
  OrchestrationEngine._update_task_result_synthesis()
          │
          ├─ WRITE: task_results → tenant-prime DB
          └─ WRITE: memories (user_id="orchestrator", being_id="prime") → tenant-prime DB

  Later: DreamCycle runs for Scholar
          │
          ├─ READ: memories WHERE being_id="scholar" (tenant-scholar DB)
          ├─ READ: task_results WHERE beings_used LIKE '%"scholar"%'
          │         WARNING: may be empty if querying wrong tenant DB
          ├─ LLM consolidation + derivation
          │
          ├─ WRITE: memories (derived insights, being_id="scholar")
          └─ WRITE: memories in OTHER beings' tenant DBs (cross-pollination)
                    + WRITE: workspaces/sai-memory/dream_logs/{timestamp}.md
```

---

*End of audit. All claims above are traceable to specific file:line references as cited throughout.*
