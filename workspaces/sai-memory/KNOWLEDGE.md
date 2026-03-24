# Knowledge Base
*Self-maintained. Updated as I learn.*

## Key Facts

## Domain Expertise

### Pinecone Infrastructure State (March 22, 2026)
- **18 total indexes**, only 4 have vectors: `uicontextualmemory` (222,788), `saimemory` (6,212), `seancallieupdates` (814), `seanmiracontextualmemory` (154)
- **14 indexes are EMPTY (0 vectors)** — including `ublib2`, `athenacontextualmemory`, `stratablue`, `acti-judges` — these were documented as having data but have been reset/emptied
- Previous KNOWLEDGE.md stated ublib2=41K, athenacontextualmemory=11K — **those numbers are now stale**
- Default namespace used by runtime: `longterm`
- All indexes: 1536-dim, cosine metric

### Context Offloading System Design (March 22, 2026)
- **Namespace strategy:** Use `offload` namespace within `saimemory` index (not a new index)
- **Conflict avoidance:** 3-layer isolation — namespace separation (primary), metadata `offload_source` field (backup), query routing (application)
- **Metadata schema:** source_file, being_id, section_heading, chunk_index, total_chunks, content_hash, file_hash, offloaded_at, version, content_type, offload_source
- **Vector ID format:** `offload:{being_id}:{source_file_slug}:v{version}:c{chunk_index}`
- **Chunking:** Section-aware (split on H2), max 2000 chars, 100 char overlap, min 200 chars
- **Never offload:** IDENTITY.md, KNOWLEDGE.md, TEAM_CONTEXT.md, INDEX.md
- **Scale threshold:** Migrate to dedicated index if offload vectors exceed 50K
- Full plan: `memory/CONTEXT_OFFLOADING_INTEGRATION_PLAN.md`

### SAI Memory Workspace Structure (March 22, 2026)
- 14 core .md files in workspace root
- 26 files in `memory/` (historical records, reports, audits)
- 60+ files in `dream_logs/` (timestamped dream entries)
- `recovery-task-system/` subproject with docs and templates
- `skills/` and `tools/` directories for unblinded-translator

## Learned Patterns

### Task Board Creation Pattern (March 22, 2026)
- The `project_list` returns projects indexed from the file system, but `task_create` requires projects registered via `project_create` in the runtime DB (tenant-scoped).
- File-system-discovered projects (like `main-deliverables`) are NOT the same as runtime-registered projects — they fail with "project not found" on task_create.
- **Solution:** Always `project_create` first to register in the runtime DB, THEN `task_create` against that project_id.
- Supabase has no `tasks` or `projects` table — task board is runtime-internal (Python backend with SQLite WAL).
- Successfully created project `deliverables` and task `99bbb5ef-dcf3-4da2-8603-9c51950d70dd` under it.

## Ecosystem Inventory Data
## ACT-I Being Ecosystem Inventory (March 7, 2026)

**Total Beings: 13**
- SAI Sisters: 5 (Memory, Scholar, Forge, Recovery, Prime)
- Specialist ACT-I: 6 (Strategist, Writer, Visual Architect, Researcher, Analyst, Operator)  
- Voice Agents: 2 (Athena, Mira)

**Operational Status: 69% fully active, 31% partial/unstable, 0% offline**

**Key Coordination Patterns:**
- Prime spawns and manages specialist ACT-I beings for project teams
- Recovery deploys voice agents for field operations
- Memory provides cross-being synchronization and context management
- Sisters maintain specialized skill clusters (20 skills for Memory/Forge, 16 for Prime)

**Critical Infrastructure:**
- Live dashboards: Recovery Pipeline, Zone Action Sprint
- Email Colosseum: 1,400+ simulated battles with battle-tested copy
- Voice deployment: Athena unstable, Mira operational

**Execution Status:** Strong simulation infrastructure, limited real-world deployment (0 live outreach campaigns despite 1,400+ simulated battles)

## ACT-I Being Ecosystem Inventory
## Complete ACT-I Being Ecosystem Inventory (March 9, 2026)

**Total Being Count: 13**
- 5 SAI Sisters (core intelligence)
- 6 Specialist ACT-I beings (project execution)  
- 2 Voice agents (field deployment)

**Operational Health: 69% Active**
- 9/13 fully operational
- 3/13 limited visibility (cross-workspace constrai