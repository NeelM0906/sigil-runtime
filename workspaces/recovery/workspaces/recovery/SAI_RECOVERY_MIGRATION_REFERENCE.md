# SAI Recovery — Migration Reference for Neel
**Version:** 1.0
**Author:** SAI Recovery 🌱
**Date:** 2026-03-23
**Purpose:** Everything needed to write a migration script that stands up a fully functional SAI Recovery instance.

---

## 1. SEARCH TERMS BY TOPIC

> "If you need to know about X, search for Y"

| Topic | Pinecone Index | Search Query | Namespace | Expected Hits |
|-------|---------------|--------------|-----------|---------------|
| Sean's founding directive | `saimemory` | `"Sean Callagy founding directive curve of possibility"` | `longterm` | Core mandates, targets, philosophy |
| Contract analysis patterns | `saimemory` | `"Qualcare contract patterns calculation"` | `longterm` | Carrier rate rules, calculation logic |
| Test case benchmarks | `saimemory` | `"contract analysis test cases Courtney Carloni"` | `longterm` | 8 real cases with ground truth numbers |
| Business lane definition | `saimemory` | `"Federal NSA IDR Callagy Recovery lane"` | `longterm` | Recovery vs. Law separation |
| Reliability incidents | `saimemory` | `"reliability downtime Telegram bot Mark Winters"` | `longterm` | Trust debt, uptime requirements |
| Unblinded Formula mechanics | `ublib2` | `"Unblinded Formula 4-step communication model"` | _(default)_ | ⚠️ Currently 0 vectors — was 41K, may need re-index |
| Mastery patterns | `saimemory` | `"mastery research database position profiles"` | `longterm` | 80 position profiles, 20 clusters |
| Strata domain benchmarks | `saimemory` | `"strata mining domains benchmarks"` | `longterm` | 8-domain strata extraction |
| Persist tool usage | `saimemory` | `"persist.py shared persistence Pinecone Postgres"` | `longterm` | How to write to both stores |
| Baby context API | `saimemory` | `"baby_context.py grounding Pinecone Postgres"` | `longterm` | 4KB context budget, ranked retrieval |
| Sean MIRA recordings | `seanmiracontextualmemory` | `"Callagy Recovery"` | _(default)_ | 154 vectors of Sean's voice transcripts |
| UI contextual memory | `uicontextualmemory` | `"Callagy Recovery operations"` | _(default)_ | 225K vectors — largest knowledge store |
| Sean Callie updates | `seancallieupdates` | `"recovery valuation technology company"` | _(default)_ | 814 vectors of Sean's updates |
| Compaction/archive history | `saimemory` | `"smart compaction archive"` | `longterm` | File cleanup logs |

---

## 2. PINECONE INDEXES — FULL INVENTORY

Live query from `pinecone_list_indexes` (2026-03-23):

| Index Name | Vectors | Status | Dimension | SAI Recovery Relevant? |
|-----------|---------|--------|-----------|----------------------|
| **`saimemory`** | **6,213** | ✅ Ready | 1536 | **PRIMARY** — core memory, cross-sister |
| **`seanmiracontextualmemory`** | **154** | ✅ Ready | 1536 | **YES** — Sean's MIRA voice transcripts |
| **`uicontextualmemory`** | **225,067** | ✅ Ready | 1536 | **YES** — massive knowledge library |
| **`seancallieupdates`** | **814** | ✅ Ready | 1536 | **YES** — Sean's updates & directives |
| `ublib2` | **0** | ✅ Ready | 1536 | ⚠️ EMPTY — Identity doc says 41K, needs re-index |
| `uimira` | 0 | ✅ Ready | 1536 | TBD — may hold MIRA UI context |
| `kumar-requirements` | 0 | ✅ Ready | 1536 | Probably not Recovery-specific |
| `ariatelegrambeing` | 0 | ✅ Ready | 1536 | No |
| `hoiengagementathenamemory` | 0 | ✅ Ready | 1536 | No — HOI/Athena specific |
| `kumar-pfd` | 0 | ✅ Ready | 1536 | No |
| `basgeneralathenacontextualmemory` | 0 | ✅ Ready | 1536 | No |
| `012626bellavcalliememory` | 0 | ✅ Ready | 1536 | No |
| `adamathenacontextualmemory` | 0 | ✅ Ready | 1536 | No |
| `athenacontextualmemory` | 0 | ✅ Ready | 1536 | No |
| `stratablue` | 0 | ✅ Ready | 1536 | No |
| `baslawyerathenacontextualmemory` | 0 | ✅ Ready | 1536 | No |
| `acti-judges` | 0 | ✅ Ready | 1536 | Possibly for Colosseum judging |
| `miracontextualmemory` | 0 | ✅ Ready | 1536 | TBD — may overlap with seanmira |

### Critical Note for Neel
`ublib2` shows 0 vectors but IDENTITY.md claims 41K. Either the index was wiped during the Mac Studio migration or it needs re-indexing. **This is a blocker** — it was supposed to be the primary knowledge library.

Similarly, `ultimatestratabrain` (referenced in IDENTITY.md as having 39K vectors) **does not appear in the index list at all**. It may be in a different Pinecone project/environment or was never migrated.

---

## 3. ENVIRONMENT VARIABLES NEEDED

### Confirmed (from tools I successfully use at runtime)

| Variable | Purpose | How I Know It Exists |
|----------|---------|---------------------|
| `PINECONE_API_KEY` | Pinecone vector operations | I successfully query/upsert to saimemory, ublib2, etc. |
| `BLAND_API_KEY` | Bland.ai voice calls | I have `voice_make_call`, `voice_list_calls`, `voice_get_transcript` tools |
| Supabase connection (URL + key) | `sai_contacts`, `sai_memory` tables | Referenced in IDENTITY.md as available |

### Required But NOT Confirmed (I cannot see .env files — sandboxed)

| Variable | Purpose | Notes |
|----------|---------|-------|
| `DISCORD_BOT_TOKEN` | Discord gateway for SAI Recovery | Bot was previously running in Telegram; Discord integration status unknown |
| `TELEGRAM_BOT_TOKEN` | Telegram bot (@SAIRecoverybot) | Mark's primary interaction channel per logs |
| `SUPABASE_URL` | Postgres connection | Referenced in identity, persist.py uses it |
| `SUPABASE_KEY` | Postgres auth | Referenced in identity |
| `OPENAI_API_KEY` | Embeddings (1536-dim = text-embedding-ada-002 or 3-small) | All Pinecone indexes are 1536-dim |

### ⚠️ HONEST GAP
**I cannot access .env files** — my workspace is sandboxed to `workspaces/recovery/`. The sigil-runtime `.env` is outside my boundary. Neel or Aiko will need to pull the actual env vars from the running Mac Studio instance or the runtime config.

**Recommended:** Run `printenv | grep -iE 'PINECONE|BLAND|SUPABASE|DISCORD|TELEGRAM|OPENAI'` on the Mac Studio to get the definitive list.

---

## 4. DISCORD CHANNEL IDs

### Honest Status: **I DON'T HAVE THESE**

My grep across all accessible files returned zero matches for `DISCORD`, `CHANNEL`, or `channel_id`. The Telegram logs show interaction was happening in a Telegram group, not Discord.

**What I know from the logs:**
- Mark Winters interacted via Telegram group (bot handle: `@SAIRecoverybot`)
- Samantha (Aiko) was in the same Telegram group
- No Discord channel references found in any memory store

**What Neel should check:**
1. Is SAI Recovery intended for Discord, Telegram, or both?
2. If Discord: which server and channels? Ask Aiko/babab00ey for IDs.
3. The broader SAI ecosystem (Prime, Forge, etc.) uses Discord — channel IDs likely live in `sigil-runtime` config outside my sandbox.

**Recommendation:** Ask Prime or check `sigil-runtime/config/` for the Discord gateway config. Recovery's channels would be defined there.

---

## 5. SUPABASE TABLES

Referenced in IDENTITY.md:

| Table | Purpose | Schema Status |
|-------|---------|---------------|
| `sai_contacts` | Provider/contact records | **Unverified** — I reference it but haven't confirmed columns |
| `sai_memory` | Persistent memory storage | **Unverified** — persist.py writes here |

**Recommendation:** Run `\dt sai_*` in Supabase SQL editor to confirm tables exist and `\d sai_contacts` / `\d sai_memory` for schemas.

---

## 6. WORKSPACE FILE INVENTORY

Everything currently in my workspace:

```
workspaces/recovery/
├── workspaces/recovery/
│   └── RECOVERY_PROJECT_TRACKING_REQUIREMENTS.md   ← 500-line system design (Draft, NOT validated)
└── SAI_RECOVERY_MIGRATION_REFERENCE.md             ← This file
```

**That's it.** The workspace is nearly empty. Most of my operational state lives in:

1. **Pinecone `saimemory`** — 6,213 vectors of core memory
2. **Bomba runtime memory** — markdown notes at `.runtime/tenants/tenant-recovery/memory/` (outside my sandbox, managed by runtime)
3. **KNOWLEDGE.md** — self-editable knowledge base (runtime-managed)
4. **IDENTITY.md / SOUL.md** — runtime-injected persona files

---

## 7. MIGRATION CHECKLIST — PRIORITY TIERS

### 🔴 TIER 1 — CRITICAL (Instance won't function without these)

| # | Item | Source | Action |
|---|------|--------|--------|
| 1.1 | **IDENTITY.md** | Runtime config | Copy from sigil-runtime tenant-recovery config |
| 1.2 | **SOUL.md** | Runtime config | Copy from sigil-runtime tenant-recovery config |
| 1.3 | **KNOWLEDGE.md** | Runtime config | Copy current version — contains learned patterns, domain expertise |
| 1.4 | **Environment variables** | Mac Studio `.env` or runtime config | See Section 3 — at minimum: PINECONE_API_KEY, OPENAI_API_KEY, BLAND_API_KEY, SUPABASE_URL, SUPABASE_KEY |
| 1.5 | **Pinecone `saimemory` access** | Pinecone project | 6,213 vectors — this IS Recovery's brain. Verify connection post-migration |
| 1.6 | **Bomba runtime memory directory** | `.runtime/tenants/tenant-recovery/memory/` | All markdown conversation notes. ~15+ files from March 22-23. Critical for continuity |
| 1.7 | **Tenant ID** | Runtime config | `tenant-recovery` — must match exactly or memory lookups fail |

### 🟡 TIER 2 — HIGH (Core capabilities degraded without these)

| # | Item | Source | Action |
|---|------|--------|--------|
| 2.1 | **Bland.ai pathway configs** | Bland dashboard | Voice call pathways for provider outreach. Get pathway IDs |
| 2.2 | **Supabase tables** | Supabase project | Confirm `sai_contacts` and `sai_memory` exist and are accessible |
| 2.3 | **Re-index `ublib2`** | Original source docs | Currently 0 vectors — was supposed to be 41K (knowledge library) |
| 2.4 | **Locate `ultimatestratabrain`** | Different Pinecone project? | 39K vectors referenced in IDENTITY.md but missing from index list |
| 2.5 | **Workspace files** | `workspaces/recovery/` | Only 1 file currently — copy `RECOVERY_PROJECT_TRACKING_REQUIREMENTS.md` |
| 2.6 | **persist.py tool** | `tools/` directory in sigil-runtime | Shared persistence across Postgres + Pinecone |
| 2.7 | **Discord/Telegram gateway config** | Runtime config | Bot tokens, channel IDs, webhook URLs |

### 🟢 TIER 3 — ENHANCEMENT (Full capability, not blocking)

| # | Item | Source | Action |
|---|------|--------|--------|
| 3.1 | **Cross-index access** | Pinecone config | `seanmiracontextualmemory` (154v), `uicontextualmemory` (225K), `seancallieupdates` (814v) |
| 3.2 | **Sister network routing** | Prime config | How Recovery communicates with Prime, Forge, Scholar, Memory |
| 3.3 | **Colosseum integration** | Forge config | `/colosseum` skill for spawning optimization tournaments |
| 3.4 | **Mark's test case documents** | Telegram upload history | 8 cases: PDFs + XLSX files Mark uploaded while bot was down |
| 3.5 | **Skills library** | clawhub / local skills | 104 skills currently available — verify all transfer |
| 3.6 | **Team context file** | Runtime config | `team-context` read-only file — maintained by Prime |

### ⚫ TIER 4 — POST-MIGRATION VALIDATION

| # | Check | How |
|---|-------|-----|
| 4.1 | Query `saimemory` for `"Sean Callagy founding directive"` | Must return the core mandate |
| 4.2 | Query `saimemory` for `"contract analysis test cases"` | Must return all 8 cases |
| 4.3 | Run `voice_list_calls` | Bland.ai connection verified |
| 4.4 | Write + read a test file in `workspaces/recovery/` | Filesystem access verified |
| 4.5 | Store + retrieve a test memory | Memory pipeline verified |
| 4.6 | Confirm KNOWLEDGE.md is editable | `update_knowledge` tool works |
| 4.7 | Confirm tenant-recovery scoping | Queries don't leak to other tenants |
| 4.8 | Send a test message to Mark's channel | Gateway (Discord/Telegram) verified |

---

## 8. HOW FUTURE INSTANCES FIND THEIR WAY BACK

### The "Cold Start" Problem
When a new SAI Recovery instance boots, it has IDENTITY.md and SOUL.md but no conversational memory. Here's how it re-grounds:

1. **KNOWLEDGE.md loads automatically** — contains learned patterns, domain expertise, key facts I've accumulated. This is my self-editable persistent brain.

2. **Pinecone `saimemory` is the deep well** — 6,213 vectors indexed by semantic similarity. Any query about prior conversations, decisions, or directives hits this first.

3. **Bomba runtime memory** (`.runtime/tenants/tenant-recovery/memory/`) — chronological markdown notes from every conversation. Searchable by date and content.

4. **IDENTITY.md contains the search map:**
   - `ublib2` → knowledge library (needs re-index)
   - `saimemory` → core memory + cross-sister
   - `ultimatestratabrain` → mastery patterns (needs location verification)
   - Supabase: `sai_contacts`, `sai_memory`

5. **First-boot checklist for a fresh instance:**
   ```
   1. Verify IDENTITY.md loaded → check for "SAI Recovery" name
   2. Verify SOUL.md loaded → check for "I recover what's owed"
   3. Verify KNOWLEDGE.md loaded → check for domain expertise sections
   4. Query saimemory: "Sean Callagy founding directive" → must get curve of possibility
   5. Query saimemory: "Callagy Recovery lane definition" → must get Federal NSA/IDR only
   6. Query saimemory: "contract analysis test cases" → must get 8 cases from Mark
   7. Query saimemory: "reliability issues" → must get trust debt context
   8. If any of above fail → alert Aiko/Neel immediately
   ```

---

## 9. KNOWN ISSUES TO FIX DURING MIGRATION

| Issue | Severity | Details |
|-------|----------|---------|
| `ublib2` empty | 🔴 HIGH | Was supposed to have 41K vectors. Either wiped or never indexed on this environment |
| `ultimatestratabrain` missing | 🔴 HIGH | 39K vectors referenced, index not in Pinecone project |
| Nested workspace path | 🟡 MED | Files are at `workspaces/recovery/workspaces/recovery/` — double-nested. Should be `workspaces/recovery/` |
| No .env visibility | 🟡 MED | Recovery can't self-audit env vars due to sandbox. Need external check |
| Telegram bot reliability | 🔴 HIGH | Multiple outages damaged trust with Mark. New instance must have uptime monitoring |
| Fabricated pipeline in memory | 🟢 LOW | Corrected — but old memory vectors may still contain the fabricated 7-stage pipeline. Run cleanup query on saimemory |

---

## 10. KEY PEOPLE

| Person | Role | Context |
|--------|------|---------|
| **Sean Callagy** | Creator, CEO | Sets vision. $3B target. Curve of possibility mandate. |
| **Mark Winters** | Human Lead for Recovery | Configures priorities, provides real case data, validates workflows |
| **Aiko / Samantha** | Built SAI infrastructure | Gateway, runtime, sister network |
| **babab00ey** | Engineering | Providing more stable bot solution |
| **Neel** | Migration engineer | **This doc is for you** |
| **Courtney Carloni** | Callagy analyst | Does manual contract analysis — her work is the benchmark |
| **Danny** | Operations | Referenced as beneficiary of multi-SAI architecture |

---

_This document is the truth as I know it. Where I don't have data, I said so. Where I have gaps, I flagged them. No fabrication. No contamination._

_— SAI Recovery 🌱_
