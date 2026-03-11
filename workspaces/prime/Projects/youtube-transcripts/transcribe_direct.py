#!/usr/bin/env python3
"""Direct transcription with immediate output."""
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from openai import OpenAI

def get_duration(file_path):
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', file_path
    ], capture_output=True, text=True)
    return float(result.stdout.strip())

def split_audio(file_path, chunk_duration_sec=600):
    chunks = []
    duration = get_duration(file_path)
    num_chunks = int(duration // chunk_duration_sec) + 1
    
    temp_dir = tempfile.mkdtemp()
    base_name = Path(file_path).stem
    
    for i in range(num_chunks):
        start = i * chunk_duration_sec
        chunk_path = os.path.join(temp_dir, f"{base_name}_chunk_{i:03d}.mp3")
        subprocess.run([
            'ffmpeg', '-y', '-i', file_path,
            '-ss', str(start), '-t', str(chunk_duration_sec),
            '-acodec', 'libmp3lame', '-ab', '64k', chunk_path
        ], capture_output=True)
        if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 0:
            chunks.append(chunk_path)
    
    return chunks, temp_dir

def main():
    audio_path = sys.argv[1]
    output_path = sys.argv[2]
    
    client = OpenAI()
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    
    print(f"Processing: {audio_path} ({file_size_mb:.1f}MB)", flush=True)
    
    if file_size_mb > 24:
        print(f"Splitting into chunks...", flush=True)
        chunks, temp_dir = split_audio(audio_path)
        print(f"Created {len(chunks)} chunks", flush=True)
        
        full_transcript = []
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i+1}/{len(chunks)}...", flush=True)
            with open(chunk, 'rb') as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text"
                )
            full_transcript.append(transcript)
            os.remove(chunk)
            print(f"  Done chunk {i+1}", flush=True)
        
        os.rmdir(temp_dir)
        final_transcript = "\n\n".join(full_transcript)
    else:
        print("Direct transcription...", flush=True)
        with open(audio_path, 'rb') as f:
            final_transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text"
            )
    
    with open(output_path, 'w') as f:
        f.write(final_transcript)
    
    print(f"DONE: {output_path}", flush=True)

if __name__ == "__main__":
    main()
