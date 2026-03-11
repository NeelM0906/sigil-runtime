# Audio Extraction Skill

Extract audio from video files, voice notes, or any media.

## Usage

```bash
# Extract audio from video
ffmpeg -i input.mp4 -vn -acodec libmp3lame -q:a 2 output.mp3

# Extract audio keeping original codec
ffmpeg -i input.mp4 -vn -acodec copy output.aac

# Extract from Telegram voice note (usually .oga)
ffmpeg -i voice.oga -acodec libmp3lame -q:a 2 voice.mp3

# Extract and transcribe with Whisper
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 output.wav
whisper output.wav --model base --output_format txt
```

## Common Formats

| Input | Command | Output |
|-------|---------|--------|
| .mp4 | `-vn -acodec libmp3lame -q:a 2` | .mp3 |
| .oga (Telegram) | `-acodec libmp3lame -q:a 2` | .mp3 |
| .webm | `-vn -acodec libopus` | .opus |
| Any → Whisper | `-vn -acodec pcm_s16le -ar 16000 -ac 1` | .wav |

## Batch Extract

```bash
for f in *.mp4; do
  ffmpeg -i "$f" -vn -acodec libmp3lame -q:a 2 "${f%.mp4}.mp3"
done
```

## Transcribe with OpenAI Whisper API

```bash
curl -X POST https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer [REDACTED]" \
  -H "Content-Type: multipart/form-data" \
  -F file=@audio.mp3 \
  -F model=whisper-1
```
