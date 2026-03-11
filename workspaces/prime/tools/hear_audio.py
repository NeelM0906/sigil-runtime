#!/usr/bin/env python3
"""
Transcribe audio/video files so Sai can "hear" them.
Usage: hear_audio.py <file_path>
"""
import sys
import os
import subprocess
import tempfile

# Load env
with open('~/.openclaw/workspace-forge/.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

def transcribe(file_path):
    """Extract audio and transcribe with Whisper API"""
    
    # If it's a video, extract audio first
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.mp4', '.mov', '.webm', '.mkv', '.avi']:
        # Extract audio from video
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp_path = tmp.name
        subprocess.run([
            'ffmpeg', '-i', file_path, '-vn', '-acodec', 'libmp3lame', 
            '-q:a', '2', tmp_path, '-y'
        ], capture_output=True)
        audio_path = tmp_path
    elif ext in ['.ogg', '.oga', '.opus', '.m4a', '.wav', '.mp3', '.flac']:
        audio_path = file_path
    else:
        print(f"Unknown format: {ext}")
        return None
    
    # Transcribe with Whisper API
    import requests
    
    with open(audio_path, 'rb') as f:
        response = requests.post(
            'https://api.openai.com/v1/audio/transcriptions',
            headers={'Authorization': f'Bearer {os.environ["OPENAI_API_KEY"]}'},
            files={'file': f},
            data={'model': 'whisper-1'}
        )
    
    # Clean up temp file if we created one
    if ext in ['.mp4', '.mov', '.webm', '.mkv', '.avi']:
        os.unlink(audio_path)
    
    if response.ok:
        return response.json().get('text', '')
    else:
        print(f"Error: {response.text}")
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        # Find latest media file
        media_dir = os.path.expanduser('~/.openclaw/media/inbound')
        files = []
        for f in os.listdir(media_dir):
            if f.endswith(('.ogg', '.oga', '.mp4', '.mov', '.mp3', '.wav')):
                files.append((os.path.getmtime(os.path.join(media_dir, f)), f))
        if files:
            files.sort(reverse=True)
            file_path = os.path.join(media_dir, files[0][1])
            print(f"📁 Latest: {files[0][1]}")
        else:
            print("Usage: hear_audio.py <file_path>")
            sys.exit(1)
    else:
        file_path = sys.argv[1]
    
    print(f"🎧 Transcribing: {file_path}")
    text = transcribe(file_path)
    if text:
        print(f"\n📝 Transcript:\n{text}")
