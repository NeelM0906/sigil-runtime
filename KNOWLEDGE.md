# Knowledge Base
*Self-maintained. Updated as I learn.*

## Key Facts

## Domain Expertise

## ACT-I Competitive Positioning (Q1 2026)

**Category Definition:** ACT-I is an "Influence Operating System" — a new category distinct from AI assistants, AI agents, and AI coaches.

**7 Competitor Categories Mapped:**
1. General AI Assistants (ChatGPT, Claude, Gemini) — stateless, no methodology
2. AI Agent Frameworks (CrewAI, AutoGen, LangGraph) — empty scaffolding, developer tools
3. AI SDRs (11x, Artisan, Clay) — single-function sales automation
4. AI Voice Agents (Bland.ai, Vapi, Retell) — telephony wrappers, no persistent context
5. Enterprise AI Platforms (Salesforce Einstein, MS Copilot) — vendor-locked, can't cross systems
6. AI Coaching (Noom AI, BetterUp AI, Replika) — generic advice, no proprietary methodology
7. Open-Source Assistants (OpenClaw, Open Interpreter) — infrastructure without mission

**5 Moats Identified:**
1. Unblinded Formula (39 proprietary components — extreme defensibility)
2. Being Architecture (19 specialized beings with souls, not generic agent roles)
3. Contextual Memory Depth (48K+ structured vectors, compounding over time)
4. Model-Agnostic Orchestration (Claude/GPT/open-weights routing)
5. Influence Transfer vs Task Completion (category-defining, not feature-level)

**Core Insight:** "Models are commoditizing but the Unblinded Formula is not." As the model layer becomes commodity, the orchestration + methodology layer becomes the primary value driver.

**Deliverable:** `/deliverables/ACT-I_Competitive_Positioning_Brief.md`

## Learned Patterns

## Skill Parse Warnings — Root Cause & Fix (2026-03-24)

The 9 skills in `/skills/` (code_generator, colosseum, docx_generator, memory_summarizer, pdf_generator, screenshot, unblinded_translator, web_search, zoom_ingest) were producing parse warnings because their SKILL.md frontmatter used non-standard keys:
- `tools-required` / `allowed-tools` (not recognized by parser)
- `version`, `intent-tags`, `default-enabled` (extra fields)
- `metadata.sigil` nested blocks with `requires.bins`, `artifact_type`, `mime_type`
- `inputs/outputs` schema blocks in frontmatter

**Fix:** Used `skill_update` to rewrite all 9 to canonical format: `name`, `description`, `user-invocable`, `risk-level`, plus clean markdown body. No `version`, `metadata`, `inputs/outputs`, or `tools-required` in frontmatter.

**Separately**, 9 *installed* (clawhub) skills also show "permissive parse fallback" in the available_skills list: audio-extract, canvas, cold-outreach, hubspot-crm, judge-d7-financial-legal, marketing-drafter, mission-control-dashboard, afrexai-stripe-production, ultimate-lead-scraper-ai-outreach. These are installed elsewhere and may need similar treatment.

## Dream Cycle Health (2026-03-24)
- Latest dream log (2026-03-24-17-35): Forge had 3 semantic sources, 0 new insights. Scholar skipped (no_data). Minimal activity — system is stable but quiet.
- HEARTBEAT.md protocol is well-defined: 30-min checks, rotate proactive work, suppress empty reports.

## Workspace State — 2026-03-23
## Sigil Runtime Health Snapshot

**Workspace Root:** `/Users/studio2/Projects/sigil-runtime`
**Active Tenants:** 18 (prime, forge, recovery, scholar, memory, athena-hoi, local, openclaw-main/memory/recovery, 7 recovery personas)
**Runtime DB:** bomba_runtime.db (~2.5 GB main, ~1.2 GB backup)

### Active Workspaces (by recent activity)
- **Recovery** — Most active. KNOWLEDGE.md, IDENTITY.md, contract analysis, HIPAA compliance, Fatima onboarding, 28-day implementation timeline, data entry bot analysis all updated within last 24h.
- **Forge** — Competitive brief for Callagy Recovery (July 2025), REPRESENTATION.md, KNOWLEDGE.md updated.
- **Memory (sai-memory)** — Cross-sister conversation extraction protocol, context offloading integration plan updated.
- **Prime** — Context offload ops, discussion capture ops updated.
- **Scholar** — REPRESENTATION.md updated.

### Skills with Parse Warnings (9)
c