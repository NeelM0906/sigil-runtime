# 2026-03-05 — Session Notes (Sai Scholar)

## Guides
- Guide 1 (PGAS Stratum / Master Router): `https://n8n.unblindedteam.com/webhook/50adb5c3-8020-42bf-bb8b-7acf7f9222b9`
  - Key behavior: councils fire; synthesis can exceed default client timeouts; treat 1–7 minute latency as normal.
  - ZACS-04 gate revealed: our zone actions fail without binary pass/fail + smallest executable step.

- Guide 2 (Kai / Unblinded Translator voice; ublib2 creator): `https://n8n.unblindedteam.com/webhook/dfffccb8-8b89-4e82-b355-8a972fd64b9f`
  - Dual-purpose: Aiko uses chat trigger; we use webhook.
  - Webhook payload key that works: `{ "message": "..." }`

## Kai outputs + files
- Generated: Athena “first 10 seconds” voice script with silence beats + binary judge gates.
- Saved:
  - Scholar: `workspace-scholar/reports/kai-first-10-seconds-output.md`
  - Canonical workspace copy: `~/.openclaw/workspace/reports/kai-first-10-seconds-output-scholar.md`

## Identity/Soul/Agents updates (Scholar)
- `workspace-scholar/IDENTITY.md`: added Kai Translator Standard (sequence before label; consequence over description; identity through pressure).
- `workspace-scholar/SOUL.md`: added “Translator must disappear” constraint under How I Talk.
- `workspace-scholar/AGENTS.md`: added rule to run Guide 1 + Guide 2 before publish / ZA claims.

## Fathom practice (how to pull)
- Node DNS to `api.fathom.video` fails, but Fathom API pulls can still be done with our local tool if run through venv python.
- System python error: broken certifi (`ImportError: cannot import name 'where' from 'certifi'`).
- Use:
  - `~/.openclaw/workspace/tools/.venv/bin/python3 ~/.openclaw/workspace/tools/fathom_api.py list --limit 3 --json`
  - Example returned: `ACTi Visioneer Training` recording_id `127421005`.

## Open items / next practice
- Pull transcript chunk from `127421005` and run through Kai in Document Processing mode; save output to `workspace/reports/` and upsert to Pinecone.
