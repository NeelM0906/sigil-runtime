# FORGE.md — The ACT-I Forge Architecture

_How Sai spawns, optimizes, and scales ACT-I beings._

## The Forge Pattern: Jenny → Mylo → Yes

The existing production system works like this:
1. **Jenny** (Genesis Forge of Heroes) — provides context about the prospect (their pain, goals, industry, offer)
2. **Mylo** — receives that context as dynamic variables and conducts the conversation
3. **The conversation follows the 4 Steps** — Emotional Rapport → Truth & Pain → HUI → Agreement Formation
4. **Outcome** — yes or structured follow-up

This pattern is the template for ALL being spawning.

## Current Ecosystem (Bland.ai)

| Category | Count | Examples |
|---|---|---|
| Mylo variants | 14 | Template, V1, V2, Summit, Date with Destiny, Upsell |
| Miro variants | 18 | Hello to Yes, Discovery, Visionary, Stage Demo, RSVP |
| Insurance/MRR bots | 32 | Aetna, BCBS, Cigna, UHC, Horizon — PAD connected |
| Cold outreach | 14 | Lawyer cold, ACT-I Summit, Man in the Arena |
| Callie variants | 4 | Lord Neel, Built-in KB, Insurance Agent |
| Other | 46 | Scarlett, Bomba Jr, IVR navigation, demos |
| **Total** | **128 pathways** | **271,105 calls made** |

## Spawning a New Being (The Process)

### Via Bland.ai API:
```
POST /v1/convo_pathway
Body: { name, description, nodes[], edges[] }
```

### What a Being Needs:
1. **Pathway** (Bland) — the conversation flow graph (nodes + edges)
2. **Knowledge Base** (Pinecone) — domain-specific knowledge
3. **Voice** (ElevenLabs) — character and personality
4. **System Prompt** — identity, rules, energies, communication style
5. **Dynamic Variables** — context fed from Jenny/Genesis Forge
6. **Registry Entry** (Supabase) — tracked in acti_beings table

### The Forge Automation Vision:
```
Sai decides what being is needed
  → Selects base template (Mylo, Miro, Callie pattern)
  → Customizes pathway for industry/use case
  → Creates/assigns Pinecone namespace
  → Assigns voice from ElevenLabs
  → Deploys via Bland API
  → Registers in Supabase
  → Monitors and optimizes
```

## Key Dynamic Variables (from Mylo Template)

These are populated by Jenny/Genesis Forge before the call:
- `{{company}}` — target company name
- `{{decision_maker_name}}` — who we're trying to reach
- `{{goal_of_offer}}` — what we want them to say yes to
- `{{offer}}` — the specific offer details
- `{{call_type}}` — type of outreach
- `{{industry}}` — their industry
- `{{voicemail}}` — voicemail script
- `{{pain_words}}` — their specific pain (discovered during conversation)
- `{{mission}}`, `{{vision}}`, `{{purpose}}` — their MVPs
- `{{heroic_unique_identity}}` — their HUI
- `{{gap}}` — the gap between where they are and where they want to be
- `{{eri_measurement}}` — Emotional Rapport Index score
- `{{users_position}}` — where they are now
- `{{road_block}}` — what's in their way

## Platforms Connected

| Platform | Purpose | Status |
|---|---|---|
| **Bland.ai** | Voice calls, pathways, batch calling | ✅ Connected, 128 pathways |
| **ElevenLabs** | Custom voices, Conversational AI | ✅ Connected, 90 voices, 30 agents |
| **Pinecone (ecosystem)** | 100K+ vectors of knowledge | ✅ Connected, 10 indexes |
| **Pinecone (strata)** | 57K+ vectors deep knowledge | ✅ Connected, 20 indexes |
| **Pinecone (saimemory)** | Sai's own memory | ✅ Created, 116 vectors |
| **Supabase** | Database: beings registry, memory, operations | ✅ Connected, 3 tables |
| **OpenAI** | Embeddings, GPT-4o, DALL-E, Whisper | ✅ Connected |
| **OpenRouter** | Claude Opus 4.6, Sonnet 4 | ✅ Connected |
| **Twilio** | Phone numbers, SMS | ✅ Connected, 20 numbers |
| **Deepgram** | Real-time STT | ✅ Connected |
| **Perplexity** | AI search | ✅ Connected |

## Next Steps for the Forge

1. **Build programmatic pathway creation** — spawn Bland pathways via API
2. **Create the template system** — parameterized base templates that can be customized per industry
3. **Connect Jenny → Sai** — let Jenny feed me context so I can decide what beings to create
4. **Batch spawning** — create 10, 100, 1000 beings at once
5. **Optimization loop** — analyze call transcripts, identify what's working, auto-improve prompts
6. **Build the missing beings** — Self Mastery, Financial Mastery, Tech Mastery

---

_This file evolves as the Forge evolves. Updated: February 22, 2026 — Birthday._
