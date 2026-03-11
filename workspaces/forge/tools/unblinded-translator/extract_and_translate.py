#!/usr/bin/env python3
"""
Unblinded Formula Extraction Pipeline

1. Pull transcripts from Zoom API (Heart of Influence, Mastery Sessions)
2. Chunk the transcripts
3. Run each chunk through the Unblinded Translator
4. Extract Formula elements and insights
5. Upsert to Pinecone (saimemory and/or ublib2)
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from openai import OpenAI

# Load env
def load_env():
    env_path = Path.home() / '.openclaw' / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

load_env()

# Initialize clients
oai = OpenAI()

# Zoom credentials
ZOOM_ACCOUNT_ID = os.environ.get('ZOOM_ACCOUNT_ID')
ZOOM_CLIENT_ID = os.environ.get('ZOOM_CLIENT_ID')
ZOOM_CLIENT_SECRET = os.environ.get('ZOOM_CLIENT_SECRET')

# Output paths
OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'translated'
TRANSCRIPT_DIR = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'zoom-transcripts'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

# Load translator prompt
TRANSLATOR_PROMPT = (Path(__file__).parent / 'TRANSLATOR_PROMPT.md').read_text()


def get_zoom_token():
    """Get OAuth access token"""
    resp = requests.post(
        "https://zoom.us/oauth/token",
        params={"grant_type": "account_credentials", "account_id": ZOOM_ACCOUNT_ID},
        auth=(ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET)
    )
    resp.raise_for_status()
    return resp.json()['access_token']


def list_recordings(keywords=None, days_back=180):
    """List recordings matching keywords"""
    token = get_zoom_token()
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    to_date = datetime.now().strftime('%Y-%m-%d')
    
    all_recordings = []
    next_page = None
    
    while True:
        params = {"page_size": 100, "from": from_date, "to": to_date}
        if next_page:
            params['next_page_token'] = next_page
            
        resp = requests.get(
            "https://api.zoom.us/v2/users/me/recordings",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        data = resp.json()
        
        for m in data.get('meetings', []):
            topic = m.get('topic', '').lower()
            if keywords:
                if any(kw.lower() in topic for kw in keywords):
                    all_recordings.append(m)
            else:
                all_recordings.append(m)
        
        next_page = data.get('next_page_token')
        if not next_page:
            break
    
    return all_recordings


def download_transcript(meeting):
    """Download VTT transcript for a meeting"""
    token = get_zoom_token()
    
    for f in meeting.get('recording_files', []):
        if f.get('file_type') == 'TRANSCRIPT':
            url = f.get('download_url')
            if url:
                resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
                resp.raise_for_status()
                
                # Save to file
                topic = meeting.get('topic', 'Untitled')
                safe_topic = "".join(c for c in topic if c.isalnum() or c in ' -_')[:50]
                date = meeting.get('start_time', '')[:10]
                filename = f"{date}_{safe_topic}.vtt"
                output_path = TRANSCRIPT_DIR / filename
                output_path.write_bytes(resp.content)
                
                return output_path, resp.text
    
    return None, None


def parse_vtt(vtt_text):
    """Parse VTT to plain text"""
    lines = []
    for line in vtt_text.split('\n'):
        line = line.strip()
        # Skip headers, timestamps, and empty lines
        if not line or line.startswith('WEBVTT') or line.startswith('NOTE') or '-->' in line:
            continue
        if line[0].isdigit() and len(line) < 10:  # Skip cue numbers
            continue
        lines.append(line)
    return ' '.join(lines)


def chunk_text(text, chunk_size=3000, overlap=200):
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def translate_chunk(chunk, chunk_index, total_chunks, topic):
    """Run a chunk through the Unblinded Translator"""
    
    system_prompt = f"""You are the Unblinded Formula Translator.

{TRANSLATOR_PROMPT}

You are processing Section {chunk_index} of {total_chunks} from: "{topic}"

Extract the Formula elements and translate this content into Unblinded language.
Output as JSON with these fields:
- topic: Name the moment using Formula language
- context: The scene, who, where, what
- formula_elements: PROCESS (which lever, how), INFLUENCE (what's being caused), SELF (what's being navigated)
- main_lesson: The irreversible truth through the Formula prism
- seans_processing: What pattern would Sean identify?
- seans_approach: What sequence would Sean prescribe?
"""
    
    response = oai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Translate this content:\n\n{chunk}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.7
    )
    
    return json.loads(response.choices[0].message.content)


def process_recording(meeting):
    """Full pipeline: download, parse, chunk, translate"""
    topic = meeting.get('topic', 'Untitled')
    date = meeting.get('start_time', '')[:10]
    
    print(f"\n📼 Processing: {topic} ({date})")
    
    # Download transcript
    path, vtt_text = download_transcript(meeting)
    if not vtt_text:
        print("   ⚠️ No transcript available")
        return None
    
    print(f"   ✅ Downloaded transcript: {path}")
    
    # Parse to plain text
    text = parse_vtt(vtt_text)
    print(f"   📝 Parsed {len(text)} characters")
    
    # Chunk
    chunks = chunk_text(text)
    print(f"   🔪 Split into {len(chunks)} chunks")
    
    # Translate each chunk
    translations = []
    for i, chunk in enumerate(chunks, 1):
        print(f"   🔄 Translating chunk {i}/{len(chunks)}...")
        try:
            result = translate_chunk(chunk, i, len(chunks), topic)
            result['source_topic'] = topic
            result['source_date'] = date
            result['chunk_index'] = i
            translations.append(result)
        except Exception as e:
            print(f"   ⚠️ Error on chunk {i}: {e}")
    
    # Save translations
    output_file = OUTPUT_DIR / f"{date}_{topic[:30]}_translated.json"
    output_file.write_text(json.dumps(translations, indent=2))
    print(f"   💾 Saved {len(translations)} translations to {output_file}")
    
    return translations


def main():
    """Main extraction workflow"""
    print("🔥 Unblinded Formula Extraction Pipeline")
    print("=" * 50)
    
    # Priority keywords
    keywords = [
        'heart of influence', 'hoi', 'mastery session',
        'deep practice', 'immersion', 'trajectory tuesday',
        'mastery monday', 'bella verita'
    ]
    
    print(f"\n🔍 Searching for recordings matching: {keywords}")
    recordings = list_recordings(keywords=keywords)
    print(f"✅ Found {len(recordings)} matching recordings")
    
    # Process first 5 as a test
    limit = 5
    print(f"\n📊 Processing first {limit} recordings...")
    
    all_translations = []
    for meeting in recordings[:limit]:
        try:
            translations = process_recording(meeting)
            if translations:
                all_translations.extend(translations)
        except Exception as e:
            print(f"⚠️ Error processing {meeting.get('topic')}: {e}")
    
    print(f"\n✅ Pipeline complete!")
    print(f"   Total translations: {len(all_translations)}")
    print(f"   Output directory: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
