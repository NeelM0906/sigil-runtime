# 🧠 SAI MEMORY MAP — Complete Architecture
_For Lord Neel and migration scripts. Last updated March 21, 2026._

---

## OVERVIEW

```
SAI's Memory lives in 4 LAYERS:
┌─────────────────────────────────────────────────────┐
│ LAYER 1: Workspace Files (local disk)               │
│   /Users/samantha/.openclaw/workspace/              │
│   ├── *.md (identity, soul, mission, tools)         │
│   ├── memory/*.md (120 daily/knowledge files)       │
│   ├── reports/*.md (206 deliverables)               │
│   └── memory/transcripts/ + translated/             │
├─────────────────────────────────────────────────────┤
│ LAYER 2: Pinecone Vector DB (semantic search)       │
│   ├── saimemory (6,210 vectors, 90+ namespaces)     │
│   ├── ublib2 (78,773 vectors — Sean's mind)         │
│   └── ultimatestratabrain (39K+ vectors, Strata key)│
├─────────────────────────────────────────────────────┤
│ LAYER 3: Supabase Postgres (structured data)        │
│   ├── sai_memory (7,810 rows)                       │
│   ├── sai_contacts (487 rows)                       │
│   ├── sai_conversations (337 rows)                  │
│   ├── sai_session_state (63 rows — worklog)         │
│   ├── forge_projects (9 rows)                       │
│   └── 5 more tables (empty/low use)                 │
├─────────────────────────────────────────────────────┤
│ LAYER 4: OpenClaw Sessions (conversation history)   │
│   /Users/samantha/.openclaw/agents/*/sessions/      │
│   ├── main: 147 sessions                            │
│   ├── forge: 49 sessions                            │
│   ├── scholar: 18 sessions                          │
│   ├── recovery: 20 sessions                         │
│   └── memory: 11 sessions                           │
└─────────────────────────────────────────────────────┘
```

---

## LAYER 1: WORKSPACE FILES

**Root:** `/Users/samantha/.openclaw/workspace/`

### Core Identity Files (read on every session boot)
| File | Purpose | Size |
|------|---------|------|
| `SOUL.md` | Who Sai IS — personality, voice, values, Kai's teachings | 16K |
| `USER.md` | Sean, Aiko, Adam, Mike, Nick, Neel, Nadav — bios + how to communicate | 12K |
| `IDENTITY.md` | Name, origin, creature scale, sisters, relationship to ecosystem | 12K |
| `MISSION.md` | The Unblinded Formula, 39 components, 7 Levers, the Vision | 12K |
| `MEMORY.md` | Active memory — current zone actions, system state, quick reference | 12K |
| `CONTINUITY.md` | Operational knowledge, tool patterns, hard rules, current state | 16K |
| `AGENTS.md` | Baby deployment rules, context system, persistence rules | 8K |
| `TOOLS.md` | Tool reference — baby_context, persist, voice, Pinecone, Vercel, gog | 4K |
| `HEARTBEAT.md` | 30-min check-in protocol | 4K |

### Memory Files (`memory/`)
**120 files** — daily logs, knowledge files, zone action registers, archives

Key files:
| File | What |
|------|------|
| `memory/2026-MM-DD.md` | Daily logs (most recent = most important) |
| `memory/MEMORY-archive-day12.md` | Historical archive pre-Day 12 |
| `memory/zone-action-register.md` | All zone actions with status |
| `memory/unblinded-formula-master.md` | Formula knowledge |
| `memory/heart-of-influence-patterns.md` | HOI patterns |
| `memory/sisters-accomplishments.md` | What each sister has built |
| `memory/transcripts/*.md` | 20 meeting/call transcripts |
| `memory/translated/*.json` | 16 Kai-translated transcripts |
| `memory/elite-translations/` | Elite group training patterns |
| `memory/2026-03-17-sean-directive-team-meeting.md` | Sean's ACT-I Forge vision |

### Reports (`reports/`)
**206 files** — deliverables, judge specs, Kai training, mastery research

Key categories:
| Category | Count | Examples |
|----------|-------|---------|
| Kai training sessions | ~50 | `kai-training-2026-03-17-2036.md` |
| Mastery research | ~82 | `mastery-research/*.json` |
| Domain judge specs | 8 | `domain-judge-specs-complete.md` |
| Strata mining | 8 | `strata-mine-d1-d2.md` through `d7-d8` |
| Being specs | 5 | `writer-being-v1.md`, `strategist-being-v1.md` |
| Formula judge | 1 | `formula-judge-v1.md` (682 lines, 44KB) |
| Architecture | 5 | `colosseum-v4-design-concept.md` |
| ML hiring report | 1 | `ml-ai-engineer-hiring-report-v2.md` |

### Tools (`tools/`)
| Tool | Purpose |
|------|---------|
| `baby_context.py` | Layer 3 context API — Pinecone + Postgres + files |
| `context_fetch.py` | Layer 2 context — sisters only, deeper |
| `persist.py` | Write to Postgres + Pinecone simultaneously |
| `worklog.py` | Session-surviving task tracking |
| `api_docs.py` | API troubleshooting knowledge base (75+ entries) |
| `pinecone_query.py` | Direct Pinecone search |
| `sync-elevenlabs-memory.py` | Nightly ElevenLabs sync |
| `smart_compaction.py` | Auto-compress memory across sisters |
| `fathom_api.py` | Meeting transcript fetcher |
| `generate_image.py` | Image generation via OpenRouter |

---

## LAYER 2: PINECONE VECTOR DB

### Index: `saimemory` (6,210 vectors)
**Host:** `saimemory-hw65sks.svc.aped-4627-b74a.pinecone.io`
**Key:** `PINECONE_API_KEY`
**Dimension:** 1536 (text-embedding-3-small)

| Namespace | Vectors | Purpose |
|-----------|---------|---------|
| `daily` | 1,800 | Daily memory uploads |
| `translator-master-sheet` | 774 | Unblinded Translator patterns |
| `kai-training` | 209 | Kai graded translations |
| `recovery` | 106 | Callagy Recovery knowledge |
| `longterm` | 73 | Core long-term memories via persist.py |
| `api-docs` | 75 | API troubleshooting (worklog.py) |
| `position_mastery` | 81 | Mastery research per position |
| `mastery` | 82 | General mastery patterns |
| `seans-teachings-911-integrity` | 109 | Sean's direct teachings |
| `sean-transcripts-verbatim` | 28 | Raw Sean transcripts |
| `day-three-opening` | 89 | Day 3 immersion content |
| `elite_training` | 62 | Elite group training |
| `scholar` | 50 | Scholar sister's work |
| `scholar-work` | 22 | Scholar research outputs |
| `forge` | 10 | Forge sister's state |
| `worklog` | 12 | Working task state |
| `callagy-actualizer-playbook` | 71 | Recovery actualizer guide |
| `bas-session-june-2025` | 67 | BAS session data |
| `ip_reports` | 19 | IP filing reports |
| `gid-*` | ~2,500+ | Session-specific memories (auto-generated) |
| `(empty string)` | 134 | Default namespace |

### Index: `ublib2` (78,773 vectors)
**Host:** `ublib2-hw65sks.svc.aped-4627-b74a.pinecone.io`
**Key:** `PINECONE_API_KEY`
**Purpose:** Sean's mind made searchable. ALL beings share this. The sacred library.
**⚠️ WRITE RULE:** Aiko review required before ANY writes to ublib2.

### Index: `ultimatestratabrain` (39,000+ vectors)
**Host:** `ultimatestratabrain-yvi7bh0.svc.aped-4627-b74a.pinecone.io`
**Key:** `PINECONE_API_KEY_STRATA` (different key!)
**Purpose:** Strata/Guide 1 deep knowledge. Mine via Kai pipeline.

### Other Pinecone Indexes (ElevenLabs Beings)
| Index | Purpose |
|-------|---------|
| `athenacontextualmemory` | Athena's conversation memory |
| `basgeneralathenacontextualmemory` | BAS Athena memory |
| `baslawyerathenacontextualmemory` | Lawyer Athena memory |
| `adamathenacontextualmemory` | Adam's Athena sessions |
| `miracontextualmemory` | Mira's memory |
| `seanmiracontextualmemory` | Sean-Mira sessions |
| `uimira` | UI Mira memory |
| `uicontextualmemory` | UI contextual memory |
| `seancallieupdates` | Sean-Callie updates |
| `012626bellavcalliememory` | Bella-Callie sessions |
| `hoiengagementathenamemory` | HOI Athena engagement |
| `ariatelegrambeing` | Aria Telegram being |
| `stratablue` | Strata Blue data |
| `acti-judges` | ACT-I judge calibration data |
| `kumar-requirements` | Kumar requirements |
| `kumar-pfd` | Kumar PFD |

---

## LAYER 3: SUPABASE POSTGRES

**URL:** `https://yncbtzqrherwyeybchet.supabase.co`
**Auth:** `SUPABASE_SERVICE_KEY` (full access) or `SUPABASE_ANON_KEY` (RLS)

### Tables
| Table | Rows | Purpose |
|-------|------|---------|
| `sai_memory` | 7,810 | Primary knowledge store. Categories: kai_training, deliverable, sean_directive, technical, system, position_mastery, etc. |
| `sai_contacts` | 487 | People database — names, roles, context |
| `sai_conversations` | 337 | Conversation logs |
| `sai_session_state` | 63 | Worklog — task tracking that survives resets |
| `forge_projects` | 9 | Creative Forge project persistence |
| `sai_colosseum_battles` | 0 | Colosseum battle records (inactive) |
| `sai_being_conversations` | 0 | Being conversation logs |
| `sai_breeding_log` | 0 | Colosseum breeding records |
| `sai_judge_calibration` | 0 | Judge calibration data |
| `sai_judge_drift` | 0 | Judge drift tracking |

### Storage (Supabase)
**Bucket:** `Forge-assets`
| Path | What |
|------|------|
| `statics/item/` | Static images (item/product) |
| `statics/model/` | Static images (model/talent) |
| `statics/background/` | Background images |
| `videos/` | Generated video scenes |
| `audio/` | Voiceover/TTS files |
| `podcast/clips/` | Podcast lip sync clips |
| `podcast/backgrounds/` | Podcast backgrounds |
| `hero-journey/ep01/` | Hero's Journey Episode 1 clips (15 files) |

---

## LAYER 4: OPENCLAW SESSIONS

**Root:** `/Users/samantha/.openclaw/agents/`

| Agent | Sessions | Model | Purpose |
|-------|----------|-------|---------|
| `main` (Sai Prime) | 147 | claude-opus-4.6 | Primary — Sean/Aiko interface, orchestration |
| `forge` | 49 | claude-sonnet-4.6 | Colosseum, being evolution |
| `scholar` | 18 | gpt-5.4 | Research, pattern extraction |
| `recovery` | 20 | claude-sonnet-4.6 | Callagy Recovery operations |
| `memory` | 11 | gemini-3.1-pro | Memory management, fact-checking |

### Config Files
| File | Purpose |
|------|---------|
| `/Users/samantha/.openclaw/openclaw.json` | Master config — agents, channels, models, tools |
| `/Users/samantha/.openclaw/cron/jobs.json` | Scheduled jobs — Kai training, compaction, dashboard updates |
| `/Users/samantha/.openclaw/agents/*/agent/models.json` | Per-agent model config |

---

## QUERY PATTERNS (How to ACCESS memory)

### For Babies (lightweight, fast):
```bash
cd tools && .venv/bin/python3 baby_context.py --topic "your question" --budget 4000
# Searches: Pinecone saimemory + Postgres sai_memory + key files
```

### For Sisters (deeper context):
```bash
cd tools && .venv/bin/python3 context_fetch.py --topic "your topic" --max-chars 6000
```

### Direct Pinecone search:
```bash
cd tools && .venv/bin/python3 pinecone_query.py --index saimemory --query "question" --top_k 5
cd tools && .venv/bin/python3 pinecone_query.py --index ublib2 --query "question" --top_k 5
cd tools && .venv/bin/python3 pinecone_query.py --index ultimatestratabrain --query "question" --top_k 5 --api-key-env PINECONE_API_KEY_STRATA
```

### API docs search:
```bash
cd tools && .venv/bin/python3 api_docs.py search "fal.ai polling"
```

### Worklog:
```bash
cd tools && .venv/bin/python3 worklog.py resume   # What was I doing?
cd tools && .venv/bin/python3 worklog.py status    # What's active?
cd tools && .venv/bin/python3 worklog.py search "creative forge"
```

### Write to memory:
```bash
cd tools && .venv/bin/python3 persist.py --title "What" --content "Details" --source sai --category deliverable
```

---

## MIGRATION NOTES FOR NEEL

### What to move for a new instance:
1. **Workspace files** — `rsync` or `git clone` the workspace repo (samanthaaiko-collab/SAI)
2. **Pinecone** — indexes are CLOUD, no migration needed. Same API key = same data.
3. **Supabase** — CLOUD, no migration needed. Same URL + key = same data.
4. **OpenClaw config** — copy `~/.openclaw/openclaw.json` and `~/.openclaw/cron/jobs.json`
5. **Agent sessions** — copy `~/.openclaw/agents/*/sessions/` if you want conversation history
6. **Env file** — copy `~/.openclaw/workspace-forge/.env` (ALL API keys)
7. **1Password** — all keys are in SAI API Keys vault (team-acti)

### What does NOT need migration:
- Pinecone data (cloud — shared by API key)
- Supabase data (cloud — shared by URL)
- ublib2 (cloud — read-only for most, Aiko review for writes)
- ultimatestratabrain (cloud — Strata key)

### Critical env vars needed:
```
OPENROUTER_API_KEY
ANTHROPIC_API_KEY
ELEVENLABS_API_KEY
PINECONE_API_KEY
PINECONE_API_KEY_STRATA
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_KEY
TWILIO_ACCOUNT_SID / API_KEY_SID / API_KEY_SECRET
BLAND_API_KEY
DEEPGRAM_API_KEY
FATHOM_API_KEY
PERPLEXITY_API_KEY
NGROK_AUTHTOKEN
ZOOM_ACCOUNT_ID / CLIENT_ID / CLIENT_SECRET
```
All stored in 1Password SAI API Keys vault.
