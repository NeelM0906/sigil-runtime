---
name: zoom-ingest
description: Extract and download transcripts from Zoom Cloud Recordings. Filters by priority keywords (heart of influence, mastery session, etc.)
license: MIT
user-invocable: true
allowed-tools: web_fetch file_write memory_note
metadata:
  openclaw:
    requires:
      env: [ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET]
---
# Zoom Transcript Ingest Workflow

Use this skill when the user asks to pull Zoom Cloud Recording transcripts into workspace memory.

## Preconditions
1. Confirm required env vars are available: `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`.
2. Confirm destination path: `memory/zoom/` under the current workspace.
3. Ask for explicit date range if the user did not provide one.

## Procedure
1. Get OAuth token using Zoom Server-to-Server credentials.
2. Call Zoom recordings list endpoint for the date range.
3. Filter recordings by transcript priority keywords:
   - heart of influence
   - mastery session
   - zone action
   - ecosystem merging
4. For each matching recording:
   - find downloadable transcript files (`.vtt` preferred)
   - download transcript content
   - parse speaker/time markers into plain text blocks
5. Save outputs to workspace memory:
   - `memory/zoom/<recording-date>-<recording-id>.md`
   - include source metadata (recording id, topic, host, start time)
6. Emit a final summary table with:
   - recordings scanned
   - recordings matched
   - transcripts downloaded
   - files written

## Output Contract
Return:
- `matched_recordings` count
- `downloaded_transcripts` count
- `written_files` list
- `errors` list (if any)

## Failure Handling
- If OAuth fails, stop and report credentials issue.
- If transcript file is missing for a recording, skip and log it.
- If a write fails, continue processing remaining recordings and report partial success.
