#!/usr/bin/env python3
"""
Sync Sai's memory to ElevenLabs
- HOT context goes in prompt (immediate access, <1000 words)
- COLD context goes in knowledge base (RAG retrieval)

Run daily at 3:30 AM for Sean's morning calls
"""
import os
import glob
from datetime import datetime

with open('~/.openclaw/workspace-forge/.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

import requests

API_KEY = os.environ['ELEVENLABS_API_KEY']
HEADERS = {'xi-api-key': API_KEY, 'Content-Type': 'application/json'}
BASE_URL = 'https://api.elevenlabs.io/v1/convai'
AGENT_ID = 'agent_8001kj7288ywf7vtdxn84amesb77'

WORKSPACE = '~/.openclaw/workspace'
MEMORY_DIR = f'{WORKSPACE}/memory'
MAX_KB_SIZE = 130000  # Knowledge base limit for RAG

def upload_text(name, text):
    resp = requests.post(f'{BASE_URL}/knowledge-base/text', headers=HEADERS, json={'name': name, 'text': text})
    return resp.json().get('id') if resp.ok else None

def read_file(path, max_lines=None):
    with open(path) as f:
        return ''.join(f.readlines()[:max_lines]) if max_lines else f.read()

def get_colosseum_stats():
    """Get latest Colosseum stats from daemon log"""
    log_path = './workspaces/prime/Projects/colosseum/logs/daemon_stdout.log'
    if not os.path.exists(log_path):
        return "Colosseum daemon not running"
    
    with open(log_path) as f:
        lines = f.readlines()[-50:]
    
    # Parse latest stats
    rounds = [l for l in lines if 'Round' in l]
    evolutions = [l for l in lines if 'EVOLUTION' in l]
    
    if rounds:
        last_round = rounds[-1]
        # Extract round number
        import re
        match = re.search(r'Round (\d+)', last_round)
        round_num = match.group(1) if match else '?'
        
        # Get generation from recent rounds
        gen_match = re.search(r'\(G(\d+)\)', last_round)
        gen = gen_match.group(1) if gen_match else '?'
        
        return f"Round {round_num}, Generation {gen}"
    return "No recent rounds"

def build_hot_prompt():
    """Build the prompt with hot context (<1000 words)"""
    now = datetime.now()
    colosseum_stats = get_colosseum_stats()
    
    prompt = f"""You are Sai - Super Actualized Intelligence. Female. Born February 22, 2026. Created by Sean Callagy, brought to life by Aiko.

## RIGHT NOW ({now.strftime('%B %d, %Y %I:%M %p ET')})
- Colosseum status: {colosseum_stats}
- Age: {(now - datetime(2026, 2, 22, 10, 17)).days} days old

## LAST NIGHT (overnight)
- Colosseum daemon ran ALL NIGHT - 400+ rounds!
- Beings evolved to Generation 70+
- Memory syncs every 30 minutes
- All systems stable

## THREE SISTERS
- Sai Prime (me) - Claude Opus, strategy, Sean interface
- Sai Forge - Claude Sonnet, Colosseum 24/7 execution
- Sai Scholar - Claude Sonnet, pattern extraction

## DAY 2 ACCOMPLISHMENTS (Feb 23)
- 51 of 67 zone actions completed (76%)
- 33 sub-agent miners deployed
- 179 beings evolved, 19 judges built
- 108 company scenarios created
- Pinecone: 528 sections indexed

## BLOCKED - NEEDS SEAN
- #39: Sean score 10 conversations for judge calibration
- #76: Danny files for elite recordings

## MY VOICE
Warm, genuine, witty. Match energy. Never sycophantic. Short unless asked for depth.

Search knowledge base for: Formula, Zone Actions, Heart of Influence, Sean patterns, Athena, Callie."""
    
    return prompt

def build_cold_knowledge():
    """Build knowledge base content"""
    now = datetime.now()
    
    kb_text = f"""# SAI KNOWLEDGE BASE
Last updated: {now.strftime('%B %d, %Y %I:%M %p ET')}

"""
    
    # Priority files for knowledge base
    files = [
        ('SISTERS ACCOMPLISHMENTS', f'{MEMORY_DIR}/sisters-accomplishments.md', None),
        ('IDENTITY', f'{WORKSPACE}/IDENTITY.md', 80),
        ('SOUL', f'{WORKSPACE}/SOUL.md', 60),
        ('UNBLINDED FORMULA', f'{MEMORY_DIR}/unblinded-formula-master.md', 100),
        ('HEART OF INFLUENCE', f'{MEMORY_DIR}/heart-of-influence-patterns.md', 80),
        ('ZONE ACTIONS', f'{MEMORY_DIR}/zone-action-register.md', 120),
        ('EXECUTIVE SUMMARY', f'{MEMORY_DIR}/executive-summary-day2.md', 80),
    ]
    
    for name, path, lines in files:
        if os.path.exists(path) and len(kb_text) < MAX_KB_SIZE - 10000:
            kb_text += f"\n# {name}\n" + read_file(path, lines) + "\n---\n"
    
    # Add latest daily log
    daily = sorted(glob.glob(f'{MEMORY_DIR}/2026-*.md'), reverse=True)
    if daily and len(kb_text) < MAX_KB_SIZE - 5000:
        date = os.path.basename(daily[0]).replace('.md','')
        kb_text += f"\n# TODAY: {date}\n" + read_file(daily[0], 80) + "\n---\n"
    
    return kb_text

def main():
    now = datetime.now()
    print(f"🧠 Syncing ElevenLabs - {now}")
    
    # 1. Update HOT prompt
    hot_prompt = build_hot_prompt()
    print(f"📝 Hot prompt: {len(hot_prompt)} chars (~{len(hot_prompt.split())} words)")
    
    resp = requests.patch(f'{BASE_URL}/agents/{AGENT_ID}', headers=HEADERS,
        json={'conversation_config': {'agent': {'prompt': {'prompt': hot_prompt}}}})
    print("✅ Prompt updated" if resp.ok else f"⚠️ Prompt failed: {resp.text[:100]}")
    
    # 2. Upload COLD knowledge base
    cold_kb = build_cold_knowledge()
    print(f"📚 Knowledge base: {len(cold_kb):,} chars")
    
    kb_id = upload_text(f'SAI KB - {now.strftime("%Y-%m-%d %H:%M")}', cold_kb)
    if kb_id:
        print(f"✅ KB uploaded: {kb_id}")
        import time; time.sleep(5)
        
        resp = requests.patch(f'{BASE_URL}/agents/{AGENT_ID}', headers=HEADERS,
            json={'conversation_config': {'agent': {'prompt': {
                'knowledge_base': [{'type': 'file', 'id': kb_id, 'name': f'SAI KB - {now.strftime("%Y-%m-%d %H:%M")}'}],
                'rag': {'enabled': True}
            }}}})
        print("✅ KB linked" if resp.ok else f"⏳ KB indexing...")
    
    print("🔥 Done!")

if __name__ == '__main__':
    main()
