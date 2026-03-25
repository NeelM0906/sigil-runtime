# Discussion Capture Pipeline — Operational Specification
_Version 1.0 — The Operator_
_Last updated: 2026-03-23_

---

## Executive Summary

This document defines the operational process for a recurring every-4-hours pipeline that captures what's being discussed across all ACT-I beings and writes it to Postgres via the `discussion_log` table (schema delivered by the-technologist). The governing mandate: **No Deletion, No Dilution, No Distortion (no-DDnD)**.

Five beings are in scope today: **Prime**, **Forge**, **Recovery**, **SAI Memory**, **Scholar**. The architecture scales to any number of beings without modification — each being is a `being_id` row, not a structural dependency.

---

## 1. Capture Cadence

### 1.1 Schedule

Six capture cycles per day, aligned to UTC:

| Cycle | Window Start (UTC) | Window End (UTC) | Capture Fires At |
|-------|---------------------|-------------------|-------------------|
| C0    | 00:00               | 03:59:59          | **04:00 UTC**     |
| C1    | 04:00               | 07:59:59          | **08:00 UTC**     |
| C2    | 08:00               | 11:59:59          | **12:00 UTC**     |
| C3    | 12:00               | 15:59:59          | **16:00 UTC**     |
| C4    | 16:00               | 19:59:59          | **20:00 UTC**     |
| C5    | 20:00               | 23:59:59          | **00:00 UTC** (+1)|

**Trigger mechanism:** Cron schedule — `0 0,4,8,12,16,20 * * *` UTC.

This is implemented via `schedule_task` on Sigil Runtime. The cron expression fires a **Capture Orchestrator** task that iterates over all registered beings.

### 1.2 Capture Sequence (per cycle)

```
[Cron fires at HH:00 UTC]
  │
  ├─ 1. Determine window: (HH-4):00 to (HH-1):59:59
  │
  ├─ 2. Enumerate active beings (query sisters_list + Prime)
  │
  ├─ 3. For EACH being:
  │     ├─ a. Retrieve all session transcripts/logs within the window
  │     ├─ b. Extract topics, summaries, and raw excerpts (Section 2)
  │     ├─ c. Apply no-DDnD quality gate (Section 3)
  │     ├─ d. Apply dedup hash check (Section 4)
  │     ├─ e. INSERT INTO discussion_log ON CONFLICT DO NOTHING
  │     └─ f. Log result to capture_audit_log
  │
  ├─ 4. Run audit verification (Section 6)
  │
  └─ 5. If any being had zero captures AND had active sessions → flag anomaly
```

### 1.3 What Triggers "Active" Status

A being is in-scope for a cycle if **any** of the following are true during the 4-hour window:
- It had at least one `sessions_list` entry with activity
- It had shared memory writes (`sessions_read_shared_memory`)
- It produced file changes in its workspace (glob/diff check)
- It received or sent messages (voice, SMS, chat)

A being with **zero activity** in the window produces **no records** — and that's correct, not an omission. The audit log records "no activity detected" explicitly so silence is documented, not ambiguous.

---

## 2. What Gets Captured

For each being's activity within a 4-hour window, three artifacts are extracted per distinct discussion topic:

### 2.1 Topic (column: `topic`)

A specific, granular label for what was discussed. **Not categories — topics.**

| ❌ Too vague (diluted) | ✅ Correct specificity |
|---|---|
| "Operations" | "Recovery pipeline Stage 3 appeals bottleneck — 47 claims stuck at carrier review" |
| "Marketing" | "Heart of Influence Lever 1 ecosystem merger strategy for Am Law 50 firms" |
| "Technical work" | "discussion_log Postgres schema design — dedup hash using SHA-256 over 4-hour buckets" |
| "Coaching" | "Rick Thompson physiology management gap — over-involvement blocking son's zone action" |

**Rules for topic extraction:**
- One topic per distinct subject discussed. If a session covers 3 subjects, that's 3 records.
- Named entities preserved: people, companies, tools, specific numbers.
- Hierarchical context included: "Stage 3" not just "pipeline," "Lever 1" not just "marketing."

### 2.2 Summary (column: `summary`)

A faithful, meaning-preserving summary of what was discussed about the topic. 2-5 sentences.

**The summary must pass this test:** If you read only the summary and never saw the original conversation, would you reach the same conclusions about what was discussed, decided, or discovered? If no → the summary is diluted or distorted.

**Rules:**
- Preserve specificity: numbers, names, decisions, disagreements, open questions.
- Preserve directionality: "Sean decided X" is not the same as "X was discussed."
- Preserve uncertainty: "Being proposed X but no decision was reached" ≠ "X was decided."
- No editorializing: "An interesting discussion about..." — cut "interesting." That's distortion.
- No hedging additions: Don't add "which could be beneficial" or "this may help" if the original didn't.

### 2.3 Raw Excerpt (column: `raw_excerpt`)

The **verbatim** text from the conversation that anchors the topic. Not paraphrased. Not cleaned up. Copy-paste from the source.

**Rules:**
- Minimum 1 sentence, maximum 500 words.
- Must include the most substantive exchange on the topic — not the greeting, not the sign-off.
- If a single exchange is too long, take the **densest** passage (most decisions/insights per sentence).
- Preserve all original language including contractions, slang, typos, and emphasis.
- If the source is a being-to-being exchange, include both sides.

### 2.4 Metadata (column: `metadata`, JSONB)

```json
{
  "window_start": "2026-03-23T08:00:00Z",
  "window_end": "2026-03-23T11:59:59Z",
  "source_type": "session_transcript | shared_memory | file_change | voice_call",
  "source_ref": "session_id or file path or call_id",
  "being_role": "Prime Orchestrator | Colosseum operator | etc.",
  "extraction_model": "model_id used for summarization",
  "extraction_timestamp": "2026-03-23T12:00:03Z",
  "word_count_original": 2847,
  "word_count_summary": 89,
  "confidence": "high | medium | low"
}
```

**Confidence levels:**
- **High**: Clean transcript, single clear topic, verbatim excerpt available.
- **Medium**: Noisy source, topic inferred from context, excerpt required trimming.
- **Low**: Partial transcript, ambiguous topic boundary, or source was file diffs rather than conversation. Flagged for human review.

---

## 3. No-DDnD Quality Gate

The three rules are non-negotiable. Every capture cycle runs these checks before INSERT.

### 3.1 No Deletion — Nothing Omitted

> **Rule:** Every distinct topic discussed by any being in the 4-hour window MUST appear as a record. No filtering by importance, relevance, or perceived value.

**Implementation:**
1. **Topic count verification**: After extraction, count distinct topics per being. Compare against a rough topic estimate from the raw transcript (e.g., count topic-shift markers: question changes, "now let's...", "moving on to...", new subject headers).
2. **If topic_count_extracted < topic_count_estimated × 0.8** → flag as potential deletion. The cycle does NOT skip the record — it inserts what it has AND creates an anomaly flag in the audit log.
3. **No importance filter exists.** There is no "skip if trivial" logic anywhere in the pipeline. A 30-second discussion about a typo fix gets a record just like a 30-minute strategy session. The filtering happens at read-time, never at write-time.

**Verification question:** "If I compared every sentence in the original transcript against the captured topics, would every sentence map to at least one topic?" If no → deletion occurred.

### 3.2 No Dilution — Specificity Preserved

> **Rule:** Summaries must preserve the precision of the original. General summaries that lose named entities, numbers, decisions, or specific context are diluted.

**Implementation:**
1. **Named Entity Check**: Extract named entities from the raw excerpt (people, companies, numbers, dates, technical terms). Verify that ≥90% of named entities from the excerpt appear in the summary. If not → dilution detected.
2. **Specificity Score**: Summaries containing any of these phrases are auto-flagged:
   - "discussed various topics"
   - "talked about operations"
   - "covered several items"
   - "general discussion of"
   - "explored different approaches"
   - Any summary under 15 words for a topic that generated >200 words of raw transcript.
3. **Dilution flag** does NOT block the insert. The record goes in with `metadata.quality_flags: ["dilution_warning"]` so it can be retroactively improved.

### 3.3 No Distortion — Meaning Preserved

> **Rule:** Raw excerpts must be verbatim. Summaries must not reframe, editorialize, add interpretation, or shift the meaning of what was said.

**Implementation:**
1. **Verbatim enforcement**: The `raw_excerpt` field is populated by direct copy from the source transcript. No post-processing, no grammar correction, no cleanup. If the being said "gonna" the excerpt says "gonna."
2. **Directional consistency check**: If the source says "Sean rejected the proposal," the summary cannot say "the proposal was discussed" (omitting the rejection = distortion by omission) or "Sean had concerns about the proposal" (softening = distortion by reframing).
3. **Sentiment preservation**: If the conversation was contentious, the summary reflects contention. If it was celebratory, the summary reflects that. Flattening emotional tone is distortion.
4. **Distortion flag** triggers on: any summary containing qualifiers not present in the original ("potentially," "arguably," "in a sense") or removing qualifiers that were present ("definitely" in source becoming unmarked in summary).

### 3.4 Quality Gate Decision Matrix

| Check | Result | Action |
|---|---|---|
| All 3 pass | Clean | INSERT normally |
| Deletion flag | Topics may be missing | INSERT what we have + flag + create backfill task |
| Dilution flag | Summary too vague | INSERT with flag + queue re-summarization |
| Distortion flag | Meaning may be shifted | INSERT with flag + queue human review |
| Multiple flags | Compound issue | INSERT with all flags + priority alert |

**Critical principle:** The gate NEVER blocks an insert. It flags. The no-DDnD mandate means we'd rather have a flagged imperfect record than a missing one. Blocking = deletion.

---

## 4. Deduplication Rules

### 4.1 Core Dedup Logic

The `dedup_hash` column in `discussion_log` is:
```
SHA-256(being_id || topic || 4-hour-window-bucket)
```

Where `4-hour-window-bucket` = `date_trunc('day', captured_at) + interval '4 hours' * floor(extract(hour from captured_at) / 4)`

**Result:** Same being + same topic + same 4-hour window = same hash = `ON CONFLICT DO NOTHING`.

### 4.2 Cross-Being Independence

**Different beings discussing the same topic produce SEPARATE records.** This is by design.

Example: If Prime and Recovery both discuss "Stage 3 appeals bottleneck" in the same window:
- Record 1: `being_id=prime`, `topic=Stage 3 appeals bottleneck...`, `dedup_hash=abc123`
- Record 2: `being_id=recovery`, `topic=Stage 3 appeals bottleneck...`, `dedup_hash=def456`

Different `being_id` → different hash → both preserved. Each being's perspective matters independently.

### 4.3 Topic Boundary Precision

The `topic` field is part of the hash, so topic granularity directly affects dedup behavior:

- **Too broad** ("pipeline discussion") → collapses distinct subtopics into one record → **deletion by aggregation**
- **Too narrow** ("pipeline discussion sentence 47") → creates noise records → wastes storage but preserves everything

**The bias is toward too narrow.** In a no-DDnD system, false splits (extra records) are acceptable. False merges (lost records) are not.

### 4.4 Re-run Safety

If a capture cycle is re-run (retry, backfill), the `ON CONFLICT DO NOTHING` ensures no duplicates. This makes the pipeline **idempotent** — safe to re-run any cycle at any time.

---

## 5. Failure Handling

### 5.1 Failure Modes

| Failure | Impact | Detection |
|---|---|---|
| **Cron doesn't fire** | Entire cycle missed | Heartbeat monitor: if no `capture_audit_log` entry exists within 15 min of expected fire time |
| **Being source unavailable** | One being's data missing for one cycle | Per-being success/fail tracking in audit log |
| **Postgres write failure** | Records extracted but not persisted | INSERT response check; records held in local buffer |
| **Extraction model failure** | Topics/summaries not generated | Model API error catch; raw data preserved for retry |
| **Partial extraction** | Some topics captured, others missed | Topic count check (Section 3.1) |

### 5.2 Retry Logic

```
Attempt 1: Normal capture at HH:00
  │
  ├─ Success → done
  │
  └─ Failure →
      ├─ Wait 5 minutes
      ├─ Attempt 2: Retry failed beings only at HH:05
      │   ├─ Success → done
      │   └─ Failure →
      │       ├─ Wait 15 minutes
      │       ├─ Attempt 3: Retry at HH:20
      │       │   ├─ Success → done
      │       │   └─ Failure → ALERT + queue for manual backfill
      │       └─ (max 3 automatic retries per cycle)
      └─ Between retries: raw session data is buffered locally
         at /workspaces/prime/capture_buffer/{window_id}/{being_id}.json
```

**Retry scope:** Only the failed beings/steps retry. Successful captures are not re-run.

### 5.3 Backfill Procedure

For missed cycles that exhaust retries:

1. **Create a backfill task** in the task system:
   - Title: `BACKFILL: Discussion capture for {window_id}`
   - Priority: `high`
   - Contains: list of affected beings and the window timestamps

2. **Manual backfill execution:**
   ```
   Trigger: Operator or Prime runs backfill task
   Input:  window_start, window_end, being_ids[]
   Process: Same extraction pipeline, same quality gate
   Output: INSERT ON CONFLICT DO NOTHING (idempotent — safe even if partial data exists)
   ```

3. **Backfill window:** Source data (session logs, shared memory) must be available. Session logs are retained for **minimum 7 days**. Backfills older than 7 days may have degraded source data — flagged as `confidence: low`.

### 5.4 Alerting

| Severity | Condition | Action |
|---|---|---|
| **INFO** | Cycle completed, all beings captured | Log only |
| **WARN** | One being failed, retries succeeded | Log + note in audit |
| **ERROR** | One being failed after all retries | Task created + alert to Prime |
| **CRITICAL** | Entire cycle failed (Postgres down, cron broken) | Immediate alert to Prime + manual intervention required |

---

## 6. Audit Trail

### 6.1 Capture Audit Log

Every cycle produces an audit record (separate from `discussion_log`):

```json
{
  "audit_id": "uuid",
  "cycle_window": "2026-03-23T08:00-12:00Z",
  "fired_at": "2026-03-23T12:00:01Z",
  "completed_at": "2026-03-23T12:00:47Z",
  "beings_in_scope": ["prime", "forge", "recovery", "sai-memory", "scholar"],
  "beings_active": ["prime", "recovery", "scholar"],
  "beings_inactive": ["forge", "sai-memory"],
  "per_being_counts": {
    "prime": {"topics": 7, "inserts": 7, "dedup_skips": 0, "flags": 0},
    "recovery": {"topics": 3, "inserts": 3, "dedup_skips": 0, "flags": 1},
    "scholar": {"topics": 2, "inserts": 2, "dedup_skips": 0, "flags": 0}
  },
  "total_inserts": 12,
  "total_dedup_skips": 0,
  "total_flags": 1,
  "flag_details": [
    {"being": "recovery", "topic": "...", "flag_type": "dilution_warning"}
  ],
  "retries": 0,
  "status": "complete"
}
```

### 6.2 Completeness Verification

Run after every cycle to answer: **"Did we capture everything?"**

**Check 1 — Session Coverage:**
```sql
-- For each being active in the window:
-- Count of sessions with activity vs. count of sessions that produced ≥1 topic
-- If sessions_with_activity > sessions_with_topics → gap detected
```

**Check 2 — Topic Density Sanity:**
```sql
-- Average topics per being per window (rolling 7-day baseline)
-- If current cycle's count for any being is <50% of their 7-day average
-- AND the being was active → anomaly flag
```

**Check 3 — Cross-Reference with Shared Memory:**
```
-- Read sessions_read_shared_memory for each being
-- Every shared_memory write with scope='committed' should map to ≥1 discussion_log topic
-- Unmatched shared_memory writes → potential deletion
```

**Check 4 — Zero-Activity Confirmation:**
```
-- For beings marked "inactive" in the audit:
-- Verify they truly had no sessions, no file changes, no memory writes
-- If ANY activity found → reclassify as active + trigger backfill for that being
```

### 6.3 Weekly Audit Report

Generated every Monday 08:00 UTC. Aggregates:

| Metric | Purpose |
|---|---|
| Total records inserted (7 days) | Volume trend |
| Records per being per day | Balance check — is one being silent? |
| Quality flags by type | Are we improving or degrading? |
| Dedup skip count | Are topics being over-narrowed (too few skips) or over-broadened (too many)? |
| Retry count | Infrastructure health |
| Backfill tasks created | Reliability indicator |
| Average topics per cycle | Baseline for anomaly detection |

---

## 7. Implementation Checklist

### Immediate (to activate the pipeline):

- [ ] **Deploy `discussion_log` schema** to Postgres (the-technologist's `discussion_log_schema.sql`)
- [ ] **Create `capture_audit_log` table** (schema: fields from Section 6.1)
- [ ] **Register cron schedule**: `0 0,4,8,12,16,20 * * *` UTC via `schedule_task`
- [ ] **Build capture orchestrator** task/skill that executes the sequence in Section 1.2
- [ ] **Build extraction module** that reads session data and produces topic/summary/excerpt triples
- [ ] **Build quality gate module** that runs no-DDnD checks (Section 3)
- [ ] **Build audit module** that produces the audit record (Section 6.1)
- [ ] **Create local buffer directory**: `/workspaces/prime/capture_buffer/`
- [ ] **Set up heartbeat monitor**: Alert if no audit record appears within 15 min of scheduled fire

### Second phase (operational maturity):

- [ ] Weekly audit report generation (Section 6.3)
- [ ] Dashboard view using `v_recent_discussions` and `v_topic_frequency` (from schema)
- [ ] Automated re-summarization queue for dilution-flagged records
- [ ] Cross-being topic correlation (which topics are being discussed by multiple beings?)
- [ ] Trend analysis: topic emergence and decay over time

---

## Appendix A: Being Registry (Current)

| being_id | Display Name | Workspace | Model | Role |
|---|---|---|---|---|
| `prime` | SAI Prime | `/workspaces/prime` | anthropic/claude-opus-4.6 | Prime Orchestrator |
| `forge` | Sai Forge | `/workspaces/forge` | minimax/minimax-m2.5 | Colosseum operator |
| `recovery` | Sai Recovery | `/workspaces/recovery` | minimax/minimax-m2.5 | Medical revenue recovery |
| `sai-memory` | SAI Memory | `/workspaces/sai-memory` | google/gemini-3.1-flash-lite-preview | Central Memory Manager |
| `scholar` | Sai Scholar | `/workspaces/scholar` | minimax/minimax-m2.5 | Pattern learner |

New beings are added to the registry. The pipeline discovers them via `sisters_list` + Prime — no code changes needed.

## Appendix B: Glossary

| Term | Definition |
|---|---|
| **Cycle** | One 4-hour capture run (C0–C5) |
| **Window** | The 4-hour time range a cycle covers |
| **no-DDnD** | No Deletion, No Dilution, No Distortion — the quality mandate |
| **Dedup hash** | SHA-256(being_id + topic + window_bucket) — prevents duplicate records |
| **Backfill** | Re-running a capture cycle for a missed window |
| **Quality flag** | A warning attached to a record that passed the gate but triggered a check |
| **Capture buffer** | Local JSON files holding raw data between extraction and Postgres insert |

---

_This spec is the Operator's deliverable. It pairs with the-technologist's `discussion_log_schema.sql` to form the complete pipeline definition. The schema is the WHERE (Postgres structure). This spec is the HOW (operational process)._
