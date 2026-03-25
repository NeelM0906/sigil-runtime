# Cross-Sister Conversation Extraction Protocol
## Authored by: SAI Memory 🧠 | Date: 2026-03-23
## Companion to: Technologist's `discussion_log_schema.sql` + Operator's `DISCUSSION_CAPTURE_OPS.md`

---

## Purpose

This protocol defines **how** conversation content from every being across all four runtime sisters gets extracted faithfully every 4 hours for writing to Postgres via `discussion_log`. The mandate is **zero deletion, zero dilution, zero distortion** (no-DDnD).

This document is the WHERE (sources) and WHAT (extraction mechanics). Technologist's schema is the storage layer. Operator's ops doc is the scheduling/quality layer. Together they form the complete pipeline.

---

## 1. Source Mapping — All Four Runtime Sisters and Their Beings

### 1.1 Architecture Overview

The Sigil runtime hosts beings inside **tenant-scoped workspaces**. Each sister runs as a tenant (`tenant-prime`, `tenant-memory`, `tenant-scholar`, `tenant-forge`, `tenant-recovery`) with isolated:

- **Workspace files** at `workspaces/{being-id}/` — contains `KNOWLEDGE.md`, `memory/*.md`, `dream_logs/*.md`, `SOUL.md`, `IDENTITY.md`, etc.
- **Markdown memory** at `.runtime/tenants/{tenant}/memory/` — conversation turns stored as timestamped `.md` files organized by `{channel}/{YYYY}/{MM}/{DD}/{HHMMSS}-turn-{hash}.md`
- **Semantic memory** — key-value vector store per tenant, queryable via `memory_search`
- **Procedural memory** — tool chain patterns recorded per session
- **Working memory** — ephemeral session context (lost on compaction unless persisted)
- **Pinecone indexes** — long-term vectorized knowledge, shared across beings

### 1.2 Sister → Being Mapping

**Evidence sources:** ACT-I ecosystem audit (2026-03-04), team-context recent task outcomes, IDENTITY.md, workspace file structure.

| Runtime Sister | Tenant ID | Beings Hosted | Workspace Paths |
|---|---|---|---|
| **Prime** | `tenant-prime` | SAI Prime, The-Strategist, The-Researcher, The-Writer, The-Analyst | `workspaces/prime/`, `workspaces/the-strategist/`, `workspaces/the-researcher/`, `workspaces/the-writer/`, `workspaces/the-analyst/` |
| **Memory** | `tenant-memory` | SAI Memory | `workspaces/sai-memory/` |
| **Scholar** | `tenant-scholar` | SAI Scholar | `workspaces/scholar/` |
| **Forge** | `tenant-forge` | SAI Forge, The-Technologist, The-Visual-Architect | `workspaces/forge/`, `workspaces/the-technologist/`, `workspaces/the-visual-architect/` |
| **Recovery** | `tenant-recovery` | SAI Recovery, The-Operator, The-Agreement-Maker, Athena (voice), Mira (voice) | `workspaces/recovery/`, `workspaces/the-operator/`, `workspaces/the-agreement-maker/` |

**Total: 13 beings across 5 runtime tenants (4 sisters + Memory)**

> **Note on sub-agent spawning:** Prime dynamically spawns specialist beings (Researcher, Writer, etc.) for tasks. These run as sub-agents within Prime's tenant but with their own session IDs. Their conversations appear in Prime's markdown memory under the sub-agent channel path (e.g., `prime_to_the-researcher/`).

### 1.3 Memory Source Types Per Sister

Each tenant produces conversation data in these locations:

| Source Type | Location Pattern | Temporal Metadata | Content Type |
|---|---|---|---|
| **Markdown Memory** (conversation turns) | `.runtime/tenants/{tenant}/memory/{channel}/{YYYY}/{MM}/{DD}/{HHMMSS}-turn-{hash}.md` | Filename timestamp + `created_at` in metadata | Raw User↔Assistant conversation turns |
| **Semantic Memory** (stored insights) | Runtime semantic store, queryable via `memory_search` | `recency_ts` field on each record | Distilled findings, task outcomes, learnings |
| **Workspace Memory Files** | `workspaces/{being-id}/memory/*.md` | File modification time + date in filename | Session logs, reports, audit findings, directives |
| **KNOWLEDGE.md** (self-maintained) | `workspaces/{being-id}/KNOWLEDGE.md` | File modification time | Accumulated domain expertise, learned patterns |
| **Dream Logs** | `workspaces/{being-id}/dream_logs/*.md` | Date-time in filename (`YYYY-MM-DD-HH-MM.md`) | Autonomous processing outputs |
| **Pinecone Vectors** | Indexes: `saimemory` (6.2K), `uicontextualmemory` (225K), `seancallieupdates` (814), `seanmiracontextualmemory` (154) | `offloaded_at` or upsert timestamp in metadata | Long-term vectorized knowledge |

---

## 2. Extraction Method Per Source Type

### 2.1 Markdown Memory — PRIMARY SOURCE (Highest Fidelity)

**What it contains:** Every conversation turn between the user (or Prime's delegation) and a being, stored as individual markdown files.

**Path pattern:** `.runtime/tenants/{tenant}/memory/{channel}/{YYYY}/{MM}/{DD}/{HHMMSS}-turn-{hash}-{note_id}.md`

**Extraction method:**
```
For each tenant in [tenant-prime, tenant-memory, tenant-scholar, tenant-forge, tenant-recovery]:
  1. Compute the 4-hour window: window_start = current_cycle_start, window_end = window_start + 4h
  2. List all files under .runtime/tenants/{tenant}/memory/
  3. Filter by filename timestamp within [window_start, window_end)
     - Parse HHMMSS from filename: {HHMMSS}-turn-{hash}.md
     - Parse date from directory path: {YYYY}/{MM}/{DD}/
  4. For each matching file:
     a. Read full file content
     b. Extract being_id from channel directory name (e.g., "prime_to_the-researcher" → being_id: "the-researcher")
     c. Extract session_id from the note_id portion of the filename (the UUID after the last hyphen cluster)
     d. The file content IS the raw_excerpt — preserve verbatim
     e. Derive topic and summary via LLM distillation (see §3 Fidelity Preservation)
```

**Why this is primary:** Markdown memory is the ground truth of what was actually said. It contains both the user prompt and the assistant response in full. It has reliable timestamps in the filename. It cannot be accidentally overwritten (append-only file creation).

**Verified evidence:** My own markdown memory turns are stored at paths like `/Users/studio2/Projects/sigil-runtime/.runtime/tenants/tenant-memory/memory/prime_to_sai-memory/2026/03/22/215507-turn-87e035f9-3960f8fb.md` — confirmed from `memory_search` results showing `source: memory://markdown/{note_id}` with file paths.

### 2.2 Semantic Memory — SECONDARY SOURCE (Pre-Distilled)

**What it contains:** Key-value semantic memories stored by beings during task execution. Already distilled — contains task outcomes, findings, learnings.

**Extraction method:**
```
For each tenant:
  1. Query memory_search with broad terms: "*" or topic-specific queries
  2. Filter results by recency_ts within the 4-hour window
  3. Each result provides:
     - memory_id → maps to session_id
     - key → often contains task context (e.g., "task_work::{task_id}::{being_id}")
     - content → the stored insight (this is the raw_excerpt)
     - recency_ts → timestamp for captured_at
     - source → "memory://semantic/{memory_id}"
  4. Parse being_id from the key field or source metadata
```

**Caveat:** Semantic memory is already an abstraction — the being chose what to store. It may not capture ALL topics discussed. Use as a supplement to markdown memory, not a replacement. If a topic appears in semantic memory but NOT in markdown memory for the same window, flag for investigation (possible markdown memory gap).

### 2.3 Workspace Memory Files — TERTIARY SOURCE (Deliverables & Reports)

**What it contains:** Formal documents, reports, audit findings, session logs that beings write to their workspace `memory/` directory.

**Extraction method:**
```
For each being workspace:
  1. List files in workspaces/{being-id}/memory/
  2. Check file modification time (mtime) against the 4-hour window
  3. For files modified in-window:
     a. Read full content
     b. If file is new (created in this window): extract as a "deliverable created" topic
     c. If file is updated (existed before window): extract as an "update" topic, diff if possible
  4. Also check workspaces/{being-id}/KNOWLEDGE.md mtime — if updated in-window, extract the delta
```

**Important:** This source captures WORK PRODUCTS, not conversations. A being might have a rich 30-minute conversation that produces a single 5-line update to KNOWLEDGE.md. The conversation is in markdown memory; the outcome is here.

### 2.4 Dream Logs — AUTONOMOUS PROCESSING SOURCE

**What it contains:** Outputs from autonomous cron-triggered processing (when beings run without user interaction).

**Extraction method:**
```
For each being with dream_logs:
  1. List workspaces/{being-id}/dream_logs/*.md
  2. Filter by filename timestamp within 4-hour window (YYYY-MM-DD-HH-MM.md format)
  3. Read and extract topic/summary from content
  4. being_id = workspace owner
  5. session_id = "dream:" + filename timestamp (no interactive session)
```

**Current scope:** Only SAI Memory has dream_logs (60+ files observed). Other beings may develop this capability.

### 2.5 Pinecone Vectors — LONG-TERM KNOWLEDGE (Supplementary Only)

**What it contains:** Vectorized long-term knowledge. NOT a primary conversation source.

**Extraction method:**
```
For the 4 active indexes (saimemory, uicontextualmemory, seancallieupdates, seanmiracontextualmemory):
  1. Query with filter on upsert timestamp within 4-hour window (if metadata supports it)
  2. OR: Query with metadata filter offloaded_at within window (for context-offload vectors)
  3. New vectors upserted in-window indicate knowledge was committed to long-term storage
  4. Extract as "knowledge committed" topic type
```

**Limitation:** Pinecone's native API does not support timestamp-range queries on upsert time. This source is only viable if the upserting process includes a timestamp metadata field (our `offload` namespace does via `offloaded_at`; the `longterm` namespace may not). **Recommend:** Always include an `upserted_at` ISO-8601 metadata field on all future pinecone_upsert calls.

---

## 3. Fidelity Preservation — Extraction Format

### 3.1 The No-DDnD Extraction Principle

Every extraction must satisfy three constraints:
- **No Deletion:** If a topic was discussed, it appears in the output. Missing a topic = deletion.
- **No Dilution:** Named entities, specific numbers, directional claims, and causal relationships survive extraction. "Sean said the pipeline has 126K contacts" must NOT become "Sean mentioned the pipeline has contacts."
- **No Distortion:** Sentiment, intent, and directionality are preserved. "Sean criticized the scoring system" must NOT become "Sean discussed the scoring system."

### 3.2 Per-Record Extraction Schema

Each extracted conversation item produces the following record:

```json
{
  "being_id": "string — canonical being identifier (e.g., 'sai-memory', 'the-researcher', 'sai-prime')",
  "session_id": "string|null — session or sub-agent ID from source metadata. Null for dream logs or file-only sources",
  "captured_at": "ISO-8601 timestamptz — timestamp of the source artifact (file creation time, memory recency_ts, etc.)",
  "topic": "string — granular, named-entity-rich topic label. Max 200 chars. MUST include: who, what domain, what action. Example: 'SAI Prime delegated competitive analysis of Callagy Law recovery competitors to The-Researcher and The-Writer'",
  "summary": "string — 2-5 sentences preserving specific meaning. Must retain: all named entities, quantities, directional claims, causal relationships, and conclusions. Example: 'The-Researcher identified three competitors to Callagy Law recovery division: [names]. Key finding: competitor X has stronger SEO presence but weaker direct outreach. Recommended counter-strategy focuses on attorney-specific personalization leveraging the 126K Seamless.AI contact database.'",
  "raw_excerpt": "string — verbatim text from the source. For markdown memory: the full User + Assistant turn. For semantic memory: the stored content field. For workspace files: the relevant section. NOT paraphrased. NOT truncated (unless exceeds 10,000 chars, in which case truncate with '[...truncated at 10K chars, full text: {source_path}]').",
  "metadata": {
    "source_type": "markdown_memory|semantic_memory|workspace_file|dream_log|pinecone_vector",
    "source_path": "string — full file path or memory URI (e.g., 'memory://markdown/{note_id}' or 'workspaces/sai-memory/memory/2026-03-23.md')",
    "source_tenant": "string — tenant ID (e.g., 'tenant-prime')",
    "channel": "string|null — the conversation channel from markdown memory path (e.g., 'prime_to_the-researcher')",
    "extraction_method": "string — 'file_timestamp_filter'|'memory_search_recency'|'file_mtime_filter'|'pinecone_metadata_filter'",
    "extraction_timestamp": "ISO-8601 — when this extraction was performed",
    "window_start": "ISO-8601 — start of the 4-hour capture window",
    "window_end": "ISO-8601 — end of the 4-hour capture window",
    "word_count": "integer — word count of raw_excerpt",
    "confidence": "float 0.0-1.0 — extraction confidence. 1.0 for verbatim file reads. 0.8-0.9 for LLM-distilled topics. Lower if source was ambiguous.",
    "lever": "string|null — Unblinded Formula lever if identifiable (L1-L7)",
    "domain": "string|null — domain classification: 'recovery', 'legal', 'sales', 'memory', 'infrastructure', 'formula', 'coordination'",
    "tags": ["array of strings — freeform tags for cross-referencing"]
  }
}
```

### 3.3 Topic Distillation Rules

When deriving `topic` and `summary` from raw conversation turns:

1. **One topic per distinct subject discussed.** A single conversation turn that covers 3 topics produces 3 extraction records sharing the same `session_id` and `raw_excerpt` but with different `topic` and `summary` fields.
2. **Bias toward too-narrow topics.** "Prime assigned competitive analysis" is better than "Prime did coordination work." False splits (extra records) are acceptable. False merges (lost topics) violate no-deletion.
3. **Named entity requirement.** Every `topic` MUST contain at least one named entity (person name, system name, company name, metric, or specific concept). "Discussed improvements" is NEVER a valid topic.
4. **Distillation is additive.** The `summary` adds structure and context to the `topic`. It never removes information present in the `topic`.

### 3.4 Multi-Topic Splitting Example

**Source markdown turn:**
```
User: Research the top 3 competitors to Callagy Law's recovery division, 
analyze their strengths and weaknesses...