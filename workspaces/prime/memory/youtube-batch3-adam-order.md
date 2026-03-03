# YouTube Batch 3 - Adam Order (Post-Sadia Khan)

**Extracted by:** Miner 31
**Date:** 2026-02-23

## Summary

All 5 videos require **Whisper transcription** - YouTube blocked auto-subtitle access (missing PO token).

## Videos Needing Whisper

| # | Guest | Video ID | Status |
|---|-------|----------|--------|
| 1 | Michael Uslan - Batman Story | `s6ClwnpCZzg` | ❌ No auto-subs |
| 2 | Kevin Mayer - Disney/TikTok AI | `7E5bL6UIOBc` | ❌ No auto-subs |
| 3 | Chevy Chase - Comedy | `aolQ4h5Ffxo` | ❌ No auto-subs |
| 4 | Ralph Macchio - Karate Kid | `DAFnv89vNRw` | ❌ No auto-subs |
| 5 | Charlie Sheen | `_becVUQpsAI` | ❌ No auto-subs |

## Technical Details

YouTube error: "There are missing subtitles languages because a PO token was not provided."

This batch requires audio download + Whisper transcription as fallback.

## Next Steps

These 5 videos should be queued for Whisper processing:
- Download audio: `yt-dlp -x --audio-format mp3 <url>`
- Transcribe with Whisper
