# Whisper Transcription Report - Miner 28

**Date:** 2026-02-23 19:07 EST
**Video:** Mike Tyson interview (0SlsEgZxj9c)
**Status:** ✅ SUCCESS

## Summary

Successfully downloaded and transcribed the Mike Tyson YouTube video that was blocked for other extraction methods.

## Files Created

- **Audio:** `/Users/samantha/Projects/youtube-transcripts/tyson.mp3` (22MB)
- **Transcript:** `/Users/samantha/Projects/youtube-transcripts/tyson-transcript.txt` (44,022 characters)

## Process Notes

1. **Download Challenge:** Initial attempts with yt-dlp 2025.10.14 failed with HTTP 403 Forbidden
2. **Solution:** Upgraded to yt-dlp 2026.02.21 via Homebrew, which includes:
   - `deno` JavaScript solver for YouTube challenges
   - Android VR player API fallback
   - Updated throttling workarounds
3. **Transcription:** Used OpenAI Whisper API (`whisper-1` model) - completed in ~30 seconds

## Content Preview

The video is a **Sean Callagy Unblinded Podcast** episode featuring Mike Tyson. Topics include:
- Tyson's relationship with Cus D'Amato (legendary mentor)
- His transformation from Brooklyn streets to youngest heavyweight champion
- Themes of mentorship, resilience, and personal evolution
- Discussion of what Ali vs Tyson in their primes would look like

## Technical Details

- **yt-dlp version:** 2026.02.21 (latest)
- **Downloaded format:** 251 (opus audio in webm), converted to MP3
- **Whisper model:** whisper-1
- **Python:** 3.9 (for OpenAI SDK)
