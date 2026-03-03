# Heart of Influence — Extraction Plan

_Documented Feb 24, 2026_

## Discovery

Sean has 500+ episodes of "Heart of Influence" on Facebook Video — this is the motherload of his live coaching patterns.

## Source Details

- **Location:** facebook.com/profile.php?id=100093213169620 (Bella Verita's page)
- **Co-host:** Bella Verita
- **Episode count:** 500+
- **Guest count:** 2,500+ (estimated)
- **Episode length:** 15-60 minutes typical
- **Format:** Live coaching conversations

## Why This Matters

This is Sean IN ACTION. Not theory, not prepared content — real-time:
- How he opens with energy
- How he reads people
- How he creates emotional connection
- How he uses humor
- How he moves people from skepticism to belief
- The 4-Step Communication Model live
- Zone Action identification in conversation
- Heroic language patterns

**Adam's directive:** Only process content where Sean is on the recording. He IS the model.

## Extraction Pipeline

### Phase 1: Catalog URLs
1. Use browser automation to scroll through video library
2. Extract video URLs, titles, dates, durations
3. Store in structured format (JSON or CSV)
4. Filter for episodes with Sean speaking

### Phase 2: Download Videos
1. Use yt-dlp or similar for Facebook video download
2. Store in organized directory structure
3. Create manifest of downloaded content

### Phase 3: Transcribe
1. Use Whisper (local or API) for transcription
2. Include timestamps for reference
3. Identify speakers (Sean vs guest)

### Phase 4: Pattern Extraction
1. Apply same analysis used for Mylo (324K words)
2. Identify Sean's unique patterns:
   - Opening hooks
   - Energy markers
   - Transition phrases
   - Closing techniques
3. Cross-reference with 4-Step Communication Model

### Phase 5: Knowledge Base
1. Upload to Pinecone `saimemory` or dedicated index
2. Namespace by episode or topic
3. Enable semantic search for pattern retrieval

## Technical Notes

- **Browser profile:** Use `openclaw` (managed browser)
- **No Chrome extension needed** for this task
- **Storage estimate:** ~500 episodes × 30min avg × 1MB/min = ~15GB video, ~50MB transcripts

## Priority Episodes

Start with:
1. Most recent (best audio quality, current Sean)
2. Episodes with high engagement (comments/reactions)
3. Any marked as "best of" or featured

## Files

- `memory/heart-of-influence/catalog.json` — URL catalog
- `memory/heart-of-influence/transcripts/` — Raw transcripts
- `memory/heart-of-influence/patterns/` — Extracted patterns

---

_This is the goldmine. 500+ episodes of Sean coaching in real-time._
