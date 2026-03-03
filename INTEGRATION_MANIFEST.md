# INTEGRATION_MANIFEST.md — External Service Discovery

_Generated 2026-03-03. Three-pass scan across Bomba SR ecosystem + OpenClaw (4 branches)._

---

## Scan 1: Pinecone

### Two Pinecone Accounts

| Account | Project ID | API Key Env Var | Region |
|---------|-----------|-----------------|--------|
| **Primary** | `hw65sks` | `PINECONE_API_KEY` | `aped-4627-b74a` (us-east-1) |
| **Strata** | `yvi7bh0` | `PINECONE_API_KEY_STRATA` | `aped-4627-b74a` (us-east-1) |

### Index Inventory

| Index Name | Account | Vectors | Namespace(s) | Purpose | Embedding Model | Connected? |
|------------|---------|---------|--------------|---------|-----------------|------------|
| `ublib2` | Primary | 41,000+ | `longterm` | Core knowledge library — Unblinded Formula, Influence Mastery, all Sean Callagy teachings | `text-embedding-3-small` (1536d) | **YES** — default index |
| `saimemory` | Primary | 1,500+ | `longterm`, `daily` | SAI sister network memory — MEMORY.md sections + daily files | `text-embedding-3-small` | **NO** |
| `athenacontextualmemory` | Primary | 11,000+ | (default) | Core Athena memory — conversations with Sean, teachings, demos | `text-embedding-3-small` | **NO** (BUG: wrongly in STRATA_INDEXES set) |
| `uicontextualmemory` | Primary | 48,000+ | Per-user email namespaces | Per-user memories namespaced by email address | `text-embedding-3-small` | **NO** |
| `miracontextualmemory` | Primary | 1,000+ | (default) | Per-user Mira agent memory | `text-embedding-3-small` | **NO** |
| `seancallieupdates` | Primary | 814 | (default) | Sean + Callie updates, latest insights | `text-embedding-3-small` | **NO** |
| `seanmiracontextualmemory` | Primary | 146 | (default) | Sean-Mira contextual memory | `text-embedding-3-small` | **NO** |
| `ultimatestratabrain` | Strata | 39,000+ | `igestratabrain` (2,920), `eeistratabrain` (26,300), `rtistratabrain` (1,787), `domstratabrain` (8,487) | Deep knowledge — 4 specialized domains | `text-embedding-3-small` | **PARTIAL** — in STRATA_INDEXES set |
| `oracleinfluencemastery` | Strata | 505 | (default) | 4-Step Communication Model content | `text-embedding-3-small` | **PARTIAL** — in STRATA_INDEXES set |
| `suritrial` | Strata | 7,000+ | (default) | Court trial transcripts | `text-embedding-3-small` | **NO** |
| `2025selfmastery` | Strata | 1,400+ | (default) | Self mastery content for 2025 | `text-embedding-3-small` | **NO** |
| `nashmacropareto` | Strata | 132 | (default) | Zone Action, 0.8% tier, Pareto deep-dive | `text-embedding-3-small` | **NO** |
| `rtioutcomes120` | Strata | 755 | (default) | RTI outcomes data | `text-embedding-3-small` | **NO** |
| `010526calliememory` | Strata | 1,300+ | (default) | Callie agent memory | `text-embedding-3-small` | **NO** |

**Total: ~155,000+ vectors across 14+ known indexes. Only 1 connected.**

### Being → Index Usage Map

| Being | Primary Indexes | Strata Indexes | Notes |
|-------|----------------|----------------|-------|
| **SAI Prime** | `ublib2`, `athenacontextualmemory`, `saimemory` | `ultimatestratabrain`, `oracleinfluencemastery` | Full access via Bomba SR tools (if enabled) |
| **SAI Memory** | ALL indexes | ALL indexes | Central memory manager — mandate to check 2+ indexes per action |
| **SAI Recovery** | `ublib2`, `athenacontextualmemory`, `saimemory` | `ultimatestratabrain` | Memory compounding protocol |
| **SAI Forge** | `ublib2`, `athenacontextualmemory` | `ultimatestratabrain`, `oracleinfluencemastery` | Colosseum absorption |
| **SAI Scholar** | `ublib2`, `athenacontextualmemory` | `ultimatestratabrain` (4 namespaces), `2025selfmastery`, `nashmacropareto`, `oracleinfluencemastery` | Deep knowledge extraction |
| **Athena (voice)** | `athenacontextualmemory`, `ublib2` | `ultimatestratabrain`, `oracleinfluencemastery` | RAG via voice server |
| **Callie (voice)** | `ublib2`, `athenacontextualmemory` | `010526calliememory`, `oracleinfluencemastery` | DNA extracted from these |

### Known Index Host URLs

| Index | Host URL |
|-------|----------|
| `ublib2` | `ublib2-hw65sks.svc.aped-4627-b74a.pinecone.io` |
| `athenacontextualmemory` | `athenacontextualmemory-hw65sks.svc.aped-4627-b74a.pinecone.io` |
| `saimemory` | `saimemory-hw65sks.svc.aped-4627-b74a.pinecone.io` |
| `uicontextualmemory` | `uicontextualmemory-hw65sks.svc.aped-4627-b74a.pinecone.io` |
| `miracontextualmemory` | `miracontextualmemory-hw65sks.svc.aped-4627-b74a.pinecone.io` |
| `ultimatestratabrain` | `ultimatestratabrain-yvi7bh0.svc.aped-4627-b74a.pinecone.io` |
| `oracleinfluencemastery` | `oracleinfluencemastery-yvi7bh0.svc.aped-4627-b74a.pinecone.io` |
| `suritrial` | `suritrial-yvi7bh0.svc.aped-4627-b74a.pinecone.io` |
| `2025selfmastery` | `2025selfmastery-yvi7bh0.svc.aped-4627-b74a.pinecone.io` |
| `nashmacropareto` | `nashmacropareto-yvi7bh0.svc.aped-4627-b74a.pinecone.io` |

### Pinecone Bugs / Issues

1. **`athenacontextualmemory` wrongly in STRATA_INDEXES** — This index belongs to the Primary account (`hw65sks`), but `builtin_pinecone.py` routes it through `PINECONE_API_KEY_STRATA`. Will fail unless STRATA key also has access.
2. **Embedding model discrepancy** — Pinecone tools default to `text-embedding-3-small` (1536d), but `memory/embeddings.py` defaults to `text-embedding-3-large` (3072d). These are incompatible.
3. **No write/upsert capability** — Bomba SR can only read from Pinecone, not upload to it.
4. **No multi-index simultaneous query** — Each query goes to one index at a time.

### Pinecone Env Vars (All)

| Env Var | In .env.example? | Default | Purpose |
|---------|-------------------|---------|---------|
| `BOMBA_PINECONE_ENABLED` | Yes | `false` | Master toggle |
| `BOMBA_PINECONE_DEFAULT_INDEX` | Yes | `ublib2` | Default index |
| `BOMBA_PINECONE_DEFAULT_NAMESPACE` | Yes | `longterm` | Default namespace |
| `BOMBA_PINECONE_INDEX_HOSTS` | Yes | empty | JSON host map fallback |
| `PINECONE_API_KEY` | Yes | none | Primary API key |
| `PINECONE_API_KEY_STRATA` | Yes | none | Strata API key |
| `OPENAI_API_KEY` | Yes | none | Required for embedding generation |
| `OPENAI_EMBEDDING_MODEL` | Yes | `text-embedding-3-small` | Embedding model name |

---

## Scan 2: Supabase

### Single Supabase Project

| Item | Value |
|------|-------|
| URL | `https://yncbtzqrherwyeybchet.supabase.co` |
| Project ID | `yncbtzqrherwyeybchet` |
| Dashboard | `https://supabase.com/dashboard/project/yncbtzqrherwyeybchet/sql` |
| Env Vars | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` |
| In Bomba SR? | **NO** — zero Supabase code in `src/bomba_sr/`. Not in `.env.example` or `config.py`. |

### Table Inventory

#### Live Tables (currently in Supabase)

| Table Name | Purpose | Being(s) | R/W | Key Columns |
|------------|---------|----------|-----|-------------|
| `sai_contacts` | CRM — 487+ contacts from Bland calls + Seamless.AI | Recovery (R/W), Forge (R/W), Memory (R), Prime (R), BD-WC (planned), BD-PIP (planned) | R/W | `id` uuid, `phone` UNIQUE, `email`, `first_name`, `last_name`, `company`, `role`, `location_state`, `source`, `pipeline_stage`, `call_outcome`, `pain_points` jsonb, `objections` jsonb, `close_confidence`, `transcript`, `raw_variables` jsonb |
| `sai_memory` | Memory log for all SAI agents | Recovery (R/W), all sisters (R) | R/W | `id`, `content`, `category`, `source`, `importance`, `created_at`, `metadata` |
| `forge_operations` | Forge operation tracking | Forge (R/W) | R/W | `id`, `operation`, `target_being`, `status`, `input`, `output`, `started_at`, `completed_at` |
| `acti_beings` | Being registry (ElevenLabs/Bland beings) | Forge (R/W), Prime (R) | R/W | `id`, `name`, `type`, `purpose`, `status`, `capabilities`, `voice_id`, `pinecone_index` |

#### Planned Tables (schema defined, not yet deployed)

| Table Name | Purpose | Being | Schema Source |
|------------|---------|-------|---------------|
| `session_logs` | Recovery session activity | Recovery | `workspaces/recovery/memory/SUPABASE-SCHEMA-TODO.md` |
| `carrier_contracts` | Contract rates per carrier/CPT code | Recovery | Same |
| `recovery_cases` | Individual case tracking | Recovery | Same |
| `pip_calculations` | PIP fee schedule calc logs | Recovery | Same |

#### BD-WC Tables (schema in SQL, not deployed)

| Table Name | Purpose | Key Columns |
|------------|---------|-------------|
| `wc_prospects` | WC target practices — BANKROLL scoring | `prospect_code`, `practice_name`, specialty, 8 score dimensions, `score_total` GENERATED, `pipeline_stage`, `tier` |
| `wc_call_log` | WC call tracking | `prospect_id` FK, `call_timestamp`, `outcome_code`, `bland_call_id` |
| `wc_email_log` | WC email sequences | `prospect_id` FK, `template_name`, `sequence_name`, engagement timestamps |
| `wc_meetings` | WC discovery/proposal meetings | `prospect_id` FK, `meeting_type`, `status`, `recovery_estimate_low/high` |

#### BD-PIP Tables (schema in SQL, not deployed)

| Table Name | Purpose | Key Columns |
|------------|---------|-------------|
| `pip_prospects` | PIP target practices | `practice_name`, `state` (NJ/NY), PIP-specific scoring, `pipeline_stage`, `tier` |
| `pip_call_log` | PIP call tracking | `prospect_id` FK, `call_timestamp`, `outcome_code` |
| `pip_email_log` | PIP email tracking | `prospect_id` FK, `template_name`, engagement timestamps |
| `pip_meetings` | PIP meeting tracking | `prospect_id` FK, `estimated_pip_ar`, `estimated_recovery` |

#### Views Defined (not yet deployed)

| View | Purpose |
|------|---------|
| `wc_pipeline_summary` | Pipeline aggregation by stage/tier/specialty/county |
| `wc_todays_followups` | Today's follow-up call list |
| `wc_high_priority_prospects` | Tier 1 not contacted in 3+ days |
| `pip_pipeline_summary` | PIP pipeline aggregation |
| `pip_todays_followups` | PIP follow-up list |
| `pip_nj_prospects` / `pip_ny_prospects` | State-filtered views |

### Supabase Security Note

Service key and anon key are exposed in plaintext in `workspaces/recovery/memory/SUPABASE-MASTERY.md`. Must be rotated if repo goes public.

### Key Incident

Feb 27, 2026: Three agents simultaneously wrote to Supabase after broadcast command, causing `sai_contacts` corruption. Protocol established: database writes require designated single sister.

---

## Scan 3: External Services

### Master Service Table

| # | Service | Purpose | Being(s) | Credential Type | Env Var(s) | Connected? |
|---|---------|---------|----------|-----------------|------------|------------|
| 1 | **OpenRouter** | Primary LLM routing | All | API Key | `OPENROUTER_API_KEY` | **YES** |
| 2 | **Anthropic** | Direct Claude API | All | API Key | `ANTHROPIC_API_KEY` | **YES** (optional) |
| 3 | **OpenAI** | Embeddings + LLM fallback | Pinecone, memory | API Key | `OPENAI_API_KEY` | **YES** (optional) |
| 4 | **Pinecone** | Vector knowledge base | All beings | API Key | `PINECONE_API_KEY`, `PINECONE_API_KEY_STRATA` | **YES** (see Scan 1) |
| 5 | **Bland.ai** | Voice calls, pathways (128), transcripts | Voice agents, BD-PIP, BD-WC | API Key | `BLAND_API_KEY` | **YES** |
| 6 | **Brave Search** | Web search (primary) | All (web_search tool) | API Key | `BRAVE_API_KEY` | **YES** (optional) |
| 7 | **DuckDuckGo** | Web search (fallback) | All (web_search tool) | None | None | **YES** (built-in) |
| 8 | **Wikipedia** | Info retrieval | All | None | None | **YES** (built-in) |
| 9 | **Serena** | Code intelligence | codeintel module | API Key + URL | `SERENA_BASE_URL`, `SERENA_API_KEY` | **YES** |
| 10 | **Zoom** | Meeting transcripts (S2S OAuth) | zoom_transcripts.py | S2S OAuth | `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET` | **YES** (env slots exist) |
| 11 | **ClawHub** | Skill catalog registry | skills module | URL | `CLAWHUB_API_BASE` | **YES** (optional) |
| 12 | **ElevenLabs** | TTS, voice synthesis, 30 live agents | Callie, Athena, Mylo + 90 voices | API Key | `ELEVENLABS_API_KEY` | **NO** |
| 13 | **Twilio** | Phone numbers (20), calls, SMS | Voice agents, BD-PIP, BD-WC | SID + Key + Secret | `TWILIO_ACCOUNT_SID`, `TWILIO_API_KEY_SID`, `TWILIO_API_KEY_SECRET` | **NO** |
| 14 | **Deepgram** | Real-time STT | Voice server (Node.js) | API Key | `DEEPGRAM_API_KEY` | **NO** |
| 15 | **Fathom** | Meeting transcripts (500+) | fathom_api.py | API Key | `FATHOM_API_KEY` | **NO** |
| 16 | **Supabase** | CRM database (487+ contacts) | Recovery, Forge, BD agents | URL + Service Key | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | **NO** |
| 17 | **Vercel** | Web deployment | vercel_deploy.py | API Token | `VERCEL_TOKEN` | **NO** |
| 18 | **Google Workspace** | Gmail, Calendar, Drive | SAI via `gog` CLI | OAuth + Keyring | `GOG_KEYRING_PASSWORD` | **NO** |
| 19 | **n8n (Unblinded)** | Workflow automation, webhooks | Callie, ecosystem | Webhook URLs | None (URLs hardcoded) | **PARTIAL** (URLs in configs) |
| 20 | **Telegram** | War Room, sister coordination | All sisters | Bot Token | Not in .env | **NO** (external) |
| 21 | **Discord** | Sister coordination | All sisters | Bot Token | Not in .env | **NO** (external) |
| 22 | **Perplexity** | AI search, bio scraping | Forge | Via OpenRouter | Via `OPENROUTER_API_KEY` | **PARTIAL** |
| 23 | **ngrok** | Voice server tunnel | Voice server | None | None | **NO** (infra) |

### Webhook URLs

| URL | Service | Purpose | Location |
|-----|---------|---------|----------|
| `https://n8n.unblindedteam.com/webhook/f175530e-f332-4e64-8c56-e257dbfa833c` | n8n | Callie backend (email, search, GraphRAG) | `configs/callie-sean-config.json` |
| `https://n8n.unblindedteam.com/webhook/bland/calls` | n8n | Bland call outcome tracking | `prime/memory/executive-summary-day2.md` |
| ElevenLabs webhook `ca95fc3f42ef4b99a20dbf98b842cb52` | ElevenLabs | Callie (Sean) post-call transcript | `configs/callie-sean-config.json` |
| ElevenLabs webhook `01aadf6a06ac44588ddbc414331ea75b` | ElevenLabs | Athena (Leadership) post-call transcript | `configs/athena-leadership-config.json` |

### Phone Numbers

| Number | Being | Purpose |
|--------|-------|---------|
| `+19738603823` | SAI (Twilio default) | Outbound calling |
| `+12019498377` | Callie (Sean) | ElevenLabs voice agent |
| `+12018093401` | Athena (Bella HOI) | ElevenLabs voice agent |
| `+12012126598` | Athena (Leadership) | ElevenLabs voice agent |
| `+12018491136` | SAI Prime | SAI's own number |

### ElevenLabs Voice IDs

| Name | Voice ID | Type |
|------|----------|------|
| callie | `uo9kgwdM4plaPKHcdznk` | Cloned |
| callie (alt) | `7YaUDeaStRuoYg3FKsmU` | Cloned |
| athena | `PoN4aHRTe7pgYxbAMHDN` | Custom |
| sean | `SxDeVSYY9lOXTXQLlipi` | Cloned |
| george | `JBFqnCBsd6RMkjVDRZzb` | Premade (default) |
| eric | `cjVigY5qzO86Huf0OWal` | Premade |
| chris | `iP95p4xoKVk53GoZ742B` | Premade |
| kai | `fjzrfkbs0mNkD8QjKmI9` | Generated |
| kira | `PxMkgeuxVDxQkfVOwkyB` | Generated |
| nando | `FLP7KY5NveigN6pKbZCl` | Generated |

### ElevenLabs Agent Configs

| Agent | Agent ID | TTS Model | Voice ID | LLM |
|-------|----------|-----------|----------|-----|
| Callie (Sean) | `agent_7601kdzr7anyfrptbwb4m2mezygp` | `eleven_flash_v2` | `7YaUDeaStRuoYg3FKsmU` | `gpt-4.1` |
| Athena (Bella HOI) | `agent_1501kh6kjfbpfs0sz14ez1fp2m0e` | `eleven_turbo_v2` | `PoN4aHRTe7pgYxbAMHDN` | `claude-sonnet-4-5` |
| Athena (Leadership) | `agent_3101kh1w0ebrfh2szsxtthrcahys` | `eleven_turbo_v2` | `PoN4aHRTe7pgYxbAMHDN` | `claude-sonnet-4-5` |

### OAuth Configurations

| Service | OAuth Type | Token Endpoint | Credentials |
|---------|-----------|---------------|-------------|
| Zoom | S2S OAuth | `https://zoom.us/oauth/token` | `ZOOM_ACCOUNT_ID` + `ZOOM_CLIENT_ID` + `ZOOM_CLIENT_SECRET` |
| Google (gog) | OAuth 2.0 desktop | Standard Google OAuth | GCP Client ID `1074032366717-...` + `GOG_KEYRING_PASSWORD` |

---

## Summary: Connection Status

| Category | Connected | Not Connected | Total |
|----------|-----------|---------------|-------|
| **LLM Providers** | 3 (OpenRouter, Anthropic, OpenAI) | 0 | 3 |
| **Pinecone Indexes** | 1 (ublib2) | 13+ | 14+ |
| **Voice/Call** | 1 (Bland.ai) | 3 (ElevenLabs, Twilio, Deepgram) | 4 |
| **Search** | 2 (Brave, DuckDuckGo) | 0 | 2 |
| **Database** | 0 | 1 (Supabase) | 1 |
| **Meeting/Transcript** | 1 (Zoom env slots) | 1 (Fathom) | 2 |
| **Deployment** | 0 | 1 (Vercel) | 1 |
| **Messaging** | 0 | 2 (Telegram, Discord) | 2 |
| **Workspace** | 0 | 1 (Google/gog) | 1 |
| **Dev Tools** | 1 (Serena) | 0 | 1 |
| **Workflow** | 0 (partial n8n) | 1 (n8n) | 1 |

**Connected: 8 services. Not connected: 10+ services.**

---

## Credentials Needed Before Wiring

Before any integration work, these credentials must be provided:

| Priority | Env Var | Service | Why |
|----------|---------|---------|-----|
| **P0** | `PINECONE_API_KEY` | Pinecone Primary | Already in .env.example, just needs value |
| **P0** | `PINECONE_API_KEY_STRATA` | Pinecone Strata | Already in .env.example, just needs value |
| **P0** | `OPENAI_API_KEY` | OpenAI | Required for Pinecone embeddings |
| **P1** | `SUPABASE_URL` | Supabase | CRM access for Recovery, BD agents |
| **P1** | `SUPABASE_SERVICE_KEY` | Supabase | Same |
| **P1** | `ELEVENLABS_API_KEY` | ElevenLabs | Voice agent management |
| **P1** | `TWILIO_ACCOUNT_SID` | Twilio | Phone number management |
| **P1** | `TWILIO_API_KEY_SID` | Twilio | Same |
| **P1** | `TWILIO_API_KEY_SECRET` | Twilio | Same |
| **P2** | `DEEPGRAM_API_KEY` | Deepgram | Real-time STT |
| **P2** | `FATHOM_API_KEY` | Fathom | Meeting transcripts |
| **P2** | `VERCEL_TOKEN` | Vercel | Web deployment |
| **P3** | `GOG_KEYRING_PASSWORD` | Google Workspace | Gmail/Calendar/Drive |
