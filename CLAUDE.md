# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## PRIME DIRECTIVE
**READ source code BEFORE attempting any fix or guess.** Do not hypothesize about behavior — open the file, read the function, then act.

## Tech Stack
- **Language:** Python 3.11+ (venv at `.venv/`, Python 3.14 active)
- **API Framework:** FastAPI + Uvicorn (`src/bomba_sr/api/app.py`)
- **Database:** PostgreSQL (primary, via `BOMBA_POSTGRES_DSN`) with SQLite fallback per-tenant
- **LLM routing:** OpenRouter (primary), Bedrock (HIPAA), Anthropic direct, StaticEchoProvider fallback
- **Frontend:** React + Vite (`mission-control/`), served from `mission-control/dist/` by FastAPI
- **Testing:** `pytest` (700+ tests)
- **Key dependencies:** `PyYAML`, `croniter`, `bcrypt`, `boto3`, `pypdf`, `openpyxl`, `xlrd`

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
        sisters.py               # SisterConfig + SisterRegistry loader/lifecycle
        tenancy.py               # Multi-tenant context binding
      llm/providers.py           # LLM provider selection + ChatMessage model
      context/policy.py          # Context assembly + TurnProfile enum
      tools/                     # base.py (ToolExecutor) + builtin_*.py per domain
        builtin_web.py           # web_search (Brave/DuckDuckGo) + web_fetch tools
        builtin_pinecone.py      # pinecone_query + pinecone_list_indexes tools
        builtin_voice.py         # Bland.ai call management tools
        builtin_colosseum.py     # CHDDIA² Colosseum v2 tournament tools (5 tools)
        builtin_prove_ahead.py   # Prove-Ahead competitive intelligence tools (4 tools)
        builtin_sisters.py       # Prime sister management tools
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
      dashboard/
        service.py               # DashboardService -- MC beings, messages, SSE, tasks
        openclaw_sync.py         # OpenClaw session mirroring to MC
        pi_bridge.py             # Pi coding agent RPC bridge (Code tab backend)
      storage/db.py              # SQLite RuntimeDB wrapper (WAL mode, thread-safe RLock)
      models/capabilities.py     # OpenRouter capability fetch + cache
      identity/profile.py        # User profile + signal approvals
      identity/soul.py           # SoulConfig loader from SOUL/IDENTITY mission files
      projects/service.py        # Project/task service
      artifacts/store.py         # Artifact persistence
      info/retrieval.py          # Wikipedia/generic info retrieval
      plugins/                   # Plugin registration + discovery
  scripts/
    run_chat_cli.py              # Interactive CLI entry point
    run_runtime_server.py        # HTTP server entry point
    run_user_e2e.py              # E2E scripted test
    import_sai_identity.py       # SAI identity/mission file import
    import_sai_memory.py         # SAI memory + formula import
  contracts/                     # JSON Schema files for all domain models
  tests/                         # pytest tests (all phases + ouroboros)
  sql/migrations/                # SQL migration scripts (reference schemas, 001-008)
  docs/                          # Authoritative runtime documentation
  skills/                        # Workspace skill definitions (SKILL.md files)
    web_search/SKILL.md          # Bundled web search skill
  mission-control/                     # React 19 + Vite + Tailwind dashboard
    src/
      App.jsx                    # Tab router (Overview, Tasks, Comms, Teams, Code)
      api.js                     # REST client (tasks, beings, chat, code, acti, auth)
      components/
        CodeWorkspace.jsx        # Code tab -- Pi agent chat, diff viewer, file tree
        CodeStatusCard.jsx       # Overview sidebar -- code agent health card
        ChatWindow.jsx           # Comms tab -- multi-session being chat
        AgentTeams.jsx           # Teams tab -- ACT-I cluster explorer
        TaskBoard.jsx            # Task management with drag-and-drop
        Header.jsx               # Nav tabs + status indicators
      hooks/
        useSSE.js                # MC-wide SSE subscription
        useCodeSSE.js            # Per-session Code tab SSE subscription
    vite.config.js               # Dev proxy to backend :8787
  workspaces/
    prime/
      configs/                   # Agent JSON configs (Mylo, Callie, Athena)
      tools/                     # SAI reference tool scripts (bland, pinecone, voice, zoom)
      prove-ahead/               # Prove-Ahead competitive intelligence data + reports
      memory/                    # Imported memory state files
    forge/
      colosseum/v2/              # Colosseum v2 source + data (beings, judges, scenarios)
  acceptance/                    # Acceptance criteria documents
  product/                       # Product specs and manifests
  .runtime/                      # Runtime state dir (SQLite DB, tenant data)
```

**CRITICAL: All commands MUST run from the project root** (`/Users/studio2/Projects/sigil-runtime`).
Background tasks via `run_in_background` execute in a temp directory — always `cd` to project root first:
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

# 6. Mission Control dashboard (separate terminal)
cd mission-control && npx vite
# Open http://localhost:5173

# 7. SAI Code CLI (any terminal, any folder)
sai-code  # alias for pi with SAI Prime identity
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
| **Pinecone** | | | |
| `BOMBA_PINECONE_ENABLED` | No | `false` | Enable Pinecone retrieval tools |
| `BOMBA_PINECONE_DEFAULT_INDEX` | No | `ublib2` | Default Pinecone index |
| `BOMBA_PINECONE_DEFAULT_NAMESPACE` | No | `longterm` | Default Pinecone namespace |
| `PINECONE_API_KEY` | Conditional | none | Primary Pinecone API key |
| `PINECONE_API_KEY_STRATA` | No | none | Optional key for STRATA indexes |
| `BOMBA_PINECONE_INDEX_HOSTS` | No | none | Optional JSON host map fallback |
| **Voice (Bland.ai)** | | | |
| `BOMBA_VOICE_ENABLED` | No | `false` | Enable voice call management tools |
| `BOMBA_VOICE_PROVIDER` | No | `bland` | Voice provider selector |
| `BLAND_API_KEY` | Conditional | none | Bland API key |
| **Colosseum** | | | |
| `BOMBA_COLOSSEUM_ENABLED` | No | `false` | Enable Colosseum v2 tournament tools |
| `BOMBA_COLOSSEUM_MODEL_ID` | No | `gpt-4o-mini` | Model for being/judge LLM calls |
| **Prove-Ahead** | | | |
| `BOMBA_PROVE_AHEAD_ENABLED` | No | `false` | Enable Prove-Ahead competitive intelligence tools |
| **Zoom Skill Prereqs** | | | |
| `ZOOM_ACCOUNT_ID` | No | none | Zoom S2S OAuth account id |
| `ZOOM_CLIENT_ID` | No | none | Zoom S2S OAuth client id |
| `ZOOM_CLIENT_SECRET` | No | none | Zoom S2S OAuth client secret |
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
| **Code Agent (Pi)** | | | |
| `BOMBA_PI_ENABLED` | No | `true` | Enable Code tab Pi agent |
| `BOMBA_PI_MODEL` | No | `openrouter/anthropic/claude-sonnet-4` | Model for code agent |
| `BOMBA_PI_TOOLS` | No | `read,bash,edit,write,grep,find,ls` | Pi tools to enable |
| `BOMBA_PI_THINKING` | No | `off` | Pi thinking level (off/minimal/low/medium/high) |
| `BOMBA_PI_IDENTITY` | No | `true` | Inject SAI Prime identity into Pi system prompt |

Full reference: `docs/03-config-reference.md` and `src/bomba_sr/runtime/config.py`

## Testing
```bash
# Activate venv (REQUIRED)
source .venv/bin/activate

# With print output
PYTHONPATH=src .venv/bin/python -m pytest -s tests/test_wave1_capabilities.py
```
Test naming convention: `test_wave{N}_*`, `test_phase{N}_*`, `test_product_sequence{N}_*`, `test_ouroboros_*`, `test_ws{N}_*`, `test_skill*`, `test_builtin_*`, `test_import_*`, `test_soul_*`, `test_sisters*`, `test_pi_bridge*`.

# Run single test
PYTHONPATH=src python -m pytest tests/test_file.py::TestClass::test_method -v

# Start API server (MUST be from project root)
cd /Users/studio2/Projects/sigil-runtime
set -a && source .env && set +a
PYTHONPATH=src python scripts/run_api_server.py --host 0.0.0.0 --port 8787

# Build frontend
cd mission-control && npm run build

# After frontend build, restart server to serve new bundle
```

## Two Databases — Critical Distinction
- **PostgreSQL** (`BOMBA_POSTGRES_DSN` in `.env`): Shared Mission Control DB — users, beings, messages, sessions, teams, auth tokens. The running server uses THIS for all dashboard operations.
- **SQLite** (`.runtime/bomba_runtime.db`): Legacy/fallback. Tests use this. DO NOT create users or modify being configs in SQLite — the server won't see them.
- **Per-tenant SQLite** (`.runtime/tenants/{tenant-id}/bomba_runtime.db`): Conversation turns, memories, skills, scheduled tasks. One DB per tenant.

When creating users, resetting passwords, or changing being configs: **use PostgreSQL** via `bomba_sr.storage.postgres.PostgresDB(os.environ['BOMBA_POSTGRES_DSN'])`.

## Architecture

### Core Flow: User Message → Being Response
1. Frontend POST `/api/mc/chat/messages` → `chat.py` router
2. `DashboardService._route_to_being_sync()` (runs in background thread)
3. Classifies message: `not_task` / `light_task` / `full_task`
4. `full_task` → immediate ack + background execution with progress streaming
5. `RuntimeBridge.handle_turn()` — the central orchestrator
6. Loads SoulConfig (identity) from workspace SOUL.md/IDENTITY.md
7. Auto-retrieves from Pinecone (saimemory + ublib2) in parallel
8. Assembles context: system prompt + replay history + semantic recall
9. `AgenticLoop.run()` — iterates: LLM generate → parse tool calls → execute → loop
10. Returns result → dashboard creates chat message → SSE to frontend

### Key Files
- `src/bomba_sr/runtime/bridge.py` — RuntimeBridge, handle_turn, the god object
- `src/bomba_sr/runtime/loop.py` — AgenticLoop with auto-compaction at 75% context
- `src/bomba_sr/dashboard/service.py` — DashboardService, beings, messages, sessions, teams
- `src/bomba_sr/api/app.py` — FastAPI app factory, lifespan, router registration
- `src/bomba_sr/llm/providers.py` — Provider selection (OpenRouter > Bedrock > Anthropic > Echo)
- `src/bomba_sr/llm/bedrock.py` — AWS Bedrock with retry backoff
- `src/bomba_sr/memory/hybrid.py` — HybridMemoryStore (SQLite + markdown + embeddings)
- `src/bomba_sr/memory/auto_retrieval.py` — Automatic Pinecone search on every turn
- `src/bomba_sr/context/policy.py` — Context assembly with profile-weighted budget allocation
- `src/bomba_sr/identity/soul.py` — SoulConfig loader from workspace identity files
- `src/bomba_sr/governance/tool_profiles.py` — Tool groups and being access profiles
- `src/bomba_sr/governance/being_tool_profiles.py` — Per-tenant tool allow/deny

### Beings & Tenants
5 core beings, each with their own tenant and workspace:
| Being | Tenant | Model | Workspace |
|-------|--------|-------|-----------|
| Prime (SAI) | tenant-prime | anthropic/claude-opus-4.6 | workspaces/prime/ |
| Forge | tenant-forge | anthropic/claude-sonnet-4.6 | workspaces/forge/ |
| Scholar | tenant-scholar | openai/gpt-5.4 | workspaces/scholar/ |
| Recovery | tenant-recovery | anthropic/claude-sonnet-4.6 | workspaces/recovery/ |
| SAI Memory | tenant-memory | google/gemini-3.1-pro | workspaces/sai-memory/ |

ACT-I specialized beings exist but default to **offline**. Voice agents (athena-hoi, callie, mylo) are also offline.

### Pinecone (Vector Memory)
- **saimemory** (7K+ vectors): Operational memory. Per-tenant namespace routing via `.runtime/tenant_pinecone_map.json`
- **ublib2** (82K+ vectors): Sean's master knowledge library. Vectors in **default (empty) namespace** — never pass a namespace for ublib2
- Auto-retrieval searches both on every turn (`auto_retrieval.py`)
- `BOMBA_PINECONE_INDEX_HOSTS` env var maps index names to hosts
- `pinecone_list_indexes` describes up to 20 indexes (MAX_DESCRIBE_INDEXES)

### Embedding Routing
Embeddings use **OpenAI directly** (not OpenRouter) when `OPENAI_API_KEY` is set. Both `memory/embeddings.py` and `tools/builtin_pinecone.py` prefer OpenAI over OpenRouter for embedding calls.

### Frontend (Mission Control)
- React SPA in `mission-control/`, built with Vite
- Served from `mission-control/dist/` by the FastAPI server
- After editing JSX: `cd mission-control && npm run build`, then restart server
- SSE for real-time updates (chat messages, typing indicators, progress, task updates)
- Browser caching: users must hard-refresh (Cmd+Shift+R) after deploys

### Session Management
- Sessions persisted in `mc_chat_sessions` (PostgreSQL)
- `activeSessionId` stored in browser localStorage
- Auto-creates "General" session if user has zero sessions
- Sessions categorized: own / shared / team channels
- Full conversation transcript replayed (limit=500 turns, 70% context budget)

### Teams System
- Teams, members, channels, session sharing in PostgreSQL
- `mc_teams`, `mc_team_members`, `mc_session_shares`, `mc_team_channels` tables
- Any member can share sessions; only admins add/remove members
- Team channels appear in all members' Comms sidebar

### Cron Scheduler
- Enabled by default (`BOMBA_CRON_ENABLED=true`)
- 3 schedule types: `cron`, `at` (one-shot), `every` (interval)
- Run history tracked in `scheduled_task_runs` table
- API: `/api/mc/cron/*`, frontend panel on Overview tab

### Tool Governance
- Tools organized in groups: `group:fs`, `group:web`, `group:memory`, `group:cron`, `group:seo`, `group:skills`, etc.
- Being profiles map tenants to allowed tool groups (being_tool_profiles.py)
- `parse_document` is in `group:fs` — all beings with fs access can use it

## User Accounts
Accounts live in **PostgreSQL**. Key user groups:
- `@callagyrecovery.com` — password `SPCL01!`, tenant `tenant-recovery-*`
- `@sigil.ai` / `@acti.ai` — password `SPATI01!`, tenant `tenant-sai`
- `neel@sai.ai` — admin, tenant `tenant-prime`

## Common Pitfalls
1. **Wrong database**: Creating users/beings in SQLite when server uses Postgres
2. **Embedding 401**: OpenAI key sent to OpenRouter URL (or vice versa)
3. **ublib2 shows 0 vectors**: Passing a namespace filter (ublib2 uses default namespace)
4. **Beings echo stubs**: Wrong model_id in Postgres (e.g., `minimax/minimax-m2.5`)
5. **Auto-logout**: Token expiry — tokens last 30 days with auto-renewal
6. **Frontend not updating**: Serve stale bundle — rebuild + restart + hard refresh
7. **Bedrock model ID**: Must strip `openrouter/` prefix, map to `us.anthropic.*` format
8. **ACT-I beings online**: They reset to online on config load if not set to offline in code

## Environment Variables (Key Ones)
| Variable | Purpose |
|----------|---------|
| `BOMBA_POSTGRES_DSN` | PostgreSQL connection (primary DB) |
| `OPENROUTER_API_KEY` | LLM calls (primary provider) |
| `OPENAI_API_KEY` | Embeddings for Pinecone queries |
| `PINECONE_API_KEY` | Vector memory access |
| `BOMBA_LLM_PROVIDER_PRIORITY` | `openrouter` (default) or `bedrock` |
| `BOMBA_AUTO_RETRIEVAL` | `true`/`false` — auto Pinecone on every turn |
| `BOMBA_REPLAY_HISTORY_BUDGET_FRACTION` | `0.7` — 70% of context for conversation replay |
| `BOMBA_MAX_LOOP_ITERATIONS` | `50` — max tool call iterations per turn |
| `BOMBA_CRON_ENABLED` | `true` — enable cron scheduler |

### Code Tab (Pi Coding Agent Integration)
- **Harness:** Pi coding agent v0.62.0 (`@mariozechner/pi-coding-agent`), spawned as subprocess in RPC mode.
- **Bridge:** `dashboard/pi_bridge.py` — manages Pi process lifecycle, stdin/stdout JSONL communication, event dispatch, session tracking with local message persistence.
- **Protocol:** Pi RPC over pipes. Commands: `prompt`, `abort`, `new_session`, `get_state`, `get_messages`. Events: `text_delta`, `toolcall_start/end`, `tool_execution_start/end`, `agent_start/end`, `extension_ui_request`.
- **Multi-workspace:** Each session can target any folder. Pi restarts with new `cwd` when workspace changes. `git stash create` snapshots working tree at session start for scoped diffs.
- **Identity injection:** SAI Prime identity (SOUL.md + IDENTITY.md + MISSION.md) appended to Pi's system prompt via `--append-system-prompt`. Controlled by `BOMBA_PI_IDENTITY` env var.
- **SSE streaming:** Per-session SSE at `/api/mc/code/sessions/{id}/events`. 18 event types mapped from Pi events to `code_*` MC events.
- **Git diff viewer:** `git_diff()` runs `git diff <snapshot>` scoped to session. Parses unified diff into structured `{files, hunks, lines}`. Untracked files filtered against session-start snapshot.
- **Approval flow:** Pi `extension_ui_request` events (from `pi-permissions` extension) dispatched as `code_approval_required` SSE events. Frontend shows modal with Accept/Deny/Cancel. Responses sent back via `extension_ui_response` on stdin.
- **File browsing:** `file_tree()` scans workspace with skip-list (`.git`, `.venv`, `node_modules`, etc.). `read_file()` with path traversal guard and 100KB truncation.
- **Frontend:** `CodeWorkspace.jsx` — session sidebar, chat panel (streaming markdown + DiffBlock tool views), file tree with touched-file highlighting, right panel with Diff/Changes/Activity/Usage tabs.
- **Cross-tab:** Comms "Code" button, Task Board "Code" action, Overview `CodeStatusCard`, Header status indicator. `initialPrompt` prop auto-creates session and sends prompt.
- **CLI alias:** `sai-code` in `~/.zshrc` launches Pi TUI with SAI Prime identity in any terminal.

| Env Var | Default | Description |
|---|---|---|
| `BOMBA_PI_ENABLED` | `true` | Enable/disable code agent |
| `BOMBA_PI_MODEL` | `openrouter/anthropic/claude-sonnet-4` | Model for code agent |
| `BOMBA_PI_TOOLS` | `read,bash,edit,write,grep,find,ls` | Enabled Pi tools |
| `BOMBA_PI_THINKING` | `off` | Thinking level |
| `BOMBA_PI_IDENTITY` | `true` | Inject SAI Prime identity into system prompt |

**API Endpoints:**
```
GET    /api/mc/code/health                    — Pi bridge status
GET    /api/mc/code/sessions                  — List sessions
POST   /api/mc/code/sessions                  — Create session {title, workspace_root}
DELETE /api/mc/code/sessions/{id}             — Delete session
POST   /api/mc/code/sessions/{id}/prompt      — Send prompt {message}
POST   /api/mc/code/sessions/{id}/abort       — Cancel current operation
GET    /api/mc/code/sessions/{id}/messages    — Session conversation history
GET    /api/mc/code/sessions/{id}/events      — SSE event stream
POST   /api/mc/code/sessions/{id}/respond-ui  — Approval response {request_id, response}
GET    /api/mc/code/state                     — Pi agent state
GET    /api/mc/code/files?depth=3&workspace=  — Workspace file tree
GET    /api/mc/code/files/read?path=&workspace= — Read file content
GET    /api/mc/code/diff?workspace=&session_id= — Session-scoped git diff
```

## Safety Rules
1. **Never overwrite `.env`** — contains live API keys
2. **Never `git reset --hard`** without confirmation
3. **PostgreSQL is the source of truth** for users/beings/sessions
4. **ublib2 is SACRED** — Aiko review before any writes
5. **Always use absolute paths** — working directory is the project root

## Query Enrichment Hook
A `UserPromptSubmit` hook at `.claude/hooks/enrich-prompt.sh` auto-injects per-query dynamic context (branch, diff, relevant paths). Config: `.claude/settings.json`.
