# CLAUDE.md -- BOMBA SR Runtime

## PRIME DIRECTIVE
**READ source code BEFORE attempting any fix or guess.** Do not hypothesize about behavior -- open the file, read the function, then act. This single rule would have prevented the majority of past session failures.

## Tech Stack (LOCKED -- do not flip)
- **Language:** Python 3.11+ (venv at `.venv/`, Python 3.14 active)
- **Framework:** stdlib `http.server.ThreadingHTTPServer` -- NOT Flask, NOT FastAPI, NOT Django
- **Database:** SQLite (WAL mode) via `src/bomba_sr/storage/db.py` -- NOT PostgreSQL, NOT MongoDB
- **LLM routing:** OpenRouter (primary), Anthropic direct, OpenAI direct, StaticEchoProvider fallback
- **Code intelligence:** Serena-first, native fallback
- **Frontend:** None. This is a backend runtime. No Vite, no Next.js, no React.
- **Package management:** `pyproject.toml` + `setuptools` -- no `package.json` exists anywhere
- **Testing:** `pytest` (100+ tests, all passing) -- NOT unittest discover
- **Dependencies:** `PyYAML>=6.0`, `croniter>=1.3.0`, `html2text>=2024.2.26`

## Directory Layout
```
PROJEKT/                         # <-- THIS is the project root. Always work from here.
  .env                           # Active env vars (DO NOT commit)
  .env.example                   # Env template with all vars documented
  pyproject.toml                 # Project metadata + pytest config
  HEARTBEAT.md                   # Proactive autonomy checklist (user-editable)
  src/
    bomba_sr/                    # Main package -- ALL source code lives here
      runtime/
        bridge.py                # RuntimeBridge -- THE central orchestrator
        config.py                # RuntimeConfig -- all env var parsing
        loop.py                  # AgenticLoop -- iterative tool-call loop
        health.py                # HealthSnapshot for loop system prompt
        rescue.py                # Git-based workspace rescue snapshots
        tenancy.py               # Multi-tenant context binding
      llm/providers.py           # LLM provider selection + ChatMessage model
      context/policy.py          # Context assembly + TurnProfile enum
      tools/                     # base.py (ToolExecutor) + builtin_*.py per domain
        builtin_web.py           # web_search (Brave/DuckDuckGo) + web_fetch tools
        builtin_subagents.py     # sessions_spawn, sessions_poll, sessions_list tools
        builtin_scheduler.py     # schedule_task, list_schedules tools
      governance/                # tool_policy.py, policy_pipeline.py, tool_profiles.py
      skills/                    # loader, registry, engine, ecosystem, parser, eligibility
        skillmd_parser.py        # Agent Skills standard parser (SKILL.md YAML frontmatter)
        eligibility.py           # OpenClaw metadata gating (requires.env, bins, os)
        ecosystem.py             # Skill catalog install (ClawHub, Anthropic Skills)
      commands/                  # parser, router, disclosure, skill_nl_router
      memory/
        hybrid.py                # Hybrid memory (DB + markdown + embeddings + conversation history)
        consolidation.py         # MemoryConsolidator (semantic + procedural memories)
        embeddings.py            # Optional OpenAI embeddings for semantic search
      subagents/
        protocol.py              # SubAgentTask/events, shared memory, event streaming
        orchestrator.py          # Async spawn, crash recovery, cascade stop, depth enforcement
        worker.py                # SubAgentWorkerFactory -- real LLM-backed sub-agent workers
      autonomy/
        heartbeat.py             # HeartbeatEngine -- background daemon for proactive checks
        scheduler.py             # CronScheduler -- recurring task execution
      adaptation/
        runtime_adaptation.py    # Metrics aggregation, policy versioning/rollback, self-correction
        self_evaluation.py       # SelfEvaluator -- LLM-based performance self-assessment
      codeintel/                 # router.py (Serena vs native), serena.py, native.py
      storage/db.py              # SQLite RuntimeDB wrapper (WAL mode, thread-safe RLock)
      models/capabilities.py     # OpenRouter capability fetch + cache
      identity/profile.py        # User profile + signal approvals
      projects/service.py        # Project/task service
      artifacts/store.py         # Artifact persistence
      info/retrieval.py          # Wikipedia/generic info retrieval
      plugins/                   # Plugin registration + discovery
  scripts/
    run_chat_cli.py              # Interactive CLI entry point
    run_runtime_server.py        # HTTP server entry point
    run_user_e2e.py              # E2E scripted test
  contracts/                     # JSON Schema files for all domain models
  tests/                         # pytest tests (all phases + ouroboros)
  sql/migrations/                # SQL migration scripts (reference schemas, 001-008)
  docs/                          # Authoritative runtime documentation
  skills/                        # Workspace skill definitions (SKILL.md files)
    web_search/SKILL.md          # Bundled web search skill
  acceptance/                    # Acceptance criteria documents
  product/                       # Product specs and manifests
  .runtime/                      # Runtime state dir (SQLite DB, tenant data)
```

## Startup Sequence
```bash
# 1. Activate venv (REQUIRED -- system python lacks deps)
source .venv/bin/activate

# 2. Verify env
cp .env.example .env  # if .env missing; then fill OPENROUTER_API_KEY

# 3. Run tests first to confirm clean state
PYTHONPATH=src python -m pytest -q
# Expected: 100+ passed

# 4a. CLI mode
PYTHONPATH=src python scripts/run_chat_cli.py \
  --tenant-id tenant-local --user-id user-local \
  --workspace "$(pwd)"

# 4b. HTTP server mode
PYTHONPATH=src python scripts/run_runtime_server.py --host 127.0.0.1 --port 8787

# 5. Health check
curl -s http://127.0.0.1:8787/health | python -m json.tool
# Expected: {"ok": true}
```

## Environment Variables
| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Yes (for live LLM) | none | Primary LLM provider key |
| `BOMBA_MODEL_ID` | No | `anthropic/claude-opus-4.6` | Default model ID |
| `BOMBA_RUNTIME_HOME` | No | `.runtime` | Runtime state directory |
| `BOMBA_AGENTIC_LOOP_ENABLED` | No | `true` | Enable agentic tool-call loop |
| `BOMBA_MAX_LOOP_ITERATIONS` | No | `25` | Max iterations per turn |
| `BOMBA_LOOP_DETECTION_WINDOW` | No | `5` | Repeating tool-call detection window |
| `BOMBA_BUDGET_LIMIT_USD` | No | `2.0` | Per-turn spending limit |
| `BOMBA_BUDGET_HARD_STOP_PCT` | No | `0.9` | Budget fraction that triggers hard stop |
| `BOMBA_TOOL_PROFILE` | No | `full` | Tool visibility profile |
| `BOMBA_TOOL_ALLOW` | No | `` | Comma-separated tool allow list |
| `BOMBA_TOOL_DENY` | No | `` | Comma-separated tool deny list |
| `BOMBA_LEARNING_AUTO_APPLY_CONFIDENCE` | No | `0.4` | Auto-apply threshold for learning signals |
| **Conversation History** | | | |
| `BOMBA_REPLAY_HISTORY_BUDGET_FRACTION` | No | `0.3` | Max fraction of input tokens for turn replay |
| **Autonomy** | | | |
| `BOMBA_HEARTBEAT_ENABLED` | No | `false` | Enable background heartbeat |
| `BOMBA_HEARTBEAT_INTERVAL` | No | `1800` | Heartbeat interval in seconds |
| `BOMBA_CRON_ENABLED` | No | `false` | Enable cron scheduler |
| **Adaptation** | | | |
| `BOMBA_ADAPTATION_METRICS_INTERVAL` | No | `5` | Turns between metrics-based self-correction |
| `BOMBA_ADAPTATION_LLM_EVAL_INTERVAL` | No | `10` | Turns between LLM self-evaluation |
| `BOMBA_ADAPTATION_AUTO_CORRECT` | No | `true` | Enable automatic policy correction |
| **Web Search** | | | |
| `BOMBA_WEB_SEARCH_ENABLED` | No | `true` | Enable web search/fetch tools |
| `BRAVE_API_KEY` | No | none | Brave Search API key (falls back to DuckDuckGo) |
| **Sub-agents** | | | |
| `BOMBA_SUBAGENT_MAX_SPAWN_DEPTH` | No | `3` | Max sub-agent nesting depth |
| `BOMBA_SUBAGENT_CRASH_WINDOW` | No | `60` | Crash detection window (seconds) |
| `BOMBA_SUBAGENT_CRASH_MAX` | No | `3` | Max crashes before cooldown |
| `BOMBA_SUBAGENT_CRASH_COOLDOWN` | No | `120` | Cooldown after crash threshold |
| **Serena** | | | |
| `SERENA_BASE_URL` | No | `http://127.0.0.1:9121` | Serena code intel endpoint |
| `SERENA_API_KEY` | No | none | Serena API key |
| `SERENA_FALLBACK_TO_NATIVE` | No | `true` | Fall back to native codeintel |
| **Skills** | | | |
| `BOMBA_SKILL_ROOTS` | No | `` | Additional skill directories |
| `BOMBA_SKILL_WATCHER` | No | `true` | Auto-reload skills on file change |
| `BOMBA_SKILL_CATALOG_SOURCES` | No | `clawhub,anthropic_skills` | Skill catalog sources |
| `CLAWHUB_API_BASE` | No | none | ClawHub registry API base URL |

Full reference: `docs/03-config-reference.md` and `src/bomba_sr/runtime/config.py`

## Testing
```bash
# All tests (fast -- ~1.5s)
PYTHONPATH=src .venv/bin/python -m pytest -q

# Single test file
PYTHONPATH=src .venv/bin/python -m pytest tests/test_wave1_capabilities.py -v

# Single test
PYTHONPATH=src .venv/bin/python -m pytest tests/test_wave1_capabilities.py::TestName::test_method -v

# With print output
PYTHONPATH=src .venv/bin/python -m pytest -s tests/test_wave1_capabilities.py
```
Test naming convention: `test_wave{N}_*`, `test_phase{N}_*`, `test_product_sequence{N}_*`, `test_ouroboros_*`, `test_ws{N}_*`, `test_skill*`.

## HTTP API Curl Templates (heredoc-safe for agents)
```bash
# Chat turn -- use heredoc to avoid JSON escaping disasters
curl -s http://127.0.0.1:8787/chat \
  -H 'content-type: application/json' \
  -d "$(cat <<'ENDJSON'
{
  "tenant_id": "tenant-local",
  "session_id": "sess-1",
  "user_id": "user-local",
  "workspace_root": "/absolute/path/to/project",
  "message": "your message here"
}
ENDJSON
)" | python -m json.tool

# Spawn sub-agent
curl -s http://127.0.0.1:8787/subagents/spawn \
  -H 'content-type: application/json' \
  -d "$(cat <<'ENDJSON'
{
  "tenant_id": "tenant-local",
  "parent_session_id": "sess-1",
  "parent_turn_id": "turn-1",
  "workspace_root": "/absolute/path",
  "task_id": "task-uuid",
  "idempotency_key": "unique-key-12chars",
  "goal": "describe the goal",
  "done_when": ["criterion 1"],
  "input_context_refs": [],
  "output_schema": {},
  "priority": "normal",
  "run_timeout_seconds": 120,
  "cleanup": "keep"
}
ENDJSON
)"

# Poll sub-agent events
curl -s "http://127.0.0.1:8787/subagents/events?tenant_id=tenant-local&run_id=RUN_ID"

# Code intelligence
curl -s http://127.0.0.1:8787/codeintel \
  -H 'content-type: application/json' \
  -d '{"tenant_id":"tenant-local","tool_name":"find_symbol","arguments":{"symbol":"RuntimeBridge"}}'
```

**JSON/curl rule:** ALWAYS use `cat <<'ENDJSON'` heredoc for multi-line JSON. Single quotes on the delimiter prevent shell expansion.

## Key Architectural Facts

### Core Architecture
- **RuntimeBridge** (`runtime/bridge.py`) is the single entry point for all operations. CLI and HTTP server both call `handle_turn()`.
- **Tenant isolation:** Each tenant gets its own RuntimeDB, memory store, skill registry. Cached in `_tenant_runtimes` dict.
- **Agentic loop** (`runtime/loop.py`) iterates: generate -> parse tool calls -> execute via governance -> append results -> check stop conditions.
- **Provider selection order:** Anthropic key > OpenAI key > OpenRouter key > StaticEchoProvider.

### Three-Tier Memory System
1. **Working/Episodic** — `markdown_notes` table + filesystem notes under workspace `memory/` dir. Persists session observations and task notes.
2. **Semantic** — `memories` + `memory_archive` tables via `MemoryConsolidator`. Handles contradiction detection (archives old belief, promotes new), versioned updates, and recency-weighted lexical retrieval.
3. **Procedural** — `procedural_memories` table. Tracks tool-chain strategies with success/failure counters. Retrieval ranked by `lexical_score * success_ratio`. Learned automatically after successful tool chains.

### Conversation History (Sliding Window + Summary)
- `conversation_turns` table stores every turn with `turn_number`, `token_estimate`.
- Last 3-5 turns replayed as full `ChatMessage` pairs (budget-capped at 30% of available input tokens via `_cap_recent_turn_messages()`).
- Older turns condensed into `session_summaries` via LLM-generated digests (triggered every 5 turns, window=3).
- Summaries injected into `recent_history` input of context assembly.

### Sub-Agents
- **Real workers** — `SubAgentWorkerFactory` creates workers that call `bridge.handle_turn()` recursively with their own session.
- Async execution via `ThreadPoolExecutor`, non-blocking. Parent continues while children run.
- **Depth enforcement** — `subagent_max_spawn_depth` (default 3) prevents runaway nesting.
- **Cascade stop** — when parent budget exhausts or max iterations hit, active children are terminated.
- **Crash recovery** — crash window/max/cooldown prevents rapid respawning.
- **Shared memory writes** require: `writer_agent_id`, `ticket_id`, `timestamp`, `confidence`, `scope` (scratch|proposal|committed).

### Proactive Autonomy
- **Heartbeat** — `HeartbeatEngine` runs a background daemon thread. Reads `HEARTBEAT.md` checklist from workspace root at configured interval (default 30min). Invokes `bridge.handle_turn()` with the checklist content. Reports only actionable items.
- **Cron** — `CronScheduler` polls for due tasks every 15s. Stores tasks in `scheduled_tasks` table. Uses `croniter` for full cron expression parsing, with built-in fallback for `@hourly`, `@daily`, `*/N * * * *`. Each execution gets a unique session ID.

### Self-Correcting Adaptation
- **Metrics-based** (every N turns, default 5) — `RuntimeAdaptationEngine.check_and_correct()` detects regressions across retrieval precision, search escalation, sub-agent success, loop incidents. On 2+ signals: rollback to last known-good policy. On 1 signal: targeted adjustment.
- **LLM self-evaluation** (every N turns, default 10) — `SelfEvaluator.evaluate()` reviews recent `loop_executions`, asks the LLM to score itself on tool_efficiency, memory_quality, goal_completion, and suggest policy_updates.
- **Policy versioning** — all policy changes versioned in `policy_versions` table with diffs and rollback references.

### Web Search
- `web_search` tool — Brave Search API (if `BRAVE_API_KEY` set), falls back to DuckDuckGo instant answers.
- `web_fetch` tool — fetches URL content, strips HTML to text.
- Gated by `BOMBA_WEB_SEARCH_ENABLED` config.

### Skills System
- **Agent Skills standard** (agentskills.io) compliant `SKILL.md` files with YAML frontmatter.
- **OpenClaw `metadata.openclaw`** extensions supported: `requires.env`, `requires.bins`, `requires.anyBins`, `requires.os`.
- **Skill loading precedence:** workspace skills > user skills (`~/.sigil/skills/`) > bundled > plugin dirs.
- **Catalog sources:** ClawHub, Anthropic Skills (configurable via `BOMBA_SKILL_CATALOG_SOURCES`).
- **Path traversal protection** on skill install — IDs sanitized with `re.sub(r'[^a-z0-9_-]', '', id)`.
- **Tool governance:** two-layer — PolicyPipeline (visibility/allow-deny) then ToolGovernanceService (per-call risk/confidence).
- **Confidence-gated learning:** `>=0.4` auto-applies, `<0.4` goes to approval queue.

## Safety Rules
1. **No `rm` or `mv` without `cp` backup first.** Always: `cp -r target target.bak && rm -rf target`
2. **No `git reset --hard` or `git clean -fd`** without explicit user confirmation.
3. **Never overwrite `.env`** -- it contains live API keys. Use `.env.example` as reference.
4. **Always use absolute paths** in commands. The working directory is `/Users/zidane/Downloads/PROJEKT`.
5. **Do not create files outside the project root** without explicit instruction.

## Debugging Protocol
1. **Read the source file first.** Open `src/bomba_sr/<module>.py` and read the relevant function.
2. **Check the contract schema** in `contracts/` if the issue involves request/response shape.
3. **Run the specific failing test** with `-v -s` to see full output.
4. **Check `.runtime/bomba_runtime.db`** for state issues -- it is SQLite, use `sqlite3` CLI.
5. **Read `docs/06-components-reference.md`** to understand which component owns what.
6. **Check adaptation state** — query `policy_versions` and `runtime_metrics_rollup` tables for self-correction decisions.

## Common Mistakes to Avoid
- **Wrong python:** Use `.venv/bin/python` or activate venv. System python lacks PyYAML.
- **Missing PYTHONPATH:** Always set `PYTHONPATH=src` when running scripts or tests.
- **Relative imports in tests:** Tests use `from bomba_sr.X import Y` -- requires `PYTHONPATH=src` in pyproject.toml.
- **Assuming a web framework:** There is no Flask/FastAPI. The HTTP server is raw `http.server`.
- **Editing SQL migrations for runtime changes:** The SQLite tables are created in-code by each service. The `sql/migrations/` are reference schemas only.
- **Wrong directory:** All commands assume cwd is `/Users/zidane/Downloads/PROJEKT`. Do not cd into subdirectories.
- **Forgetting thread safety:** `RuntimeDB` wraps all operations in `threading.RLock()`. Do not bypass.
- **Sub-agent depth:** Default max depth is 3. If sub-agents fail silently, check depth limit.

## Query Enrichment Hook
A `UserPromptSubmit` hook at `.claude/hooks/enrich-prompt.sh` auto-injects
per-query dynamic context into every prompt. It classifies the query intent
and selects minimal, high-value context (branch, diff, relevant paths).

Categories: `debug` | `test` | `api` | `file` | `git` | `refactor` | `general`

Config: `.claude/settings.json` (project-level hook registration).
The hook runs in <200ms and injects ~100-200 tokens of `additionalContext`.
