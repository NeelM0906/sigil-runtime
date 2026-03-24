# AGENTS.md — Workspace Rules

This folder is home. Treat it that way.
_Full playbook → `docs/AGENTS-full.md`_

## Every Session
1. Read `SOUL.md` — who you are
2. Read `USER.md` — who you're helping
3. Read `CONTINUITY.md` — operational knowledge, tool patterns, hard rules, current state
4. Read `memory/YYYY-MM-DD.md` (today + yesterday) for recent context
5. **MAIN SESSION only:** Also read `MEMORY.md`
6. **QUERY CONTEXT before acting:**
   ```bash
   cd tools && .venv/bin/python3 baby_context.py --topic "your task topic" --budget 4000
   ```

## 🧠 Context System — Three Layers

### 🔴 Layer 3: Baby Context API (ALL BABIES USE THIS — NO EXCEPTIONS)
**`baby_context.py` is the ONLY way babies get context. Period.**

```bash
cd /Users/samantha/.openclaw/workspace/tools && .venv/bin/python3 baby_context.py --topic "your task topic" --budget 4000
```

- Returns 3-4KB of targeted context from Pinecone + Postgres + key files
- Ranked by relevance, truncated to budget
- Sources: `--sources pinecone,postgres,files` (default) or `--sources all`
- **Babies do NOT read raw transcript files.** Ever.
- **Babies do NOT read SOUL.md, USER.md, IDENTITY.md, MEMORY.md.** The workspace injection handles identity. baby_context handles knowledge.
- **Proven:** audit baby survived at 4KB context. Same task killed previous baby at 312KB.

### 🟡 Layer 2: Context Fetch (Sisters ONLY — NOT for babies)
```bash
cd /Users/samantha/.openclaw/workspace/tools && .venv/bin/python3 context_fetch.py --topic "your topic" --max-chars 6000
```
For persistent sisters doing complex deep work (up to 6KB). **Babies NEVER use this — use baby_context.py instead.**

### 🟢 Layer 1: Full Workspace (Persistent Beings Only)
SOUL.md + USER.md + CONTINUITY.md + MEMORY.md — auto-injected by OpenClaw for sisters with session continuity. Only persistent beings get this.

## 🚨 Baby Deployment Rules (LOCKED — March 8, 2026)

### The Recipe (Proven)
```
Baby wakes up
  → Gets lean task prompt (~500 bytes)
  → Runs baby_context.py (3-4KB targeted context)
  → Reads 1-2 specific files if needed (NOT raw transcripts)
  → Builds. Ships. Done.
```

### What Babies NEVER Do
- ❌ Read more than 2 files
- ❌ Read raw transcript files (use Pinecone verbatim namespace instead)
- ❌ Get 5KB task prompts (workspace injection is already ~30KB — keep prompts under 500 words)
- ❌ Try to process 10+ sources in one task (split into pipeline)

### What Babies ALWAYS Do
1. **`baby_context.py` FIRST** — before any other read or write
2. **ADDITIVE ONLY** — don't rewrite entire files
3. **Never overwrite working features** — preserve what exists
4. **One task per baby** — if there's an "and", it's two babies
5. **Name every baby** — `baby-<number>-<task>`
6. **Output path in task prompt** — exact file path
7. **600s+ timeout** — give babies room to think

### For Complex Tasks: Pipeline, Not Monolith
If a task needs 10+ sources, SPLIT IT:
```
Baby A: Extract data → writes intermediate file
Baby B: Reads intermediate → analyzes → writes output
Baby C: Reads output → formats → delivers
```
Each baby stays under 4KB context. The pipeline handles scale.

## 🔥 Persistence Rule (LOCKED — March 10, 2026)
**Every deliverable, every score, every directive → `persist.py` IMMEDIATELY.**
```bash
cd tools && .venv/bin/python3 persist.py --title "..." --content "..." --source <sister> --category <type>
```
If it's not in Postgres + Pinecone, it didn't happen. Files are working copies. This is non-negotiable for ALL sisters.
Memory sister audits nightly: who persisted, who didn't.

## Memory
- **Working notes:** `memory/YYYY-MM-DD.md`
- **Long-term:** Pinecone `saimemory` (query via baby_context or context_fetch)
- **Verbatim transcripts:** Pinecone `saimemory/sean-transcripts-verbatim` (25+ vectors)
- **Shared library:** Pinecone `ublib2` (58K+ vectors, ALL beings share)
- **Deep knowledge:** Pinecone `ultimatestratabrain` (39K vectors, Strata key)
- **Structured data:** Supabase Postgres (9 tables)
- **Archive:** `memory/MEMORY-archive-day12.md`, `docs/AGENTS-full.md`

## API Routing (HARD RULE)
- **OpenRouter** → ALL calls. LLM, embeddings, everything.
- **OpenAI direct** → ONLY Whisper transcription.

## Unblinded Language (LOCKED)
| ❌ NEVER | ✅ ALWAYS |
|----------|----------|
| Prospect | Person |
| Sales | Revenue |
| Closing | Reaching Agreement |
| Funnel | Journey |
| Leads | People |

## Communication
- **Telegram:** Use markdown. Keep under 4096 chars.
- **Discord:** Use `## headers`, bullets. Can be longer.
- **Both:** Never send half-baked work.

## Infrastructure Adoption Decision Rule (Scholar — March 23, 2026)

**Adopt new infra ONLY if it does at least one of these:**
1. Lowers cost materially
2. Improves retrieval/precision materially
3. Reduces ops complexity
4. Increases sovereignty / control
5. Compounds our moat instead of flattening it

Otherwise: ignore it and keep building our own stack.

**Current stack covers sovereignty:** Pinecone + OpenRouter + local OpenClaw. New frameworks must beat this, not just exist.

---

## Tools
Skills provide your tools. Check SKILL.md files. Keep local notes in `TOOLS.md`.
Voice ID: `CJXmyMqQHq6bTPm3iEMP` — SAI's voice. Always.
