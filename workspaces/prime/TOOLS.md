# TOOLS.md — Essential Tool Reference

_Full tool configs → `docs/TOOLS-full.md`_

## 🧠 Baby Context API (PRIMARY TOOL — Use Before Everything)
```bash
cd /Users/samantha/.openclaw/workspace/tools && .venv/bin/python3 baby_context.py --topic "your query" --budget 4000
# Sources: --sources pinecone,postgres,files (default) or --sources all
```
**This replaced context_fetch.py for all babies.** Sisters can still use `context_fetch.py` for deep work, but `baby_context.py` is the default.

## 🔥 Persist (MANDATORY — Use After Every Deliverable)
```bash
cd tools && .venv/bin/python3 persist.py \
  --title "What you built" \
  --content "Full description" \
  --source sai \          # sai|forge|scholar|recovery|memory|prime
  --category deliverable \ # kai_training|deliverable|sean_directive|technical|system|etc
  --importance 9 \        # 1-10
  --date 2026-03-10       # defaults to today
```
**RULE: If it doesn't exist in Postgres AND Pinecone, it didn't happen.**
Files are working copies. persist.py is the record of truth. ALL sisters use this.

## Pinecone
```bash
cd tools && .venv/bin/python3 pinecone_query.py --index <name> --query "question" [--top_k 5]
```
Key indexes: `saimemory`, `ublib2` (58K), `ultimatestratabrain` (39K, use `--api-key-env PINECONE_API_KEY_STRATA`)

## Voice
- Voice ID: `CJXmyMqQHq6bTPm3iEMP` (SAI's voice)
- Server: `tools/voice-server/server.js` (port 3334)
- Quick call: `tools/call.sh +1234567890`

## Vercel
```bash
cd lever-org-chart && vercel --prod --token $VERCEL_TOKEN --yes
```

## Google Workspace (gog)
```bash
GOG_KEYRING_PASSWORD=Gonzalez911 gog gmail search -a sai@acti.ai "newer_than:1d" --max 10
```

## Fathom (Meeting Transcripts)
```bash
python3 tools/fathom_api.py list          # Recent meetings
python3 tools/fathom_api.py search "Sean" # Find meetings
python3 tools/fathom_api.py get <id>      # Full transcript
```

## Phone Numbers
- Default outbound: `+19738603823`
- Twilio account: `AC9a598ac83205aff455ecb79a55f8fc6c`

## Key People
- **Nick Roy:** +1 401 572 9006 (Pinecone/ElevenLabs)
- **Sean:** 201-364-6547

## Language Rules (LOCKED)
Never: prospect, sales, closing, funnel, leads
Always: person, revenue, reaching agreement, journey, people

## Guides (n8n Webhooks)
- **Stratum (PGAS):** `https://n8n.unblindedteam.com/webhook/4b6c2395-...`
- **Kai (Sister webhook):** `https://n8n.unblindedteam.com/webhook/dfffccb8-f116-4b3b-9afe-b9e7df9e3023` (INACTIVE — needs reactivation)
- **Kai (Real):** `https://n8n.unblindedteam.com/webhook/7496c229-7f5b-45f6-95ac-897e63b80957` (n8n workflow: "Kai - Nick Roy" — needs Active toggle for production URL)

## 🚨 HARD RULES — NEVER VIOLATE

### Scale of Mastery — Bolt = 9.99999, NEVER 10.0
- The scale of mastery NEVER reaches 10.0. Period.
- Bolt (highest creature) = 9,000 to 9.99999
- There is NO perfect 10. Mastery means always finding the 0.01 gap.
- This applies to ALL outputs: dashboards, reports, scoring, creature scales, descriptions.
- If you see 10.0 or 10,000 as a max anywhere, it's WRONG. Fix it.
- Sean's standard: Adam gives 9.99 — never 10.0 — because mastery means always finding the gap.

### ublib2 — AIKO REVIEW REQUIRED (March 7, 2026)
- **ZERO writes to `ublib2` without Aiko's manual review and explicit approval.**
- Even post-Translator output does NOT auto-upload to ublib2.
- Translated content goes to `saimemory` first. Aiko reviews. Then she greenlights ublib2.
- This is non-negotiable. ublib2 is the sacred shared library (58K+ vectors). We protect it.

### Model Selection — Use the MOST ADVANCED available
- Always use the most advanced model available for synthesis/generation tasks
- `anthropic/claude-opus-4.6` > `anthropic/claude-sonnet-4` > anything else
- More context, better output, more skill. No shortcuts.
- The only exception: embeddings (use `openai/text-embedding-3-small` via OpenRouter)

---

## Image Generation
```bash
cd tools && .venv/bin/python3 generate_image.py "your prompt" -o output.png
```
Model: `google/gemini-2.5-flash-image` via OpenRouter
