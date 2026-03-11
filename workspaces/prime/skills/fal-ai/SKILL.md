---
name: fal-ai
description: "Generate and analyze video/images via fal.ai unified API. Supports 1000+ models: text-to-video, image-to-video, text-to-image, video analysis, upscaling, lipsync, and more."
metadata:
  openclaw:
    emoji: "🎬"
    requires:
      env: [FAL_KEY]
      bins: [python3]
---

# fal.ai — Unified Video & Image Generation

One API key. 1000+ models. Video gen, image gen, video analysis, lipsync, upscaling, and more.

## Setup

1. Get API key: https://fal.ai/dashboard/keys
2. Add to the repo `.env` (or export it in your shell):
   ```
   FAL_KEY=[REDACTED]
   ```
3. SDK installed in workspace venv: `fal-client==0.13.1`

## Quick Start

All commands run from the skill directory:

```bash
cd {baseDir} && python3 fal_generate.py <command> [options]
```

### Text-to-Video

```bash
python3 fal_generate.py video --prompt "A golden retriever running through a sunlit meadow" --model kling-v2 --duration 5
```

### Image-to-Video

```bash
python3 fal_generate.py video --image /path/to/image.jpg --prompt "camera slowly zooms in" --model kling-v2
```

### Text-to-Image

```bash
python3 fal_generate.py image --prompt "A cyberpunk cityscape at night" --model flux-dev
```

### Video Analysis (Depth Map)

```bash
python3 fal_generate.py depth --video /path/to/video.mp4
```

## Available Models

### Video Generation
| Model ID | Name | Strengths | Duration |
|----------|------|-----------|----------|
| `kling-v2` | Kling V2 Master | Human motion, faces | 5-10s |
| `kling-v2-turbo` | Kling V2.5 Turbo | Fast, good quality | 5-10s |
| `ltx-video` | LTX-2 19B | Audio + video | 5s |
| `minimax-video` | MiniMax Hailuo | Long form, creative | 6s |
| `veo3` | Veo 3.1 | Best overall quality | 5-8s |
| `runway-gen4` | Runway Gen-4.5 | Complex motion | 5-10s |
| `pika-v2` | Pika 2.2 | Fast iteration | 3-4s |
| `wan-video` | Wan 2.6 | Open source, good | 5s |

### Image Generation
| Model ID | Name | Strengths |
|----------|------|-----------|
| `flux-dev` | FLUX.1 Dev | High quality, versatile |
| `flux-schnell` | FLUX.1 Schnell | Ultra fast (1-4 steps) |
| `flux-pro` | FLUX.2 Pro | Best quality |
| `seedream` | Seedream 4.5 | Realistic, high fidelity |

### Analysis & Utilities
| Model ID | Name | Purpose |
|----------|------|---------|
| `depth` | Video Depth Anything | Per-frame depth estimation |
| `upscale` | Topaz Upscale | Video/image upscaling |

## Model Selection Guide

- **Best quality, no budget concern:** `veo3` or `runway-gen4`
- **Human faces/motion:** `kling-v2`
- **Fast iteration/testing:** `flux-schnell` (image) or `kling-v2-turbo` (video)
- **Video with audio:** `ltx-video`
- **Ad content / product shots:** `flux-pro` (image) → `kling-v2` (animate)

## Output

- Videos saved to `/tmp/fal_output/` by default (or `--output /path/to/file`)
- Images returned as URLs + downloaded locally
- All outputs logged with model, prompt, and cost info

## Cost Control

- Start with shortest duration (3-5s) to validate prompts
- Use turbo variants for drafts
- Preview at lower resolution when available
- Download immediately — signed URLs expire (typically 24h)

## Programmatic Video Assembly

Full pipeline: generate multiple clips → assemble with transitions, overlays, audio, and platform-specific formatting.

```bash
# Show example pipeline config
python3 fal_assemble.py example

# Run a pipeline from config
python3 fal_assemble.py --config pipeline.json --output final.mp4
```

### Scene Types

| Type | Description | Required Fields |
|------|-------------|-----------------|
| `title` | Solid color + text card | `text`, `duration` |
| `video` | Generate clip from prompt | `prompt`, `model`, `duration` |
| `image_to_video` | Generate image → animate | `image_prompt`, `motion_prompt` |
| `file` | Use existing local video | `path` |

### Pipeline Features

- **Crossfade transitions** between scenes (configurable duration)
- **Text overlays** with positioning, timing, and background opacity
- **Background audio** with volume control and looping
- **Platform resize** — youtube, tiktok, instagram-reel, instagram-feed, linkedin, facebook, twitter
- **Title/CTA cards** with custom colors, fonts, sizing
- **Normalization** — all clips auto-matched to consistent resolution/fps/codec

### Example: Ad Video Pipeline

```json
{
  "settings": {"width": 1280, "height": 720, "crossfade_duration": 0.5},
  "scenes": [
    {"type": "title", "text": "The $47K Mistake", "duration": 3},
    {"type": "video", "prompt": "Attorney in courthouse...", "model": "kling-v2", "duration": 5},
    {"type": "image_to_video", "image_prompt": "Viking warrior...", "motion_prompt": "camera push in", "duration": 5},
    {"type": "title", "text": "Don't be the bottleneck.", "duration": 2}
  ],
  "overlays": [{"text": "ACT-I Legal Visionnaire", "position": "bottom", "start": 3, "end": 12}],
  "platform": "youtube"
}
```

## API Patterns

All video generation is async:
1. Submit request → get request ID
2. Poll until complete (SDK handles this via `subscribe()`)
3. Download from signed URL

Both `fal_generate.py` and `fal_assemble.py` handle polling automatically.
