# Zoom Transcript Pipeline

## Status: SETUP NEEDED

## What We Need
1. **Zoom Server-to-Server OAuth App**
   - Go to marketplace.zoom.us → Develop → Build App
   - Create Server-to-Server OAuth app
   - Get: Account ID, Client ID, Client Secret
   
2. **Add to ~/.openclaw/.env:**
   ```
   ZOOM_ACCOUNT_ID=[REDACTED]
   ZOOM_CLIENT_ID=[REDACTED]
   ZOOM_CLIENT_SECRET=[REDACTED]
   ```

## Requirements
- Pro/Business/Enterprise Zoom plan ✅ (UNBLINDED account is Licensed)
- Cloud Recording enabled ✅ (4,059 recordings exist)
- Audio transcript toggle ON (need to verify)

## API Endpoint
```
GET /v2/meetings/{meetingId}/recordings
```
Returns all recording files including VTT transcript.

## The Pipeline (once credentials are set)
1. List all recordings via API
2. Filter for: Heart of Influence, Mastery Sessions, Huddles, Immersions
3. Download VTT transcripts
4. Parse and chunk for embedding
5. Upsert to saimemory Pinecone index

## Alternative Sources
- **Facebook:** ~1,500 HOI episodes on Unblinded page
- **Academy:** 1,500+ sessions at academy.unblindedmastery.com (already logged in via browser)

## Priority Recordings
1. Heart of Influence / Bella Verita (~2,000 episodes)
2. Tuesday/Thursday Mastery Sessions
3. Process Mastery Immersion 2024-2026
4. Aspire stage recordings
5. Ecosystem merging conversations
