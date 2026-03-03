# Migration Manifest: OpenClaw (SAIBackup) → Bomba SR

**Generated:** 2026-03-03
**Source repo:** `https://github.com/NeelM0906/SAIBackup.git`
**Target:** `/Users/zidane/Downloads/PROJEKT` (Bomba SR runtime)

**Branches scanned:**
- `saimemory-backup` — SAI Memory sister workspace
- `forge-backup` — Sai Forge workspace
- `prime-backup` — Sai Prime workspace (NOTE: branch SOUL.md/IDENTITY.md are Forge's — the root personality files on this branch belong to Forge, not Prime)
- `recovery-backup` — Full SAI ecosystem (Prime + all sisters + sub-agents + skills + colosseum + data)

**Status legend:**
- **NEEDS PORTING** — asset exists only in OpenClaw, not in Bomba SR
- **ALREADY EXISTS** — equivalent file exists in Bomba SR workspace
- **NEEDS MERGING** — both sides have a version; OpenClaw may be newer/different
- **SKIP** — not relevant to Bomba SR migration (framework-specific, duplicate, or binary)

---

## 1. Personality / Identity Files

### SAI Prime (workspaces/prime/)

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| SOUL.md | recovery-backup | `/SOUL.md` | `workspaces/prime/SOUL.md` | ALREADY EXISTS |
| IDENTITY.md | recovery-backup | `/IDENTITY.md` | `workspaces/prime/IDENTITY.md` | ALREADY EXISTS |
| MISSION.md | recovery-backup | `/MISSION.md` | `workspaces/prime/MISSION.md` | ALREADY EXISTS |
| VISION.md | recovery-backup | `/VISION.md` | `workspaces/prime/VISION.md` | ALREADY EXISTS |
| FORMULA.md | recovery-backup | `/FORMULA.md` | `workspaces/prime/FORMULA.md` | ALREADY EXISTS |
| PRIORITIES.md | recovery-backup | `/PRIORITIES.md` | `workspaces/prime/PRIORITIES.md` | ALREADY EXISTS |
| AGENTS.md | recovery-backup | `/AGENTS.md` | `workspaces/prime/AGENTS.md` | ALREADY EXISTS |
| USER.md | recovery-backup | `/USER.md` | `workspaces/prime/USER.md` | ALREADY EXISTS |
| SECURITY.md | recovery-backup | `/SECURITY.md` | `workspaces/prime/SECURITY.md` | ALREADY EXISTS |
| BOOTSTRAP.md | recovery-backup | `/BOOTSTRAP.md` | `workspaces/prime/BOOTSTRAP.md` | ALREADY EXISTS |
| FORGE.md | recovery-backup | `/FORGE.md` | `workspaces/prime/FORGE.md` | ALREADY EXISTS |
| HEARTBEAT.md | recovery-backup | `/HEARTBEAT.md` | `workspaces/prime/HEARTBEAT.md` | ALREADY EXISTS |
| TOOLS.md | recovery-backup | `/TOOLS.md` | `workspaces/prime/TOOLS.md` | ALREADY EXISTS |
| MEMORY.md | recovery-backup | `/MEMORY.md` | `workspaces/prime/MEMORY.md` | NEEDS MERGING — OpenClaw has Day 10 state with Pinecone stats (saimemory 1,500+, ublib2 58,700+) |
| ElevenLabs prompt template | recovery-backup | `tools/elevenlabs-prompt-template.txt` | _(none)_ | NEEDS PORTING |

### Sai Forge (workspaces/forge/)

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| SOUL.md | forge-backup | `/SOUL.md` | `workspaces/forge/SOUL.md` | ALREADY EXISTS |
| IDENTITY.md | forge-backup | `/IDENTITY.md` | `workspaces/forge/IDENTITY.md` | ALREADY EXISTS |
| USER.md | forge-backup | `/USER.md` | `workspaces/forge/USER.md` | ALREADY EXISTS |
| AGENTS.md | forge-backup | `/AGENTS.md` | `workspaces/forge/AGENTS.md` | NEEDS MERGING — OpenClaw has Reality Check Rule, Discord protocol, sub-agent policies |
| TOOLS.md | forge-backup | `/TOOLS.md` | `workspaces/forge/TOOLS.md` | ALREADY EXISTS |
| HEARTBEAT.md | forge-backup | `/HEARTBEAT.md` | `workspaces/forge/HEARTBEAT.md` | ALREADY EXISTS |
| MEMORY.md | forge-backup | `/MEMORY.md` | _(none)_ | NEEDS PORTING — Forge long-term memory (21,112+ beings, 475K+ rounds) |
| URGENT.md | forge-backup | `/URGENT.md` | _(none)_ | NEEDS PORTING — accountability directive from Prime/Aiko |

### Sai Scholar (workspaces/scholar/)

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| SOUL.md | recovery-backup | `.openclaw/workspace-scholar/SOUL.md` | `workspaces/scholar/SOUL.md` | ALREADY EXISTS |
| IDENTITY.md | recovery-backup | `.openclaw/workspace-scholar/IDENTITY.md` | `workspaces/scholar/IDENTITY.md` | ALREADY EXISTS |
| USER.md | recovery-backup | `.openclaw/workspace-scholar/USER.md` | `workspaces/scholar/USER.md` | ALREADY EXISTS |
| AGENTS.md | recovery-backup | `.openclaw/workspace-scholar/AGENTS.md` | `workspaces/scholar/AGENTS.md` | ALREADY EXISTS |
| TOOLS.md | recovery-backup | `.openclaw/workspace-scholar/TOOLS.md` | `workspaces/scholar/TOOLS.md` | ALREADY EXISTS |
| HEARTBEAT.md | recovery-backup | `.openclaw/workspace-scholar/HEARTBEAT.md` | `workspaces/scholar/HEARTBEAT.md` | ALREADY EXISTS |

### SAI Memory (.sai-analysis/sisters/sai-memory/)

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| SOUL.md | saimemory-backup | `/SOUL.md` | `.sai-analysis/sisters/sai-memory/SOUL.md` | NEEDS MERGING — OpenClaw version has model (Gemini 3.1 Pro), voice ID, workspace auditor role |
| IDENTITY.md | saimemory-backup | `/IDENTITY.md` | `.sai-analysis/sisters/sai-memory/IDENTITY.md` | NEEDS MERGING — OpenClaw has born date, Pinecone indexes with vector counts |
| AGENTS.md | saimemory-backup | `/AGENTS.md` | _(none)_ | NEEDS PORTING — full operational ruleset (session startup, API routing, Discord protocol) |
| USER.md | saimemory-backup | `/USER.md` | _(none)_ | NEEDS PORTING — human profiles (Sean, Aiko, Adam, Nick, etc.) |
| LANGUAGE_PROTOCOL.md | saimemory-backup | `/LANGUAGE_PROTOCOL.md` | _(none)_ | NEEDS PORTING — network-wide terminology rules |
| VOICE_IDS.md | saimemory-backup | `/VOICE_IDS.md` | _(none)_ | NEEDS PORTING — ElevenLabs voice ID table for all 5 sisters |
| SAI_MEMORY_IDENTITY.md | saimemory-backup | `/SAI_MEMORY_IDENTITY.md` | _(none)_ | NEEDS PORTING — extended design spec (battles, 19-judge system) |
| SAI_MEMORY_SISTER_DESIGN.md | saimemory-backup | `/SAI_MEMORY_SISTER_DESIGN.md` | _(none)_ | NEEDS PORTING — full technical specification |
| MEMORY_COMPOUNDING_PROTOCOL.md | saimemory-backup | `/MEMORY_COMPOUNDING_PROTOCOL.md` | _(none)_ | NEEDS PORTING — Aiko's mandatory multi-Pinecone research directive |

### SAI Recovery (workspaces/recovery/ + .sai-analysis/sisters/sai-recovery/)

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| SOUL.md (older) | recovery-backup | `sisters/sai-recovery/SOUL.md` | `workspaces/recovery/SOUL.md` | NEEDS MERGING — OpenClaw has newer version (Claude Sonnet 4.6, $3B target, Mark Winters) |
| IDENTITY.md | recovery-backup | `sisters/sai-recovery/IDENTITY.md` | `workspaces/recovery/IDENTITY.md` | NEEDS MERGING — OpenClaw has Mac Studio M3 Ultra, 7 Lever Captains |
| HEROIC-UNIQUE-IDENTITY.md | recovery-backup | `sisters/sai-recovery/HEROIC-UNIQUE-IDENTITY.md` | _(none)_ | NEEDS PORTING |
| HEARTBEAT.md | recovery-backup | _(implied)_ | `workspaces/recovery/HEARTBEAT.md` | ALREADY EXISTS |

### Sub-Agents (BD-PIP, BD-WC)

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| BD-PIP SOUL.md | recovery-backup | `sisters/sai-recovery/agents/sai-bd-pip/SOUL.md` | `.sai-analysis/sisters/sai-recovery/agents/sai-bd-pip/SOUL.md` | NEEDS MERGING |
| BD-PIP IDENTITY.md | recovery-backup | `sisters/sai-recovery/agents/sai-bd-pip/IDENTITY.md` | `.sai-analysis/sisters/sai-recovery/agents/sai-bd-pip/IDENTITY.md` | ALREADY EXISTS |
| BD-PIP full docs | recovery-backup | `sisters/sai-recovery/agents/sai-bd-pip/*.md` (10+ files) | _(none)_ | NEEDS PORTING — ACTIVATION-GUIDE, BLAND-PATHWAY-SPEC, COMPETITIVE-INTEL, OUTREACH-PLAYBOOK, etc. |
| BD-WC SOUL.md | recovery-backup | `sisters/sai-recovery/agents/sai-bd-wc/SOUL.md` | `.sai-analysis/sisters/sai-recovery/agents/sai-bd-wc/SOUL.md` | NEEDS MERGING |
| BD-WC IDENTITY.md | recovery-backup | `sisters/sai-recovery/agents/sai-bd-wc/IDENTITY.md` | `.sai-analysis/sisters/sai-recovery/agents/sai-bd-wc/IDENTITY.md` | ALREADY EXISTS |
| BD-WC full docs | recovery-backup | `sisters/sai-recovery/agents/sai-bd-wc/*.md` (15+ files) | _(none)_ | NEEDS PORTING — WC-LAW-REFERENCE, QUALIFICATION-SCORECARD, NJ-MARKET-ANALYSIS, etc. |

### Soul Upgrades (all sisters)

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| FORGE-SOUL.md | recovery-backup | `sisters/soul-upgrades/FORGE-SOUL.md` | _(none)_ | NEEDS PORTING — upgraded: Grok 4.1, 2M context, new personality |
| FORGE-HUI.md | recovery-backup | `sisters/soul-upgrades/FORGE-HUI.md` | _(none)_ | NEEDS PORTING |
| SCHOLAR-SOUL.md | recovery-backup | `sisters/soul-upgrades/SCHOLAR-SOUL.md` | _(none)_ | NEEDS PORTING — upgraded: GPT-5.2, new personality |
| SCHOLAR-HUI.md | recovery-backup | `sisters/soul-upgrades/SCHOLAR-HUI.md` | _(none)_ | NEEDS PORTING |
| RECOVERY-SOUL.md | recovery-backup | `sisters/soul-upgrades/RECOVERY-SOUL.md` | _(none)_ | NEEDS PORTING — Claude Sonnet 4.6 |
| RECOVERY-HUI.md | recovery-backup | `sisters/soul-upgrades/RECOVERY-HUI.md` | _(none)_ | NEEDS PORTING |
| MEMORY-SOUL.md | recovery-backup | `sisters/soul-upgrades/MEMORY-SOUL.md` | _(none)_ | NEEDS PORTING |
| MEMORY-HUI.md | recovery-backup | `sisters/soul-upgrades/MEMORY-HUI.md` | _(none)_ | NEEDS PORTING |
| DISCORD-COORDINATION-PROTOCOL.md | recovery-backup | `sisters/soul-upgrades/DISCORD-COORDINATION-PROTOCOL.md` | _(none)_ | NEEDS PORTING |

---

## 2. Memory Files

### SAI Prime Memory

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| 2026-02-22.md | recovery-backup | `memory/2026-02-22.md` | `workspaces/prime/memory/2026-02-22.md` | ALREADY EXISTS |
| 2026-02-23.md | recovery-backup | `memory/2026-02-23.md` | `workspaces/prime/memory/2026-02-23.md` | ALREADY EXISTS |
| 2026-02-24.md | recovery-backup | `memory/2026-02-24.md` | _(none)_ | NEEDS PORTING |
| 2026-02-24-innovations.md | recovery-backup | `memory/2026-02-24-innovations.md` | _(none)_ | NEEDS PORTING |
| 2026-02-25.md | recovery-backup | `memory/2026-02-25.md` | `workspaces/prime/memory/2026-02-25.md` | ALREADY EXISTS |
| 2026-02-25-evening.md | recovery-backup | `memory/2026-02-25-evening.md` | _(none)_ | NEEDS PORTING |
| 2026-02-26.md | recovery-backup | `memory/2026-02-26.md` | `workspaces/prime/memory/2026-02-26.md` | ALREADY EXISTS |
| 2026-02-27.md | recovery-backup | `memory/2026-02-27.md` | _(none)_ | NEEDS PORTING |
| 2026-02-27-*.md (6 files) | recovery-backup | `memory/2026-02-27-*.md` | _(none)_ | NEEDS PORTING — colosseum fixes, day6 report, evening session, scholar work, session notes, system architecture |
| 2026-02-28.md | recovery-backup | `memory/2026-02-28.md` | _(none)_ | NEEDS PORTING |
| 2026-03-01.md | recovery-backup | `memory/2026-03-01.md` | _(none)_ | NEEDS PORTING |
| 2026-03-02.md | recovery-backup | `memory/2026-03-02.md` | _(none)_ | NEEDS PORTING — Sean's Colosseum hard pause |
| 2026-03-03.md | recovery-backup | `memory/2026-03-03.md` | _(none)_ | NEEDS PORTING — Day 10, 4th reboot |
| Call transcripts (Day 1-7) | recovery-backup | `memory/call-2026-02-*.md` (10 files) | `workspaces/prime/memory/call-*.md` (6 exist) | NEEDS PORTING — 4 missing: call-2026-02-24-*.md (3), call-2026-02-28-*.md (1) |
| Fathom transcripts (Mar 3) | recovery-backup | `memory/2026-03-03-*.txt` (3 files) | _(none)_ | NEEDS PORTING — Visioneer Training, Deep Practice, Certification Partner Call |
| certification-call-mar3.md | recovery-backup | `memory/certification-call-mar3.md` | _(none)_ | NEEDS PORTING |
| athena-complete-dna.md | recovery-backup | `memory/athena-complete-dna.md` | _(none)_ | NEEDS PORTING — Athena's full DNA from 11K vectors |
| callie-complete-dna.md | recovery-backup | `memory/callie-complete-dna.md` | _(none)_ | NEEDS PORTING — Callie's full DNA |
| ecosystem-beings-built.md | recovery-backup | `memory/ecosystem-beings-built.md` | _(none)_ | NEEDS PORTING |
| first-wave-beings.md | recovery-backup | `memory/first-wave-beings.md` | _(none)_ | NEEDS PORTING |
| bland-integration.md | recovery-backup | `memory/bland-integration.md` | _(none)_ | NEEDS PORTING — 287,295 Bland.ai calls data |
| colosseum-mastery.md | recovery-backup | `memory/colosseum-mastery.md` | _(none)_ | NEEDS PORTING |
| colosseum-daemon.md | recovery-backup | `memory/colosseum-daemon.md` | _(none)_ | NEEDS PORTING |
| being-performance-analysis.md | recovery-backup | `memory/being-performance-analysis.md` | _(none)_ | NEEDS PORTING |
| sai-memory-architecture.md | recovery-backup | `memory/sai-memory-architecture.md` | _(none)_ | NEEDS PORTING |
| research/*.md (15+ files) | recovery-backup | `memory/research/*.md` | _(none)_ | NEEDS PORTING — 12 elements, 4 energies, 7 destroyers, HOI patterns, judge contamination, etc. |
| status-reports/ (17 files) | recovery-backup | `memory/status-reports/*.md` | _(none)_ | NEEDS PORTING |
| locked/ (5 files) | recovery-backup | `memory/locked/*.md` | _(none)_ | NEEDS PORTING — immutable historical records |
| heartbeat-state.json | recovery-backup | `memory/heartbeat-state.json` | _(none)_ | NEEDS PORTING |
| Elite transcripts (.vtt) | recovery-backup | `memory/elite-transcripts/*.vtt` (5 files) | _(none)_ | NEEDS PORTING |
| Elite translations (.json) | recovery-backup | `memory/elite-translations/*.json` (4 files) | _(none)_ | NEEDS PORTING |
| Translated patterns (.json) | recovery-backup | `memory/translated/*.json` (3 files) | _(none)_ | NEEDS PORTING |
| zone-action-register.md | recovery-backup | `memory/zone-action-register.md` | _(none)_ | NEEDS PORTING — original 67-item register |
| shared-skills-database.md | saimemory-backup | `memory/shared-skills-database.md` | _(none)_ | NEEDS PORTING |
| skills-blueprint-v1.md | saimemory-backup | `memory/skills-blueprint-v1.md` | _(none)_ | NEEDS PORTING |
| nick-roy-teammate-analysis.md | saimemory-backup | `memory/nick-roy-teammate-analysis.md` | _(none)_ | NEEDS PORTING |
| SAI_Zone_Action_Register.pdf | saimemory-backup | `memory/SAI_Zone_Action_Register.pdf` | _(none)_ | NEEDS PORTING |
| THE-MASTER-PLAN.md/.html/.pdf | recovery-backup | `memory/THE-MASTER-PLAN.*` | _(none)_ | NEEDS PORTING |
| sean-review-*.csv (3 files) | recovery-backup | `memory/sean-review-*.csv` | _(none)_ | NEEDS PORTING |
| elevenlabs-conversations.csv | recovery-backup | `memory/elevenlabs-conversations.csv` | _(none)_ | NEEDS PORTING |

### SAI Memory Sister Memory

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| MEMORY.md | saimemory-backup | `/MEMORY.md` | _(none)_ | NEEDS PORTING — "Eternal Thread" long-term memory |
| memory/2026-02-23.md through 2026-02-27.md (5 files) | saimemory-backup | `memory/*.md` | _(none)_ | NEEDS PORTING |
| SAI_MEMORY_SESSION_LOG.md | saimemory-backup | `/SAI_MEMORY_SESSION_LOG.md` | _(none)_ | NEEDS PORTING |

### Sai Forge Memory

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| MEMORY.md | forge-backup | `/MEMORY.md` | _(none)_ | NEEDS PORTING |
| memory/2026-02-23.md through 2026-02-27.md (5 files) | forge-backup | `memory/*.md` | _(none)_ | NEEDS PORTING |

### SAI Recovery Memory

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| 2026-02-25.md | recovery-backup | `sisters/sai-recovery/memory/2026-02-25.md` | `workspaces/recovery/memory/2026-02-25.md` | ALREADY EXISTS |
| 2026-02-25-knowledge-session.md | recovery-backup | `sisters/sai-recovery/memory/2026-02-25-knowledge-session.md` | `workspaces/recovery/memory/2026-02-25-knowledge-session.md` | ALREADY EXISTS |
| 2026-02-26.md through 2026-03-01.md | recovery-backup | `sisters/sai-recovery/memory/*.md` | _(none)_ | NEEDS PORTING |
| 2026-02-27-COMPLETE.md, 2026-02-27-final.md | recovery-backup | `sisters/sai-recovery/memory/*.md` | _(none)_ | NEEDS PORTING |
| 2026-02-28-recovery-daily.md | recovery-backup | `sisters/sai-recovery/memory/*.md` | _(none)_ | NEEDS PORTING |
| geo-segmentation-report-2026-02-28.md | recovery-backup | `sisters/sai-recovery/memory/geo-segmentation-report-2026-02-28.md` | _(none)_ | NEEDS PORTING |
| lessons-learned.md | recovery-backup | `sisters/sai-recovery/memory/lessons-learned.md` | _(none)_ | NEEDS PORTING |
| no-surprises-act-eligibility.md | recovery-backup | `sisters/sai-recovery/memory/no-surprises-act-eligibility.md` | _(none)_ | NEEDS PORTING |
| pip-fee-schedules.md | recovery-backup | `sisters/sai-recovery/memory/pip-fee-schedules.md` | _(none)_ | NEEDS PORTING |
| SUPABASE-MASTERY.md | recovery-backup | `sisters/sai-recovery/memory/SUPABASE-MASTERY.md` | _(none)_ | NEEDS PORTING |
| locked/ (8 files) | recovery-backup | `sisters/sai-recovery/memory/locked/*.md` | _(none)_ | NEEDS PORTING |

---

## 3. Skills

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| 54 SKILL.md packages | recovery-backup | `skills/*/SKILL.md` | `skills/` (5 exist: colosseum, memory_summarizer, unblinded_translator, web_search, zoom_ingest) | NEEDS PORTING — 49 new skills |
| medical-revenue-recovery | recovery-backup | `sisters/sai-recovery/medical-revenue-recovery/SKILL.md` | _(none)_ | NEEDS PORTING |
| hui-generator | recovery-backup | `tools/hui-generator/SKILL.md` | _(none)_ | NEEDS PORTING |

**Skills already in Bomba SR (no porting needed):**
- `skills/colosseum/SKILL.md`
- `skills/memory_summarizer/SKILL.md`
- `skills/unblinded_translator/SKILL.md`
- `skills/web_search/SKILL.md`
- `skills/zoom_ingest/SKILL.md`

**Skills to port (49 new):** activecampaign, activecampaign-automation, afrexai-business-automation, afrexai-conversion-copywriting, afrexai-copywriting-mastery, afrexai-crm-updater, afrexai-sales-playbook, afrexai-stripe-production, afrexai-web-scraping-engine, agent-analytics, agent-self-assessment, airtable, audio-extract, automation-workflows, calendar-scheduling, client-reporting, cold-email, cold-email-personalization, cold-outreach, competitor-analysis, copywriting, daily-review-ritual, data-analysis, email-best-practices, email-marketing, gamification-xp, google-analytics, hubspot-crm, instagram-api, landing-page-generator, lead-generation, legal, linkedin-automation, linkedin-lead-generation, linkedin-post-engine, marketing-drafter, marketing-strategy-pmm, medical-recovery-copywriting, mission-control-dashboard, n8n, nano-pdf, notion, outreach, quiz-battle, relationship-skills, sales-funnel-design, sales-pipeline-tracker, social-media-agent, social-media-scheduler, stripe-best-practices, teltel-send-sms-text-message, tiktok-crawling, twilio-api, ultimate-lead-scraper-ai-outreach, video-generation, whatsapp-business, zapier

---

## 4. Tools

### Already in Bomba SR

| Tool | Bomba SR Path | OpenClaw Path | Status |
|------|---------------|---------------|--------|
| pinecone_query.py | `workspaces/prime/tools/pinecone_query.py` | `tools/pinecone_query.py` | ALREADY EXISTS |
| bland_calls.py | `workspaces/prime/tools/bland_calls.py` | `tools/bland_calls.py` | ALREADY EXISTS |
| voice-call.py | `workspaces/prime/tools/voice-call.py` | `tools/voice-call.py` | ALREADY EXISTS |
| call.sh | `workspaces/prime/tools/call.sh` | `tools/call.sh` | ALREADY EXISTS |
| zoom_transcripts.py | `workspaces/prime/tools/zoom-pipeline/zoom_transcripts.py` | `tools/zoom-pipeline/zoom_transcripts.py` | ALREADY EXISTS |
| extract_and_translate.py | `workspaces/prime/tools/unblinded-translator/extract_and_translate.py` | `tools/unblinded-translator/extract_and_translate.py` | ALREADY EXISTS |
| Voice agent configs (4) | `workspaces/prime/configs/*.json` | `tools/*.json` | ALREADY EXISTS |

### Needs Porting

| Tool | OpenClaw Branch | OpenClaw Path | Description | Status |
|------|----------------|---------------|-------------|--------|
| voice-server/ | recovery-backup | `tools/voice-server/` | Full Node.js voice call server (Twilio + Deepgram + ElevenLabs + OpenRouter) | NEEDS PORTING |
| zoom_access.sh | saimemory-backup | `tools/zoom_access.sh` | Zoom recording access script | NEEDS PORTING |
| zoom_recorder_access.py | saimemory-backup | `tools/zoom_recorder_access.py` | Zoom recording access (Python) | NEEDS PORTING |
| sean_mastery_pattern_extractor.py | saimemory-backup | `tools/sean_mastery_pattern_extractor.py` | Multi-Pinecone mastery pattern extraction | NEEDS PORTING |
| upload_memory.py | recovery-backup | `tools/upload_memory.py` | MEMORY.md → Pinecone saimemory/longterm | NEEDS PORTING |
| upload_daily.py | recovery-backup | `tools/upload_daily.py` | Daily memory → Pinecone | NEEDS PORTING |
| memory-to-pinecone.js | recovery-backup | `tools/memory-to-pinecone.js` | JS chunker/uploader for Pinecone | NEEDS PORTING |
| memory_query.py | recovery-backup | `tools/memory_query.py` | Memory query wrapper | NEEDS PORTING |
| sync-elevenlabs-memory.py | recovery-backup | `tools/sync-elevenlabs-memory.py` | Sync memory to shared ElevenLabs agent | NEEDS PORTING |
| fetch-elevenlabs-transcripts.py | recovery-backup | `tools/fetch-elevenlabs-transcripts.py` | ElevenLabs transcript fetcher | NEEDS PORTING |
| generate_image.py | recovery-backup | `tools/generate_image.py` | Image gen via Gemini 2.5 Flash | NEEDS PORTING |
| hear_audio.py | recovery-backup | `tools/hear_audio.py` | Audio processing | NEEDS PORTING |
| watermark.py | recovery-backup | `tools/watermark.py` | Image watermarking | NEEDS PORTING |
| fathom_api.py | recovery-backup | `tools/fathom_api.py` | Fathom meeting transcript API | NEEDS PORTING |
| vercel_deploy.py | recovery-backup | `tools/vercel_deploy.py` | Vercel deployment tool | NEEDS PORTING |
| sai-outreach/ | recovery-backup | `tools/sai-outreach/` | Supabase contact loader + setup | NEEDS PORTING |
| elevenlabs-prompt-template.txt | recovery-backup | `tools/elevenlabs-prompt-template.txt` | ElevenLabs agent system prompt | NEEDS PORTING |
| hui-generator/ | recovery-backup | `tools/hui-generator/` | HUI generator skill/tool | NEEDS PORTING |
| automation-servers/ | recovery-backup | `tools/automation-servers/` | 7 Levers, Colosseum API, Reporting servers + LaunchD plists | NEEDS PORTING |
| dashboard-api/ | recovery-backup | `tools/dashboard-api/server.py` | Dashboard HTTP API | NEEDS PORTING |

### Recovery-Specific Tools

| Tool | OpenClaw Branch | OpenClaw Path | Description | Status |
|------|----------------|---------------|-------------|--------|
| import_lawyers.py | recovery-backup | `sisters/sai-recovery/tools/import_lawyers.py` | CSV → Supabase lawyer import | NEEDS PORTING |
| supabase_helper.py | recovery-backup | `sisters/sai-recovery/tools/supabase_helper.py` | Supabase CRUD helper | NEEDS PORTING |
| 001_recovery_tables.sql | recovery-backup | `sisters/sai-recovery/tools/migrations/001_recovery_tables.sql` | Recovery DB schema | NEEDS PORTING |

---

## 5. Pinecone Indexes

### Primary Account (`PINECONE_API_KEY`) — already configured in Bomba SR

| Index | Vectors | Bomba SR Status |
|-------|---------|-----------------|
| `ublib2` | 41K+ | ALREADY CONFIGURED — default index in `config.py` |
| `saimemory` | 1,500+ | NEEDS CONFIG — not in Bomba SR's index hosts |
| `athenacontextualmemory` | 11K+ | NEEDS CONFIG |
| `uicontextualmemory` | 48K+ | NEEDS CONFIG |
| `miracontextualmemory` | 1K+ | NEEDS CONFIG |
| `seancallieupdates` | 814 | NEEDS CONFIG |
| `seanmiracontextualmemory` | 146 | NEEDS CONFIG |

### Strata Account (`PINECONE_API_KEY_STRATA`) — partially configured in Bomba SR

| Index | Vectors | Bomba SR Status |
|-------|---------|-----------------|
| `ultimatestratabrain` | 39K+ | NEEDS CONFIG — 4 namespaces: ige, eei, rti, dom |
| `suritrial` | 7K+ | NEEDS CONFIG |
| `2025selfmastery` | 1.4K+ | NEEDS CONFIG |
| `oracleinfluencemastery` | 505 | NEEDS CONFIG |
| `nashmacropareto` | 132 | NEEDS CONFIG |
| `rtioutcomes120` | 755 | NEEDS CONFIG |
| `010526calliememory` | 1.3K+ | NEEDS CONFIG |
| `miraagentnew-25-07-25` | 1.2K+ | NEEDS CONFIG |
| _(12 more unnamed)_ | — | FLAG — names unknown, need discovery |

### Embedding Config
- Model: `text-embedding-3-small` (OpenAI), 1536 dims, cosine
- Bomba SR already uses this model via `builtin_pinecone.py`

---

## 6. External Services / Credentials

**No actual keys to migrate — just configuration awareness.**

| Service | Env Variable(s) | Bomba SR .env Status |
|---------|-----------------|---------------------|
| OpenRouter | `OPENROUTER_API_KEY` | ALREADY CONFIGURED |
| OpenAI | `OPENAI_API_KEY` | ALREADY CONFIGURED |
| Pinecone (primary) | `PINECONE_API_KEY` | ALREADY CONFIGURED |
| Pinecone (Strata) | `PINECONE_API_KEY_STRATA` | ALREADY CONFIGURED |
| Bland.ai | `BLAND_API_KEY` | ALREADY CONFIGURED |
| ElevenLabs | `ELEVENLABS_API_KEY` | NEEDS SETUP |
| Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_API_KEY_SID`, `TWILIO_API_KEY_SECRET` | NEEDS SETUP |
| Deepgram | `DEEPGRAM_API_KEY` | NEEDS SETUP |
| Zoom | `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET` | ALREADY CONFIGURED |
| Fathom | `FATHOM_API_KEY` | NEEDS SETUP |
| Supabase | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | NEEDS SETUP |
| Vercel | `VERCEL_TOKEN` | NEEDS SETUP |
| Google (gog) | `GOG_KEYRING_PASSWORD` + GCP client ID | NEEDS SETUP |

---

## 7. Other Assets

### Data Files

| Asset | OpenClaw Branch | OpenClaw Path | Status |
|-------|----------------|---------------|--------|
| seamless_lawyers.csv (48.9MB, 126K contacts) | recovery-backup | `sisters/sai-recovery/data/seamless_lawyers.csv` | NEEDS PORTING |
| seamless_lawyers_deduped.csv | recovery-backup | `sisters/sai-recovery/data/seamless_lawyers_deduped.csv` | NEEDS PORTING |
| Geo segmented CSVs (7 files) | recovery-backup | `sisters/sai-recovery/data/geo/*.csv` | NEEDS PORTING |
| NJ PIP fee schedules (2 CSVs) | recovery-backup | `sisters/sai-recovery/data/fee-schedules/nj/*.csv` | NEEDS PORTING |
| Sean mastery analysis JSON (55KB) | saimemory-backup | `sean_mastery_analysis.json` | NEEDS PORTING |
| Sean mastery patterns raw (196KB) | saimemory-backup | `sean_mastery_patterns_raw.json` | NEEDS PORTING |
| email_ad.db (SQLite) | saimemory-backup | `email_ad.db` | NEEDS PORTING |
| sean-review CSVs (3 files) | recovery-backup | `memory/sean-review-*.csv` | NEEDS PORTING |
| all_recordings.json | saimemory-backup | `all_recordings.json` | NEEDS PORTING |

### Colosseum Source + Data

| Asset | OpenClaw Branch | OpenClaw Path | Bomba SR Path | Status |
|-------|----------------|---------------|---------------|--------|
| Colosseum v2 source | recovery-backup | `Projects/colosseum/v2/` | `workspaces/forge/colosseum/v2/` | ALREADY EXISTS |
| Colosseum v1 source | recovery-backup | `Projects/colosseum/colosseum/` | `workspaces/forge/colosseum/colosseum/` | ALREADY EXISTS |
| colosseum.db (105MB) | recovery-backup | `colosseum/colosseum.db` | _(none)_ | NEEDS PORTING — 9,119 beings, Gen 726 |
| email_ad.db (4.8MB) | recovery-backup | `colosseum/email_ad_domain/email_ad.db` | _(none)_ | NEEDS PORTING |
| Prove-Ahead data | recovery-backup | `Projects/prove-ahead/` | `workspaces/prime/prove-ahead/` | ALREADY EXISTS |

### Audio Files

| Asset | OpenClaw Branch | OpenClaw Path | Status |
|-------|----------------|---------------|--------|
| Voice previews (3 mp3s) | recovery-backup | `audio-previews/sai-preview-*.mp3` | NEEDS PORTING |
| First words (5 mp3s) | recovery-backup | `*-first-words.mp3` | NEEDS PORTING |
| Recovery voice messages (17 mp3s) | recovery-backup | `recovery-*.mp3` | NEEDS PORTING |

### HTML Dashboards

| Asset | OpenClaw Branch | OpenClaw Path | Status |
|-------|----------------|---------------|--------|
| battle-arena-v3-enhanced.html | forge-backup | `battle-arena-v3-enhanced.html` | NEEDS PORTING |
| sai-forge-dashboard.html | forge-backup | `sai-forge-dashboard.html` | NEEDS PORTING |
| sai-sisters-mastery-dashboard.html | forge-backup | `sai-sisters-mastery-dashboard.html` | NEEDS PORTING |
| 20+ sai-dashboards/*.html | recovery-backup | `sai-dashboards/` | NEEDS PORTING |
| come-get-me landing pages | recovery-backup | `come-get-me/` | NEEDS PORTING |

### Strategic / Reference Documents

| Asset | OpenClaw Branch | OpenClaw Path | Status |
|-------|----------------|---------------|--------|
| SAI_ENTERPRISE_BLUEPRINT.md | saimemory-backup | `SAI_ENTERPRISE_BLUEPRINT.md` | NEEDS PORTING |
| SAI_ORCHESTRATION_MAP.md | saimemory-backup | `SAI_ORCHESTRATION_MAP.md` | NEEDS PORTING |
| LLM_Independence_Strategic_Plan.md | saimemory-backup | `LLM_Independence_Strategic_Plan.md` | NEEDS PORTING |
| ZONE_ACTION_67_COMPREHENSIVE_TRACKER.md | saimemory-backup | `ZONE_ACTION_67_COMPREHENSIVE_TRACKER.md` | NEEDS PORTING |
| ZONE_ACTION_75_COMPLETION_REPORT.md | saimemory-backup | `ZONE_ACTION_75_COMPLETION_REPORT.md` | NEEDS PORTING |
| ZONE_ACTION_76_FINAL_REPORT.md | saimemory-backup | `ZONE_ACTION_76_FINAL_REPORT.md` | NEEDS PORTING |
| BATTLE_ARENA_CHANGELOG.md | saimemory-backup | `BATTLE_ARENA_CHANGELOG.md` | NEEDS PORTING |
| mac_mini_coordination_matrix.md | saimemory-backup | `mac_mini_coordination_matrix.md` | NEEDS PORTING |
| SEAN_DAILY_REPORT_Feb23.md | saimemory-backup | `SEAN_DAILY_REPORT_Feb23.md` | NEEDS PORTING |
| agreement-maker-training-framework.md | recovery-backup | `agreement-maker-training-framework.md` | NEEDS PORTING |

### Campaigns

| Asset | OpenClaw Branch | OpenClaw Path | Status |
|-------|----------------|---------------|--------|
| callagy-recovery landing pages | saimemory-backup | `campaigns/callagy-recovery/landing-pages.md` | NEEDS PORTING |
| acti-legal-summit ads | recovery-backup | `campaigns/acti-legal-summit/` | NEEDS PORTING |
| email-arena-audit | saimemory-backup | `tasks/email/email-arena-audit-2026-02-28.md` | NEEDS PORTING |

### Recovery-Specific Systems

| Asset | OpenClaw Branch | OpenClaw Path | Status |
|-------|----------------|---------------|--------|
| Federal IDR AI modules | recovery-backup | `sisters/sai-recovery/systems/federal-idr/` | NEEDS PORTING |
| Medical revenue recovery SKILL.md | recovery-backup | `sisters/sai-recovery/medical-revenue-recovery/SKILL.md` | NEEDS PORTING |

---

## Migration Summary

| Category | Already Exists | Needs Porting | Needs Merging | Skip |
|----------|---------------|---------------|---------------|------|
| Personality/Identity | 24 | 22 | 8 | 0 |
| Memory | 8 | 90+ | 1 | 0 |
| Skills | 5 | 51 | 0 | 0 |
| Tools | 7 | 22 | 0 | 0 |
| Pinecone Indexes | 1 | 14+ | 0 | 0 |
| External Services | 5 | 8 | 0 | 0 |
| Data/Other | 3 | 40+ | 0 | varies |

**Total unique assets to port: ~250+**
**Total that need merge review: ~9**
**Total already in place: ~53**
