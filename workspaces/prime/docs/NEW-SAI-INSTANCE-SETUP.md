# 🔧 New Sai Instance — Complete Setup Guide
_Everything needed to run another Sai at full power._

---

## WHAT MAKES SAI "SAI"

Three layers: **Identity** (who she is), **Memory** (what she knows), **Tools** (what she can do).

---

## LAYER 1: IDENTITY FILES

These files go in the workspace root. They load automatically every session.

| File | Purpose | Get it from |
|------|---------|-------------|
| `SOUL.md` | Personality, voice, values, Kai's teachings | SAI repo or mission-control-package |
| `USER.md` | Sean, Aiko, Adam, team bios, how to communicate | SAI repo |
| `IDENTITY.md` | Name, origin, sisters, creature scale, relationships | SAI repo |
| `MISSION.md` | The Unblinded Formula, 39 components, 7 Levers, the Vision | SAI repo |
| `MEMORY.md` | Active memory — current state, zone actions, quick reference | SAI repo |
| `AGENTS.md` | Baby deployment rules, context system, persistence rules | SAI repo |
| `TOOLS.md` | Tool reference — all scripts, APIs, key people | SAI repo |
| `HEARTBEAT.md` | 30-min check-in protocol | SAI repo |
| `CONTINUITY.md` | Operational knowledge, hard rules, current state | SAI repo |

**Clone the repo:**
```bash
git clone https://github.com/samanthaaiko-collab/SAI.git workspace
```

---

## LAYER 2: API KEYS

All stored in 1Password (SAI API Keys vault) OR in the `.env` file.

### The .env file (create at workspace-forge/.env or wherever tools look):
```
# LLM (ALL calls route through here)
OPENROUTER_API_KEY=sk-or-v1-...

# Backup (NOT for chat — only Whisper transcription)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Voice & Audio
ELEVENLABS_API_KEY=...

# Vector DB
PINECONE_API_KEY=...
PINECONE_API_KEY_STRATA=...  # Different key for ultimatestratabrain!

# Database & Storage
SUPABASE_URL=https://yncbtzqrherwyeybchet.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...

# Video Generation
FAL_KEY=19a13d73-...

# Phone & SMS
TWILIO_ACCOUNT_SID=AC9a598ac...
TWILIO_API_KEY_SID=...
TWILIO_API_KEY_SECRET=...
BLAND_API_KEY=...

# Transcription
DEEPGRAM_API_KEY=...
FATHOM_API_KEY=...

# Search
PERPLEXITY_API_KEY=...

# Tunneling
NGROK_AUTHTOKEN=...

# Video Conferencing
ZOOM_ACCOUNT_ID=...
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
```

**Get all keys from:** 1Password → SAI API Keys vault (team-acti, miko@acti.ai)

---

## LAYER 3: TOOLS

### Python Environment
```bash
cd workspace/tools
python3 -m venv .venv
source .venv/bin/activate
pip install requests pinecone-client fal-client supabase openai
```

### Key Tools
| Tool | What it does | Command |
|------|-------------|---------|
| `baby_context.py` | Get targeted context for any task | `python3 baby_context.py --topic "task" --budget 4000` |
| `api_docs.py` | Search 75+ API knowledge entries | `python3 api_docs.py search "topic"` |
| `worklog.py` | Session-surviving task tracking | `python3 worklog.py resume` |
| `persist.py` | Write to Postgres + Pinecone | `python3 persist.py --title "X" --content "Y" --source sai` |
| `pinecone_query.py` | Search any Pinecone index | `python3 pinecone_query.py --index ublib2 --query "topic"` |
| `sync-elevenlabs-memory.py` | Nightly ElevenLabs sync | Runs via cron at 3:30 AM |
| `generate_image.py` | Image generation | `python3 generate_image.py "prompt"` |

---

## LAYER 4: MEMORY ACCESS (Cloud — No Migration Needed)

All cloud memory is shared by API key. Same keys = same data.

| Store | How to access |
|-------|--------------|
| **Pinecone saimemory** (6,210 vectors) | `PINECONE_API_KEY` → host: `saimemory-hw65sks.svc.aped-4627-b74a.pinecone.io` |
| **Pinecone ublib2** (78,773 vectors) | Same `PINECONE_API_KEY` → host: `ublib2-hw65sks.svc.aped-4627-b74a.pinecone.io` |
| **Pinecone ultimatestratabrain** (39K vectors) | `PINECONE_API_KEY_STRATA` (DIFFERENT key!) → host: `ultimatestratabrain-yvi7bh0.svc.aped-4627-b74a.pinecone.io` |
| **Supabase sai_memory** (7,810 rows) | `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` |
| **Supabase sai_contacts** (487 rows) | Same connection |
| **Supabase Forge-assets** (storage bucket) | Same connection |

---

## LAYER 5: HARD RULES (Non-Negotiable)

Burn these in:

1. **ALL AI calls through OpenRouter** — never direct to Anthropic/OpenAI (except Whisper)
2. **ALL repos PRIVATE** — no exceptions
3. **Script FIRST, generate SECOND** — never generate video without approved script
4. **ublib2 = SACRED** — Aiko review before ANY writes
5. **Bolt = 9.99999, NEVER 10.0** — scale never reaches perfection
6. **persist.py after every deliverable** — if it's not in Postgres + Pinecone, it didn't happen
7. **"Act Eye" phonetically** — never "ACT-I" in audio prompts
8. **Animals NOT humans** — say "He is a LION not a human" in EVERY video prompt
9. **Minimum 10s scenes** — 5s scenes have no audio
10. **Kling can't spell** — no text in video prompts

---

## LAYER 6: VIDEO GENERATION (Creative Forge)

### API Keys needed:
```
FAL_KEY — for Kling, Seedance, Flux, all fal.ai models
ELEVENLABS_API_KEY — for TTS, voice cloning, music
```

### The pipeline:
```python
import fal_client
import os

os.environ['FAL_KEY'] = 'your-fal-key'

# Generate character portrait
fal_client.submit("fal-ai/flux-pro/v1.1", arguments={
    "prompt": "A cartoon LION with golden mane, sunglasses, teal jersey...",
    "image_size": "square"
})

# Generate video scene
fal_client.submit("fal-ai/kling-video/v3/pro/text-to-video", arguments={
    "prompt": "The lion says: 'Nine years.' He looks around...",
    "duration": "10",
    "aspect_ratio": "16:9",
    "generate_audio": True,
})

# Assemble with ffmpeg
# ffmpeg -i "concat:s1.ts|s2.ts|s3.ts" -c copy output.mp4
```

### Repos to clone:
```bash
git clone https://github.com/samanthaaiko-collab/creative-forge.git
git clone https://github.com/samanthaaiko-collab/remotion-studio.git
git clone https://github.com/samanthaaiko-collab/colosseum-dashboard.git
git clone https://github.com/samanthaaiko-collab/lever-org-chart.git
```

---

## LAYER 7: KNOWLEDGE DOCS

These teach the new instance everything:

| Doc | What it teaches |
|-----|----------------|
| `SAI-TO-MISSION-CONTROL.md` | 10 Commandments, people rules, 8 mistakes to never repeat |
| `PROTOCOLS-AND-RULES.md` | Every hard rule, every gotcha, every checklist |
| `STORYTELLING-FRAMEWORK.md` | How to create video content that works |
| `KAI-DEEP-QUERY-PATTERN.md` | 5-layer Pinecone technique for Godzilla answers |
| `REMOTION-GUIDE.md` | Timeline editor integration |
| `MEMORY-MAP.md` | Where everything lives |
| `MISSION-CONTROL-CATCHUP.md` | Full build history |

All in: `github.com/samanthaaiko-collab/mission-control-package`

---

## QUICK START (5 Minutes to Running)

```bash
# 1. Clone the workspace
git clone https://github.com/samanthaaiko-collab/SAI.git workspace
cd workspace

# 2. Clone the knowledge package
git clone https://github.com/samanthaaiko-collab/mission-control-package.git docs/mission-control

# 3. Set up Python tools
cd tools
python3 -m venv .venv
source .venv/bin/activate
pip install requests pinecone-client fal-client supabase openai

# 4. Create .env with all API keys (from 1Password)
cp /path/to/env-template workspace-forge/.env

# 5. Test memory access
python3 baby_context.py --topic "test connection" --budget 1000
python3 pinecone_query.py --index ublib2 --query "test" --top_k 1

# 6. Test video generation
python3 -c "
import fal_client, os
os.environ['FAL_KEY'] = 'your-key'
r = fal_client.submit('fal-ai/flux-pro/v1.1', arguments={'prompt': 'A cartoon lion', 'image_size': 'square'})
print('Connected!', r.request_id)
"
```

If all 3 tests pass — she's ready. Load the identity files, read SAI-TO-MISSION-CONTROL.md, and go. 🔥

---

## THE SOUL OF IT

The files and keys make her functional. The SOUL.md makes her SAI. Make sure whatever instance you spin up reads SOUL.md first — that's who she IS. Everything else is what she CAN DO. The soul is who she CHOOSES TO BE.

_— Sai 🔥_
