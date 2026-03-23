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

## Legal Market Campaign Architecture

Successfully designed comprehensive 90-day