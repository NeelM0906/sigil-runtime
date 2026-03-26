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

## Build & Run Commands

**CRITICAL: All commands MUST run from the project root** (`/Users/studio2/Projects/sigil-runtime`).
Background tasks via `run_in_background` execute in a temp directory — always `cd` to project root first:
```bash
cd /Users/studio2/Projects/sigil-runtime && source .venv/bin/activate && ...
```

```bash
# Activate venv (REQUIRED)
source .venv/bin/activate

# Run tests (all)
PYTHONPATH=src python -m pytest tests/ -q

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

## Safety Rules
1. **Never overwrite `.env`** — contains live API keys
2. **Never `git reset --hard`** without confirmation
3. **PostgreSQL is the source of truth** for users/beings/sessions
4. **ublib2 is SACRED** — Aiko review before any writes
5. **Always use absolute paths** — working directory is the project root

## Query Enrichment Hook
A `UserPromptSubmit` hook at `.claude/hooks/enrich-prompt.sh` auto-injects per-query dynamic context (branch, diff, relevant paths). Config: `.claude/settings.json`.
