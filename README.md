# SAI Dashboard Runtime

<!-- Last verified: 2026-03-11. Update this date when sections are reviewed. -->

This branch packages the live SAI dashboard and runtime into one portable repo. The repo includes the dashboard UI, runtime backend, bundled OpenClaw-compatible workspace tree, projects, skills, tools, Colosseum assets, and historical session data so the system can be moved to another machine without depending on a separate `~/.openclaw` install.

The runtime still behaves like a multi-being ecosystem: Prime, Forge, Scholar, Recovery, and Memory share one dashboard and one backend, with access to Pinecone, Supabase, Postgres fallback reads, Fal video generation, Colosseum data, and the bundled project tree.

## Portable Layout

The repo is self-contained around these roots:

| Path | Purpose |
|---|---|
| `mission-control/` | React dashboard frontend |
| `src/bomba_sr/` | Runtime, orchestration, tools, dashboard API |
| `workspaces/` | Bundled Prime / Forge / Scholar / Recovery / Memory workspaces |
| `portable-openclaw/` | Portable OpenClaw-style root used by legacy scripts and session imports |
| `.portable-home/` | Portable HOME shim for scripts that expect `~/.openclaw` |
| `.runtime/` | Local runtime DBs, events, artifacts, and tenant state |

If you need to re-import from an existing OpenClaw source tree, use `scripts/import_portable_assets.sh /path/to/source-root`. It copies the full workspace folders and agent folders into this repo.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Being Ecosystem](#being-ecosystem)
3. [Memory Architecture](#memory-architecture)
4. [Context Assembly](#context-assembly)
5. [Orchestration Engine](#orchestration-engine)
6. [Inter-Agent Communication](#inter-agent-communication)
7. [Dashboard & Mission Control](#dashboard--mission-control)
8. [External Service Integrations](#external-service-integrations)
9. [Tool System & Governance](#tool-system--governance)
10. [ACT-I Integration](#act-i-integration)
11. [Quick Start & Development](#quick-start--development)
12. [GitHub Publishing](#github-publishing)
13. [Configuration Reference](#configuration-reference)
14. [Migration History](#migration-history)

---

## Architecture

### Core Flow

```
User Input (CLI or HTTP)
       |
  RuntimeBridge.handle_turn()
       |
  +--------------------------------------+
  |  1. Memory Recall                    |  <- HybridMemoryStore.recall()
  |  2. Identity Injection               |  <- SoulConfig (SOUL/IDENTITY/MISSION/VISION)
  |  3. History Replay                   |  <- Last 3-5 turns + session summary
  |  4. Context Assembly                 |  <- TurnProfile + budget allocation
  |  5. Tool Profile Filtering           |  <- Per-tenant tool deny lists
  |  6. Agentic Loop                     |  <- generate -> tool calls -> execute -> repeat
  |  7. Turn Recording                   |  <- Store turn, trigger summary if needed
  |  8. Learning                         |  <- Extract signals, confidence-gate, store
  |  9. Adaptation Check                 |  <- Metrics correction / LLM self-eval
  +--------------------------------------+
       |
  Response (text + tool results + metadata)
```

### Entry Points

| Entry Point | File | Description |
|---|---|---|
| CLI | `scripts/run_chat_cli.py` | Interactive terminal chat |
| HTTP Server | `scripts/run_runtime_server.py` | REST API on `http.server.ThreadingHTTPServer` |
| Dashboard API | `src/bomba_sr/dashboard/service.py` | Mission Control endpoints (`/api/mc/*`) |

All entry points route through `RuntimeBridge.handle_turn()` — the single orchestrator.

### Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| HTTP | stdlib `http.server.ThreadingHTTPServer` |
| Database | SQLite (WAL mode, thread-safe RLock) |
| LLM Routing | OpenRouter (primary), Anthropic, OpenAI, StaticEchoProvider fallback |
| Code Intelligence | Serena-first, native fallback |
| Frontend | React (Mission Control dashboard, port 5173) |
| Testing | pytest (76 test files, 100+ tests) |
| Dependencies | PyYAML, croniter, html2text |

### Module Map

```
src/bomba_sr/
+-- runtime/            Bridge, config, agentic loop, health, rescue, tenancy, sisters
+-- llm/                LLM provider abstraction (OpenRouter, Anthropic, OpenAI, Echo)
+-- context/            Context assembly engine, TurnProfile, budget allocation
+-- tools/              ToolExecutor + 20 builtin modules (web, voice, colosseum, etc.)
+-- governance/         PolicyPipeline, ToolGovernance, tool_profiles, being_tool_profiles
+-- skills/             SKILL.md parser, registry, ecosystem, OpenClaw eligibility
+-- commands/           Slash-command parser, router, disclosure, NL skill router
+-- memory/             HybridMemoryStore, MemoryConsolidator, embeddings
+-- subagents/          Protocol, orchestrator, worker factory (real LLM workers)
+-- orchestration/      4-phase planning engine (plan -> delegate -> review -> synthesize)
+-- autonomy/           HeartbeatEngine, CronScheduler
+-- adaptation/         RuntimeAdaptationEngine, SelfEvaluator, policy versioning
+-- acti/               ACT-I architecture loader (beings, clusters, skill families)
+-- codeintel/          Serena router, native fallback
+-- identity/           SoulConfig loader, user profile, signal approvals
+-- dashboard/          Mission Control service (110+ API endpoints)
+-- storage/            RuntimeDB (SQLite WAL, thread-safe)
+-- models/             OpenRouter capability fetch + cache
+-- projects/           Project/task service
+-- artifacts/          Artifact persistence
+-- info/               Wikipedia/generic info retrieval
+-- search/             Local file search (rg two-pass)
+-- plugins/            Plugin registration + discovery
```

---

## Being Ecosystem

The runtime operates as a hierarchy of **beings** — autonomous agents with distinct identities, tool access, and domains.

### Sister Architecture

```
SAI Prime (tenant-prime)
  |-- Full tool access (49 tools), orchestration authority
  |-- Hosts: sai-prime, executive-assistant, the-strategist, the-operator
  |
  +-- Forge (tenant-forge, 36 tools)
  |     Creative + code + production
  |     Hosts: the-writer, the-visual-architect, the-filmmaker,
  |            the-sound-engineer, the-stage-director, the-voice,
  |            the-media-buyer, the-messenger, the-technologist
  |
  +-- Scholar (tenant-scholar, 12 tools)
  |     Research + retrieval
  |     Hosts: the-analyst, the-researcher
  |
  +-- Recovery (tenant-recovery, 15 tools)
  |     Medical revenue recovery + CRM
  |     Hosts: the-connector, the-agreement-maker, the-keeper, the-multiplier
  |
  +-- Memory (tenant-memory, 12 tools)
        Cross-sister memory coordination, Pinecone synthesis
```

### Being Types

| Type | Count | Description |
|---|---|---|
| `runtime` | 1 | SAI Prime — the host runtime |
| `sister` | 4 | Persistent sister runtimes (Forge, Scholar, Recovery, Memory) |
| `acti` | 17 | ACT-I specialized beings (hosted by parent sisters) |
| `voice` | variable | Bland.ai voice agents (not chat-routable) |
| `subagent` | variable | Ephemeral sub-agents (BD-PIP, BD-WC, etc.) |

### Identity Injection (SoulConfig)

Each being loads identity from up to 9 workspace files via `identity/soul.py`:

| File | Injected Into | Char Limit |
|---|---|---|
| `SOUL.md` | System contract | 4,000 |
| `IDENTITY.md` | System contract | 2,000 |
| `MISSION.md` | System contract | — |
| `VISION.md` | System contract | — |
| `DESCRIPTION.md` | System contract | — |
| `FORMULA.md` | Semantic candidates | — |
| `PRIORITIES.md` | Working memory | — |
| `KNOWLEDGE.md` | System contract | — |
| `TEAM_CONTEXT.md` | System contract | — |

Identity files live under each sister's `workspaces/<sister>/` directory.

### Per-Being Tool Filtering

Each sister operates with a curated tool set defined in `governance/being_tool_profiles.py`. Tools not in a being's profile are denied before serialization, saving ~200 tokens per excluded tool per turn.

| Tenant | Tools | Groups |
|---|---|---|
| `tenant-prime` | 49 (full) | All |
| `tenant-forge` | 36 | fs, memory, web, pinecone, runtime, codeintel, skills, knowledge, sessions, colosseum |
| `tenant-scholar` | 12 | memory, web, pinecone, fs, knowledge |
| `tenant-recovery` | 15 | memory, web, pinecone, voice, fs, knowledge, sessions |
| `tenant-memory` | 12 | memory, pinecone, fs, web, knowledge |

Filtering is injected into `ResolvedPolicy` via `dataclasses.replace()` in `bridge.py`, merging being-specific denied tools with the existing policy pipeline output.

---

## Memory Architecture

Three-tier memory, all persisted in per-tenant SQLite databases.

### Tier 1: Working / Episodic

Markdown notes in `markdown_notes` table + filesystem files under `memory/` directory. Used for session observations, task notes, ephemeral context.

### Tier 2: Semantic

Managed by `MemoryConsolidator` with two tables:

- **`memories`** — versioned key-value beliefs with entity tracking, recency timestamps, active/inactive status
- **`memory_archive`** — historical versions archived when contradictions detected

Retrieval: lexical scoring + recency boost (exponential decay, 14-day half-life). Meta-noise patterns filtered out.

**Contradiction handling:** When a new belief contradicts an existing one, the old belief is archived (not deleted) and the new one is promoted. Both versions are timestamped for audit.

### Tier 3: Procedural

The `procedural_memories` table tracks tool-chain strategies:
- Each strategy has `strategy_key`, `content`, `success_count`, `failure_count`
- Retrieval ranked by `lexical_score * success_ratio`
- Learned automatically after successful tool chains
- Failed strategies tracked to reduce future ranking

### Conversation History

| Mechanism | Description |
|---|---|
| `conversation_turns` table | Every turn stored with `turn_number`, `token_estimate` |
| Sliding window | Last 3-5 turns replayed as full `ChatMessage` pairs |
| Budget cap | 30% of available input tokens (`BOMBA_REPLAY_HISTORY_BUDGET_FRACTION`) |
| Session summaries | LLM-generated digests every 5 turns (window=3) |

### SQLite Tables

| Table | Owner | Purpose |
|---|---|---|
| `markdown_notes` | HybridMemoryStore | Working/episodic notes |
| `memories` | MemoryConsolidator | Semantic beliefs (versioned) |
| `memory_archive` | MemoryConsolidator | Archived contradicted beliefs |
| `procedural_memories` | MemoryConsolidator | Tool-chain strategies |
| `conversation_turns` | HybridMemoryStore | Per-turn records |
| `session_summaries` | HybridMemoryStore | Compressed session digests |
| `loop_executions` | RuntimeBridge | Agentic loop telemetry |
| `subagent_runs` | SubAgentProtocol | Sub-agent lifecycle tracking |
| `subagent_events` | SubAgentProtocol | Sub-agent event stream |
| `shared_memory_writes` | SubAgentProtocol | Cross-agent shared memory |
| `scheduled_tasks` | CronScheduler | Recurring task definitions |
| `raw_search_metrics` | RuntimeAdaptationEngine | Search telemetry |
| `raw_subagent_metrics` | RuntimeAdaptationEngine | Sub-agent telemetry |
| `raw_prediction_metrics` | RuntimeAdaptationEngine | Prediction scores |
| `raw_loop_incidents` | RuntimeAdaptationEngine | Loop detection events |
| `runtime_metrics_rollup` | RuntimeAdaptationEngine | Aggregated metrics |
| `policy_versions` | RuntimeAdaptationEngine | Policy history + diffs |

Tables are created in-code by each service's `_ensure_schema()` method. The `sql/migrations/` directory contains reference schemas (001-008) for documentation only.

---

## Context Assembly

The `ContextPolicyEngine` (`context/policy.py`) allocates context window budget across competing information sources using profile-specific weights.

### Turn Profiles

| Profile | Use Case |
|---|---|
| `chat` | Standard conversation — favors recent history |
| `task_execution` | Active task work — favors working memory |
| `planning` | Orchestration planning — balanced allocation |
| `memory_recall` | Memory-focused queries — favors semantic memory |
| `subagent_orchestration` | Sub-agent coordination — favors predictions |

### Budget Allocation

The engine reserves 20% of model context for output and 3% as safety floor, then distributes the remaining budget across 6 optional sections:

| Section | chat | task_exec | planning | mem_recall | subagent |
|---|---|---|---|---|---|
| working_memory | 0.26 | 0.34 | 0.24 | 0.12 | 0.28 |
| world_state | 0.08 | 0.10 | 0.15 | 0.08 | 0.10 |
| semantic | 0.24 | 0.18 | 0.22 | 0.42 | 0.18 |
| recent_history | 0.34 | 0.20 | 0.17 | 0.26 | 0.14 |
| procedural | 0.05 | 0.12 | 0.18 | 0.06 | 0.12 |
| predictions | 0.03 | 0.06 | 0.04 | 0.06 | 0.18 |

**Required blocks** (always included, never dropped): `system_contract`, `user_message`, `explicit_constraints`, `task_state`, `tool_provenance`.

**Post-assembly invariants:** explicit constraints preserved, tool source references preserved, contradiction labels paired with recency labels.

---

## Orchestration Engine

The `OrchestrationEngine` (`orchestration/engine.py`) breaks complex tasks into sub-tasks and delegates them to specialized beings.

### 4-Phase Lifecycle

```
_phase_plan()          ->  LLM generates a structured plan with being assignments
      |
_phase_delegate()      ->  Executes sub-tasks (parallel or sequential)
      |
_phase_review()        ->  Evaluates sub-task outputs against acceptance criteria
      |
_phase_synthesize()    ->  Combines outputs into a coherent final result
```

### Status Flow

```
planning -> delegating -> awaiting_completion -> reviewing -> [revising ->] synthesizing -> completed
                                                                                        -> failed
```

### Planning Phase

The LLM receives all registered beings as JSON and produces a structured plan:
```json
{
  "summary": "...",
  "synthesis_strategy": "...",
  "sub_tasks": [
    {
      "being_id": "the-analyst",
      "title": "...",
      "instructions": "...",
      "done_when": "..."
    }
  ]
}
```

Rules enforced by `PLAN_SYSTEM_PROMPT`:
- Each sub-task assigned to exactly one being based on role/strengths
- ACT-I beings (type `"acti"`) preferred for domain-matching tasks
- Instructions must be self-contained (being has no parent context)
- Each being gets at most one sub-task unless truly required

### Delegation

`_execute_subtask()` calls `bridge.handle_turn()` directly using:
- Session ID: `subtask:{parent_task_id}:{being_id}`
- The being's own `tenant_id` (tool filtering applies automatically)
- The being's own `workspace_root`
- ACT-I identity prefix injected via `get_being_identity_text()` if `type == "acti"`
- Prior being outputs included in delegation message (sequential mode)

After completion, a `learn_semantic()` memory is written into the being's tenant at confidence 0.8.

---

## Inter-Agent Communication

### Sub-Agent System

Sub-agents are real LLM-backed workers, not stubs.

```
Parent calls sessions_spawn
      |
SubAgentOrchestrator spawns worker via ThreadPoolExecutor
      |
Worker calls RuntimeBridge.handle_turn() recursively
      |
Worker writes results to shared_memory_writes
      |
Parent polls via sessions_poll / sessions_list
```

**Safety mechanisms:**
- Max spawn depth: 3 (configurable). Prevents runaway recursive spawning.
- Cascade stop: parent budget exhaustion terminates active children.
- Crash recovery: after 3 crashes in 60s, enters 120s cooldown.

### Sister Lifecycle

`SisterRegistry` (`runtime/sisters.py`) manages sister spawning and control:

| Method | Description |
|---|---|
| `list_sisters()` | All sister configs with live status |
| `get_sister(id)` | Single sister config |
| `spawn_sister(id)` | Creates SubAgentTask, spawns via orchestrator |
| `stop_sister(id)` | Cascade stop via protocol |

Config loaded from `workspaces/prime/sisters.json`. Workspace paths validated against `workspaces/` directory (path traversal protection).

### Shared Memory Protocol

Cross-agent memory writes require:
- `writer_agent_id` — who wrote it
- `ticket_id` — deduplication key
- `timestamp` — write time
- `confidence` — 0.0-1.0 score
- `scope` — `scratch` | `proposal` | `committed`

### Proactive Autonomy

| Feature | Description |
|---|---|
| **Heartbeat** | Background daemon reads `HEARTBEAT.md` checklist at configurable interval (default 30min). Reports only actionable items. |
| **Cron Scheduler** | Recurring tasks via `croniter`. Stored in `scheduled_tasks` table. Supports full cron expressions + `@hourly`, `@daily` shortcuts. |

---

## Dashboard & Mission Control

The dashboard service (`dashboard/service.py`) exposes 110+ API endpoints under `/api/mc/*` for the React-based Mission Control frontend (port 5173).

### API Route Groups

| Group | Base Path | Key Endpoints |
|---|---|---|
| Beings | `/api/mc/beings` | List, detail, file access, skills |
| Tasks | `/api/mc/tasks` | CRUD, steps, artifacts, children, orchestration |
| Chat | `/api/mc/chat` | Messages, system messages |
| Orchestration | `/api/mc/orchestration` | Trigger, status, log |
| ACT-I | `/api/mc/acti` | Architecture, beings, clusters, skill families, levers |
| Sub-Agents | `/api/mc/subagents` | List active sub-agents |
| Artifacts | `/api/mc/artifacts` | Preview, download |
| Dream Cycle | `/api/mc/dream-cycle` | Logs, status, trigger |
| SSE Events | `/api/mc/events` | Server-Sent Events stream |

### Base Runtime Server Endpoints

| Group | Endpoints |
|---|---|
| Chat | `POST /chat` |
| Health | `GET /health` |
| Code Intel | `POST /codeintel` |
| Sub-Agents | `POST /subagents/spawn`, `GET /subagents/events` |
| Skills | `GET/POST /skills/*` (register, execute, catalog, install, telemetry) |
| Governance | `GET /approvals`, `POST /approvals/decide` |
| Projects | `GET/POST /projects`, `GET/POST /tasks` |
| Identity | `GET /profile`, `GET/POST /profile/signals` |

---

## External Service Integrations

### Connected Services

| Service | Module | Gated By |
|---|---|---|
| **OpenRouter** | `llm/providers.py` | `OPENROUTER_API_KEY` |
| **Anthropic** | `llm/providers.py` | `ANTHROPIC_API_KEY` |
| **OpenAI** | `llm/providers.py`, `memory/embeddings.py` | `OPENAI_API_KEY` |
| **Pinecone** | `tools/builtin_pinecone.py` | `BOMBA_PINECONE_ENABLED` + `PINECONE_API_KEY` |
| **Bland.ai** | `tools/builtin_voice.py` | `BOMBA_VOICE_ENABLED` + `BLAND_API_KEY` |
| **Brave Search** | `tools/builtin_web.py` | `BRAVE_API_KEY` (falls back to DuckDuckGo) |
| **Serena** | `codeintel/serena.py` | `SERENA_BASE_URL` |

### Pinecone Indexes

14 indexes documented in `INTEGRATION_MANIFEST.md` (155K+ vectors total). Default index/namespace: `ublib2` / `longterm`. STRATA key routing supported for known STRATA indexes via `PINECONE_API_KEY_STRATA`.

### Voice (Bland.ai)

| Tool | Risk | Description |
|---|---|---|
| `voice_list_calls` | Low | List recent calls |
| `voice_get_transcript` | Low | Get call transcript |
| `voice_make_call` | **High** | Outbound call (governance approval required) |
| `voice_list_pathways` | Low | List available pathways |

---

## Tool System & Governance

### Two-Layer Policy

```
Layer 1: PolicyPipeline (visibility)
  - BOMBA_TOOL_PROFILE (minimal/research/standard/full)
  - BOMBA_TOOL_ALLOW / BOMBA_TOOL_DENY
  - Per-tenant being_tool_profiles
      |
      v
  ResolvedPolicy (frozen dataclass: allowed_tools, denied_tools, source_layers)
      |
Layer 2: ToolGovernanceService (per-call)
  - Risk level assessment
  - Confidence threshold
  - High-risk -> approval queue
```

### Tool Profiles

| Profile | Description |
|---|---|
| `minimal` | Read-only tools only |
| `research` | Minimal + search + web tools |
| `standard` | Research + code tools |
| `full` | All tools enabled (default) |

### Tool Groups

Defined in `governance/tool_profiles.py` (8 base groups) and `governance/being_tool_profiles.py` (12 extended groups):

| Group | Tools |
|---|---|
| `group:fs` | read, write, edit, apply_patch, glob, grep |
| `group:memory` | memory_search, memory_get, memory_store |
| `group:web` | web_search, web_fetch |
| `group:runtime` | exec, process, compact_context, switch_model |
| `group:codeintel` | code_search + serena symbol tools |
| `group:pinecone` | pinecone_query, pinecone_multi_query, pinecone_upsert, pinecone_list_indexes |
| `group:voice` | voice_list_calls, voice_get_transcript, voice_make_call, voice_list_pathways |
| `group:colosseum` | colosseum_run_round, colosseum_leaderboard, colosseum_being_list, colosseum_evolve, colosseum_scenario_list |
| `group:sisters` | sisters_list, sisters_spawn, sisters_stop, sisters_status, sisters_message |
| `group:team` | team_graph_*, team_node_*, team_edge_*, team_deploy_*, team_schedule_* |
| `group:projects` | project_create, project_list, task_create, task_list, task_update |
| `group:scheduler` | schedule_task, list_schedules, remove_schedule, set_schedule_enabled |

### Skills System

Implements the [Agent Skills standard](https://agentskills.io) with OpenClaw extensions:

- **SKILL.md files** with YAML frontmatter (name, description, allowed-tools, metadata.openclaw)
- **Loading precedence:** workspace > user (`~/.sigil/skills/`) > bundled > plugin dirs
- **Catalog sources:** ClawHub, Anthropic Skills
- **OpenClaw gating:** `requires.env`, `requires.bins`, `requires.anyBins`, `requires.os`
- **Path traversal protection** on skill install

### Self-Correcting Adaptation

| Mechanism | Frequency | Action |
|---|---|---|
| Metrics-based | Every 5 turns | Detects regressions in retrieval precision, search escalation, sub-agent success, loop incidents. 2+ signals: rollback. 1 signal: targeted adjustment. |
| LLM self-eval | Every 10 turns | LLM scores tool_efficiency, memory_quality, goal_completion (0.0-1.0). Suggests policy_updates. |
| Policy versioning | Every change | Full JSON snapshot + diff stored in `policy_versions` table with rollback reference. |

### Confidence-Gated Learning

- Signals >= 0.4: auto-applied to memory
- Signals < 0.4: routed to approval queue
- Configurable via `BOMBA_LEARNING_AUTO_APPLY_CONFIDENCE`

---

## ACT-I Integration

ACT-I (Autonomous Collaborative Team Intelligence) provides the being specialization layer.

### Architecture

- **19 beings** organized across 4 runtime sisters
- **80 clusters** (operational teams) grouped into 9 skill families
- **8 levers** (L0.5 through L7) — capability dimensions
- **2,524 positions** distributed across clusters
- **4 shared heart skills** universal to all beings

### Data Source

ACT-I data lives in `workspaces/acti-architecture/`:
- `beings/*.md` — one file per being with structured frontmatter
- `clusters/**/*.md` — cluster definitions organized by skill family
- `skills/skill-families.md` — family metadata

Loaded by `acti/loader.py` with singleton caching.

### Being-Sister Mapping

| Sister | Beings |
|---|---|
| Prime | sai-prime, executive-assistant, the-strategist, the-operator |
| Scholar | the-analyst, the-researcher |
| Forge | the-writer, the-visual-architect, the-filmmaker, the-sound-engineer, the-stage-director, the-voice, the-media-buyer, the-messenger, the-technologist |
| Recovery | the-connector, the-agreement-maker, the-keeper, the-multiplier |

ACT-I beings share their parent sister's tenant (no new databases). Identity is injected via delegation message, not SoulConfig. This means when "the-analyst" receives work, it runs through `tenant-scholar` with The Analyst's identity prefix in the prompt.

### Cluster Tiers

| Tier | Icon | Description |
|---|---|---|
| Core | fire | Primary operational clusters |
| Supporting | blue | Secondary capability clusters |
| Aspirational | white | Future/emerging capability clusters |

---

## Quick Start & Development

### Requirements

- Python 3.11+
- Node.js 20+
- `OPENROUTER_API_KEY`

### Portable Setup

```bash
# 1. Clone
git clone https://github.com/NeelM0906/sigil-runtime.git
cd sigil-runtime

# 2. Python env
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Frontend deps
cd mission-control
npm install
cd ..

# 4. Configure secrets
cp .env.example .env
# Fill in the keys you actually use:
# OPENROUTER_API_KEY
# PINECONE_API_KEY / PINECONE_API_KEY_STRATA
# SUPABASE_URL / SUPABASE_SERVICE_KEY / DATABASE_URL
# FAL_KEY
# BLAND_API_KEY / ELEVENLABS_API_KEY / DEEPGRAM_API_KEY / ZOOM_* as needed

# 5. Build the portable OpenClaw layout
python3 scripts/bootstrap_portable_root.py

# 6. Run backend
PYTHONPATH=src python scripts/run_runtime_server.py --host 127.0.0.1 --port 8787

# 7. Run frontend in another terminal
cd mission-control
npm run dev

# 8. Health check
curl -s http://127.0.0.1:8787/health | python -m json.tool
```

Open:

- Dashboard: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8787`

### Optional Helper Shell

Some bundled legacy scripts still expect a HOME-style OpenClaw layout. Use this helper before running them manually:

```bash
source scripts/use_portable_openclaw.sh
```

That exports a repo-local `HOME`, `OPENCLAW_HOME`, and `OPENCLAW_ENV_FILE` so those scripts resolve inside this repo instead of a machine-global install.

### What Is Bundled

- Full workspace copies under `workspaces/`
- Portable agent/session history under `portable-openclaw/agents/`
- Colosseum project data under `workspaces/prime/Projects/colosseum/`
- Prove Ahead, webinar, transcript, and recovery project folders under `workspaces/*/Projects/`
- Dashboard artifacts and task output in `.runtime/`

### Testing

```bash
# Main regression suites
PYTHONPATH=src python -m pytest tests/test_dashboard_service.py tests/test_orchestration_engine.py tests/test_orchestration_subagent.py -q

# Full suite
PYTHONPATH=src python -m pytest -q

# Single test with output
PYTHONPATH=src python -m pytest tests/test_wave1_capabilities.py::TestName::test_method -v -s
```

76 test files. Naming conventions: `test_wave{N}_*`, `test_phase{N}_*`, `test_product_sequence{N}_*`, `test_ouroboros_*`, `test_ws{N}_*`, `test_skill*`, `test_builtin_*`, `test_sisters*`, `test_dashboard_*`, `test_orchestration_*`, `test_acti_*`.

## GitHub Publishing

This repo is meant to be portable across machines, but secrets are intentionally not committed.

1. Copy `.env.example` to `.env`
2. Fill in the API keys you actually use
3. Run `python3 scripts/bootstrap_portable_root.py`
4. Start the backend and frontend with the commands above

If you are preparing a public push after importing a fresh OpenClaw bundle, run:

```bash
python3 scripts/sanitize_portable_bundle.py portable-openclaw workspaces README.md
```

That pass scrubs embedded credentials and machine-specific paths from imported history and configs before you commit.

GitHub limit note:
- This repo intentionally excludes oversized generated artifacts that GitHub rejects, including Colosseum SQLite databases, large Colosseum logs, and large source MP3 files under `workspaces/prime/Projects/youtube-transcripts/`.
- Those files are not required to run the dashboard or runtime. If you have a private local copy and want them back in a working tree, place them in the same paths after cloning.

### Adding a New Tool

1. Create `src/bomba_sr/tools/builtin_<domain>.py`
2. Define `ToolDefinition` with name, description, parameters (JSON Schema), risk_level, action_type, execute function
3. Register in `RuntimeBridge._build_tool_executor()`
4. Add to the appropriate group in `governance/tool_profiles.py`
5. If sister-specific, add to `TENANT_TOOL_PROFILES` in `governance/being_tool_profiles.py`

### Adding a New Being

1. Add entry to `BEING_SISTER_MAP` in `acti/loader.py`
2. Create being markdown in `workspaces/acti-architecture/beings/`
3. Create associated clusters in `workspaces/acti-architecture/clusters/`
4. The being will automatically appear in dashboard and be available for orchestration

### Adding a New Sister

1. Add sister config to `workspaces/prime/sisters.json`
2. Create workspace directory under `workspaces/<sister-id>/`
3. Add identity files (SOUL.md, IDENTITY.md, DESCRIPTION.md, USER.md, AGENTS.md, TOOLS.md)
4. Add tenant entry to `TENANT_TOOL_PROFILES` in `governance/being_tool_profiles.py`
5. Map ACT-I beings to the sister in `BEING_SISTER_MAP`

### CLI Commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/skills` | List loaded skills |
| `/approvals` | List pending approvals |
| `/profile` | Show user profile |
| `/heartbeat status\|start\|stop` | Manage heartbeat engine |
| `/cron list\|add\|remove\|enable\|disable` | Manage scheduled tasks |
| `/<skill-name>` | Invoke any user-invocable skill |

### Documentation

| File | Description |
|---|---|
| `docs/02-architecture.md` | System architecture |
| `docs/03-config-reference.md` | Configuration reference |
| `docs/04-cli-reference.md` | CLI usage guide |
| `docs/05-http-api-reference.md` | HTTP API reference |
| `docs/06-components-reference.md` | Component ownership |
| `CLAUDE.md` | Agent development guidelines |

---

## Configuration Reference

All configuration via environment variables, loaded in `src/bomba_sr/runtime/config.py`.

### Required

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | Required primary model routing key |

### LLM & Runtime

| Variable | Default | Description |
|---|---|---|
| `BOMBA_MODEL_ID` | `anthropic/claude-opus-4.6` | Default model |
| `BOMBA_RUNTIME_HOME` | `.runtime` | Runtime state directory inside the repo |
| `BOMBA_AGENTIC_LOOP_ENABLED` | `true` | Enable tool loop |
| `BOMBA_MAX_LOOP_ITERATIONS` | `25` | Max loop iterations |
| `BOMBA_LOOP_DETECTION_WINDOW` | `5` | Repeating call detection |
| `BOMBA_BUDGET_LIMIT_USD` | `2.0` | Per-turn budget |
| `BOMBA_BUDGET_HARD_STOP_PCT` | `0.9` | Budget hard stop threshold |

### Memory & History

| Variable | Default | Description |
|---|---|---|
| `BOMBA_LEARNING_AUTO_APPLY_CONFIDENCE` | `0.4` | Auto-apply threshold |
| `BOMBA_REPLAY_HISTORY_BUDGET_FRACTION` | `0.3` | Max token fraction for history replay |

### Autonomy

| Variable | Default | Description |
|---|---|---|
| `BOMBA_HEARTBEAT_ENABLED` | `false` | Enable heartbeat daemon |
| `BOMBA_HEARTBEAT_INTERVAL` | `1800` | Interval in seconds |
| `BOMBA_CRON_ENABLED` | `false` | Enable cron scheduler |

### Adaptation

| Variable | Default | Description |
|---|---|---|
| `BOMBA_ADAPTATION_METRICS_INTERVAL` | `5` | Turns between metrics checks |
| `BOMBA_ADAPTATION_LLM_EVAL_INTERVAL` | `10` | Turns between LLM self-eval |
| `BOMBA_ADAPTATION_AUTO_CORRECT` | `true` | Enable auto-correction |

### External Services

| Variable | Default | Description |
|---|---|---|
| `BOMBA_WEB_SEARCH_ENABLED` | `true` | Enable web tools |
| `BRAVE_API_KEY` | none | Brave Search API key |
| `BOMBA_PINECONE_ENABLED` | `false` | Enable Pinecone tools |
| `BOMBA_PINECONE_DEFAULT_INDEX` | `ublib2` | Default Pinecone index |
| `PINECONE_API_KEY` | none | Primary Pinecone API key |
| `PINECONE_API_KEY_STRATA` | none | STRATA indexes key |
| `SUPABASE_URL` | none | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | none | Supabase service role key |
| `DATABASE_URL` | none | Postgres connection string or fallback source for postgres tools |
| `BOMBA_VOICE_ENABLED` | `false` | Enable voice tools |
| `BLAND_API_KEY` | none | Bland API key |
| `ELEVENLABS_API_KEY` | none | ElevenLabs voice / transcript integrations |
| `DEEPGRAM_API_KEY` | none | Deepgram STT integrations |
| `FAL_KEY` | none | Fal text-to-video / media generation |
| `BOMBA_COLOSSEUM_ENABLED` | `false` | Enable Colosseum tools |
| `BOMBA_PROVE_AHEAD_ENABLED` | `false` | Enable Prove-Ahead tools |

### Sub-Agents

| Variable | Default | Description |
|---|---|---|
| `BOMBA_SUBAGENT_MAX_SPAWN_DEPTH` | `3` | Max nesting depth |
| `BOMBA_SUBAGENT_CRASH_WINDOW` | `60` | Crash window (seconds) |
| `BOMBA_SUBAGENT_CRASH_MAX` | `3` | Max crashes before cooldown |
| `BOMBA_SUBAGENT_CRASH_COOLDOWN` | `120` | Cooldown (seconds) |

### Tools & Governance

| Variable | Default | Description |
|---|---|---|
| `BOMBA_TOOL_PROFILE` | `full` | Tool visibility profile |
| `BOMBA_TOOL_ALLOW` | `` | Allow list (comma-separated) |
| `BOMBA_TOOL_DENY` | `` | Deny list (comma-separated) |

### Skills

| Variable | Default | Description |
|---|---|---|
| `BOMBA_SKILL_ROOTS` | `` | Additional skill directories |
| `BOMBA_SKILL_WATCHER` | `true` | Auto-reload on change |
| `BOMBA_SKILL_CATALOG_SOURCES` | `clawhub,anthropic_skills` | Catalog sources |

### Serena Code Intelligence

| Variable | Default | Description |
|---|---|---|
| `SERENA_BASE_URL` | `http://127.0.0.1:9121` | Serena endpoint |
| `SERENA_API_KEY` | none | Serena auth key |
| `SERENA_FALLBACK_TO_NATIVE` | `true` | Fall back to native tools |

Full reference: `docs/03-config-reference.md` and `src/bomba_sr/runtime/config.py`.

---

## Migration History

### Phase 1: ACT-I Identity Migration (2026-03-05)

Trimmed all 5 sisters' identity files to ACT-I Build Guide standards:
- SOUL.md < 4,000 chars, IDENTITY.md < 2,000 chars
- 6 required files per being: DESCRIPTION.md, AGENTS.md, TOOLS.md, SOUL.md, IDENTITY.md, USER.md
- **Result:** 24,661 chars / 6,397 tokens saved across system prompts

### Phase 2: Per-Being Tool Filtering (2026-03-06)

Introduced `being_tool_profiles.py` with per-tenant tool allow-lists:
- Wired into `bridge.py` policy resolution via `ResolvedPolicy` merge
- **Result:** 13-37 tools removed per non-Prime being, saving ~2,600-7,400 tokens/turn in tool definitions

### Commits

| Hash | Description |
|---|---|
| `39f594d` | Phase 1 complete: All 5 sisters at 6/6 ACT-I identity compliance |
| `61c1a88` | Phase 2.1: Per-being tool profiles |
| `7681b30` | Phase 2.2: Wire tool filtering into bridge.py |
| `1443462` | Phase 2.3: Annotate sister configs with tool_profile + model updates |

---

## License

See `LICENSE` file.
