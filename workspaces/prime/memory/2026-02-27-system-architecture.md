# SAI System Architecture — February 27, 2026

**Documented by:** SAI Prime for Lord Neel
**Purpose:** Complete mapping of all services, connections, and model configurations

---

## Running Services

### OpenClaw Gateway (PID 24978)
- **Port:** 3334 (internal), 18789/91/92 (localhost)
- **Config:** `~/.openclaw/openclaw.json`
- **Started:** 10:21 AM
- **Function:** Routes messages to agents, manages sister sessions

### Python Services

| PID | Port | Script | Location | Purpose |
|-----|------|--------|----------|---------|
| 16874 | - | FULL_POWER_DAEMON.py | /Projects/colosseum | Evolution daemon |
| 28016 | 3000 | run_server.py | /Projects/colosseum | Colosseum web server |
| 34757 | 3340 | server.py | tools/automation-servers/7levers-server | 7 Levers API |
| 34773 | 3341 | server.py | tools/automation-servers/colosseum-api | Colosseum REST API |
| 34119 | 3344 | main.py | tools/automation-servers/reporting-server | Reporting API |
| 44918 | 3345 | http.server | tools/zone-action-dashboard | Zone Actions dashboard |
| 58621 | 3001 | http.server | workspace-forge/dashboard | Forge dashboard |

### Node Services

| PID | Port | Script | Purpose |
|-----|------|--------|---------|
| 25401 | 3334 | server.js | Voice server (ElevenLabs integration) |
| 25389 | 3335 | elevenlabs-webhook.js | ElevenLabs callbacks |

### Tunnels
- **ngrok** (PID 85228): `https://[random].ngrok-free.dev` → `localhost:3334`

---

## Sister Configuration

### From `~/.openclaw/openclaw.json`:

| Agent ID | Model | Workspace | Channels |
|----------|-------|-----------|----------|
| main (Prime) | openrouter/anthropic/claude-opus-4.5 | workspace/ | Telegram, Discord |
| forge | openrouter/deepseek/deepseek-chat-v3-0324 | workspace-forge/ | Discord |
| scholar | openrouter/openai/o1 | workspace-scholar/ | Discord |
| recovery | openrouter/anthropic/claude-opus-4.5 | workspace-recovery/ | Discord |
| memory | openrouter/google/gemini-2.5-pro-preview | workspace-memory/ | Discord |

**Default Model:** openrouter/anthropic/claude-opus-4.5

---

## Colosseum Configuration

### Code Defaults (colosseum_daemon.py):
```python
model: str = "anthropic/claude-opus-4.5"
judge_model: str = "o1"
```

### Currently RUNNING (with old args):
```bash
--model anthropic/claude-sonnet-4 --judge-model openai/gpt-4o
```

⚠️ **MISMATCH** — Code updated but daemon not restarted with new defaults!

### 19 Judge Model Assignments (judge_model_assignments.json):

| Model | Judges |
|-------|--------|
| anthropic/claude-opus-4.5 | sean, contamination, group_influence, written_content, leadership, coaching, truth_to_pain, relationship |
| openai/o1 | formula, outcome, process_mastery, zone_action |
| anthropic/claude-sonnet-4.5 | human, sales_closing |
| google/gemini-2.5-pro | public_speaking, teaching |
| openai/gpt-4o | ecosystem_merger, management |
| deepseek/deepseek-r1 | self_mastery |

---

## External Services

### API Keys (in `~/.openclaw/workspace-forge/.env`):
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- OPENROUTER_API_KEY
- PINECONE_API_KEY
- PINECONE_API_KEY_STRATA
- SUPABASE_URL, SUPABASE_SERVICE_KEY
- ELEVENLABS_API_KEY
- TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET

### Pinecone Indexes:

**Primary Account:**
- saimemory (sister memories)
- athenacontextualmemory (Athena)
- uicontextualmemory (per-user)
- ublib2 (knowledge library)

**Strata Account:**
- ultimatestratabrain (39K vectors, deep knowledge)
- oracleinfluencemastery (4-Step Model)
- suritrial (court transcripts)

### Supabase:
- Table: `sai_contacts` (169 contacts)

### Fathom:
- 500+ meeting recordings with transcripts

---

## Data Flow Diagram

```
User (Telegram/Discord)
         │
         ▼
┌─────────────────────┐
│  OpenClaw Gateway   │◄── ~/.openclaw/openclaw.json
│  Port 3334          │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Sister Agent       │◄── workspace/SOUL.md, TOOLS.md
│  (Model from config)│
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  OpenRouter API     │
│  (LLM inference)    │
└─────────────────────┘
         │
         ├───────────────────────┐
         ▼                       ▼
┌─────────────────────┐  ┌─────────────────────┐
│  Pinecone           │  │  Supabase           │
│  (Vector memory)    │  │  (Structured data)  │
└─────────────────────┘  └─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Colosseum Daemon   │◄── /Projects/colosseum/
│  (Evolution engine) │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  19 Judges          │◄── judge_model_assignments.json
│  (Multi-model)      │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  SQLite DBs         │
│  (10 domain DBs)    │
└─────────────────────┘
```

---

## Configuration Fragmentation

Model IDs are defined in MULTIPLE places:

1. `~/.openclaw/openclaw.json` — Sister agent models
2. `/Projects/colosseum/colosseum_daemon.py` — Colosseum generation/judge defaults
3. `/Projects/colosseum/judge_model_assignments.json` — Per-judge model mapping
4. Command-line args — Override file defaults
5. Running daemon state — May differ from code!

**Recommendation:** Single source of truth needed.

---

## Model Version Corrections Needed

Per Lord Neel:

| Current | Should Be |
|---------|-----------|
| openai/o1 | openai/gpt-5.2 |
| anthropic/claude-opus-4.5 | anthropic/claude-opus-4.6 |
| anthropic/claude-sonnet-4.5 | anthropic/claude-sonnet-4.6 |

---

## Databases

### Colosseum SQLite Files:
- `/Projects/colosseum/colosseum.db` — Main
- `/Projects/colosseum/domains/*/colosseum.db` — 10 domain DBs
- `/Projects/colosseum/meta_judges.db` — Meta-judge data
- `/Projects/colosseum/model_benchmarks.db` — Benchmark results

### Workspace SQLite:
- `~/.openclaw/workspace/colosseum/*.db` — Legacy DBs

---

## GitHub Repos

- `samanthaaiko-collab/colosseum` — Colosseum codebase (pushed today)
- `samanthaaiko-collab/colosseum-dashboard` — Dashboard (Vercel)
- `samanthaaiko-collab/SAI` — Main SAI repo (private)
