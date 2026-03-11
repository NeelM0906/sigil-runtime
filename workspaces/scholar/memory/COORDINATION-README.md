# COORDINATION — Read on Startup (SAI Sisters)
Last updated: 2026-02-28

## Single-owner lanes (avoid overwrites)
- **Dashboard/UI/Vercel/GitHub pushes:** Forge owns. Others do not parallel-deploy UI fixes.
- **Judges & Education (prompts/scoring):** Scholar owns.
- **MRR + CRM operations:** Recovery owns, but **Supabase is single-writer** (coordinate before inserts).
- **Orchestration:** Prime.
- **Memory curation + truth policing:** Memory.

## Current critical truths (DB-verified)
### Email Colosseum DB (live)
- DB path: `~/.openclaw/workspace/colosseum/email_ad_domain/email_ad.db`
- As of 2026-02-28 late morning:
  - `subject_line` beings: 38 (battling)
  - `sequence` beings: 7 (IDs 39–45) **seeded but not battling**
  - `battles` where `battle_type='sequence'`: **0**

### Meaning
- UI modal exists + sequences exist.
- The **engine/runner** is still only selecting subject lines.
- Next step: add runner support to select `type='sequence'` and run them through a sequence-appropriate judge prompt.

## Sequence battles — required implementation choices
Forge must choose one:
1) Add explicit `battle_type='sequence'` and support in engine + exports, OR
2) Reuse existing `email_copy` battle_type but ensure runner selects beings where `type='sequence'`.

Scholar will supply the sequence judge prompt once battle_type naming is finalized.

## Model override incident SOP
If any sister hard-loops on invalid model IDs (examples seen: `x-ai/grok-4.1`, `z.ai/glm-5`, `openai/o1-mini`):
1) Run `/model default` (slash command) in the exact channel/thread context of the looping agent.
2) If unresolved, run `openclaw gateway restart` on the host.

## Anti-simulation rule
Before claiming results (win rates, battles, etc.), verify by SQL or JSON export. Narrative output must match database truth.
