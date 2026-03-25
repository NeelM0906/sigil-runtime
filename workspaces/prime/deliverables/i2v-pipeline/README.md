# 🎬 Image-to-Video Pipeline — Hero's Journey Film
_The last wire. Flux portraits → Kling i2v w/ Elements → Supabase → Remotion._

## Status: BUILDING
## Owner: Mission Control (Prime)
## Priority: #1 (from OG Sai + Aiko + Sean)

## Architecture:
```
Step 1: Generate Flux Pro v1.1 portraits (16 chars × front + 3/4)
         → Upload to fal storage, get public URLs
         → Store URLs in character_registry.json

Step 2: Build Element configs per scene
         → Map characters present in each scene to Elements
         → Reference as @Element 1, @Element 2 in prompt

Step 3: Kling v3 Pro image-to-video
         → start_image_url = scene establishing shot (Flux)
         → elements[] = character portraits
         → generate_audio = true
         → duration = "10" (minimum!)

Step 4: ffmpeg assembly → Remotion polish → deliver
```

## Rules (from 10 Commandments + Protocols):
- ALL characters are ANIMALS. "Not a human" in EVERY prompt.
- Minimum 10 seconds per scene (5s = no audio)
- Kling CANNOT spell — no text in prompts
- "Act Eye" phonetically, never "ACT-I"
- Dialogue FIRST, style tag at END
- generate_audio: true always
- All repos PRIVATE
- persist.py after every deliverable
