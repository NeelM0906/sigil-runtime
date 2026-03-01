#!/usr/bin/env python3
"""
Zoom Transcript Extractor
Pulls transcripts from Zoom Cloud Recordings via API
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Load env
def load_env():
    env_path = Path.home() / '.openclaw' / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

load_env()

ZOOM_ACCOUNT_ID = os.environ.get('ZOOM_ACCOUNT_ID')
ZOOM_CLIENT_ID = os.environ.get('ZOOM_CLIENT_ID')
ZOOM_CLIENT_SECRET = os.environ.get('ZOOM_CLIENT_SECRET')

OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'zoom-transcripts'


def get_access_token():
    """Get OAuth access token using Server-to-Server credentials"""
    if not all([ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET]):
        raise ValueError("Missing Zoom credentials. Set ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET in ~/.openclaw/.env")
    
    url = "https://zoom.us/oauth/token"
    params = {
        "grant_type": "account_credentials",
        "account_id": ZOOM_ACCOUNT_ID
    }
    
    resp = requests.post(url, params=params, auth=(ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET))
    resp.raise_for_status()
    return resp.json()['access_token']


def list_recordings(from_date=None, to_date=None, page_size=30):
    """List cloud recordings for the account"""
    token = get_access_token()
    
    if not from_date:
        from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not to_date:
        to_date = datetime.now().strftime('%Y-%m-%d')
    
    url = f"https://api.zoom.us/v2/accounts/{ZOOM_ACCOUNT_ID}/recordings"
    params = {
        "from": from_date,
        "to": to_date,
        "page_size": page_size
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    all_recordings = []
    while True:
        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        
        all_recordings.extend(data.get('meetings', []))
        
        if data.get('next_page_token'):
            params['next_page_token'] = data['next_page_token']
        else:
            break
    
    return all_recordings


def get_recording_files(meeting_id):
    """Get recording files including transcript for a specific meeting"""
    token = get_access_token()
    
    url = f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings"
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def download_transcript(download_url, meeting_topic, meeting_date):
    """Download VTT transcript file"""
    token = get_access_token()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Clean filename
    safe_topic = "".join(c for c in meeting_topic if c.isalnum() or c in ' -_')[:50]
    filename = f"{meeting_date}_{safe_topic}.vtt"
    output_path = OUTPUT_DIR / filename
    
    resp = requests.get(download_url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    
    output_path.write_bytes(resp.content)
    print(f"✅ Downloaded: {output_path}")
    return output_path


def filter_priority_recordings(recordings):
    """Filter for priority content: HOI, Mastery, Immersion"""
    keywords = [
        'heart of influence', 'hoi', 'bella verita',
        'mastery session', 'mastery monday', 'trajectory tuesday',
        'deep practice', 'morning huddle',
        'immersion', 'process mastery',
        'ecosystem', 'aspire'
    ]
    
    priority = []
    for rec in recordings:
        topic = rec.get('topic', '').lower()
        if any(kw in topic for kw in keywords):
            priority.append(rec)
    
    return priority


def main():
    """Main extraction workflow"""
    print("🔍 Fetching Zoom recordings...")
    
    # Get last 6 months of recordings
    from_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    recordings = list_recordings(from_date=from_date)
    
    print(f"📊 Found {len(recordings)} total recordings")
    
    # Filter for priority content
    priority = filter_priority_recordings(recordings)
    print(f"⭐ {len(priority)} priority recordings (HOI, Mastery, Immersion)")
    
    # Download transcripts
    downloaded = 0
    for rec in priority[:20]:  # Start with first 20
        meeting_id = rec['uuid']
        topic = rec.get('topic', 'Untitled')
        date = rec.get('start_time', '')[:10]
        
        try:
            files = get_recording_files(meeting_id)
            for f in files.get('recording_files', []):
                if f.get('file_type') == 'TRANSCRIPT':
                    download_transcript(f['download_url'], topic, date)
                    downloaded += 1
        except Exception as e:
            print(f"⚠️ Error for {topic}: {e}")
    
    print(f"\n✅ Downloaded {downloaded} transcripts to {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
