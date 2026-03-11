#!/usr/bin/env python3
"""Transcribe audio files using OpenAI Whisper API with chunking for large files."""
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from openai import OpenAI

def get_duration(file_path):
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', file_path
    ], capture_output=True, text=True)
    return float(result.stdout.strip())

def split_audio(file_path, chunk_duration_sec=600):
    """Split audio into chunks of specified duration. Returns list of chunk paths."""
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

def transcribe_file(file_path, client):
    """Transcribe a single audio file."""
    with open(file_path, 'rb') as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcript

def main():
    if len(sys.argv) < 3:
        print("Usage: python transcribe_chunked.py <audio_file> <output_file>")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    output_path = sys.argv[2]
    
    client = OpenAI()
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    
    print(f"Processing: {audio_path} ({file_size_mb:.1f}MB)")
    
    if file_size_mb > 24:
        print(f"File > 24MB, splitting into chunks...")
        chunks, temp_dir = split_audio(audio_path)
        print(f"Created {len(chunks)} chunks")
        
        full_transcript = []
        for i, chunk in enumerate(chunks):
            print(f"Transcribing chunk {i+1}/{len(chunks)}...")
            transcript = transcribe_file(chunk, client)
            full_transcript.append(transcript)
            os.remove(chunk)
        
        os.rmdir(temp_dir)
        final_transcript = "\n\n".join(full_transcript)
    else:
        print("File < 24MB, transcribing directly...")
        final_transcript = transcribe_file(audio_path, client)
    
    with open(output_path, 'w') as f:
        f.write(final_transcript)
    
    print(f"Saved transcript to: {output_path}")
    return final_transcript

if __name__ == "__main__":
    main()
