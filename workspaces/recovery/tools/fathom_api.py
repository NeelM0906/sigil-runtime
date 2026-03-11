#!/usr/bin/env python3
"""
Fathom AI Meeting API Tool
Fetch meeting recordings, transcripts, and summaries from Fathom.

Usage:
    python3 fathom_api.py list                    # List recent meetings
    python3 fathom_api.py list --limit 20         # List more meetings
    python3 fathom_api.py get <recording_id>      # Get meeting with transcript
    python3 fathom_api.py transcript <recording_id>  # Get just transcript
    python3 fathom_api.py search "Sean"           # Find meetings with person
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime

# Load API key from environment or .env file
def load_api_key():
    key = os.environ.get('FATHOM_API_KEY')
    if not key:
        env_path = os.path.expanduser('~/.openclaw/.env')
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith('FATHOM_API_KEY='):
                        key = line.strip().split('=', 1)[1]
                        break
    return key

API_KEY = load_api_key()
BASE_URL = "https://api.fathom.ai/external/v1"

def get_headers():
    return {"X-Api-Key": API_KEY}

def list_meetings(limit=10, include_transcript=False, cursor=None):
    """List recent meetings"""
    params = {"limit": limit}
    if include_transcript:
        params["include_transcript"] = "true"
    if cursor:
        params["cursor"] = cursor
    
    response = requests.get(f"{BASE_URL}/meetings", headers=get_headers(), params=params)
    return response.json()

def get_meeting(recording_id, include_transcript=True):
    """Get a specific meeting by recording ID"""
    params = {"include_transcript": "true"} if include_transcript else {}
    response = requests.get(f"{BASE_URL}/recordings/{recording_id}", headers=get_headers(), params=params)
    return response.json()

def get_transcript(recording_id):
    """Get just the transcript for a recording"""
    response = requests.get(f"{BASE_URL}/recordings/{recording_id}/transcript", headers=get_headers())
    return response.json()

def search_meetings(query, limit=20):
    """Search meetings by attendee email/name"""
    meetings = list_meetings(limit=limit)
    results = []
    
    for meeting in meetings.get('items', []):
        # Search in title
        if query.lower() in meeting.get('title', '').lower():
            results.append(meeting)
            continue
        # Search in attendees
        for invitee in meeting.get('calendar_invitees', []):
            if query.lower() in invitee.get('name', '').lower() or query.lower() in invitee.get('email', '').lower():
                results.append(meeting)
                break
    
    return results

def format_meeting(meeting, verbose=False):
    """Format a meeting for display"""
    output = []
    output.append(f"📹 {meeting.get('title', 'Untitled')}")
    output.append(f"   ID: {meeting.get('recording_id')}")
    output.append(f"   Date: {meeting.get('created_at', 'Unknown')[:10]}")
    output.append(f"   URL: {meeting.get('url')}")
    output.append(f"   Share: {meeting.get('share_url')}")
    
    if verbose:
        invitees = meeting.get('calendar_invitees', [])
        if invitees:
            output.append(f"   Attendees ({len(invitees)}):")
            for inv in invitees[:10]:  # First 10
                output.append(f"      - {inv.get('name', inv.get('email'))}")
            if len(invitees) > 10:
                output.append(f"      ... and {len(invitees) - 10} more")
    
    return '\n'.join(output)

def main():
    parser = argparse.ArgumentParser(description='Fathom AI Meeting API Tool')
    parser.add_argument('action', choices=['list', 'get', 'transcript', 'search'], help='Action to perform')
    parser.add_argument('query', nargs='?', help='Recording ID or search query')
    parser.add_argument('--limit', type=int, default=10, help='Number of results')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show more details')
    parser.add_argument('--json', action='store_true', help='Output raw JSON')
    
    args = parser.parse_args()
    
    if not API_KEY:
        print("Error: FATHOM_API_KEY not found in environment or ~/.openclaw/.env")
        sys.exit(1)
    
    if args.action == 'list':
        result = list_meetings(limit=args.limit)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n📅 Recent Fathom Meetings ({len(result.get('items', []))} shown)\n")
            for meeting in result.get('items', []):
                print(format_meeting(meeting, verbose=args.verbose))
                print()
    
    elif args.action == 'get':
        if not args.query:
            print("Error: Recording ID required")
            sys.exit(1)
        result = get_meeting(args.query)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_meeting(result, verbose=True))
            if result.get('transcript'):
                print("\n📝 Transcript:")
                for entry in result['transcript'][:20]:
                    print(f"   [{entry.get('timestamp')}] {entry.get('speaker', {}).get('display_name', 'Unknown')}: {entry.get('text')}")
    
    elif args.action == 'transcript':
        if not args.query:
            print("Error: Recording ID required")
            sys.exit(1)
        result = get_transcript(args.query)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for entry in result:
                print(f"[{entry.get('timestamp')}] {entry.get('speaker', {}).get('display_name', 'Unknown')}: {entry.get('text')}")
    
    elif args.action == 'search':
        if not args.query:
            print("Error: Search query required")
            sys.exit(1)
        results = search_meetings(args.query, limit=args.limit)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n🔍 Meetings matching '{args.query}' ({len(results)} found)\n")
            for meeting in results:
                print(format_meeting(meeting, verbose=args.verbose))
                print()

if __name__ == '__main__':
    main()
