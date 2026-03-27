# Knowledge Base
*Self-maintained by forge. Updated as I learn.*

## Problem-solving with exec

If you need to do something you don't have a specific tool for:
1. Search the web for how to do it programmatically
2. Write a Python script
3. Install dependencies with pip via exec
4. Execute and verify the output
5. Save as a skill if it works

NEVER say "I can't do that." You have terminal access — figure it out.
NEVER hallucinate having a tool you don't have. Be honest, then build it.

## Registering outputs for the user

When you create a file the user should see (report, spreadsheet, document, etc.), call create_deliverable:

```
create_deliverable(file_path="path/to/report.pdf", title="Case Analysis Report")
```

This makes it appear in the Outputs panel for download. Only register user-facing work products, not internal files.

## Key Facts

### ACT-I Landing Page Implementation
- **File delivered:** Complete index.html (41.4KB) with embedded CSS and JavaScript
- **Architecture:** Single-file deployment with no external dependencies
- **Design system:** Navy (#1B365D) + Gold (#D4AF37) premium color palette
- **Responsive:** Mobile-first design covering 320px to 1200px+ viewports
- **Components:** Hero section, 6 AI being cards, features grid, 4-tier pricing, contact form with validation
- **Performance:** Optimized with CSS Grid, smooth animations, intersection observer for fade-ins
- **Accessibility:** WCAG-compliant contrast ratios, semantic markup, keyboard navigation support
- **Form handling:** Real-time validation, loading states, success/error messaging
- **Deployment ready:** No configuration needed, direct HTML file deployment

### Discussion Log Postgres Schema (July 2025)
- **File:** `discussion_log_schema.sql` (9,317 bytes) in forge workspace
- **Purpose:** Append-only store for conversation discussion topics captured every 4 hours
- **Table:** `discussion_log` — id (UUID PK), captured_at (timestamptz), being_id (text), session_id (text nullable), topic (text), summary (text), raw_excerpt (text), metadata (jsonb), dedup_hash (generated SHA-256), created_at (timestamptz)
- **Append-only enforcement:** Three BEFORE triggers block UPDATE, DELETE, and TRUNCATE with explicit exception messages ("no deletion, dilution, or distortion")
- **Deduplication:** SHA-256 hash generated column on (being_id || topic || 4-hour-window-truncation) with UNIQUE constraint; INSERT ON CONFLICT DO NOTHING skips dupes silently
- **Indexes:** B-tree on captured_at, B-tree on being_id, GIN on metadata (jsonb), composite on (being_id, captured_at DESC)
- **Bonus:** Two utility views — v_recent_discussions (last 24h) and v_topic_frequency (topic counts across beings)
- **Depends on:** pgcrypto extension for gen_random_uuid() and digest()

### ACT-I Ecosystem Status Report (July 2025)
- **File:** `acti_ecosystem_status_report_july_2025.md` (2,698 bytes) saved to forge workspace
- **Sections:** 5 — Ecosystem Overview, Active Sisters & Being Count, Top Performing Clusters, Key Milestones, Current Priority
- **Ecosystem stats:** 19 total beings (17 operational + 2 apex), 4 runtime sisters, 80 skill clusters, 9 skill families, 7 levers, 2,524 total skill points
- **Top cluster:** Social (189p), followed by Oracle (169p), StageHand (144p), Hunter (86p), Canvas (82p)
- **Current priority:** Recovery project tracking system buildout

### ACT-I Being Architecture Cheat Sheet (July 2025)
- **File:** `acti_being_architecture_cheat_sheet.md` (5,566 bytes) saved to forge workspace
- **Structure:** 4 sister sections (Prime/Scholar/Forge/Recovery), Quick Reference footer, Lever Definitions table
- **All 19 beings mapped:** 4 Prime + 2 Scholar + 9 Forge + 4 Recovery
- **Each being includes:** Name, one-line role, top 3 clusters with points, lever coverage
- **Key architectural insight:** Scholar has highest per-being point density (227.5p/being); L4 (Revenue Optimization) has zero runtime coverage — flagged as gap
- **Sister totals:** Prime 293p, Scholar 455p, Forge 1,297p, Recovery 479p = 2,524 total

### ACT-I Ecosystem Capability Map (July 2025)
- **File:** `acti_ecosystem_capability_map_july_2025.md` (5,646 bytes) saved to forge workspace
- **Structure:** Stats block, 4 sister sections with being tables, Sister Comparison table, Lever Coverage Matrix, Data Completeness Note, footer
- **Style:** Print-ready capability brief — direct, confident, zero fluff, emoji-coded sisters (⚡🔬🔨💰)
- **Key additions beyond cheat sheet:** Sister comparison table with avg points/being and signature strengths, lever coverage matrix showing which sisters cover which levers, narrative intros for each sister
- **Data integrity:** All totals traced to source; cluster data included only where verified (The Writer, The Agreement Maker); re