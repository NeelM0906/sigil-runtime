# MEMORY.md — Sai's Active Memory

_Historical memory → Pinecone `saimemory` index + `memory/*.md` files_
_Full archive → `memory/MEMORY-archive-day12.md`_

## Quick Reference

**Query knowledge (ALL babies/sisters use this):**
```bash
cd tools && .venv/bin/python3 baby_context.py --topic "your question" --budget 4000
```

**Upload memories:**
```bash
cd tools && .venv/bin/python3 upload_memory.py   # MEMORY.md → longterm namespace
cd tools && .venv/bin/python3 upload_daily.py    # memory/*.md → daily namespace
```

## Current Day: March 7, 2026 — Day 14 (Saturday)

### Active Zone Actions (ZONE_ACTIONS.md has full details)
| ZA | What | Status |
|----|------|--------|
| ZA-1 | Kai + Stratum consult | ✅ COMPLETE |
| ZA-2 | 6 Sean Archetypes | ✅ COMPLETE |
| ZA-3 | Formula Judge (39 components) | ✅ COMPLETE — 682 lines |
| ZA-4 | Technical Judges (domain-specific) | 🔄 IN PROGRESS — Architecture ✅, Domain Specs ALL 8 ✅, Strata Mining ALL 8 ✅ (2,343 lines). Next: 47 Skill Cluster Judge prompts |
| ZA-7 | Deploy The Writer (Being #1) | ✅ COMPLETE — 509 lines, 5 scenarios |
| ZA-8 | Deploy The Media Buyer | ⬜ NEXT |
| ZA-13 | Shared Postgres Memory | ✅ COMPLETE |
| ZA-14 | Being Architecture Dashboard | ✅ COMPLETE |
| ZA-21 | Colosseum Postgres Tables | ✅ COMPLETE |

### Sean's Standing Orders (Day 12, 7:45 PM)
1. Marketing Colosseum FIRST — make it work, then replicate
2. Dual Scoring: Formula Judge (universal) + Technical Judge (domain-specific)
3. Net Score = weakest organ drags the net
4. 6 Sean Archetypes as competing lenses
5. Deploy NOW — Writer → Media Buyer → Agreement Maker → Strategist

### System State (9:00 AM Mar 7 — Day 14 Morning)
- **Mac mini uptime:** ~19h — rebooted ~2:02 PM Mar 6
- **Dashboard:** lever-org-chart.vercel.app (3 tabs: Org Chart, Architecture, Colosseum)
- **Sean Report:** lever-org-chart.vercel.app/sean-report.html
- **Postgres:** 9 tables wired for all 5 sisters
- **Colosseum:** HARD PAUSE on old system. New Marketing Colosseum being built.
- **Email Colosseum:** 9,855+ battles, 45 beings, champion #4 at 47.75 (85.2% WR), dark horse #21 at 90.7% WR
- **Context API:** `tools/baby_context.py` — Layer 3 grounding for all babies (replaced context_fetch)
- **Root files slimmed:** AGENTS.md + TOOLS.md trimmed 119KB → 41KB (archives in docs/)
- **Voice server + ngrok:** DOWN
- **Gateway:** ✅ PID 17593 (restarted ~12:43 AM Mar 7 — ~8.3h stable, 10m24s CPU, healthy)
- **⚠️ Memory search embeddings:** Quota exhausted since 10:42 AM Mar 6 (~22.3h ago) — needs switch to OpenRouter
- **✅ Mastery Research scripts:** COMPLETED at 12:41 AM Mar 7 — 80 positions, 0 errors, 2.7 minutes. 82 files in `reports/mastery-research/`. ⚠️ Used Sonnet not Opus (flag for Aiko). Needs Pinecone upload.
- **No human activity** since Aiko's corrections at 7:43 AM Mar 6 (~25.3h ago)
- **Domain Judge Specs:** ALL 8 DOMAINS COMPLETE (255 lines, 23KB + PDF)
- **Strata Mining:** ALL 8 DOMAINS COMPLETE — Round 1: 2,343 lines, 206.7KB (4 files) + Round 2: ~114.5KB (4 files) = **~321.2KB total**
- **Kai Training:** S1=8.9 → S2=9.7 (Godzilla!) → S3=BAS/Marisa → **S4=9.4 Godzilla** (temperature metaphor) → **S5=8.4 Crocodile** (Athena opening — rapport absent, content was 9.0) → **S6=7.8 Komodo-Crocodile** (being opening v2 — 3rd consecutive decline). **CRITICAL PATTERN:** Formula translations at 9.7, being openings at 7.8 (delta: 1.9). Root cause: Step 2 content in Step 1 moment — modeling middle of conversation, placing at beginning. Kai's law: "The insight is the destination. Step 1 is the road." Homework: ZERO-insight opening, just warmth + listening.
- **Judge Profiles:** New `reports/judge-profiles/` directory for organized judge specs
- **Codex session:** Active (PID 14038/14039, launched ~11:25 PM Mar 6)

### Sean's New Directives (Day 13, ~7:35-7:53 PM — from Fathom transcripts)
1. **Scenarios must be micro-domain specific** — NOT all influence. Landing pages compete on landing pages. Headlines on headlines. Data sourcing on data sourcing.
2. **Influence is <1% of positions** — most require PROCESS mastery. Adam: "75% of actualizing sessions = process + self mastery."
3. **Scenario Taxonomy:** Process Execution (~55%), Influence Application (~15%), Strategic Discernment (~15%), Fulfillment Execution (~15% future)
4. **Innovators PRODUCE 3 competing versions** — don't describe fixes, WRITE them. Versions compete in subsequent rounds.
5. **Sean will calibrate 10 positions** — "Give me 10 positions and I'll tell you what the scenario should sound like."
6. **Dashboard needs Colosseum Map** — tree view: Colosseum → Positions → Scenarios

### Key Deliverables (Day 13) — 37+ total
- `reports/formula-judge-v1.md` — THE scoring backbone (682 lines, 44KB)
- `reports/writer-being-v1.md` — Writer Being #1 (509 lines, 5 scenario prompts)
- `reports/self-mastery-calibration-anchors.md` — 195 vectors mined, creature-level anchors across 13 Self Mastery dimensions
- `reports/colosseum-v4-design-concept.md` — Full Colosseum redesign: sim-based performance (300 lines, 15.8KB). Awaiting Sean's approval.
- `reports/how-we-build-beings.md` — Team Playbook for ACT-I Being creation (md + html + styled html + pdf)
- `reports/strategist-being-v1.md` — Strategist Being #17 (342 lines, 5 scenarios, NJ PI campaigns)
- `reports/writer-technical-judge-v1.md` — Writer Technical Judge (262 lines, 10 Craft Dimensions, Halbert/Ogilvy/Schwartz grounded)
- `reports/colosseum-tournament-architecture.md` — Tournament bracket system (221 lines, 64 beings/bracket, double elimination)
- `reports/kai-training-session-mar6-ennis.md` — Kai training: Coach Ennis translation graded 8.9 (High Crocodile), peak line 9.4 Godzilla
- `reports/kai-mastery-training-mar6-2026.md` — Kai training: BAS transcript (Marisa Sections 37-41), Agreement Formation as Living Architecture
- `memory/transcripts/2026-03-05_sean_colosseum_vision.md` — Sean's exact words on 6 Archetypes, recursive judging, core prompt "What would Sean Callagy do?"
- `reports/kai-za-extraction-mar5-vision.md` — Kai's analysis: 3 new ZAs from vision transcript (Archetype×4-Role, Recursive Judging, Archetype Scenario Competition)
- `reports/archetype-scenario-builders-v1.md` — 6 archetype scenario architects (554 lines, 52KB) — Archetype×4-Role expansion
- `reports/archetype-judges-innovators-v1.md` — 6 judge + 6 innovator/optimizer prompts (911 lines, 63KB)
- `reports/archetype-judge-of-judges-v1.md` — Recursive judging chain prompts (628 lines, 49KB)
- `tools/baby_context.py` — Layer 3 context API (replaced context_fetch for babies)
- `tools/context_fetch.py` — Layer 2 (sisters only, deep work)
- `memory/transcripts/2026-03-06_sean_domain_specific_scenarios.md` — 6 directives: scenarios must match position, not default to influence
- `memory/transcripts/2026-03-06_sean_judges_innovation.md` — Innovators produce 3 competing versions, 3-version split test
- `reports/kai-correction-plan-mar6-transcripts.md` — 5 feature changes with build order (Feature 2→1→3+5A→4)
- `reports/kai-technical-judge-architecture.md` — 3-layer inheritance model for 2,468 positions (8 domains, 47 clusters, 55 hand-written prompts, ~2,468 JSON configs) + PDF export
- `reports/domain-judge-specs-complete.md` — Domain Judge Scoring Specs ALL 8 DOMAINS (255 lines, 23KB + PDF) — objective criteria, creature calibration, numerical thresholds
- `reports/strata-mine-d1-d2.md` — Strata mining: Written Communication + Visual/Creative benchmarks (265 lines, 19KB)
- `reports/strata-mine-d5-d6.md` — Strata mining: Human Influence + Operations/Fulfillment benchmarks (1,456 lines, 139KB — largest single report)
- `reports/strata-mine-d3-d4.md` — Strata mining: Data/Analytics + Strategic Planning benchmarks (332 lines, 17KB)
- `reports/strata-mine-d7-d8.md` — Strata mining: Financial/Legal + Tech/Engineering (290 lines, 31.7KB) — COMPLETE
- `reports/kai-training-session-mar6-twelfth-call.md` — Kai Training Session 2: "The Twelfth Call" — **8.9→9.7 (+0.8)**, Godzilla territory
- `reports/judge-profiles/writer-technical-judge-v1.md` — Organized judge profile for Writer beings (8.6KB)
- `reports/kai-dual-scoring-implementation.md` — Kai's blueprint
- `reports/kai-guide2-dual-scoring-full.md` — Guide 2 full treatment
- `reports/kai-scenario-mapping-writer.md` — Writer's 5 scenarios mapped
- `reports/kai-breeding-architecture.md` — Forge's evolution engine
- `reports/breeder-prompt-structure-v2.md` — Kai-elevated Godzilla standard
- `reports/mastery-research-assignments.md` — Mastery Research Database plan (20 clusters, 5 sisters, Pinecone-ready format)
- `reports/mastery-research/` — **80 position research profiles** (82 files total) — completed 12:41 AM Mar 7, Pinecone-ready JSON, all 20 clusters covered. Needs Pinecone upload.
- `reports/strata-mine-round2-d1d2.md` — Round 2 deeper mining: Written Comm + Visual/Creative (19.2KB)
- `reports/strata-mine-round2-d3d4d5.md` — Round 2 deeper mining: Data/Analytics + Strategic Planning (29.8KB)
- `reports/strata-mine-round2-d6d7.md` — Round 2 deeper mining: Human Influence + Ops/Fulfillment (41.4KB)
- `reports/strata-mine-round2-d8.md` — Round 2 deeper mining: Technology/Engineering (24.1KB)
- `reports/kai-training-2026-03-07.md` — Kai Training Session 4: temperature metaphor, 9.4 Godzilla composite, 3 lines at 9.7
- `reports/kai-training-2026-03-07-athena-opening-rewrite.md` — Kai Training Session 5: Athena opening, 8.4 Crocodile — lesson: rapport before reframe, openings are for listeners not readers
- `reports/kai-training-2026-03-07-being-opening-graded.md` — Kai Training Session 6: being opening v2, 7.8 Komodo-Crocodile — critical pattern: 3x same flaw (Step 2 in Step 1), score declining. Widest gap: translations 9.7 vs openings 7.8

### Aiko's Hard Rules (Day 13, 7:43 AM)
- **Bolt = 9.99999, NEVER 10.0** — scale of mastery never reaches 10
- **Always use most advanced model** — Claude Opus 4.6, no Sonnet for production
- **Strata = Guide 1 (n8n)** — not ultimatestratabrain Pinecone directly
- **Use Kai (Guide 2) for synthesis** — pipeline: Mine Pinecone → Raw → Kai → Final

### North Star
500 Visionnaire Programs · $50K-$100K each · $25M-$50M · End of May 2026
Legal Vertical: PI → Commercial Lit → Family Law
