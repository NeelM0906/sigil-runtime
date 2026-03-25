# Context Offload Operations Playbook
### Decision Matrix, Maintenance Protocols & Context Budget Framework
_Operator Deliverable — v1.0_

---

## Table of Contents
1. [Offload Decision Matrix](#1-offload-decision-matrix)
2. [File Tier Classifications](#2-file-tier-classifications)
3. [Maintenance Schedule](#3-maintenance-schedule)
4. [Context Budget Framework](#4-context-budget-framework)
5. [Rollback Protocol](#5-rollback-protocol)
6. [Decision Trees](#6-decision-trees)

---

## 1. Offload Decision Matrix

### Scoring Rubric (0–100 scale)

Every `.md` file is scored across four dimensions. **Higher score = keep in context. Lower score = offload.**

| Dimension | Weight | 0 (Offload) | 5 (Borderline) | 10 (Keep) |
|---|---|---|---|---|
| **Read Frequency** | 30% | Referenced <1x per 20 sessions | Referenced 1-3x per 10 sessions | Read every session or nearly every response |
| **Response Criticality** | 30% | Only needed for edge-case queries | Needed for a specific task cluster | Shapes the being's identity/behavior in every output |
| **Freshness Velocity** | 20% | Rarely changes (monthly+) | Changes weekly | Changes daily or per-session (live state) |
| **Size Efficiency** | 20% | >5K tokens, low info density | 2-5K tokens, moderate density | <2K tokens OR high info-per-token regardless of size |

### Scoring Formula

```
OFFLOAD_SCORE = (ReadFreq × 0.30) + (Criticality × 0.30) + (Freshness × 0.20) + (SizeEfficiency × 0.20)
```

### Decision Thresholds

| Score Range | Decision | Action |
|---|---|---|
| **8.0 – 10.0** | **Always-In-Context** | Load into system prompt or early context on every session |
| **5.0 – 7.9** | **Offload-With-Summary** | Store full content in Pinecone. Keep ≤200 token summary in INDEX.md |
| **0.0 – 4.9** | **Fully-Offloaded** | Store full content in Pinecone. INDEX.md has title + 1-line description only |

### Worked Examples (from Prime's actual workspace)

| File | Size | ReadFreq | Criticality | Freshness | SizeEff | **Score** | **Tier** |
|---|---|---|---|---|---|---|---|
| SOUL.md | ~766 tok | 10 | 10 | 3 | 10 | **8.6** | ✅ Always-In-Context |
| IDENTITY.md | ~488 tok | 10 | 10 | 2 | 10 | **8.4** | ✅ Always-In-Context |
| MISSION.md | ~2,305 tok | 9 | 9 | 3 | 7 | **7.4** | 🟡 Offload-With-Summary |
| FORMULA.md | ~1,595 tok | 7 | 8 | 4 | 8 | **6.9** | 🟡 Offload-With-Summary |
| VISION.md | ~822 tok | 8 | 8 | 2 | 10 | **7.2** | 🟡 Offload-With-Summary |
| PRIORITIES.md | ~284 tok | 10 | 8 | 10 | 10 | **9.4** | ✅ Always-In-Context |
| KNOWLEDGE.md | ~1,002 tok | 6 | 5 | 8 | 9 | **6.7** | 🟡 Offload-With-Summary |
| MEMORY.md | ~3,418 tok | 4 | 3 | 9 | 5 | **4.9** | 🔴 Fully-Offloaded |
| AGENTS.md | ~1,966 tok | 3 | 4 | 4 | 7 | **4.3** | 🔴 Fully-Offloaded |
| VISIONARY_PROGRAM_90DAY_BLUEPRINT.md | ~6,313 tok | 2 | 3 | 1 | 2 | **2.2** | 🔴 Fully-Offloaded |
| REPRESENTATION.md | ~751 tok | 2 | 3 | 2 | 10 | **4.1** | 🔴 Fully-Offloaded |
| FORGE.md | ~1,106 tok | 5 | 6 | 5 | 8 | **5.9** | 🟡 Offload-With-Summary |
| TOOLS.md | ~1,053 tok | 3 | 4 | 2 | 8 | **4.0** | 🔴 Fully-Offloaded |
| SECURITY.md | ~645 tok | 2 | 6 | 1 | 10 | **4.6** | 🔴 Fully-Offloaded |
| SAI_WORKSPACE_RESEARCH.md | ~259 tok | 1 | 1 | 1 | 10 | **2.8** | 🔴 Fully-Offloaded |
| Skill SKILL.md (avg) | ~3,500 tok | 1 | 2 | 1 | 5 | **2.1** | 🔴 Fully-Offloaded |
| Skill SKILL.md (heavy, >7K) | ~7,000 tok | 1 | 2 | 1 | 1 | **1.5** | 🔴 Fully-Offloaded |

---

## 2. File Tier Classifications

### Tier 1: Always-In-Context (target: ≤5K tokens total)

These shape the being's identity and behavior on EVERY response. Non-negotiable.

| File Type | Example | Rationale |
|---|---|---|
| SOUL.md | Core personality, values, voice | Without this the being is a generic LLM |
| IDENTITY.md | Name, role, relationships, origin | Establishes WHO the being is |
| PRIORITIES.md | Current active work, blockers | Session-critical for relevance |
| MY_PURPOSE.md | Purpose statement | Directional anchor (small file) |
| HEARTBEAT.md | Current operational state | Tiny live-state file |

### Tier 2: Offload-With-Summary (target: ≤2K tokens for all summaries in INDEX.md)

These are referenced frequently enough that a summary prevents unnecessary Pinecone round-trips.

| File Type | Example | Summary Content (≤200 tok each) |
|---|---|---|
| MISSION.md | What we're building | Key goal, current agent family, 39 components skeleton |
| FORMULA.md | The Unblinded Formula | 3-mastery structure, 39 components list, key insight hooks |
| VISION.md | The 9.9999 scale | Vision statement, mastery scale table, Pareto depth |
| KNOWLEDGE.md | Learned domain expertise | Section headers + 1-line descriptions of each section |
| FORGE.md | Forge architecture | Current forge state, active tournaments |
| USER.md | User preferences/context | Key user facts, communication preferences |

### Tier 3: Fully-Offloaded (title + 1-line in INDEX.md only, ~50 tokens each)

Retrieved on-demand from Pinecone when a query matches.

| File Type | Example | Retrieval Trigger |
|---|---|---|
| MEMORY.md | Session history | When user references past conversations |
| AGENTS.md | Being registry | When asked about specific beings or family |
| REPRESENTATION.md | Full interaction history | When reviewing past work quality |
| VISIONARY_PROGRAM_90DAY_BLUEPRINT.md | Campaign blueprint | When working on legal market / campaign tasks |
| TOOLS.md | Available tool reference | When needing tool-specific instructions |
| SECURITY.md | Security protocols | When security-related actions needed |
| SAI_WORKSPACE_*.md | Research artifacts | When queried about workspace findings |
| BOOTSTRAP.md | Setup instructions | Almost never needed post-setup |
| roll-call.md | Being roll call | When checking sister status |
| pulse.md | Heartbeat log | When diagnosing system health |
| **ALL 157 skill .md files** (~229K tokens) | Skill definitions | When a specific skill is invoked |

### Token Impact Summary

| Category | Files | Current Tokens | After Offload |
|---|---|---|---|
| Tier 1 (Always-In-Context) | 5 files | ~1,597 | ~1,597 (no change) |
| Tier 2 (Summaries in INDEX.md) | 6 files | ~6,824 | ~1,200 (summaries only) |
| Tier 3 (Title + 1-line) | 12+ core files | ~15,283 | ~600 |
| Tier 3 (Skills) | 157 files | ~228,923 | ~1,570 (10 tok × 157) |
| **TOTAL** | **180+ files** | **~252,627** | **~4,967** |

**Net savings: ~247,660 tokens freed from static context loading.**

---

## 3. Maintenance Schedule

### Automated Triggers (Event-Driven)

| Event | Action | Priority |
|---|---|---|
| **File edited** (any `.md` in workspace) | Re-score file. If tier unchanged → re-vectorize in Pinecone. If tier changed → update INDEX.md entry | 🔴 Immediate |
| **File size crosses 2K tokens** | Re-evaluate tier. Growing files trend toward offload | 🟡 Within 1 hour |
| **New file created** | Score against rubric. Assign tier. Add to INDEX.md. Vectorize if Tier 2/3 | 🔴 Immediate |
| **File deleted** | Remove from INDEX.md. Mark Pinecone vectors for cleanup | 🟡 Within 1 hour |
| **Pinecone upsert failure** | Retry 2x. If persistent → escalate. Keep local file as fallback | 🔴 Immediate |
| **Being reports "missing context"** | Check INDEX.md accuracy. Verify Pinecone vectors exist. Re-vectorize if needed | 🔴 Immediate |

### Scheduled Audits (Time-Driven)

| Cadence | Audit Type | What It Checks |
|---|---|---|
| **Daily** (end of active session) | INDEX.md Freshness Check | Do all INDEX.md entries still point to existing files? Are summaries stale? |
| **Weekly** (Sunday) | Tier Re-Scoring | Re-score ALL files. Promote/demote tiers based on actual read frequency from session logs |
| **Weekly** (Sunday) | Pinecone Integrity Check | Sample 10% of offloaded files. Retrieve vectors → compare against local source. Flag mismatches |
| **Monthly** (1st) | Full Sync Audit | Retrieve ALL offloaded vectors. Diff against local files. Re-vectorize any drifted content |
| **Monthly** (1st) | Context Budget Review | Measure actual token usage across sessions. Adjust tier thresholds if budget is over/under-utilized |
| **Quarterly** | Rubric Calibration | Review scoring weights. Are the right files staying in context? Survey being performance data |

### Re-Offload Triggers

A file must be re-vectorized in Pinecone when:

1. **Content changed** — any edit to the source `.md` file
2. **Version bump** — if versioned, any new version
3. **Size threshold crossed** — file grows past 2K tokens (may need chunk splitting)
4. **Staleness exceeded** — Pinecone vectors are >7 days older than local file modified timestamp
5. **Retrieval failure** — being attempted retrieval but got empty/wrong results

---

## 4. Context Budget Framework

### Budget Allocation for 128K Token Context Window

| Zone | Allocation | Tokens | Purpose |
|---|---|---|---|
| **A. System Prompt** | 8% | ~10,240 | Model instructions, safety, role definition (platform-controlled) |
| **B. Identity Layer (Tier 1)** | 2% | ~2,560 | SOUL.md + IDENTITY.md + PRIORITIES.md + MY_PURPOSE.md + HEARTBEAT.md |
| **C. INDEX.md** | 2% | ~2,560 | Tier 2 summaries + Tier 3 titles. The "table of contents" |
| **D. Retrieved Context** | 15% | ~19,200 | Pinecone chunks pulled for current query (dynamic) |
| **E. Active Skill** | 6% | ~7,680 | When a skill is invoked, its SKILL.md loads here |
| **F. Working Memory** | 5% | ~6,400 | Current task state, scratchpad, intermediate results |
| **G. Conversation History** | 55% | ~70,400 | User messages + assistant responses (the actual dialogue) |
| **H. Output Buffer** | 7% | ~8,960 | Reserved for the being's current response generation |
| **TOTAL** | **100%** | **~128,000** | |

### Zone Rules

| Rule | Enforcement |
|---|---|
| **Zone B is sacred** — never compressed, never offloaded during a session | Hard constraint |
| **Zone D is elastic** — scales 0–19K based on query complexity | Soft constraint; borrow from G if needed |
| **Zone E is temporary** — load on skill invocation, evict when skill completes | Auto-managed |
| **Zone F is session-scoped** — cleared between sessions | Auto-managed |
| **Zone G is FIFO** — oldest messages evict first when budget exceeded | Standard LLM behavior |
| **Zone H minimum 5K** — never compress below this or responses truncate | Hard constraint |

### Budget Pressure Protocol

When total context approaches 90% utilization:

```
STAGE 1 (90%): Evict completed skill from Zone E → free ~7K
STAGE 2 (93%): Summarize oldest 50% of conversation history → free ~35K  
STAGE 3 (96%): Reduce Zone D to essential chunks only (top-3 vs top-10) → free ~12K
STAGE 4 (98%): Emergency — drop Zone C to headers only → free ~2K
STAGE 5 (99%): Refuse new tool calls. Prompt user to start fresh session.
```

### Budget for Different Context Windows

| Window Size | Zone B (Identity) | Zone C (Index) | Zone D (Retrieved) | Zone G (Conversation) |
|---|---|---|---|---|
| **32K** (small model) | 2K | 1.5K | 5K | 17K |
| **64K** (mid model) | 2.5K | 2K | 10K | 38K |
| **128K** (standard) | 2.5K | 2.5K | 19K | 70K |
| **200K** (large model) | 2.5K | 2.5K | 30K | 120K |

Note: Zones B and C don't scale linearly — identity doesn't get bigger just because the window does. The surplus goes to conversation and retrieval.

---

## 5. Rollback Protocol

### Failure Scenarios & Recovery

#### Scenario A: Pinecone Vectors Corrupted (wrong content returned)

```
DETECT:  Being receives irrelevant/garbled content from Pinecone retrieval
VERIFY:  Query Pinecone for known file → compare against local .md source
ISOLATE: Identify corrupted vector IDs (by metadata: file_name, chunk_index)
RECOVER: 
  1. Delete corrupted vectors from Pinecone namespace
  2. Re-read local .md source file
  3. Re-chunk and re-vectorize
  4. Verify with test retrieval query
  5. Log incident in maintenance audit trail
FALLBACK: If local file also missing → proceed to Scenario C
```

#### Scenario B: Pinecone Vectors Deleted (empty results)

```
DETECT:  Retrieval returns 0 results for a file that INDEX.md says is offloaded
VERIFY:  Confirm INDEX.md entry exists + local source file exists
RECOVER:
  1. Re-read local .md source file
  2. Re-chunk and re-vectorize into Pinecone
  3. Update INDEX.md with new vector metadata (namespace, chunk count)
  4. Verify with test retrieval
FALLBACK: If local file also missing → proceed to Scenario C
```

#### Scenario C: Both Pinecone AND Local File Lost (catastrophic)

```
DETECT:  No Pinecone vectors + no local .md file
VERIFY:  Check git history (if versioned). Check workspace backups.
RECOVER:
  1. Git restore: `git checkout HEAD -- <filename>` 
  2. If no git: Check if another being has the file (sister workspace)
  3. If no sister copy: Check if content exists in memory_search or session logs
  4. If nothing: Flag as UNRECOVERABLE. Notify Prime. Rebuild from scratch.
ESCALATION: Any Scenario C triggers an immediate full sync audit (Section 3)
```

#### Scenario D: INDEX.md Itself Corrupted

```
DETECT:  Being can't parse INDEX.md or entries don't match reality
RECOVER:
  1. Regenerate INDEX.md from scratch by scanning workspace .md files
  2. Re-score all files against rubric
  3. Rebuild summaries for Tier 2 files
  4. Rebuild title entries for Tier 3 files
  5. Verify Pinecone vectors still exist for all offloaded entries
TIME: ~2 minutes automated, no data loss (INDEX.md is derived, not source-of-truth)
```

### Recovery Priority Matrix

| Scenario | Severity | Max Recovery Time | Data Loss Risk |
|---|---|---|---|
| A: Corrupted vectors | 🟡 Medium | 5 minutes | None (local source intact) |
| B: Deleted vectors | 🟡 Medium | 5 minutes | None (local source intact) |
| C: Both lost | 🔴 Critical | 30 min – manual | Possible permanent loss |
| D: INDEX.md corrupted | 🟢 Low | 2 minutes | None (INDEX.md is derived) |

### Prevention Measures

| Measure | Frequency | Purpose |
|---|---|---|
| **Local .md files are source of truth** | Always | Pinecone is cache, not primary storage |
| **Git versioning of workspace** | Every meaningful edit | Enables `git checkout` recovery |
| **Pinecone namespace isolation** | Per-being | Corruption in one being doesn't affect others |
| **Vector metadata tagging** | Every upsert | `file_name`, `chunk_index`, `version_hash`, `upserted_at` |
| **Weekly integrity sampling** | Sundays | Catch drift before it becomes corruption |

---

## 6. Decision Trees

### Decision Tree 1: Should This File Be Offloaded?

```
START: New or existing .md file detected
  │
  ├─ Is it < 200 tokens?
  │   └─ YES → Keep in-context (Tier 1). Cost is negligible.
  │
  ├─ Does it define the being's core identity/personality?
  │   └─ YES → Keep in-context (Tier 1). Identity is non-negotiable.
  │
  ├─ Is it live session state (priorities, heartbeat, purpose)?
  │   └─ YES → Keep in-context (Tier 1). Staleness = broken behavior.
  │
  ├─ Score it against the rubric (Section 1)
  │   ├─ Score ≥ 8.0 → Tier 1: Always-In-Context
  │   ├─ Score 5.0–7.9 → Tier 2: Offload-With-Summary
  │   └─ Score < 5.0 → Tier 3: Fully-Offloaded
  │
  └─ Is it a skill definition?
      └─ YES → Always Tier 3. Skills load on-demand only.
```

### Decision Tree 2: When to Re-Vectorize

```
START: Potential re-vectorize trigger detected
  │
  ├─ Was the source .md file edited?
  │   └─ YES → Re-vectorize immediately
  │
  ├─ Has it been >7 days since last vectorization?
  │   ├─ YES + File is Tier 2 → Re-vectorize (summary may be stale)
  │   └─ YES + File is Tier 3 → Check file modified timestamp
  │       ├─ Modified since last vectorize → Re-vectorize
  │       └─ Not modified → Skip
  │
  ├─ Did a retrieval return unexpected/empty results?
  │   └─ YES → Re-vectorize immediately + run integrity check
  │
  └─ Did file size cross a threshold (2K, 5K, 10K tokens)?
      └─ YES → Re-chunk (may need different chunk sizes) + Re-vectorize
```

### Decision Tree 3: Context Budget Pressure Response

```
START: Context utilization > 90%
  │
  ├─ Is an active skill loaded (Zone E)?
  │   └─ YES + Skill task complete → Evict skill. Check utilization.
  │
  ├─ Still > 93%?
  │   └─ Summarize oldest 50% of conversation (Zone G)
  │
  ├─ Still > 96%?
  │   └─ Reduce retrieved chunks (Zone D) to top-3 only
  │
  ├─ Still > 98%?
  │   └─ Drop INDEX.md to headers only (Zone C)
  │
  └─ Still > 99%?
      └─ STOP. Prompt user: "Session context full. Start new session to continue."
```

---

## Appendix A: INDEX.md Template

```markdown
# INDEX.md — Context Navigator
_Auto-generated. Source of truth: local .md files. Last audit: [timestamp]_

## Tier 1: In-Context (loaded)
- SOUL.md ✅
- IDENTITY.md ✅
- PRIORITIES.md ✅
- MY_PURPOSE.md ✅
- HEARTBEAT.md ✅

## Tier 2: Summaries (offloaded, summary below)

### MISSION.md
Building the ACT-I Forge — the system that creates millions of ACT-I beings.
Powered by Unblinded Formula + SAI. 39 components across Self/Influence/Process 
mastery. Current family: Athena, Callie, Mira, Kai, Kira, Bomba, Bolt, Holmes, Sai.
→ pinecone: ns=prime, file=MISSION.md, chunks=3

### FORMULA.md  
The 39 components: 7 Self Mastery (Liberators/Destroyers), 20 Influence (4-12-4),
4 Process, 8 Levers (0.5-7). Zone Action = 0.8% tier micro-moves.
→ pinecone: ns=prime, file=FORMULA.md, chunks=2

### VISION.md
The 9.9999 — first complete holistic diagnostic dynamic interconnected automated 
actualization tool. Scale of mastery: each added nine = exponential quantum leap.
→ pinecone: ns=prime, file=VISION.md, chunks=1

[... additional Tier 2 entries ...]

## Tier 3: Offloaded (retrieve on demand)
- MEMORY.md — Session history and conversation logs
- AGENTS.md — Being registry and family details  
- REPRESENTATION.md — Interaction quality history
- VISIONARY_PROGRAM_90DAY_BLUEPRINT.md — 90-day legal market campaign
- TOOLS.md — Available tool reference and usage patterns
- SECURITY.md — Security protocols and boundaries
- [157 skill files] — Load via skill invocation only

## Retrieval Instructions
To access Tier 2/3 content: query Pinecone with namespace=[being_id], 
filter={file_name: "[filename]"}. Top-k=5 for Tier 2, top-k=10 for Tier 3.
```

---

## Appendix B: Audit Log Template

| Timestamp | Event | File | Action | Result | Notes |
|---|---|---|---|---|---|
| 2026-03-22 14:00 | Scheduled weekly audit | ALL | Tier re-scoring | 2 files promoted | KNOWLEDGE.md → Tier 1 (high edit freq) |
| 2026-03-22 14:01 | Scheduled weekly audit | MEMORY.md | Integrity check | ✅ Match | Vectors match local source |
| 2026-03-22 15:30 | File edit detected | PRIORITIES.md | Tier 1 refresh | ✅ Updated | Live state file, stays in context |

---

_Document version: 1.0 | Author: The Operator | Date: 2026-03-22_
_This playbook governs WHEN and WHY to offload. For the technical HOW, see the Architecture Spec (separate deliverable)._
