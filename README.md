# Sigil Framework (Bomba SR Runtime) v1.1+

A local-first, multi-tenant runtime for self-correcting AI agents. Sigil provides a complete agent runtime layer with agentic tool loops, three-tier persistent memory, real sub-agent orchestration, proactive autonomy, web search, and a self-correcting adaptation engine.

## Features

- **Agentic Tool Loop** — iterative generate → tool-call → execute cycle with budget enforcement, loop detection, and configurable iteration limits
- **Three-Tier Memory** — working/episodic notes, semantic memories with contradiction detection, and procedural memories with success-weighted recall
- **Conversation History** — sliding window of recent turns + LLM-generated summaries for long-running sessions, budget-capped token replay
- **Real Sub-Agents** — async child agents that invoke the LLM recursively with their own sessions, depth enforcement (max 3 levels), crash recovery, cascade stop
- **Proactive Autonomy** — background heartbeat daemon (reads `HEARTBEAT.md` checklist) + cron scheduler for recurring tasks
- **Self-Correcting Adaptation** — metrics-based regression detection (every 5 turns) + LLM self-evaluation (every 10 turns) with automatic policy rollback
- **Web Search** — `web_search` (Brave Search API / DuckDuckGo fallback) + `web_fetch` (URL → text) tools
- **Agent Skills Standard** — [agentskills.io](https://agentskills.io) compatible `SKILL.md` manifests with OpenClaw `metadata.openclaw` extension support
- **Tool Governance** — two-layer policy: visibility pipeline (allow/deny) + per-call risk/confidence decisioning with approval queue and audit trail
- **Confidence-Gated Learning** — signals ≥0.4 auto-apply to memory, <0.4 go to approval queue
- **Multi-Tenant Isolation** — each tenant gets independent SQLite DB, memory store, skill registry, and adaptation state
- **Serena Code Intelligence** — structural code operations (find symbol, replace body, rename) with native fallback
- **User Identity Profiles** — learned preferences with pending signal approvals

## Requirements

- Python 3.11+
- An LLM provider API key (OpenRouter, Anthropic, or OpenAI)

## Quick Start

### 1. Clone and set up environment

```bash
git clone <repo-url> && cd PROJEKT
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```bash
OPENROUTER_API_KEY=your-key-here
```

### 3. Run tests

```bash
PYTHONPATH=src python -m pytest -q
# Expected: 100+ passed
```

### 4. Start the CLI

```bash
PYTHONPATH=src python scripts/run_chat_cli.py \
  --tenant-id tenant-local \
  --user-id user-local \
  --workspace "$(pwd)"
```

### 5. Start the HTTP server (alternative)

```bash
PYTHONPATH=src python scripts/run_runtime_server.py --host 127.0.0.1 --port 8787
```

Verify:

```bash
curl -s http://127.0.0.1:8787/health | python -m json.tool
# {"ok": true}
```

---

## Architecture

### Core Flow

```
User Input (CLI or HTTP)
       ↓
  RuntimeBridge.handle_turn()
       ↓
  ┌─────────────────────────┐
  │  1. Memory Recall       │  ← HybridMemoryStore.recall() + procedural recall
  │  2. History Replay      │  ← Last 3-5 turns + session summary
  │  3. Context Assembly    │  ← TurnProfile + skill index + health snapshot
  │  4. Agentic Loop        │  ← generate → tool calls → execute → repeat
  │  5. Turn Recording      │  ← Store turn, trigger summary if needed
  │  6. Learning            │  ← Extract signals, confidence-gate, store
  │  7. Adaptation Check    │  ← Metrics correction / LLM self-eval
  └─────────────────────────┘
       ↓
  Response (text + tool results + metadata)
```

### Entry Points

| Entry Point | File | Description |
|---|---|---|
| CLI | `scripts/run_chat_cli.py` | Interactive terminal chat |
| HTTP Server | `scripts/run_runtime_server.py` | REST API on `http.server.ThreadingHTTPServer` |
| E2E Test | `scripts/run_user_e2e.py` | Scripted integration test |

Both entry points route through `RuntimeBridge.handle_turn()` — the single orchestrator for all operations.

### Module Map

```
src/bomba_sr/
├── runtime/          # Bridge, config, agentic loop, health, rescue, tenancy
├── llm/              # LLM provider abstraction (OpenRouter, Anthropic, OpenAI, Echo)
├── context/          # Context assembly, TurnProfile enum
├── tools/            # ToolExecutor + builtin tools (web, subagents, scheduler, etc.)
├── governance/       # Tool policy pipeline, risk/confidence governance, profiles
├── skills/           # Skill loader, registry, SKILL.md parser, ecosystem, eligibility
├── commands/         # Slash-command parser, router, disclosure, NL router
├── memory/           # HybridMemoryStore, MemoryConsolidator, embeddings
├── subagents/        # Protocol, orchestrator, worker factory
├── autonomy/         # HeartbeatEngine, CronScheduler
├── adaptation/       # RuntimeAdaptationEngine, SelfEvaluator
├── codeintel/        # Serena router, native fallback
├── storage/          # RuntimeDB (SQLite WAL, thread-safe)
├── models/           # OpenRouter capability fetch + cache
├── identity/         # User profile + signal approvals
├── projects/         # Project/task service
├── artifacts/        # Artifact persistence
├── info/             # Wikipedia/generic info retrieval
├── search/           # Local file search (rg two-pass)
└── plugins/          # Plugin registration + discovery
```

---

## Memory System

Sigil uses a three-tier memory architecture. All tiers persist across sessions via SQLite.

### Tier 1: Working / Episodic Memory

Markdown notes stored in the `markdown_notes` table and as files under the workspace `memory/` directory. Used for session observations, task notes, and ephemeral context.

### Tier 2: Semantic Memory

Managed by `MemoryConsolidator` with two tables:

- **`memories`** — versioned key-value beliefs with entity tracking, recency timestamps, and active/inactive status
- **`memory_archive`** — historical versions archived when contradictions are detected

Retrieval uses lexical scoring + recency boost (exponential decay, 14-day half-life). Meta-noise patterns (e.g. "do you remember") are filtered out.

### Tier 3: Procedural Memory

The `procedural_memories` table tracks tool-chain strategies:

- Each strategy has a `strategy_key`, `content`, `success_count`, and `failure_count`
- Retrieval is ranked by `lexical_score * success_ratio`
- Strategies are learned automatically after successful tool chain executions
- Failed strategies are tracked to reduce their future ranking

### Conversation History

Turns are stored in the `conversation_turns` table with auto-incrementing `turn_number`. The sliding window replays the last 3-5 turns as full message pairs, budget-capped to 30% of available input tokens. Older turns are summarized into `session_summaries` via an LLM call every 5 turns.

---

## Sub-Agent System

Sub-agents are real LLM-backed workers, not stubs.

### How it works

1. Parent calls `sessions_spawn` tool with a goal and done-when criteria
2. `SubAgentOrchestrator` spawns a `SubAgentWorkerFactory`-created worker in a `ThreadPoolExecutor`
3. Worker calls `RuntimeBridge.handle_turn()` recursively with its own dedicated session
4. Worker writes results to shared memory with confidence scoring
5. Parent polls via `sessions_poll` or `sessions_list` to check progress

### Safety

- **Max spawn depth:** Configurable (default 3). Prevents runaway recursive spawning.
- **Cascade stop:** When parent budget exhausts or max iterations hit, active children are terminated.
- **Crash recovery:** Tracks crash frequency per window. After `crash_max` (default 3) crashes in `crash_window` (default 60s), enters cooldown (default 120s).

### Tools

| Tool | Description |
|---|---|
| `sessions_spawn` | Spawn a sub-agent with a goal, done-when criteria, priority, timeout |
| `sessions_poll` | Poll a specific run for status and events |
| `sessions_list` | List all sub-agent runs for the current tenant |

---

## Proactive Autonomy

### Heartbeat

A background daemon thread that periodically reviews a workspace checklist:

1. Create a `HEARTBEAT.md` in your workspace root (template provided)
2. Enable: `BOMBA_HEARTBEAT_ENABLED=true`
3. Configure interval: `BOMBA_HEARTBEAT_INTERVAL=1800` (seconds, default 30 min)

The heartbeat reads `HEARTBEAT.md`, invokes the agent with the checklist, and reports only actionable items.

**Example `HEARTBEAT.md`:**

```markdown
# Heartbeat Checklist
- [ ] Check pending tool and learning approvals and summarize blockers.
- [ ] Review memory for unfinished tasks and suggest next concrete actions.
- [ ] Check scheduled tasks for recent failures or stalled outcomes.
- [ ] Report only actionable updates; if no action is required, reply with "all clear".
```

### Cron Scheduler

Recurring task execution with cron expression support:

1. Enable: `BOMBA_CRON_ENABLED=true`
2. Add tasks via the `schedule_task` tool or `/cron add` command
3. Tasks are stored in `scheduled_tasks` table and survive restarts

Supports full cron expressions (via `croniter`), plus built-in shortcuts: `@hourly`, `@daily`, `*/N * * * *`.

---

## Self-Correcting Adaptation

### Metrics-Based (Every 5 Turns)

The `RuntimeAdaptationEngine` aggregates metrics into `runtime_metrics_rollup`:

| Metric | Source |
|---|---|
| Retrieval precision@k | Search tool results |
| Search escalation rate | Search → Serena fallback frequency |
| Sub-agent success rate | Completed vs failed/timed-out |
| Sub-agent P95 latency | Runtime measurements |
| Loop detector incidents | Repeating tool-call detections |

**Regression detection:** Compares latest two rollup periods. 2+ regression signals triggers automatic rollback to last known-good policy. 1 signal triggers a targeted adjustment (e.g., increase loop detection window, reduce budget stop).

### LLM Self-Evaluation (Every 10 Turns)

`SelfEvaluator` reviews recent `loop_executions` and asks the LLM to score itself:

- `tool_efficiency` (0.0–1.0)
- `memory_quality` (0.0–1.0)
- `goal_completion` (0.0–1.0)
- `recommendations` (list of strings)
- `policy_updates` (dict of policy adjustments)

Policy updates from self-evaluation are applied via the same versioned policy system.

### Policy Versioning

All policy changes are stored in `policy_versions` with:
- Full policy JSON snapshot
- Diff from previous version
- Reason (e.g., `metrics_regression_autocorrect`, `llm_self_evaluation`)
- Rollback reference to source version

---

## Web Search

### Tools

| Tool | Risk | Description |
|---|---|---|
| `web_search` | Medium | Search the web. Uses Brave Search API if `BRAVE_API_KEY` is set, otherwise DuckDuckGo instant answers. |
| `web_fetch` | Medium | Fetch URL content. Strips HTML to plain text. Configurable `max_chars` (default 20,000). |

### Configuration

```bash
BOMBA_WEB_SEARCH_ENABLED=true    # Enable web tools (default: true)
BRAVE_API_KEY=your-brave-key     # Optional: enables Brave Search (better results)
```

### Bundled Skill

The `skills/web_search/SKILL.md` provides an Agent Skills standard workflow:
1. Search with a precise query
2. Select the most relevant 1-3 results
3. Fetch selected URLs
4. Synthesize a concise answer with citations

---

## Skills System

### Agent Skills Standard

Sigil implements the [Agent Skills standard](https://agentskills.io) — the open specification used by OpenClaw, Claude Code, Cursor, and 30+ platforms.

Skills are defined as `SKILL.md` files with YAML frontmatter:

```yaml
---
name: my-skill
description: What this skill does
license: MIT
user-invocable: true
allowed-tools: tool_a tool_b
metadata:
  openclaw:
    requires:
      env: [MY_API_KEY]
      bins: [node]
      os: [darwin, linux]
---
Step-by-step instructions for the agent...
```

### Supported Fields

| Field | Description |
|---|---|
| `name` | Skill identifier |
| `description` | Human-readable description |
| `license` | License identifier (e.g., MIT, Apache-2.0) |
| `user-invocable` | Whether the user can invoke via `/skill-name` |
| `disable-model-invocation` | Block the LLM from invoking this skill |
| `allowed-tools` | Space-delimited tool whitelist |
| `compatibility` | Compatibility string |
| `metadata` | Nested dict for extensions (e.g., `metadata.openclaw`) |

### OpenClaw Compatibility

The `metadata.openclaw.requires` block enables environment gating:
- `env` — check environment variables exist
- `bins` — check binaries on PATH
- `anyBins` — at least one binary exists
- `os` — check `sys.platform` matches (`darwin`, `linux`, `win32`)

### Skill Loading Precedence

1. Workspace skills (`<workspace>/skills/`)
2. User skills (`~/.sigil/skills/`)
3. Bundled skills (shipped with Sigil)
4. Plugin directories (`BOMBA_PLUGIN_PATHS`)

### Catalog Sources

Skills can be installed from external catalogs:
- **ClawHub** — OpenClaw's skill registry
- **Anthropic Skills** — Anthropic's official skill catalog

Configure sources: `BOMBA_SKILL_CATALOG_SOURCES=clawhub,anthropic_skills`

---

## Tool Governance

### Two-Layer Policy

1. **PolicyPipeline** — visibility layer. Determines which tools the agent can see based on `BOMBA_TOOL_PROFILE`, `BOMBA_TOOL_ALLOW`, and `BOMBA_TOOL_DENY`.

2. **ToolGovernanceService** — per-call decisioning. Evaluates risk level and confidence before each tool execution. High-risk calls go to the approval queue.

### Tool Profiles

| Profile | Description |
|---|---|
| `minimal` | Read-only tools only |
| `research` | Minimal + search + web tools |
| `standard` | Research + code tools |
| `full` | All tools enabled (default) |

### Risk Levels

| Level | Example Tools |
|---|---|
| `low` | `sessions_poll`, `sessions_list`, `list_schedules` |
| `medium` | `web_search`, `web_fetch`, `schedule_task` |
| `high` | `sessions_spawn`, `shell_execute`, `replace_symbol_body` |

---

## HTTP API

### Chat & Runtime

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send a chat turn |
| `GET` | `/health` | Health check |
| `GET` | `/artifacts` | List artifacts |

### Sub-Agents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/subagents/spawn` | Spawn a sub-agent |
| `GET` | `/subagents/events` | Poll sub-agent events |

### Code Intelligence

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/codeintel` | Execute code intelligence tool |

### Skills

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/skills/register` | Register a skill |
| `GET` | `/skills` | List loaded skills |
| `POST` | `/skills/execute` | Execute a skill |
| `GET` | `/skills/executions` | List skill executions |
| `GET` | `/skills/catalog` | Browse skill catalog |
| `GET` | `/skills/diagnostics` | Skill diagnostics |
| `GET` | `/skills/install-requests` | Pending install requests |
| `POST` | `/skills/install-request` | Request skill install |
| `POST` | `/skills/install` | Install a skill |
| `GET` | `/skills/source-trust` | Source trust settings |
| `POST` | `/skills/source-trust` | Update source trust |
| `GET` | `/skills/telemetry` | Skill telemetry |

### Governance & Approvals

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/approvals` | List pending approvals |
| `POST` | `/approvals/decide` | Approve or deny |

### Projects & Tasks

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/projects` | Create project |
| `GET` | `/projects` | List projects |
| `POST` | `/tasks` | Create task |
| `GET` | `/tasks` | List tasks |
| `POST` | `/tasks/update` | Update task |

### Identity

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/profile` | User profile |
| `GET` | `/profile/signals` | Pending learning signals |
| `POST` | `/profile/signals/decide` | Approve/deny signal |

### Example: Chat Turn

```bash
curl -s http://127.0.0.1:8787/chat \
  -H 'content-type: application/json' \
  -d "$(cat <<'ENDJSON'
{
  "tenant_id": "tenant-local",
  "session_id": "sess-1",
  "user_id": "user-local",
  "workspace_root": "/absolute/path/to/project",
  "message": "Search the web for the latest Python release notes"
}
ENDJSON
)" | python -m json.tool
```

---

## CLI Commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/skills` | List loaded skills |
| `/approvals` | List pending approvals |
| `/profile` | Show user profile |
| `/heartbeat status\|start\|stop` | Manage heartbeat engine |
| `/cron list\|add\|remove\|enable\|disable` | Manage scheduled tasks |
| `/<skill-name>` | Invoke any user-invocable skill |

---

## Configuration Reference

All configuration is via environment variables, loaded in `src/bomba_sr/runtime/config.py`.

### Required

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM access |

Or use `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` directly.

### LLM & Runtime

| Variable | Default | Description |
|---|---|---|
| `BOMBA_MODEL_ID` | `anthropic/claude-opus-4.6` | Default model |
| `BOMBA_RUNTIME_HOME` | `.runtime` | State directory |
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
| `BOMBA_HEARTBEAT_ENABLED` | `false` | Enable heartbeat |
| `BOMBA_HEARTBEAT_INTERVAL` | `1800` | Interval in seconds |
| `BOMBA_CRON_ENABLED` | `false` | Enable cron |

### Adaptation

| Variable | Default | Description |
|---|---|---|
| `BOMBA_ADAPTATION_METRICS_INTERVAL` | `5` | Turns between metrics checks |
| `BOMBA_ADAPTATION_LLM_EVAL_INTERVAL` | `10` | Turns between LLM self-eval |
| `BOMBA_ADAPTATION_AUTO_CORRECT` | `true` | Enable auto-correction |

### Web Search

| Variable | Default | Description |
|---|---|---|
| `BOMBA_WEB_SEARCH_ENABLED` | `true` | Enable web tools |
| `BRAVE_API_KEY` | none | Brave Search API key |

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
| `BOMBA_TOOL_RESULT_MAX_CHARS` | `15000` | Max tool result chars |
| `BOMBA_SHELL_OUTPUT_MAX_CHARS` | `50000` | Max shell output chars |
| `BOMBA_PARALLEL_READ_TOOLS` | `true` | Parallel read tool execution |

### Skills

| Variable | Default | Description |
|---|---|---|
| `BOMBA_SKILL_ROOTS` | `` | Additional skill directories |
| `BOMBA_SKILL_WATCHER` | `true` | Auto-reload on change |
| `BOMBA_SKILL_WATCHER_DEBOUNCE_MS` | `250` | Watcher debounce |
| `BOMBA_SKILL_CATALOG_SOURCES` | `clawhub,anthropic_skills` | Catalog sources |
| `BOMBA_SKILL_PARSING_PERMISSIVE` | `true` | Lenient SKILL.md parsing |
| `BOMBA_SKILL_NL_ROUTER_ENABLED` | `true` | Natural language skill routing |
| `BOMBA_SKILLS_TELEMETRY_ENABLED` | `true` | Skill execution telemetry |
| `CLAWHUB_API_BASE` | none | ClawHub registry URL |

### Serena Code Intelligence

| Variable | Default | Description |
|---|---|---|
| `SERENA_BASE_URL` | `http://127.0.0.1:9121` | Serena endpoint |
| `SERENA_API_KEY` | none | Serena auth key |
| `SERENA_FALLBACK_TO_NATIVE` | `true` | Fall back to native tools |

### Other

| Variable | Default | Description |
|---|---|---|
| `BOMBA_CAPABILITY_CACHE_TTL_SECONDS` | `21600` | Model capability cache TTL |
| `BOMBA_GENERIC_INFO_WEB_RETRIEVAL` | `true` | Wikipedia retrieval |
| `BOMBA_RESCUE_ENABLED` | `true` | Git rescue snapshots |
| `BOMBA_PLUGIN_PATHS` | `` | Plugin directories |
| `BOMBA_PLUGIN_ALLOW` | `` | Plugin allow list |
| `BOMBA_PLUGIN_DENY` | `` | Plugin deny list |

---

## SQLite Schema

Tables are created in-code by each service. The `sql/migrations/` directory contains reference schemas (001–008).

### Core Tables

| Table | Owner | Description |
|---|---|---|
| `markdown_notes` | HybridMemoryStore | Working/episodic notes |
| `memories` | MemoryConsolidator | Semantic memories (versioned) |
| `memory_archive` | MemoryConsolidator | Archived contradicted memories |
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

---

## Documentation

| File | Description |
|---|---|
| `docs/README.md` | Documentation index |
| `docs/02-architecture.md` | System architecture |
| `docs/03-config-reference.md` | Configuration reference |
| `docs/04-cli-reference.md` | CLI usage guide |
| `docs/05-http-api-reference.md` | HTTP API reference |
| `docs/06-components-reference.md` | Component ownership |
| `docs/07-ddd-workflow.md` | Documentation-driven development workflow |
| `CLAUDE.md` | Agent development guidelines |

---

## Testing

```bash
# All tests
PYTHONPATH=src python -m pytest -q

# Verbose single file
PYTHONPATH=src python -m pytest tests/test_wave1_capabilities.py -v

# Single test with output
PYTHONPATH=src python -m pytest tests/test_wave1_capabilities.py::TestName::test_method -v -s
```

Test naming convention: `test_wave{N}_*`, `test_phase{N}_*`, `test_product_sequence{N}_*`, `test_ouroboros_*`, `test_ws{N}_*`, `test_skill*`.

---

## Development

### Adding a New Tool

1. Create `src/bomba_sr/tools/builtin_<domain>.py`
2. Define `ToolDefinition` with name, description, parameters (JSON Schema), risk_level, action_type, and execute function
3. Register in `RuntimeBridge._build_tool_executor()`
4. Add to the appropriate tool profile in `governance/tool_profiles.py`

### Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter following the Agent Skills standard
2. Skills are auto-discovered on startup and hot-reloaded on file change (if watcher is enabled)

### Adding a SQL Table

1. Add `CREATE TABLE IF NOT EXISTS` in the owning service's `_ensure_schema()` method
2. Add a reference migration in `sql/migrations/` for documentation

---

## License

See `LICENSE` file.
