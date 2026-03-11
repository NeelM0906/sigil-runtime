---
name: unblinded-translator
description: Decontaminate external content through the Unblinded Formula lens before storing in Pinecone or acting on it. Translates research, transcripts, articles, PDFs, and web content into clean 7-column Formula output. Use when processing ANY content from outside the ecosystem, translating Sean's transcripts to expose Formula mechanics, or when a sister needs to run content through the Translator before Pinecone upload. Mandatory for all SAI sisters.
---

# Unblinded Translator

**The decontamination gateway between the outside world and our knowledge base.**

## HARD RULE: Nothing Enters Pinecone Raw

ALL external content must pass through the Translator before being stored in Pinecone. No exceptions.

## What Counts as External Content
- Perplexity research, web search results
- PDF research papers, articles, studies
- Transcripts from calls, meetings, podcasts (non-Sean)
- Any content NOT created by Sean, Aiko, Adam, or our ecosystem

## What Does NOT Need Decontamination (Already Clean)
- Sean's direct teachings and transcripts (these get translated to EXPOSE the Formula, not to decontaminate)
- Internal ecosystem content (zone actions, sister outputs, ACT-I data)
- Content already translated

## Files

| File | Purpose |
|------|---------|
| `tools/unblinded-translator/TRANSLATOR_PROMPT.md` | Full v5 system prompt (24KB) — use as system prompt for any LLM |
| `tools/unblinded-translator/TRANSLATOR_PROMPT_KAI_CORE.md` | Compressed Kai Core variant (7.5KB) — more powerful, fewer tokens |
| `tools/unblinded-translator/LESSONS_LEARNED.md` | Eagle→Lion journey — distilled rules for producing Lion 9.2+ output |
| `tools/unblinded-translator/translate.py` | Production script — batch translate content via OpenRouter |
| `tools/unblinded-translator/README.md` | Quick start guide |

## How to Use

### Option 1: Script (Recommended for batch work)
```bash
cd tools/unblinded-translator
python3 translate.py --input "path/to/content.md" --output "path/to/translated.json"
```

### Option 2: Manual (For single pieces)
1. Feed `TRANSLATOR_PROMPT.md` (or `TRANSLATOR_PROMPT_KAI_CORE.md`) as the **system prompt** to any LLM via OpenRouter
2. Feed the external content as the **user message**
3. Output = 7-column Formula translation
4. Store the translated output in Pinecone

```
External Content → Translator Prompt (system) + Content (user) → LLM → 7-Column Output → Pinecone
```

### Option 3: Inline (During conversation)
When you encounter external content mid-conversation:
1. Mentally apply the Translator lens before responding
2. Don't cite the content raw — filter it through Formula mechanics first
3. If storing to Pinecone, run the full translation pipeline

## The 7 Columns
1. **Topic** — What is being discussed
2. **Context** — The situation and stakes
3. **Formula Elements** — Which Unblinded Formula components are operating
4. **Main Lesson** — The core teaching extracted
5. **Solves What Human Condition** — What suffering/limitation this addresses
6. **Sean's Processing** — How Sean would process this through the Formula
7. **Sean's Approach** — What Sean would actually DO with this

## 🔑 Dual-Pass RAG (from Kai — This Is the Secret Sauce)

**Before translating ANY content, query Pinecone TWICE:**

### Pass 1: Content-Derived Queries
Auto-generate 2-3 search queries from the content itself. What topics does this chunk cover? Query Pinecone for Sean's teachings on those specific topics.

### Pass 2: Formula-Anchor Triggers
Keyword detection fires hardcoded queries that pull CANONICAL Sean teachings:

| Content mentions... | Query Pinecone for... |
|--------------------|-----------------------|
| deals/closing/sales | "agreement formation affirmative precise who by when" |
| rapport/connection | "emotional rapport ERI I see you hear you Level 5 listening" |
| fear/hesitation | "7 destroyers fear rejection failure avoidance mismatch physiology" |
| energy/presence | "Zeus Goddess energy match plus minus certainty forward flowing" |
| mastery/scale | "scale mastery creature Gecko Godzilla Bolt" |
| coaching/teaching | "Daniel Johnny Miyagi consulting training coaching wax on wax off" |
| identity/beliefs | "GHIC growth driven heart centered integrous commitment mastery identity" |

### Combined Result: 25-30K chars of grounding per section

**CRITICAL:** These vectors are VOICE TRAINING, not reference material. Absorb the patterns. Don't cite them. The Translator output should sound like someone who THINKS in the Formula — because the RAG made it so.

```
Step 1: Read the content chunk
Step 2: Query Pinecone (Pass 1 — content queries + Pass 2 — anchor triggers)
Step 3: Feed Translator system prompt + RAG results + content → LLM
Step 4: Output = 7-column translation grounded in Sean's actual teachings
Step 5: Self-score against 7-point gate → fix weak fields → ship
```

## Calibration Loop (Proven: 8.1 → 9.2)
1. Translate the section
2. Self-score against 7-point gate:
   - □ Main Lesson = LAW? (survives alone)
   - □ Consequence WOVEN INTO every paragraph?
   - □ Identity through action? (who Sean IS)
   - □ All 3 prisms SIMULTANEOUS?
   - □ RAG grounded?
   - □ "Would Sean say that's the Formula?"
   - □ Teaching or REPORT? (flows as prose?)
3. If any field reads as REPORT not TEACHING → fix THAT field only
4. Ship when prose flows like transmission

Don't rewrite everything. Sharpen specific moments. Reps over new.

## Current Standard: Lion (9.2)

The Translator output should read like someone who has INTERNALIZED the Formula — not someone describing it from the outside. Key rules from LESSONS_LEARNED.md:

- **Declare the Law** — Define the absolute rule governing the human action
- **Name the Invisible** — Detail the underlying constraint
- **Cause Not Label** — Show what the structure CAUSES, don't describe its mechanics
- Don't describe what the Formula reveals. **BE the Formula revealing it.**

### The Kai Diagnostic (What Separates Eagle from Lion)
| Eagle (writing ABOUT) | Lion (writing FROM) |
|----------------------|---------------------|
| Labels elements | Shows what they CAUSE |
| Quotes words | Names the IMPULSE underneath |
| Describes the visible | Names the INVISIBLE |
| Explains mechanics | DECLARES law |
| "Sean deploys Reframe Mastery" | "Poaching says leave them. Competing says keep them and measure." |

## APPROVED INDEXES (For querying Formula knowledge)
- `ublib2` — 58K+ vectors (shared library ALL ACT-I beings draw from)
- `ultimatestratabrain` — 39K vectors (4 namespaces: ige/eei/rti/dom)

These two ONLY. All other indexes are operational memory, not Formula knowledge.

## Why This Matters

Every vector in our databases should be either:
1. Sean's teachings directly, OR
2. External content that has been run through this decontamination layer

Contaminated vectors compound contaminated thinking. Clean vectors compound clean thinking. The Translator IS the immune system of our knowledge base.
