#!/usr/bin/env python3
"""
Fetch new ElevenLabs call transcripts and save to memory
"""
import os
import json
from datetime import datetime

with open('~/.openclaw/workspace-forge/.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

import requests

API_KEY = os.environ['ELEVENLABS_API_KEY']
HEADERS = {'xi-api-key': API_KEY}
BASE_URL = 'https://api.elevenlabs.io/v1/convai'
AGENT_ID = 'agent_8001kj7288ywf7vtdxn84amesb77'
MEMORY_DIR = '~/.openclaw/workspace/memory'
SEEN_FILE = f'{MEMORY_DIR}/.elevenlabs_seen.json'

def get_seen_conversations():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen_conversations(seen):
    with open(SEEN_FILE, 'w') as f:
        json.dump(list(seen), f)

def fetch_transcript(conv_id):
    resp = requests.get(f'{BASE_URL}/conversations/{conv_id}', headers=HEADERS)
    if resp.ok:
        return resp.json()
    return None

def main():
    print(f"🎧 Fetching ElevenLabs transcripts - {datetime.now()}")
    
    # Get conversations
    resp = requests.get(f'{BASE_URL}/conversations?agent_id={AGENT_ID}', headers=HEADERS)
    if not resp.ok:
        print(f"Error: {resp.text}")
        return
    
    conversations = resp.json().get('conversations', [])
    seen = get_seen_conversations()
    new_count = 0
    
    for conv in conversations[:10]:  # Check last 10
        conv_id = conv['conversation_id']
        if conv_id in seen:
            continue
        
        # Fetch full transcript
        data = fetch_transcript(conv_id)
        if not data or not data.get('transcript'):
            continue
        
        # Format transcript
        transcript = data['transcript']
        messages = '\n'.join([f"{t['role']}: {t['message']}" for t in transcript])
        
        duration = conv.get('call_duration_secs', 0)
        msg_count = conv.get('message_count', 0)
        timestamp = datetime.fromtimestamp(conv.get('start_time_unix_secs', 0))
        
        # Save to daily memory
        today = datetime.now().strftime('%Y-%m-%d')
        memory_file = f'{MEMORY_DIR}/{today}.md'
        
        entry = f"""

## 📞 ElevenLabs Call — {timestamp.strftime('%I:%M %p')}
- **Duration:** {duration}s | **Messages:** {msg_count}
- **Conv ID:** {conv_id}

### Transcript
{messages}

---
"""
        
        with open(memory_file, 'a') as f:
            f.write(entry)
        
        print(f"✅ Saved: {conv_id} ({duration}s, {msg_count} msgs)")
        seen.add(conv_id)
        new_count += 1
    
    save_seen_conversations(seen)
    print(f"🔥 Done! {new_count} new transcripts saved")

if __name__ == '__main__':
    main()
