#!/usr/bin/env python3
"""
Kai Training → Translator → saimemory (namespace: kai-training)

Finds all kai-training-*.md reports, runs each through the Unblinded Translator,
then uploads translated vectors to saimemory under namespace 'kai-training'.

Usage: python3 tools/upload_kai_training.py
"""
import os, sys, json, subprocess, hashlib, requests, time
from pathlib import Path
from datetime import datetime

# Load env
for env_path in [
    Path.home() / '.openclaw' / 'workspace-forge' / '.env',
    Path.home() / '.openclaw' / '.env',
]:
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

from pinecone import Pinecone

OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PINECONE_KEY = os.environ.get('PINECONE_API_KEY', '')
TRANSLATOR = Path.home() / '.openclaw' / 'workspace' / 'tools' / 'unblinded-translator' / 'translate.py'
PYTHON = Path.home() / '.openclaw' / 'workspace' / 'tools' / '.venv' / 'bin' / 'python3'
REPORTS_DIR = Path.home() / '.openclaw' / 'workspace' / 'reports'
TRANSLATED_DIR = Path.home() / '.openclaw' / 'workspace-forge' / 'reports' / 'kai-translated'
TRANSLATED_DIR.mkdir(parents=True, exist_ok=True)

def translate_file(file_path):
    """Run file through Unblinded Translator, return translated text."""
    out_file = TRANSLATED_DIR / f"translated-{file_path.name}"
    
    if out_file.exists():
        print(f"  [cached] Using existing translation: {out_file.name}")
        return out_file.read_text()
    
    print(f"  [translate] Running Translator on {file_path.name}...")
    result = subprocess.run(
        [str(PYTHON), str(TRANSLATOR), '--file', str(file_path), '--mode', 'narrative'],
        capture_output=True, text=True, timeout=300
    )
    
    if result.returncode != 0:
        print(f"  [warn] Translator stderr: {result.stderr[:500]}")
    
    translated = result.stdout.strip()
    if len(translated) < 200:
        # Fallback: use raw content with a note
        print(f"  [warn] Translator output thin ({len(translated)} chars), using raw")
        translated = file_path.read_text()
    
    out_file.write_text(translated)
    print(f"  [done] Translated: {len(translated)} chars → {out_file.name}")
    return translated

def embed_text(text):
    """Get embedding via OpenRouter."""
    r = requests.post('https://openrouter.ai/api/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENROUTER_KEY}'},
        json={'model': 'openai/text-embedding-3-small', 'input': text[:8000]},
        timeout=30)
    return r.json()['data'][0]['embedding']

def upload_to_saimemory(file_path, translated_text):
    """Upload translated Kai training to saimemory under kai-training namespace."""
    pc = Pinecone(api_key=PINECONE_KEY)
    idx = pc.Index('saimemory')
    
    # Chunk if long (max ~8000 chars per vector)
    chunks = []
    if len(translated_text) > 8000:
        words = translated_text.split()
        chunk, chunk_size = [], 0
        for word in words:
            chunk.append(word)
            chunk_size += len(word) + 1
            if chunk_size > 7500:
                chunks.append(' '.join(chunk))
                chunk, chunk_size = [], 0
        if chunk:
            chunks.append(' '.join(chunk))
    else:
        chunks = [translated_text]
    
    print(f"  [upload] {len(chunks)} chunk(s) → saimemory/kai-training")
    
    # Extract date and topic from filename
    name = file_path.stem  # e.g. kai-training-2026-03-07
    parts = name.split('-')
    date_str = '-'.join(p for p in parts if p.isdigit() or (len(p)==4 and p.startswith('20')))
    topic = name.replace('kai-training-', '').replace('kai-training-session-', '')
    
    for i, chunk in enumerate(chunks):
        vid = f"kai-training-{hashlib.md5(f'{file_path.name}-{i}'.encode()).hexdigest()[:12]}"
        embedding = embed_text(chunk)
        
        idx.upsert(vectors=[{
            'id': vid,
            'values': embedding,
            'metadata': {
                'text': chunk,
                'source': 'kai-training',
                'file': file_path.name,
                'topic': topic,
                'date': date_str or 'unknown',
                'chunk': i,
                'total_chunks': len(chunks),
                'type': 'translated',
                'uploaded_at': datetime.utcnow().isoformat(),
                'sister': 'kai'
            }
        }], namespace='kai-training')
        
        print(f"    chunk {i+1}/{len(chunks)}: {len(chunk)} chars ✅")
        time.sleep(0.5)

def main():
    # Find all Kai training reports
    kai_files = sorted(REPORTS_DIR.glob('kai-training*.md'))
    
    # Also check for mastery training files
    mastery_files = sorted(REPORTS_DIR.glob('kai-mastery-training*.md'))
    all_files = list(kai_files) + [f for f in mastery_files if f not in kai_files]
    
    print(f"⚔️ Kai Training Upload Pipeline")
    print(f"Found {len(all_files)} files to process\n")
    
    for i, f in enumerate(all_files):
        print(f"[{i+1}/{len(all_files)}] {f.name}")
        
        try:
            translated = translate_file(f)
            upload_to_saimemory(f, translated)
            print(f"  ✅ Complete\n")
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
        
        time.sleep(2)
    
    print(f"⚔️ Done — {len(all_files)} Kai training files in saimemory/kai-training")

if __name__ == '__main__':
    main()
