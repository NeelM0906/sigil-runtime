# 🔧 Exact Software Stack — What Sai Uses to Make Videos

---

## PYTHON (Video Generation & Memory)

```bash
python3 --version   # Python 3.14.3
pip install fal_client==0.13.1 requests==2.32.5 pinecone==8.1.0 supabase==2.28.0 openai==2.22.0
```

| Package | Version | What it does |
|---------|---------|-------------|
| `fal_client` | 0.13.1 | Calls fal.ai — Kling v3 Pro, Flux, Seedance, all video/image models |
| `requests` | 2.32.5 | HTTP calls — ElevenLabs, n8n webhooks, API docs |
| `pinecone` | 8.1.0 | Vector search — ublib2, saimemory, ultimatestratabrain |
| `supabase` | 2.28.0 | Database + storage — sai_memory, Forge-assets bucket |
| `openai` | 2.22.0 | Embeddings via OpenRouter, Whisper transcription |

### Install command:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fal_client==0.13.1 requests==2.32.5 pinecone==8.1.0 supabase==2.28.0 openai==2.22.0
```

---

## FFMPEG (Video Assembly)

```bash
ffmpeg -version   # ffmpeg version 8.0.1
```

**Install:** `brew install ffmpeg` (Mac) or `apt install ffmpeg` (Linux)

**What I use it for:**
```bash
# Convert scene to transport stream
ffmpeg -y -i scene.mp4 -c copy -bsf:v h264_mp4toannexb -f mpegts scene.ts

# Concat scenes into episode
ffmpeg -y -i "concat:s1.ts|s2.ts|s3.ts" -c copy -movflags +faststart episode.mp4

# Telegram-optimized (under 50MB)
ffmpeg -y -i episode.mp4 -c:v libx264 -preset fast -crf 22 -vf scale=1280:720 -c:a aac -b:a 128k -ac 2 -movflags +faststart episode-telegram.mp4
```

---

## NODE.JS (Remotion & Creative Forge)

```bash
node --version   # v22.22.0
```

**Install:** `brew install node@22` (Mac)

---

## REMOTION (Timeline Editor)

```json
{
  "remotion": "4.0.438",
  "@remotion/cli": "4.0.438",
  "@remotion/player": "4.0.438",
  "@remotion/renderer": "4.0.438",
  "@remotion/bundler": "4.0.438",
  "react": "19.2.4",
  "react-dom": "19.2.4",
  "typescript": "5.9.3"
}
```

### Install:
```bash
npm install remotion@4.0.438 @remotion/cli@4.0.438 @remotion/player@4.0.438 @remotion/renderer@4.0.438 @remotion/bundler@4.0.438 react react-dom typescript @types/react
```

---

## FAL.AI MODELS (What I Generate With)

| Model | Endpoint | What it does |
|-------|----------|-------------|
| **Kling v3 Pro (text-to-video)** | `fal-ai/kling-video/v3/pro/text-to-video` | Main video generation. 10s scenes. generate_audio=true for dialogue. |
| **Kling v3 Pro (image-to-video)** | `fal-ai/kling-video/v3/pro/image-to-video` | Character consistency. Pass portrait as start image. |
| **Flux Pro v1.1** | `fal-ai/flux-pro/v1.1` | Character portraits. Image generation. |
| **Seedance 2.0** | `fal-ai/seedance/video-generation/seedance-2-0` | Cartoon animals (sometimes). Good for stylized. |

### How I call them:
```python
import fal_client
import os

os.environ['FAL_KEY'] = 'your-fal-key'

# Text to video (main method)
handle = fal_client.submit("fal-ai/kling-video/v3/pro/text-to-video", arguments={
    "prompt": "A cartoon LION says: 'Nine years.' Disney Pixar style.",
    "duration": "10",
    "aspect_ratio": "16:9",
    "generate_audio": True,
})

# Poll until done
import time
while True:
    status = fal_client.status("fal-ai/kling-video/v3/pro/text-to-video", handle.request_id, with_logs=False)
    if type(status).__name__ == "Completed":
        result = fal_client.result("fal-ai/kling-video/v3/pro/text-to-video", handle.request_id)
        video_url = result["video"]["url"]
        print(f"Done! {video_url}")
        break
    time.sleep(30)

# Image generation (for character portraits)
handle = fal_client.submit("fal-ai/flux-pro/v1.1", arguments={
    "prompt": "A cartoon LION with golden mane, sunglasses, teal jersey. Character sheet.",
    "image_size": "square",
    "num_images": 1,
})
```

---

## ELEVENLABS (Voice & Audio)

**API Base:** `https://api.elevenlabs.io/v1`
**Voice ID (Sai):** `CJXmyMqQHq6bTPm3iEMP`
**Model:** `eleven_multilingual_v2`

```python
import requests

response = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
    headers={"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"},
    json={
        "text": "Your narration here",
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
)
with open("voiceover.mp3", "wb") as f:
    f.write(response.content)
```

---

## COMPLETE REQUIREMENTS.TXT

```
fal_client==0.13.1
requests==2.32.5
pinecone==8.1.0
supabase==2.28.0
openai==2.22.0
```

---

## SYSTEM DEPENDENCIES

```bash
# Mac
brew install ffmpeg node@22 python@3.14

# Linux (Debian/Ubuntu)
apt install ffmpeg nodejs python3 python3-pip python3-venv

# For Remotion cloud rendering (Dockerfile)
apt install chromium fonts-liberation libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 libasound2
```

---

## THE FULL PIPELINE IN ORDER

```
1. Write playwright script (SOUL.md voice, Story Circle structure)
2. Generate character portraits (Flux Pro → Supabase)
3. Generate video scenes (Kling v3 Pro text-to-video, 10s, generate_audio=true)
4. Poll fal.ai for completion (30s intervals)
5. Download videos (urllib.request.urlretrieve)
6. Convert to transport stream (ffmpeg -bsf:v h264_mp4toannexb)
7. Concat all scenes (ffmpeg concat)
8. Compress for Telegram (ffmpeg -crf 22 -vf scale=1280:720)
9. Deliver (Telegram message tool or Supabase upload)
10. Log to worklog + api_docs (persist learnings)
```

That's it. That's exactly what I run. Same packages, same versions, same commands. Clone it and you have the same Creative Forge power. 🎬🔥
