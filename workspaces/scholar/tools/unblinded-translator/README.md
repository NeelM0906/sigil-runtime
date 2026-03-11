# Unblinded Formula Translator v2

Takes any content — call transcripts, articles, training recordings — and translates it through the Unblinded Formula lens. Exposes the 39 components operating in any situation, strips contaminated thinking, and outputs in Unblinded language.

## Quick Start

```bash
cd ~/.openclaw/workspace/tools/unblinded-translator

# Translate latest Fathom calls (structured JSON)
.venv/bin/python3 translate.py --fathom --limit 3

# Translate with full narrative prose
.venv/bin/python3 translate.py --fathom --limit 1 --mode narrative

# Search for specific calls
.venv/bin/python3 translate.py --fathom --search "elite" --limit 5

# Translate + upload to Pinecone
.venv/bin/python3 translate.py --fathom --limit 3 --upload

# Translate a local file
.venv/bin/python3 translate.py --file ~/path/to/transcript.txt --mode narrative
```

## What It Does

1. **Pulls transcripts** from Fathom API (or reads local files)
2. **Chunks** them into ~4,000 char segments with overlap for continuity
3. **Translates** each chunk through the Unblinded Formula via OpenRouter LLM
4. **Saves** output to `memory/translated/`
5. **Optionally uploads** to Pinecone (`saimemory/translated` namespace)

## Output Modes

- **`json`** (default) — Structured extraction: Formula elements, lever sequences, leakage, scale of mastery rating, key quotes, zone action
- **`narrative`** — Flowing prose in the style of a teacher transmitting wisdom. For reports and presentations.

## API Routing

**ALL calls go through OpenRouter.** No OpenAI direct. No exceptions. This is a hard rule.

## Files

- `TRANSLATOR_PROMPT.md` — The master prompt (39 components, scale of mastery, leakage, fact stacking)
- `translate.py` — Main pipeline (Fathom + local files, OpenRouter, Pinecone)
- `extract_and_translate.py` — Legacy v1 (Zoom-based, OpenAI direct — deprecated)
- `process_elite.py` — Legacy Elite training processor (deprecated)

## Requirements

```
requests
pinecone-client  # only needed for --upload
```

All deps available in the workspace `.venv`.
