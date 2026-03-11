#!/usr/bin/env python3
"""
Elite Group Training Processor

Downloads Elite transcripts from Zoom, runs them through the Unblinded Translator,
extracts Sean's patterns, and uploads to Pinecone saimemory index.
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from pinecone import Pinecone

# Load env
def load_env():
    for env_path in [
        Path.home() / '.openclaw' / 'workspace-forge' / '.env',
        Path.home() / '.openclaw' / '.env'
    ]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())

load_env()

# Initialize clients
oai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])

# Zoom credentials
ZOOM_ACCOUNT_ID = os.environ.get('ZOOM_ACCOUNT_ID', '-QuLHtVKSkqxjQwWNX6Iiw')
ZOOM_CLIENT_ID = os.environ.get('ZOOM_CLIENT_ID', 'KMOk_zwRgaWjz2SffvorA')
ZOOM_CLIENT_SECRET = os.environ.get('ZOOM_CLIENT_SECRET', '11mFHwzhmhpWYvaRKBSVYlbmaCKKa9xh')

# Output paths
OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'elite-translations'
TRANSCRIPT_DIR = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'elite-transcripts'
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


def get_elite_recordings():
    """Get all Elite recordings with transcripts"""
    token = get_zoom_token()
    all_meetings = []
    next_page = None
    
    for _ in range(10):
        params = {"page_size": 300, "from": "2023-01-01", "to": datetime.now().strftime('%Y-%m-%d')}
        if next_page:
            params['next_page_token'] = next_page
            
        resp = requests.get(
            "https://api.zoom.us/v2/accounts/me/recordings",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        data = resp.json()
        all_meetings.extend(data.get('meetings', []))
        next_page = data.get('next_page_token')
        if not next_page:
            break
    
    # Filter Elite recordings with transcripts
    elite = []
    for m in all_meetings:
        topic = m.get('topic', '').lower()
        if 'elite' in topic:
            has_transcript = any(f.get('file_type') == 'TRANSCRIPT' for f in m.get('recording_files', []))
            if has_transcript:
                elite.append(m)
    
    # Sort by date descending
    elite.sort(key=lambda x: x.get('start_time', ''), reverse=True)
    return elite


def download_transcript(meeting):
    """Download VTT transcript for a meeting"""
    token = get_zoom_token()
    
    for f in meeting.get('recording_files', []):
        if f.get('file_type') == 'TRANSCRIPT':
            url = f.get('download_url')
            if url:
                # Add access token to URL
                if '?' in url:
                    url += f'&access_token={token}'
                else:
                    url += f'?access_token={token}'
                
                resp = requests.get(url)
                resp.raise_for_status()
                
                # Save to file
                topic = meeting.get('topic', 'Untitled')
                safe_topic = "".join(c for c in topic if c.isalnum() or c in ' -_')[:40]
                date = meeting.get('start_time', '')[:10]
                filename = f"{date}_{safe_topic}.vtt"
                output_path = TRANSCRIPT_DIR / filename
                output_path.write_bytes(resp.content)
                
                return output_path, resp.text
    
    return None, None


def parse_vtt(vtt_text):
    """Parse VTT to plain text with speaker labels"""
    lines = []
    current_speaker = None
    
    for line in vtt_text.split('\n'):
        line = line.strip()
        # Skip headers, timestamps, and empty lines
        if not line or line.startswith('WEBVTT') or line.startswith('NOTE') or '-->' in line:
            continue
        if line[0].isdigit() and len(line) < 10:  # Skip cue numbers
            continue
        
        # Check for speaker labels (often in format "Speaker Name: text")
        if ':' in line and len(line.split(':')[0]) < 30:
            parts = line.split(':', 1)
            if len(parts) == 2 and parts[0].replace(' ', '').isalpha():
                speaker = parts[0].strip()
                text = parts[1].strip()
                if speaker != current_speaker:
                    lines.append(f"\n[{speaker}]")
                    current_speaker = speaker
                lines.append(text)
                continue
        
        lines.append(line)
    
    return ' '.join(lines)


def chunk_text(text, chunk_size=4000, overlap=300):
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def translate_and_extract(chunk, chunk_index, total_chunks, topic, date):
    """Run through Unblinded Translator and extract Sean's patterns"""
    
    system_prompt = f"""You are the Unblinded Formula Translator with a special focus on extracting Sean Callagy's teaching patterns.

{TRANSLATOR_PROMPT}

You are processing Section {chunk_index} of {total_chunks} from Elite Group Training: "{topic}" on {date}

Your job:
1. Identify Sean's exact teaching methodology in this section
2. Extract the Formula elements being demonstrated
3. Note specific phrases, metaphors, or frameworks Sean uses
4. Capture any new terminology or concepts introduced

Output as JSON with these fields:
- sean_patterns: List of specific teaching techniques used
- formula_elements: {{
    "process": which levers/operators demonstrated,
    "influence": what influence elements deployed,
    "self": what self-mastery addressed
  }}
- key_quotes: Exact memorable phrases (max 5)
- main_teaching: The central lesson being transmitted
- methodology: How Sean delivered this (story, live demo, confrontation, etc.)
- new_concepts: Any new terminology or frameworks introduced
- action_items: Specific actions prescribed to participants
"""
    
    response = oai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this Elite Group Training section:\n\n{chunk}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.5
    )
    
    return json.loads(response.choices[0].message.content)


def upsert_to_pinecone(translations, topic, date, meeting_uuid):
    """Upload extracted patterns to Pinecone saimemory index"""
    index = pc.Index('saimemory')
    
    vectors = []
    for i, t in enumerate(translations):
        # Create rich text for embedding
        text_for_embedding = f"""
Elite Group Training: {topic}
Date: {date}

Sean's Patterns: {', '.join(t.get('sean_patterns', []))}

Main Teaching: {t.get('main_teaching', '')}

Methodology: {t.get('methodology', '')}

Key Quotes: {'; '.join(t.get('key_quotes', []))}

Formula Elements:
- Process: {t.get('formula_elements', {}).get('process', '')}
- Influence: {t.get('formula_elements', {}).get('influence', '')}
- Self: {t.get('formula_elements', {}).get('self', '')}

New Concepts: {', '.join(t.get('new_concepts', []))}

Action Items: {', '.join(t.get('action_items', []))}
"""
        
        # Get embedding
        emb_resp = oai.embeddings.create(
            model="text-embedding-3-small",
            input=text_for_embedding
        )
        embedding = emb_resp.data[0].embedding
        
        vector_id = f"elite_{date}_{meeting_uuid[:8]}_{i}"
        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": {
                "source": f"Elite Group Training: {topic}",
                "date": date,
                "meeting_uuid": meeting_uuid,
                "chunk_index": i,
                "text": text_for_embedding[:8000],  # Pinecone metadata limit
                "sean_patterns": t.get('sean_patterns', [])[:10],
                "main_teaching": t.get('main_teaching', '')[:500],
                "key_quotes": t.get('key_quotes', [])[:5],
                "type": "elite_training"
            }
        })
    
    # Upsert in batches
    batch_size = 50
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        index.upsert(vectors=batch, namespace="elite_training")
    
    return len(vectors)


def process_recording(meeting):
    """Full pipeline: download, parse, translate, upload"""
    topic = meeting.get('topic', 'Untitled')
    date = meeting.get('start_time', '')[:10]
    uuid = meeting.get('uuid', '')
    
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
    
    # Translate and extract patterns from each chunk
    translations = []
    for i, chunk in enumerate(chunks, 1):
        print(f"   🔄 Analyzing chunk {i}/{len(chunks)}...")
        try:
            result = translate_and_extract(chunk, i, len(chunks), topic, date)
            result['source_topic'] = topic
            result['source_date'] = date
            result['chunk_index'] = i
            translations.append(result)
        except Exception as e:
            print(f"   ⚠️ Error on chunk {i}: {e}")
    
    # Save translations locally
    safe_topic = "".join(c for c in topic if c.isalnum() or c in ' -_')[:30]
    output_file = OUTPUT_DIR / f"{date}_{safe_topic}_patterns.json"
    output_file.write_text(json.dumps(translations, indent=2))
    print(f"   💾 Saved {len(translations)} extractions to {output_file}")
    
    # Upload to Pinecone
    if translations:
        count = upsert_to_pinecone(translations, topic, date, uuid)
        print(f"   📤 Uploaded {count} vectors to Pinecone saimemory/elite_training")
    
    return translations


def main():
    """Main processing workflow"""
    print("🔥 Elite Group Training Processor")
    print("=" * 50)
    
    # Get Elite recordings with transcripts
    print("\n🔍 Finding Elite recordings with transcripts...")
    elite = get_elite_recordings()
    print(f"✅ Found {len(elite)} Elite recordings with transcripts")
    
    # Process most recent 5
    limit = 5
    print(f"\n📊 Processing most recent {limit} recordings...")
    
    all_patterns = []
    processed = 0
    
    for meeting in elite[:limit]:
        try:
            patterns = process_recording(meeting)
            if patterns:
                all_patterns.extend(patterns)
                processed += 1
        except Exception as e:
            print(f"⚠️ Error processing {meeting.get('topic')}: {e}")
    
    print(f"\n✅ Processing complete!")
    print(f"   Recordings processed: {processed}/{limit}")
    print(f"   Total pattern extractions: {len(all_patterns)}")
    print(f"   Transcripts saved to: {TRANSCRIPT_DIR}")
    print(f"   Patterns saved to: {OUTPUT_DIR}")
    print(f"   Uploaded to: Pinecone saimemory/elite_training")
    
    # Summary of Sean's patterns found
    all_sean_patterns = []
    for p in all_patterns:
        all_sean_patterns.extend(p.get('sean_patterns', []))
    
    from collections import Counter
    pattern_counts = Counter(all_sean_patterns)
    
    print(f"\n📊 Top Sean Patterns Found:")
    for pattern, count in pattern_counts.most_common(10):
        print(f"   {count}x {pattern}")
    
    return all_patterns


if __name__ == '__main__':
    main()
