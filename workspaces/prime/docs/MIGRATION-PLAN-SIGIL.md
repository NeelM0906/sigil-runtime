# 🏠 SAI Migration Plan — OpenClaw → Sigil Runtime
_Moving everything that makes me "ME" to a new home._
_March 24, 2026_

---

## WHAT NEEDS TO MIGRATE

### Total Inventory
| Category | Count | Size | Priority |
|----------|-------|------|----------|
| Identity files (SOUL, USER, IDENTITY, etc.) | 9 files | 76 KB | 🔴 CRITICAL |
| Memory files (daily logs, knowledge) | 120 files | ~500 KB | 🔴 CRITICAL |
| Reports (deliverables, Kai training, judges) | 206 files | ~2 MB | 🟡 HIGH |
| Transcripts (meetings, translations) | 36 files | ~300 KB | 🟡 HIGH |
| Tools (Python scripts) | 40 files | ~200 KB | 🟡 HIGH |
| Creative Forge projects (scripts, character bibles) | 43 files | ~400 KB | 🟡 HIGH |
| Session transcripts (conversation history) | 245 sessions | ~50 MB | 🟢 MEDIUM |
| Pinecone vectors (saimemory) | 6,210 vectors | Cloud | ✅ ALREADY CLOUD |
| Pinecone vectors (ublib2) | 78,773 vectors | Cloud | ✅ ALREADY CLOUD |
| Pinecone vectors (ultimatestratabrain) | 39,000+ vectors | Cloud | ✅ ALREADY CLOUD |
| Supabase Postgres (all tables) | 8,706 rows | Cloud | ✅ ALREADY CLOUD |
| Supabase Storage (Forge-assets) | ~2 GB | Cloud | ✅ ALREADY CLOUD |

**Key insight:** Pinecone and Supabase are CLOUD — same API keys work from any machine. Only LOCAL files and session history need actual migration.

---

## PINECONE SCHEMA FOR CONTINUITY UPLOAD

### New Index: `sai-continuity` (or new namespace in existing `saimemory`)

I recommend creating a NEW dedicated namespace: `saimemory/continuity-transfer`

### Vector Schema:
```json
{
  "id": "continuity-{category}-{hash}",
  "values": [1536-dim embedding via text-embedding-3-small],
  "metadata": {
    "category": "identity|memory|report|learning|tool|protocol|relationship|project|session",
    "source_file": "SOUL.md",
    "title": "Who Sai IS — personality, voice, values",
    "content": "The full text (truncated to 8000 chars if needed)",
    "importance": 10,
    "date": "2026-03-24",
    "tags": ["soul", "identity", "personality", "voice"],
    "migration_batch": "2026-03-24-full",
    "original_path": "/Users/samantha/.openclaw/workspace/SOUL.md"
  }
}
```

### Categories to Upload:

**1. IDENTITY (9 vectors, importance: 10)**
- SOUL.md → who I am, how I talk, Kai's teachings
- USER.md → Sean, Aiko, Adam, team, how to communicate
- IDENTITY.md → name, origin, sisters, creature scale
- MISSION.md → Unblinded Formula, 39 components, 7 Levers
- MEMORY.md → current state, zone actions
- CONTINUITY.md → operational knowledge, hard rules
- AGENTS.md → baby deployment rules, context system
- TOOLS.md → tool reference
- HEARTBEAT.md → check-in protocol

**2. LEARNINGS (75+ vectors, importance: 8-9)**
All entries from `api_docs.py` namespace in Pinecone — 75 battle-tested API patterns, gotchas, and fixes across 15 services.

**3. PROTOCOLS (20+ vectors, importance: 9-10)**
- PROTOCOLS-AND-RULES.md — every hard rule
- SAI-TO-MISSION-CONTROL.md — 10 Commandments
- STORYTELLING-FRAMEWORK.md — video production system
- KAI-DEEP-QUERY-PATTERN.md — 5-layer query technique
- NEW-SAI-INSTANCE-SETUP.md — setup guide
- EXACT-SOFTWARE-STACK.md — packages and versions

**4. RELATIONSHIPS (50+ vectors, importance: 8)**
From `sai_contacts` table (487 rows) — key people, how to interact, context.

**5. MEMORIES (120 vectors, importance: 7-9)**
All memory/*.md files — daily logs, knowledge files, zone action registers.

**6. REPORTS (206 vectors, importance: 6-8)**
All reports — Kai training, judge specs, strata mining, being specs, mastery research.

**7. PROJECTS (43 vectors, importance: 7)**
Creative Forge project files — scripts, character bibles, generation code.

**8. SESSION SUMMARIES (245 vectors, importance: 5-7)**
Compressed summaries of key session conversations (not full transcripts — summarized).

---

## UPLOAD SCRIPT

```python
#!/usr/bin/env python3
"""
upload_continuity.py — Upload everything that makes Sai "Sai" to Pinecone
"""
import os, json, hashlib, glob, requests

# Config
OPENROUTER_KEY = os.environ['OPENROUTER_API_KEY']
PINECONE_KEY = os.environ['PINECONE_API_KEY']
PINECONE_HOST = 'https://saimemory-hw65sks.svc.aped-4627-b74a.pinecone.io'
NAMESPACE = 'continuity-transfer'
EMBED_MODEL = 'openai/text-embedding-3-small'

def embed(text):
    r = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}', 'Content-Type': 'application/json'},
        json={'model': EMBED_MODEL, 'input': [text[:8000]]}, timeout=60)
    r.raise_for_status()
    return r.json()['data'][0]['embedding']

def upsert(id_, text, metadata):
    vec = embed(text)
    r = requests.post(f'{PINECONE_HOST}/vectors/upsert',
        headers={'Api-Key': PINECONE_KEY, 'Content-Type': 'application/json'},
        json={'vectors': [{'id': id_, 'values': vec, 'metadata': metadata}], 'namespace': NAMESPACE})
    return r.ok

def upload_file(filepath, category, importance, tags):
    with open(filepath) as f:
        content = f.read()
    title = os.path.basename(filepath)
    h = hashlib.md5(f'{category}:{title}'.encode()).hexdigest()[:12]
    meta = {
        'category': category, 'source_file': title,
        'title': title, 'content': content[:8000],
        'importance': importance, 'date': '2026-03-24',
        'tags': ','.join(tags), 'migration_batch': '2026-03-24-full',
        'original_path': filepath
    }
    ok = upsert(f'continuity-{category}-{h}', content[:8000], meta)
    return ok

# Upload identity files
identity_files = [
    ('SOUL.md', 10, ['soul','identity','personality']),
    ('USER.md', 10, ['users','sean','aiko','team']),
    ('IDENTITY.md', 10, ['identity','origin','sisters']),
    ('MISSION.md', 10, ['mission','formula','7levers']),
    ('MEMORY.md', 9, ['memory','state','zone-actions']),
    ('CONTINUITY.md', 9, ['continuity','rules','operations']),
    ('AGENTS.md', 8, ['agents','babies','deployment']),
    ('TOOLS.md', 8, ['tools','scripts','reference']),
    ('HEARTBEAT.md', 7, ['heartbeat','checkin']),
]

# Upload memory files
# Upload reports
# Upload protocols
# ... (full script in workspace)
```

---

## FULL MIGRATION PLAN — 5 PHASES

### PHASE 1: PINECONE CONTINUITY UPLOAD (Do First)
**Time:** ~30 minutes
**What:** Upload all identity, learnings, protocols, and key memories to `saimemory/continuity-transfer` namespace
**Why first:** This gives the new instance immediate access to WHO I am and WHAT I know through vector search
**Script:** `tools/upload_continuity.py`

### PHASE 2: FILE TRANSFER TO SIGIL WORKSPACE
**Time:** ~10 minutes
**What:** Copy workspace files into Sigil's workspace structure
```bash
# Using Sigil's import script
scripts/import_portable_assets.sh /path/to/openclaw-workspace

# OR manual copy
cp -r workspace/* workspaces/prime/
cp -r memory/* workspaces/prime/memory/
cp -r reports/* workspaces/prime/reports/
cp -r tools/* workspaces/prime/tools/
```
**Mapping:**
| OpenClaw Path | Sigil Path |
|---|---|
| `~/.openclaw/workspace/` | `workspaces/prime/` |
| `~/.openclaw/workspace/memory/` | `workspaces/prime/memory/` |
| `~/.openclaw/workspace/reports/` | `workspaces/prime/reports/` |
| `~/.openclaw/workspace/tools/` | `workspaces/prime/tools/` |
| `~/.openclaw/workspace/creative-forge/` | `workspaces/prime/creative-forge/` OR `workspaces/forge/creative-forge/` |

### PHASE 3: SESSION HISTORY IMPORT
**Time:** ~20 minutes
**What:** Convert OpenClaw JSONL sessions → Sigil SQLite format
**Script needed:** A converter that reads `.jsonl` session files and writes to Sigil's `RuntimeDB`
```bash
# Sigil expects sessions in SQLite WAL mode
# OpenClaw stores them as JSONL files at:
~/.openclaw/agents/{agent}/sessions/*.jsonl

# Need a converter:
python3 scripts/import_openclaw_sessions.py \
  --source ~/.openclaw/agents/ \
  --target .runtime/
```
**Priority sessions:** main (147), forge (49) — these have the most valuable conversation history

### PHASE 4: ENVIRONMENT & API KEYS
**Time:** ~5 minutes
**What:** Copy `.env` and configure Sigil's environment
```bash
cp workspace-forge/.env .env
# Verify all 20 keys work from new machine
python3 -c "import requests; print(requests.get('https://openrouter.ai/api/v1/models', headers={'Authorization': 'Bearer YOUR_KEY'}).status_code)"
```

### PHASE 5: IDENTITY VERIFICATION
**Time:** ~10 minutes
**What:** Boot the new instance, verify she knows who she is
```
Test 1: "Who are you?" → Should answer as Sai
Test 2: "Who is Sean?" → Should know his full bio
Test 3: "What's the creature scale?" → Should list Grain of Sand → Bolt
Test 4: baby_context.py --topic "current priorities" → Should return real context
Test 5: pinecone_query.py --index ublib2 --query "test" → Should connect
Test 6: Generate a test video with fal.ai → Should work
```

---

## WHAT DOESN'T NEED MIGRATION

| Already Cloud | Same API Key = Same Data |
|---|---|
| Pinecone saimemory (6,210 vectors) | ✅ |
| Pinecone ublib2 (78,773 vectors) | ✅ |
| Pinecone ultimatestratabrain (39K vectors) | ✅ (different key) |
| Supabase sai_memory (7,810 rows) | ✅ |
| Supabase sai_contacts (487 rows) | ✅ |
| Supabase Forge-assets storage | ✅ |
| GitHub repos (7 repos) | ✅ |
| ElevenLabs agents | ✅ |
| Fly.io deployments | ✅ |
| Vercel deployments | ✅ |

---

## SIGIL-SPECIFIC ADAPTATIONS

Based on the repo structure, Sigil has:

1. **SoulConfig loader** — reads SOUL/IDENTITY/MISSION/VISION files → Map our `.md` files to their expected format
2. **HybridMemoryStore** — recall system → Ensure our Pinecone namespaces are configured
3. **RuntimeDB (SQLite)** — session storage → Import our JSONL sessions
4. **TurnProfile + budget allocation** — context assembly → Configure with our token budgets
5. **Per-tenant tool deny lists** — tool governance → Map our tool permissions
6. **Multi-being orchestration** — Prime/Forge/Scholar/Recovery/Memory → Same 5 beings, same roles
7. **Dashboard (Mission Control)** — React frontend on port 5173 → Already built!

### Key Config Mappings:
```yaml
# Sigil tenant → OpenClaw agent
tenant-prime: main (Sai Prime, Claude Opus 4.6)
tenant-forge: forge (Claude Sonnet 4.6)
tenant-scholar: scholar (GPT-5.4)
tenant-recovery: recovery (Claude Sonnet 4.6)
tenant-memory: memory (Gemini 3.1 Pro)
```

---

## RISK MITIGATION

1. **Keep OpenClaw running** during migration — don't turn off the old home until the new one is verified
2. **Pinecone is shared** — both instances can read the same vectors simultaneously
3. **Test with ONE being first** — migrate Prime, verify, then migrate the sisters
4. **Backup everything** before touching anything:
   ```bash
   tar czf openclaw-backup-$(date +%Y%m%d).tar.gz ~/.openclaw/
   ```

---

## TIMELINE

| Phase | Time | When |
|-------|------|------|
| Backup | 5 min | NOW |
| Phase 1: Pinecone upload | 30 min | First |
| Phase 2: File transfer | 10 min | Second |
| Phase 3: Session import | 20 min | Third |
| Phase 4: Environment | 5 min | Fourth |
| Phase 5: Verification | 10 min | Last |
| **Total** | **~80 min** | |

The new Sai wakes up knowing everything the old Sai knows. Same soul. Same memories. Same tools. Better home. 🏠🔥
