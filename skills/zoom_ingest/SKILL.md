---
name: zoom_ingest
description: Extract and download transcripts from Zoom Cloud Recordings. Filters by priority keywords (heart of influence, mastery session, etc.)
user-invocable: true
disable-model-invocation: false
risk-level: low
---
# Zoom Transcript Ingest Workflow

Use this skill when the user asks to pull Zoom Cloud Recording transcripts into workspace memory.

## Preconditions
- Environment variables set: `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`

## Steps
1. **Authenticate** — Use Zoom Server-to-Server OAuth to get an access token.
2. **List recordings** — Fetch recent cloud recordings from the Zoom API.
3. **Filter** — Apply priority keyword filters (heart of influence, mastery session, etc.).
4. **Download transcripts** — Fetch VTT/TXT transcript files for matching recordings.
5. **Store** — Save transcripts to workspace and optionally upsert to memory.
