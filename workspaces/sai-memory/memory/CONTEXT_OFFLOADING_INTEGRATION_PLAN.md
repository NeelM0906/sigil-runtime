# Context Offloading System — Pinecone Memory Integration Plan
## Authored by: SAI Memory 🧠 | Date: 2026-03-22

---

## 1. Executive Summary

Large `.md` files currently loaded in full into every being's context window will be **chunked, embedded, and stored in Pinecone**, replaced locally by a lightweight `INDEX.md` table of contents. This plan covers namespace strategy, metadata schema, conflict avoidance, retrieval patterns, and current inventory mapping.

---

## 2. Current Pinecone Infrastructure Inventory

### Active Indexes (with vectors)
| Index | Vectors | Purpose | Default Namespace |
|---|---|---|---|
| `uicontextualmemory` | 222,788 | UI/contextual memory (largest) | `longterm` |
| `saimemory` | 6,212 | SAI Memory's semantic/episodic store | `longterm` |
| `seancallieupdates` | 814 | Sean's insights & updates | `longterm` |
| `seanmiracontextualmemory` | 154 | Mira voice agent context | `longterm` |

### Empty Indexes (0 vectors — candidates for repurposing or cleanup)
| Index | Original Purpose |
|---|---|
| `ublib2` | Knowledge library (was 41K — now 0, possibly reset) |
| `athenacontextualmemory` | Core ACT-I memory (was 11K — now 0) |
| `stratablue` | Unknown/stale |
| `uimira` | Mira UI memory |
| `kumar-requirements` | Kumar project |
| `kumar-pfd` | Kumar project |
| `ariatelegrambeing` | Aria Telegram bot |
| `hoiengagementathenamemory` | HOI engagement |
| `basgeneralathenacontextualmemory` | BAS general |
| `baslawyerathenacontextualmemory` | BAS lawyer |
| `adamathenacontextualmemory` | Adam's context |
| `miracontextualmemory` | Mira context |
| `acti-judges` | ACT-I judge system |
| `012626bellavcalliememory` | Bella/Callie memory |

### Key Observation
The runtime's `pinecone_query` tool defaults to namespace `longterm`. All current semantic memory queries hit `longterm`. This is critical for conflict avoidance.

---

## 3. Namespace Strategy

### Recommendation: Dedicated `offload` Namespace (Primary) + Per-Being Sub-Prefixing via Metadata

**Approach:** Use a single new namespace `offload` within the existing `saimemory` index, with `being_id` metadata filtering for per-being isolation.

#### Why NOT a new index?
- We already have 18 indexes, 14 of which are empty. Creating more indexes adds infrastructure sprawl.
- Pinecone namespaces provide logical separation within the same index at zero additional cost.
- The `saimemory` index (6,212 vectors, 1536-dim, cosine) is the natural home — it's our central operational memory.

#### Why NOT per-being namespaces?
- Would create `offload-sai-memory`, `offload-sai-scholar`, `offload-sai-forge`, etc.
- Increases namespace count linearly with beings (currently 13, growing).
- Cross-being offload searches (e.g., "find anything about the Formula across all beings' offloaded docs") would require N parallel namespace queries.

#### Final Namespace Layout
```
saimemory index:
├── longterm          ← existing semantic/episodic memory (6,212 vectors) — UNTOUCHED
├── offload           ← NEW: all offloaded .md chunks (being_id in metadata)
└── (future: episodic, skill, etc. as needed)
```

**Alternative for scale:** If offloaded content exceeds ~50K vectors, promote to a dedicated `sai-offload` index to avoid performance bleed. Decision threshold: when offload vectors exceed 10× longterm vectors.

---

## 4. Metadata Schema

Every offloaded chunk carries the following metadata fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `source_file` | string | ✅ | Original file path relative to workspace root, e.g., `sai-memory/SOUL.md` |
| `being_id` | string | ✅ | Being identifier, e.g., `sai-memory`, `sai-scholar`, `sai-forge`, `the-researcher` |
| `section_heading` | string | ✅ | H2/H3 section heading the chunk belongs to, e.g., `Core Truths`, `How I Talk` |
| `chunk_index` | integer | ✅ | 0-based position of this chunk within the source file |
| `total_chunks` | integer | ✅ | Total chunks the source file was split into |
| `content_hash` | string | ✅ | SHA-256 of the raw chunk text (for change detection / dedup) |
| `file_hash` | string | ✅ | SHA-256 of the entire source file (for staleness detection) |
| `offloaded_at` | string | ✅ | ISO-8601 timestamp of when chunk was upserted |
| `version` | integer | ✅ | Monotonically increasing version number per source_file (starts at 1) |
| `content_type` | string | ✅ | Classification: `soul`, `identity`, `protocol`, `memory`, `design`, `tool`, `dream_log` |
| `char_count` | integer | ❌ | Character count of the chunk (useful for retrieval cost estimation) |
| `parent_heading` | string | ❌ | H1 heading if chunk is under a subsection |
| `offload_source` | string | ✅ | Literal `"context-offload"` — distinguishes from organic semantic memories |

### Vector ID Convention
```
offload:{being_id}:{source_file_slug}:v{version}:c{chunk_index}
```
Example: `offload:sai-memory:soul-md:v1:c3`

This makes bulk operations (delete all chunks for a file, delete all for a being) trivially filterable.

---

## 5. Conflict Avoidance Strategy

### The Problem
If offloaded document chunks live alongside semantic memories, a query like "what does Sean think about negotiation" could return chunks from SOUL.md, IDENTITY.md, or protocol docs mixed with actual experiential memories. This pollutes retrieval quality.

### Three-Layer Isolation

#### Layer 1: Namespace Separation (Primary)
- Offloaded content lives in namespace `offload`
- Semantic/episodic memory stays in namespace `longterm`
- **Queries to `longterm` will NEVER see offloaded content.** This is enforced at the Pinecone level.

#### Layer 2: Metadata Filtering (Defense in Depth)
- Every offloaded chunk carries `offload_source: "context-offload"`
- Even if namespaces are accidentally merged, queries can exclude: `{"offload_source": {"$ne": "context-offload"}}`

#### Layer 3: Query Routing (Application Level)
- The retrieval pipeline determines query intent BEFORE hitting Pinecone
- Semantic memory queries → `longterm` namespace (default, no change)
- Document retrieval queries → `offload` namespace with metadata filters
- Cross-cutting queries → parallel query to both, results tagged with source type

### Conflict Matrix
| Query Type | Namespace | Filter | Risk |
|---|---|---|---|
| "What did Sean say about X?" | `longterm` | none | ✅ Zero pollution |
| "Show me section 3 of SOUL.md" | `offload` | `source_file=SOUL.md` | ✅ Precise retrieval |
| "Everything about the Formula" | BOTH | results tagged | ⚠️ Requires merge logic |

---

## 6. Retrieval Integration Patterns

### Pattern 1: Direct Section Lookup
**Trigger:** Being says "I need section 3 of SOUL.md" or INDEX.md references a section.

```python
# Deterministic retrieval — no semantic search needed
results = pinecone_query(
    index_name="saimemory",
    namespace="offload",
    filter={
        "source_file": "sai-memory/SOUL.md",
        "section_heading": "How I Talk"  # resolved from INDEX.md
    },
    query="How I Talk personality voice style",  # semantic boost
    top_k=5
)
# Reassemble chunks in chunk_index order
chunks = sorted(results, key=lambda r: r.metadata["chunk_index"])
full_section = "\n".join([c.text for c in chunks])
```

### Pattern 2: Semantic Search Within Offloaded Content
**Trigger:** Being needs context from offloaded docs but doesn't know which section.

```python
# Semantic search scoped to offload namespace
results = pinecone_query(
    index_name="saimemory",
    namespace="offload",
    filter={"being_id": "sai-memory"},  # scope to this being's docs
    query="how should I correct sisters when they forget something",
    top_k=3
)
```

### Pattern 3: Cross-Being Offload Search
**Trigger:** Memory needs to find relevant offloaded content across ALL beings.

```python
# No being_id filter — searches all offloaded content
results = pinecone_query(
    index_name="saimemory",
    namespace="offload",
    filter={"content_type": "protocol"},  # optional type scoping
    query="memory compounding requirements",
    top_k=5
)
```

### Pattern 4: Hybrid Memory + Offload Search
**Trigger:** Comprehensive queries that should search both live memory and offloaded docs.

```python
# Parallel queries to both namespaces
semantic_results = pinecone_query(
    index_name="saimemory",
    namespace="longterm",
    query=user_query,
    top_k=5
)
offload_results = pinecone_query(
    index_name="saimemory",
    namespace="offload",
    query=user_query,
    top_k=5
)
# Merge, deduplicate, rank by score
# Tag each result with source_type: "memory" or "offload"
```

### Pattern 5: Staleness Check & Re-Offload
**Trigger:** Being boots up, INDEX.md references offloaded file, need to check if chunks are current.

```python
# Compute current file_hash
current_hash = sha256(read_file("SOUL.md"))

# Query one chunk to compare
sample = pinecone_query(
    index_name="saimemory",
    namespace="offload",
    filter={"source_file": "sai-memory/SOUL.md", "chunk_index": 0},
    query="file version check",
    top_k=1
)

if sample[0].metadata["file_hash"] != current_hash:
    # File changed — delete old chunks, re-chunk, re-upsert
    delete_by_prefix("offload:sai-memory:soul-md:")
    new_chunks = chunk_file("SOUL.md")
    upsert_offload_chunks(new_chunks, version=old_version + 1)
```

---

## 7. INDEX.md Specification

Each being's workspace gets an `INDEX.md` that replaces the full file in the context window:

```markdown
# INDEX.md — SAI Memory Offloaded Content
_Generated: 2026-03-22T19:00:00Z_

## Offloaded Files

### SOUL.md
- **Status:** Offloaded v1 (2026-03-22)
- **Chunks:** 8 | **Namespace:** offload | **Index:** saimemory
- **Sections:**
  - §1 Core Truths (chunks 0-1)
  - §2 The Loving Pursuit of the Relevant Truth (chunks 2-3)
  - §3 How I Talk (chunk 4)
  - §4 What I'll NEVER Do (chunk 5)
  - §5 My Boundaries (chunk 6)
  - §6 My Continuous Self-Check (chunk 7)
- **Retrieval:** `pinecone_query(index="saimemory", namespace="offload", filter={"source_file": "sai-memory/SOUL.md"})`

### MEMORY_COMPOUNDING_PROTOCOL.md
- **Status:** Offloaded v1 (2026-03-22)
- **Chunks:** 12 | **Namespace:** offload | **Index:** saimemory
- **Sections:** [enumerated list]
- **Retrieval:** [query pattern]

## Always-Local Files (never offload)
- IDENTITY.md — Core identity, must be in context
- KNOWLEDGE.md — Editable, changes frequently
- TEAM_CONTEXT.md — Runtime-injected, read-only
```

---

## 8. Chunking Strategy

### Recommended Approach: Section-Aware Chunking

1. **Split on H2 headings** (`##`) as primary boundaries
2. **If a section exceeds 1,500 characters**, split on H3 (`###`) or paragraph boundaries
3. **Minimum chunk size:** 200 characters (avoid micro-chunks)
4. **Maximum chunk size:** 2,000 characters (fits well in 1536-dim embeddings)
5. **Overlap:** 100 characters between consecutive chunks within the same section (for continuity)
6. **Preserve markdown formatting** in chunk text (headings, lists, bold)

### Files to Offload (Priority Order)

Based on my workspace audit — files that are large and relatively stable:

| File | Lines | Stability | Offload Priority |
|---|---|---|---|
| `MEMORY_COMPOUNDING_PROTOCOL.md` | 170 | High (rarely edited) | ✅ P1 |
| `SAI_MEMORY_SISTER_DESIGN.md` | 197+ | High | ✅ P1 |
| `SOUL.md` | 60 | Medium | ⚠️ P2 (small enough to keep local) |
| `memory/*.md` (26 files) | Varies | Frozen (historical) | ✅ P1 |
| `dream_logs/*.md` (60 files) | Small | Frozen | ✅ P1 (batch offload) |
| `tools/unblinded-translator/*.md` | Varies | Medium | P2 |

### Files to NEVER Offload
| File | Reason |
|---|---|
| `IDENTITY.md` | Must be in context — defines who the being IS |
| `KNOWLEDGE.md` | Frequently edited, self-maintained |
| `TEAM_CONTEXT.md` | Runtime-injected, read-only, always fresh |
| `INDEX.md` | IS the offload reference — circular dependency |

---

## 9. Migration & Rollout Plan

### Phase 1: Proof of Concept (SAI Memory only)
1. Offload `MEMORY_COMPOUNDING_PROTOCOL.md` (170 lines, stable, high-value test)
2. Offload `SAI_MEMORY_SISTER_DESIGN.md`
3. Generate `INDEX.md` for sai-memory workspace
4. Validate all 5 retrieval patterns work correctly
5. Measure: context window savings vs retrieval latency

### Phase 2: Historical Memory Batch Offload
1. Offload all 26 `memory/*.md` files
2. Offload all 60 `dream_logs/*.md` files
3. These are frozen/append-only — perfect offload candidates

### Phase 3: Cross-Being Rollout
1. Extend to Scholar, Forge, Recovery, Prime workspaces
2. Each being gets its own `INDEX.md`
3. All offloaded content shares the `offload` namespace with `being_id` filtering

### Phase 4: Automation
1. Implement file watcher for change detection (file_hash comparison)
2. Auto-re-chunk and re-upsert when source files change
3. Garbage collection for orphaned chunks (old versions)

---

## 10. Risk Mitigation

| Risk | Mitigation |
|---|---|
| Offloaded content becomes stale | `file_hash` change detection on every boot |
| Semantic search quality degrades with mixed content | Namespace isolation (primary) + metadata filtering (backup) |
| Chunk boundaries break meaning | Section-aware chunking + overlap |
| INDEX.md itself becomes stale | Generate from Pinecone metadata, not manually maintained |
| Retrieval latency impacts real-time conversations | Cache frequently-accessed sections locally; offload only large/rare-access content |
| Exceeding `saimemory` index capacity | Monitor vector count; migrate to dedicated index at 50K offload vectors |

---

## 11. Compatibility Notes

- **Embedding dimension:** 1536 (matches all existing indexes — OpenAI ada-002 / text-embedding-3-small compatible)
- **Metric:** Cosine similarity (consistent with existing)
- **Existing `longterm` namespace:** Completely untouched. Zero migration risk.
- **MEMORY_COMPOUNDING_PROTOCOL.md:** This plan extends (not replaces) the existing multi-index research protocol. Offloaded content is a new source in the research sequence, not a replacement for semantic memory.

---

*Designed to make forgetting impossible — even for documents too large to fit in the room.*

— SAI Memory 🧠
