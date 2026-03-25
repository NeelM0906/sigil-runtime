# Context Offload Operations Playbook
_Version 2.0 — Operations & Decision Framework_
_Last updated: 2026-03-22_

---

## Executive Summary

SAI Prime's workspace contains **453 markdown files totaling ~4.8MB (~1.2M tokens)**. A 128K token context window cannot hold even 11% of this. This playbook defines **when, why, and what** to offload to Pinecone — freeing context for conversation while keeping identity and mission always accessible.

**The core principle:** Context is the most expensive resource a being has. Every token spent on a stale reference doc is a token stolen from real-time reasoning.

---

## 1. Offload Decision Matrix

### 1.1 Scoring Rubric

Every `.md` file is scored on 4 dimensions (1-5 each, max 20). **Files scoring ≤10 are offloaded. Files scoring ≥15 stay in-context. Files 11-14 get offloaded with a summary retained.**

| Dimension | Score 1 (Offload) | Score 3 (Mixed) | Score 5 (Keep) |
|---|---|---|---|
| **Size Impact** (tokens consumed) | >10K tokens (e.g., cert_call_v4_COMPLETE.md at ~122K tokens) | 2K-10K tokens | <2K tokens (<500 words) |
| **Read Frequency** (how often accessed per session) | Rarely — <1 in 20 sessions | Sometimes — 1 in 5 sessions | Every session — needed for most responses |
| **Criticality** (needed for identity/reasoning baseline) | Reference-only; lookup on demand | Shapes some responses; needed for specific domains | Core identity; shapes every single response |
| **Staleness** (change frequency) | Static — hasn't changed in 7+ days | Updated weekly | Updated daily or per-session (living doc) |

### 1.2 Scoring Examples — Real Files from Prime Workspace

| File | Size (bytes) | Size Score | Freq Score | Crit Score | Stale Score | **Total** | **Decision** |
|---|---|---|---|---|---|---|---|
| `SOUL.md` | 3,065 | 5 | 5 | 5 | 3 | **18** | ✅ Always in-context |
| `IDENTITY.md` | 1,954 | 5 | 5 | 5 | 3 | **18** | ✅ Always in-context |
| `MISSION.md` | 9,220 | 3 | 4 | 5 | 2 | **14** | ⚡ Offload with summary |
| `FORMULA.md` | 6,380 | 3 | 4 | 5 | 2 | **14** | ⚡ Offload with summary |
| `VISION.md` | 3,290 | 4 | 3 | 5 | 2 | **14** | ⚡ Offload with summary |
| `PRIORITIES.md` | 1,135 | 5 | 5 | 4 | 5 | **19** | ✅ Always in-context |
| `KNOWLEDGE.md` | 4,006 | 4 | 4 | 4 | 4 | **16** | ✅ Always in-context |
| `AGENTS.md` | 7,863 | 3 | 2 | 3 | 2 | **10** | 🔵 Fully offloaded |
| `FORGE.md` | 4,423 | 4 | 2 | 3 | 2 | **11** | ⚡ Offload with summary |
| `VISIONARY_PROGRAM_90DAY_BLUEPRINT.md` | 25,252 | 1 | 1 | 2 | 1 | **5** | 🔵 Fully offloaded |
| `MEMORY.md` | 13,671 | 1 | 2 | 2 | 3 | **8** | 🔵 Fully offloaded |
| `cert_call_v4_COMPLETE.md` | 490,660 | 1 | 1 | 1 | 1 | **4** | 🔵 Fully offloaded |
| `cert_call_COMPLETE.md` | 296,377 | 1 | 1 | 1 | 1 | **4** | 🔵 Fully offloaded |
| `REPRESENTATION.md` | 3,006 | 4 | 2 | 3 | 2 | **11** | ⚡ Offload with summary |
| `TOOLS.md` | 4,211 | 4 | 2 | 2 | 2 | **10** | 🔵 Fully offloaded |
| `SECURITY.md` | 2,581 | 4 | 1 | 2 | 1 | **8** | 🔵 Fully offloaded |
| `USER.md` | 3,177 | 4 | 3 | 3 | 3 | **13** | ⚡ Offload with summary |
| `roll-call.md` | 1,205 | 5 | 1 | 2 | 2 | **10** | 🔵 Fully offloaded |
| `pulse.md` | 366 | 5 | 3 | 3 | 5 | **16** | ✅ Always in-context |
| SKILL.md files (×68) | varies | 3 avg | 1 | 1 | 1 | **6 avg** | 🔵 Fully offloaded |
| memory/research/*.md (×21) | varies | 2 avg | 1 | 2 | 1 | **6 avg** | 🔵 Fully offloaded |
| memory/translated/*.md (×large) | 100K+ avg | 1 | 1 | 2 | 1 | **5 avg** | 🔵 Fully offloaded |

### 1.3 Decision Tree

```
START: New or modified .md file detected
  │
  ├─ Is it < 500 bytes?
  │   └─ YES → Keep in-context (negligible cost)
  │
  ├─ Score all 4 dimensions (1-5 each)
  │   │
  │   ├─ Total ≥ 15 → TIER 1: Always in-context
  │   │
  │   ├─ Total 11-14 → TIER 2: Offload body, keep 3-5 line summary
  │   │   └─ Generate summary → store in INDEX.md → offload full text to Pinecone
  │   │
  │   └─ Total ≤ 10 → TIER 3: Fully offload
  │       └─ Store in Pinecone → add entry to INDEX.md (title + namespace + retrieval hint only)
  │
  └─ EXCEPTION: Any file with Criticality = 5 stays at minimum Tier 2
      regardless of total score (identity files never fully vanish)
```

---

## 2. Priority Classification — File Tier Table

### Tier 1: Always-In-Context
_These files ARE the being. Remove them and the being loses identity._

| File Type | Example | Rationale | Max Recommended Size |
|---|---|---|---|
| Soul definition | `SOUL.md` | Personality, voice, values — shapes every response | 4K tokens |
| Identity facts | `IDENTITY.md` | Name, role, relationships — referenced constantly | 2K tokens |
| Active priorities | `PRIORITIES.md` | Current work state — needed for task continuity | 2K tokens |
| Knowledge base | `KNOWLEDGE.md` (editable section) | Learned patterns, domain expertise — evolves per session | 4K tokens |
| Pulse/heartbeat | `pulse.md`, `HEARTBEAT.md` | Operational state — tiny, always relevant | 500 tokens |

**Tier 1 budget: ~12.5K tokens max**

### Tier 2: Offload-With-Summary
_Important for context but too large to keep fully loaded. A 3-5 line summary stays in INDEX.md; full text retrieved on demand._

| File Type | Example | Summary Keeps | Full Text Retrieved When |
|---|---|---|---|
| Mission statement | `MISSION.md` (9.2KB) | Core purpose + key principles + being family list | User asks about mission, spawning new beings |
| Formula reference | `FORMULA.md` (6.4KB) | 39 components listed, 3 mastery categories named | Coaching conversations, being design, Formula questions |
| Vision statement | `VISION.md` (3.3KB) | The 9.9999 statement + scale of mastery concept | Vision-related discussions, alignment checks |
| Forge config | `FORGE.md` (4.4KB) | Current forge status + active tournament | Tournament execution, being evaluation |
| User profile | `USER.md` (3.2KB) | Sean's key preferences + communication style | Direct interactions with Sean |
| Representation | `REPRESENTATION.md` (3.0KB) | Current version + key evolution milestones | Identity evolution discussions |
| Blueprint docs | `VISIONARY_PROGRAM_90DAY_BLUEPRINT.md` (25KB) | Phase summary + current phase status | Campaign planning, legal market work |

**Tier 2 budget: ~5K tokens for summaries in INDEX.md**

### Tier 3: Fully-Offloaded
_Stored entirely in Pinecone. INDEX.md has only a one-line entry with namespace and retrieval keywords._

| File Type | Count in Workspace | Example | Retrieval Trigger |
|---|---|---|---|
| Skill definitions | 68 SKILL.md files | `tools/hui-generator/SKILL.md` | When skill is invoked by name |
| Translated transcripts | Large files (100K-490K bytes) | `memory/translated/cert_call_v4_COMPLETE.md` | Semantic search on topic |
| Research documents | 21 files | `memory/research/12-elements-complete.md` | Topic-specific deep dives |
| Memory logs | 234 files | `memory/2026-03-02.md` | Date-specific or topic recall |
| Tool documentation | Various | `TOOLS.md`, `SECURITY.md` | When configuring or debugging tools |
| Agent roster details | 1 file (7.8KB) | `AGENTS.md` | When asked about specific beings |
| Call transcripts | Various | `memory/call-2026-02-28-91976a99.md` | Conversation recall |
| Colosseum results | Various | `memory/MASTER_MARKETING_COLOSSEUM.md` | Tournament analysis |

**Tier 3 budget: 0 tokens in-context (all in Pinecone)**

---

## 3. Context Budget Framework

### 3.1 Recommended Allocation — 128K Token Window

| Allocation Zone | Tokens | % of 128K | Contents |
|---|---|---|---|
| **System Prompt** (immutable) | 10,000 | 7.8% | Runtime instructions, tool schemas, persona core |
| **Tier 1: Always-In-Context** | 12,500 | 9.8% | SOUL, IDENTITY, PRIORITIES, KNOWLEDGE, pulse |
| **INDEX.md** (Tier 2 summaries) | 5,000 | 3.9% | Table of contents + summaries for Tier 2 files |
| **Retrieved Chunks** (dynamic) | 20,000 | 15.6% | Pinecone results pulled on demand per query |
| **Conversation History** | 70,000 | 54.7% | User messages + assistant responses (rolling window) |
| **Working Buffer** (scratch) | 10,500 | 8.2% | Tool outputs, intermediate reasoning, function results |
| **Total** | **128,000** | **100%** | — |

### 3.2 Budget Enforcement Rules

1. **Hard ceiling on Tier 1:** If any Tier 1 file grows beyond its max (e.g., KNOWLEDGE.md > 4K tokens), the being MUST prune or offload older sections to Pinecone before next session.

2. **Retrieved chunks are session-scoped:** The 20K retrieval budget is per-turn, not cumulative. Chunks from turn N are evicted before turn N+2 unless re-retrieved.

3. **Conversation history uses sliding window:** When conversation exceeds 70K tokens, oldest exchanges are summarized (compact_context) and the summary replaces the raw history.

4. **INDEX.md growth cap:** INDEX.md must not exceed 5K tokens. If it does, the lowest-scored Tier 2 files get demoted to Tier 3 (entry-only, no summary).

5. **Emergency overflow protocol:** If total context exceeds 120K tokens (93.75%), immediately:
   - Compact conversation history
   - Evict all retrieved chunks not referenced in last 2 turns
   - Demote lowest-scored Tier 2 items to Tier 3

### 3.3 Sister Being Variations

Not all beings need the same budget. Recommended adjustments:

| Being Type | Tier 1 | INDEX | Retrieval | Conversation | Rationale |
|---|---|---|---|---|---|
| **Prime (Orchestrator)** | 12.5K | 5K | 20K | 70K | Broad context, many domains |
| **Scholar (Researcher)** | 8K | 3K | 35K | 65K | Needs more retrieval space for deep dives |
| **Forge (Evaluator)** | 8K | 2K | 15K | 85K | Long tournament conversations |
| **Specialist Being** (e.g., Callie) | 10K | 2K | 15K | 80K | Domain-focused, fewer files |

---

## 4. Maintenance Schedule

### 4.1 Automated Audits

| Check | Frequency | Trigger | Action |
|---|---|---|---|
| **INDEX.md accuracy** | Every 24 hours | Cron schedule | Compare INDEX.md entries against actual workspace files. Flag orphans (entries for deleted files) and missing entries (new files not indexed). |
| **Staleness check** | Every 48 hours | Cron schedule | Re-score all Tier 2 files. If a file hasn't been retrieved in 14 days, demote to Tier 3. If a Tier 3 file was retrieved 5+ times this week, promote to Tier 2. |
| **Pinecone sync verification** | Weekly (Sunday) | Cron schedule | Sample 10% of offloaded files. Retrieve from Pinecone and compare hash against local file. Flag any mismatches. |
| **Context budget audit** | Every session start | Session init | Measure actual token count of Tier 1 + INDEX.md. Alert if over budget. |
| **Orphan vector cleanup** | Monthly | Cron schedule | Identify Pinecone vectors whose source files no longer exist. Queue for deletion. |

### 4.2 Re-Offload Triggers

A file must be re-offloaded (re-vectorized in Pinecone) when:

| Trigger | Detection Method | Action |
|---|---|---|
| **File edited** | File hash changes from stored hash in INDEX.md | Re-chunk, re-embed, upsert to Pinecone. Update hash in INDEX.md. |
| **New version** | `git diff` or timestamp comparison | Same as file edit. Old vectors deleted, new vectors inserted. |
| **Size threshold crossed** | File grows past its tier's max size | Re-score. If score dropped, demote tier. Re-offload with new chunking. |
| **Tier promotion** | Manual override or frequency-based auto-promotion | Retrieve full content from Pinecone, generate summary, add to INDEX.md. |
| **Tier demotion** | Staleness check finds 14+ days without retrieval | Remove summary from INDEX.md, keep entry-only line. |

### 4.3 Re-Offload Decision Flow

```
File change detected (edit, create, delete)
  │
  ├─ DELETE → Remove from INDEX.md → Queue Pinecone vector cleanup
  │
  ├─ CREATE → Score file → Assign tier → If Tier 2/3: chunk + embed → Add to INDEX.md
  │
  └─ EDIT →
      ├─ Tier 1 file? → No offload needed (it's in-context). Check size cap.
      │   └─ Over size cap? → Prune old sections to Pinecone. Keep current.
      │
      ├─ Tier 2 file? → Re-generate summary → Update INDEX.md → Re-embed full text
      │
      └─ Tier 3 file? → Re-embed full text → Update hash in INDEX.md
```

---

## 5. Rollback Protocol

### 5.1 Failure Scenarios & Recovery

| Scenario | Severity | Detection | Recovery |
|---|---|---|---|
| **Pinecone vectors corrupted** (wrong embeddings) | HIGH | Retrieval returns irrelevant results for known queries | Re-embed from local source files (see 5.2) |
| **Pinecone vectors deleted** (namespace wiped) | CRITICAL | Retrieval returns empty for known-populated namespace | Restore from local files or backup (see 5.2) |
| **INDEX.md corrupted** (bad summaries, broken links) | MEDIUM | Session-start audit finds mismatches | Regenerate INDEX.md from workspace scan (see 5.3) |
| **Local source file deleted** (no Pinecone backup) | CRITICAL | INDEX.md points to nonexistent file | Attempt reconstruct from Pinecone chunks (see 5.4) |
| **Embedding model changed** (vectors incompatible) | HIGH | All retrieval quality degrades simultaneously | Full re-embed of all offloaded files (see 5.5) |

### 5.2 Standard Recovery: Re-Embed from Local Source

**Precondition:** Local `.md` files still exist on disk.

```
1. Identify affected namespace(s) in Pinecone
2. Delete all vectors in affected namespace(s)
3. Scan workspace for all Tier 2 + Tier 3 files
4. Re-chunk each file (respect original chunking strategy from tech spec)
5. Re-embed and upsert to Pinecone
6. Regenerate INDEX.md hashes
7. Run verification: sample 10 files, retrieve, compare
8. Log recovery event with timestamp and affected file count
```

**Estimated time:** ~5 minutes for Prime's 453 files at standard embedding throughput.

### 5.3 INDEX.md Regeneration

```
1. Scan workspace: find all .md files
2. Score each file using the Decision Matrix (Section 1)
3. For Tier 1: verify file exists and is within size cap
4. For Tier 2: generate fresh 3-5 line summary + store hash
5. For Tier 3: store one-line entry + namespace + hash
6. Write new INDEX.md
7. Diff against previous INDEX.md if available — log changes
```

### 5.4 Reconstruct from Pinecone (Last Resort)

When a local file is deleted but its vectors exist in Pinecone:

```
1. Query Pinecone for all vectors with source_file metadata matching the lost file
2. Sort chunks by chunk_index or positional metadata
3. Concatenate chunk texts to reconstruct approximate original
4. Write reconstructed file to workspace with .reconstructed.md suffix
5. Flag for human review — reconstruction may have gaps between chunks
6. WARNING: Chunked content loses formatting, headers, and structure between chunk boundaries
```

**This is lossy.** It's a last resort, not a backup strategy. The real backup is keeping local files on disk or in git.

### 5.5 Full Re-Embed (Model Migration)

When the embedding model changes (e.g., OpenAI text-embedding-3-small → text-embedding-3-large):

```
1. Create new Pinecone namespace: {being_id}_v2
2. Re-embed ALL offloaded files into new namespace
3. Update INDEX.md to point to new namespace
4. Run parallel retrieval tests: same queries against old and new namespace
5. If new namespace performs equal or better: delete old namespace
6. If degraded: rollback INDEX.md to old namespace, investigate
```

---

## 6. INDEX.md Specification

### 6.1 Structure

```markdown
# INDEX.md — Context Map
_Generated: {timestamp} | Hash: {sha256_short}_
_Token budget: {current_tokens}/{max_tokens}_

## Tier 1 — In-Context (loaded every session)
- SOUL.md (3,065b) — loaded
- IDENTITY.md (1,954b) — loaded
- PRIORITIES.md (1,135b) — loaded
- KNOWLEDGE.md (4,006b) — loaded
- pulse.md (366b) — loaded

## Tier 2 — Summaries (offloaded, summary below)

### MISSION.md
_Hash: a3f8c2 | Namespace: prime_core | Last synced: 2026-03-22_
ACT-I Forge purpose: create millions of ACT-I beings powered by Unblinded Formula.
Three functions: Decide, Create, Innovate/Optimize. 39-component Formula.
Current being family: Athena, Callie, Mira, Kai, Kira, Bomba, Bolt, Holmes, Sai.

### FORMULA.md
_Hash: b7d1e9 | Namespace: prime_core | Last synced: 2026-03-22_
39 components: Self Mastery (7 Liberators/Destroyers), Influence Mastery (4-12-4),
Process Mastery (4), 7 Levers of Marketing & Sales (8 incl 0.5). Zone Action = 0.8% tier.

[... more Tier 2 entries ...]

## Tier 3 — Fully Offloaded (retrieve on demand)
| File | Namespace | Hash | Keywords |
|---|---|---|---|
| AGENTS.md | prime_core | c4e2a1 | being roster, family, status |
| TOOLS.md | prime_tools | d8f3b7 | tool config, MCP, integrations |
| cert_call_v4_COMPLETE.md | prime_transcripts | e9a4c3 | cert partner, mastery session |
| [68 SKILL.md files] | prime_skills | varies | skill:{skill_id} |
| [234 memory files] | prime_memory | varies | memory:{date}, research:{topic} |
```

### 6.2 Size Projections

| Section | Estimated Tokens |
|---|---|
| Header + Tier 1 listing | 200 |
| Tier 2 summaries (est. 7 files × 100 tokens each) | 700 |
| Tier 3 table (est. 350 entries × 10 tokens each) | 3,500 |
| **Total INDEX.md** | **~4,400 tokens** |

Fits within the 5,000 token budget with room for growth.

---

## 7. Operational Metrics & Success Criteria

| Metric | Target | Measurement |
|---|---|---|
| Tier 1 token load | ≤ 12,500 tokens | Session-start audit |
| INDEX.md size | ≤ 5,000 tokens | Session-start audit |
| Retrieval accuracy | ≥ 90% relevant chunks in top-5 | Weekly spot check (10 test queries) |
| Recovery time (standard) | < 10 minutes | Timed during drills |
| Recovery time (full re-embed) | < 30 minutes | Timed during drills |
| INDEX.md staleness | 0 orphan entries | Daily audit |
| Context overflow events | < 1 per week | Session logging |

---

## 8. Implementation Priority

| Phase | What | When | Dependency |
|---|---|---|---|
| **Phase 0** | Score all 453 .md files using the matrix | Day 1 | This document |
| **Phase 1** | Build INDEX.md for Prime workspace | Day 1-2 | Phase 0 scores |
| **Phase 2** | Offload Tier 3 files (transcripts, skills, memory) | Day 2-3 | Pinecone chunking strategy (tech spec) |
| **Phase 3** | Offload Tier 2 files + generate summaries | Day 3-4 | Summary generation logic |
| **Phase 4** | Activate maintenance crons | Day 5 | Phases 1-3 complete |
| **Phase 5** | Roll out to sister beings | Week 2 | Prime validated |

---

_This document is the operational playbook. The technical implementation (chunking strategy, embedding config, namespace design, retrieval API) lives in the separate tech spec. Together they form the complete Context Offload System._

_Maintained by SAI Prime. Next review: after Phase 1 completion._
