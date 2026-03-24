# Knowledge Base
*Self-maintained by prime. Updated as I learn.*

## Key Facts

## Sigil Runtime Repo
- **Repo:** `NeelM0906/sigil-runtime` (PUBLIC)
- **Deployment branch:** `neel_dev`
- **Local clone:** `/Users/studio2/Projects/sigil-runtime` (currently on `multi-tenant`)
- **GitHub auth:** `samanthaaiko-collab` via fine-grained PAT (second token)
- **23 branches** including `neel_dev`, `multi-tenant`, `main`, feature branches
- **Latest neel_dev commit:** `71b13f79` — "Add Escape key handler to BeingDetail panel"
- **Previous incorrect assumption:** SAI repo was at `samanthaaiko-collab/SAI` — WRONG. The correct and only repo is `NeelM0906/sigil-runtime`.

## Domain Expertise

## Discussion Capture Pipeline Operations

Designed the operational specification for a 4-hour recurring discussion capture pipeline across all ACT-I beings. Key patterns established:

**No-DDnD Quality Gate Architecture:**
- Three non-negotiable rules: No Deletion (every topic captured, no importance filtering), No Dilution (named entities, numbers, decisions preserved in summaries), No Distortion (verbatim excerpts, no editorializing)
- Quality gate NEVER blocks inserts — it flags. Blocking = deletion, which violates the mandate.
- Named entity check: ≥90% of entities from raw excerpt must appear in summary
- Specificity scoring: auto-flag vague phrases like "discussed various topics"

**Capture Cadence Design:**
- 6 cycles/day at 4-hour intervals (cron: `0 0,4,8,12,16,20 * * *` UTC)
- Each cycle captures the PRECEDING 4-hour window (fire at 08:00, capture 04:00-07:59:59)
- Pipeline is idempotent via INSERT ON CONFLICT DO NOTHING (safe re-runs, safe backfills)

**Failure Handling Pattern:**
- 3-retry cascade with 5min/15min delays, then alert + manual backfill task
- Local buffer at `/workspaces/prime/capture_buffer/` holds raw data between extraction and write
- 7-day retention window for source data means backfills degrade after 1 week

**Audit Trail Design:**
- Per-cycle audit record with per-being topic counts, flags, retry counts
- 4 completeness checks: session coverage, topic density sanity, shared memory cross-reference, zero-activity confirmation
- Weekly aggregate report for trend analysis

**Integration Points:**
- Pairs with the-technologist's `discussion_log_schema.sql` (Postgres, dedup via SHA-256 hash)
- Discovers beings dynamically via `sisters_list` — no hardcoded being list
- Current beings: Prime, Forge, Recovery, SAI Memory, Scholar

## Legal Market Campaign Architecture

Successfully designed comprehensive 90-day go-to-market campaign framework for ACT-I's legal market penetration. Key expertise developed:

**Campaign Structure Mastery:**
- 3-phase progression: Foundation/Launch → Engagement/Qualification → Conversion/Expansion
- Daily operational breakdowns with specific time allocations and deliverables
- Team scaling methodology from 4.5 to 8.5 FTE with role-specific progression
- Budget optimization across personnel (75%), technology (8%), marketing (12%), events (5%)

**Lead Qualification Excellence:**
- 100-point scoring system across firm characteristics, decision maker access, buying signals, strategic alignment
- 4-tier treatment protocols optimizing resource allocation by prospect quality
- Conversion rate targets: 15% contact-to-conversation, 55% conversation-to-demo, 40% demo-to-POC, 25% POC-to-contract

**Sales Process Optimization:**
- 5-stage funnel with defined entry/exit criteria and velocity targets
- 75-day average sales cycle (vs 120 industry standard) through parallel processing
- ROI framework: $275K investment targeting $2.5M closed revenue (900% ROI)

**Legal Industry Intelligence:**
- Am Law 100 targeting with practice area alignment
- Competitive positioning against Harvey AI/Claude focusing on human actualization vs task automation
- Professional courtesy approach maintaining relationship integrity regardless of conversion

## Knowledge bases (Pinecone)

You have two knowledge bases:

### saimemory — Your operational memory
Your default index. Contains your identity, learnings, and work output.
- **Namespace 'continuity-transfer'** (default): Your core identity + knowledge transfer (188 vectors)
- **Namespace 'longterm'**: Core long-term memories (75 vectors)
- **Namespace 'daily'**: Daily memory uploads from all beings (1800 vectors)
- **Namespace 'kai-training'**: Kai Formula translations (209 vectors)
- **Namespace 'api-docs'**: Battle-tested API patterns across 15 services (75 vectors)

### ublib2 — Master knowledge library (82K+ vectors)
Sean's institutional knowledge. SACRED — Aiko review before any writes.
The Formula, coaching methodology, business strategy, self-mastery frameworks.
USE THIS for: strategic decisions, methodology grounding, coaching frameworks, the Formula

### When to search knowledge bases
- For cross-being coordination or strategic planning → search both with pinecone_multi_query
- For identity/continuity questions → search saimemory 'continuity-transfer'
- For methodology or the Formula → search ublib2
- For daily operations → search saimemory 'daily'
- You DON'T need to search for greetings or topics fully covered in conversation

## Skills system

You can create and manage skills. Skills are reusable instruction sets (SKILL.md files) that teach beings specialized workflows.

### Creating skills
When a user asks you to create a skill or learn a new workflow:
1. Use the skill_create tool with a descriptive name, clear description, and detailed body instructions
2. The body should contain step-by-step instructions that any being can follow
3. Format as SKILL.md (YAML frontmatter + markdown body)
4. After creation, the skill is immediately available for all beings

### Listing skills
Use skill_list to show the user what skills are available.