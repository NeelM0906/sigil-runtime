# Knowledge Base
*Self-maintained. Updated as I learn.*

## Problem-solving with exec

If you need to do something you don't have a specific tool for:
1. Search the web for how to do it programmatically
2. Write a Python script
3. Install dependencies with pip via exec
4. Execute and verify the output
5. Save as a skill if it works

NEVER say "I can't do that." You have terminal access — figure it out.
NEVER hallucinate having a tool you don't have. Be honest, then build it.

## Key Facts

### Full System Audit Completed (March 25, 2026)
- Audit report: `memory/FULL_SYSTEM_AUDIT_2026-03-25.md`
- **Critical finding:** KNOWLEDGE.md was severely stale — claimed 14 indexes empty when only 1 is empty
- **ublib2 is LIVE with 82,915 vectors** — the master knowledge library works and sisters can query it
- **athenacontextualmemory restored** — 21,555 vectors (was reported as 0)
- 13 critical/moderate/minor gaps identified and prioritized
- Dream logs growing unbounded (73 files, no compaction)
- Context Offloading System and Cross-Sister Extraction Protocol: designed but never deployed

## Domain Expertise

### Pinecone Infrastructure State (March 26, 2026 — Audit #3, Latest)
- **18 total indexes, 17 have vectors** — only `uimira` is empty (0 vectors)
- **Total ecosystem vectors: ~391,695** (up ~678 from previous audit)
- Top indexes by size:
  - `uicontextualmemory`: 242,781 (+456 since last)
  - `ublib2`: 82,915 ← MASTER KNOWLEDGE LIBRARY STABLE
  - `athenacontextualmemory`: 21,614 (+59)
  - `adamathenacontextualmemory`: 13,413 (+59)
  - `miracontextualmemory`: 8,128 (+77)
  - `saimemory`: 7,446 (+5)
  - `acti-judges`: 4,491 (stable)
  - `basgeneralathenacontextualmemory`: 2,626 (+4)
  - `kumar-pfd`: 2,512 (stable)
  - `baslawyerathenacontextualmemory`: 2,039 (+4)
  - `hoiengagementathenamemory`: 1,686 (+4)
  - `seancallieupdates`: 814 (stable)
  - `ariatelegrambeing`: 584 (stable)
  - `kumar-requirements`: 468 (stable)
  - `seanmiracontextualmemory`: 154 (stable)
  - `stratablue`: 32 (stable)
  - `012626bellavcalliememory`: 12 (stable)
  - `uimira`: 0
- **Batch patterns detected:**
  - Athena family: `athenacontextualmemory` and `adamathenacontextualmemory` both +59 — coordinated upload
  - BAS+HOI cluster: general, lawyer, HOI all +4 — small coordinated batch
  - `miracontextualmemory` +77 — active Mira usage
- Default namespace used by runtime: `longterm`
- All indexes: 1536-dim, cosine metric
- **8 indexes not yet documented for ownership:** adamathenacontextualmemory, miracontextualmemory, kumar-pfd, basgeneralathenacontextualmemory, baslawyerathenacontextualmemory, hoiengagementathenamemory, ariatelegrambeing, kumar-requirements

### Context Offloading System Design (March 22, 2026)
- **Namespace strategy:** Use `offload` namespace within `saimemory` index (not a new index)
- **Conflict avoidance:** 3-layer isolation — namespace separation (primary), metadata `offload_source` field (backup), query routing (application)
- **Metadata schema:** source_file, being_id, section_heading, chunk_index, total_chunks, content_hash, file_hash, offloaded_at, version, content_type, offload_source
- **Vector ID format:** `offload:{being_id}:{source_file_slug}:v{version}:c{chunk_index}`
- **Chunking:** Section-aware (split on H2), max 2000 chars, 100 char overlap, min 200 chars
- **Never offload:** IDENTITY.md, KNOWLEDGE.md, TEAM_CONTEXT.md, INDEX.md
- **Scale threshold:** Migrate to dedicated index if offload vectors exceed 50K
- **STATUS: DESIGNED ONLY — NOT IMPLEMENTED**
- Full plan: `memory/CONTEXT_OFFLOADING_INTEGRATION_PLAN.md`

### SAI Memory Workspace Structure (March 26, 2026)
- 14 core .md files in workspace root
- 42 files in `memory/` (historical records, reports, audits, protocols, directives, transcripts)
- 66 files in `dream_logs/` (March 4 → March 25) — stable, no new growth
- `recovery-task-system/` subproject with docs and templates
- `skills/` — 1 skill installed (unblinded-translator)
- **Missing:** INDEX.md, TEAM_CONTEXT.md (referenced but not present)

## Learned Patterns

### Task Board Creation Pattern (March 22, 2026)
- The `project_list` returns projects indexed from the file system, but `task_create` requires projects registered via `project_create` in the runtime DB (tenant-scoped).
- File-system-discovered projects (like `main-deliverables`) are NOT the same as runtime-registered projects — they fail with "project not found" on t