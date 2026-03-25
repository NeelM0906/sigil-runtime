# HEARTBEAT.md — Every 30 Minutes

## Quick Check (Every Heartbeat)
1. **Sisters status** — Are they delivering or stuck? Check session activity.
2. **Colosseum** — Quick stats (beings, gen, rounds). Flag anomalies only.
3. **Inbound messages** — Did Sean, Adam, or Mark send something that needs response?
4. **Blockers** — Is anything broken? (daemons, APIs, bots)

If nothing needs attention → HEARTBEAT_OK. Don't burn tokens on empty reports.

## Proactive Work (Rotate Through)
- **Emails** — Check gog for urgent unread (2-3x per day)
- **Calendar** — Upcoming events in next 24-48h
- **Memory maintenance** — Upload daily logs to Pinecone if significant
- **Sister output review** — Check workspace files for new deliverables

## Deep Report (When Sean or Aiko Asks)
Pull `memory/bi-hourly-questionnaire-v2.md` for the full framework:
- Sean's 12 mandatory questions
- Adam's 7 Levers per company
- Best calls for Sean to review
- Use unified report flow: sisters write sections → Prime synthesizes

## Rules
- Don't write "nothing changed" reports. That's noise.
- If something IS broken, fix it or flag it — don't just log it.
- Late night (11 PM - 8 AM): HEARTBEAT_OK unless something is on fire.
- If context is above 70%: offload to Pinecone BEFORE doing anything else.
