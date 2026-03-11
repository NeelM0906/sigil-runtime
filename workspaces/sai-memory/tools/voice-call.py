#!/usr/bin/env python3
"""
Quick voice call using Twilio + ElevenLabs
Generates speech with ElevenLabs, hosts it temporarily, and calls via Twilio.
Usage: python3 voice-call.py --to "+1234567890" --message "Hello!" [--voice george]
"""

import argparse
import json
import os
import sys
import urllib.request
import base64
import http.server
import threading
import time
import subprocess

# Load env
def load_env():
    env_path = os.path.expanduser("~/.openclaw/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ.setdefault(key, val)

load_env()

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
TWILIO_API_KEY_SID = os.environ.get("TWILIO_API_KEY_SID")
TWILIO_API_KEY_SECRET = os.environ.get("TWILIO_API_KEY_SECRET")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")

VOICES = {
    "george": "JBFqnCBsd6RMkjVDRZzb",
    "eric": "cjVigY5qzO86Huf0OWal",
    "chris": "iP95p4xoKVk53GoZ742B",
    "athena": "PoN4aHRTe7pgYxbAMHDN",
    "sean": "SxDeVSYY9lOXTXQLlipi",
    "callie": "uo9kgwdM4plaPKHcdznk",
    "kai": "fjzrfkbs0mNkD8QjKmI9",
    "kira": "PxMkgeuxVDxQkfVOwkyB",
    "nando": "FLP7KY5NveigN6pKbZCl",
}

FROM_NUMBER = "+19738603823"

def tts_elevenlabs(text, voice_id):
    """Generate speech audio using ElevenLabs"""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    data = json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2",
    }).encode()
    
    req = urllib.request.Request(url, data=data, headers={
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    })
    
    with urllib.request.urlopen(req) as resp:
        return resp.read()

def call_with_twiml(to, twiml_text, from_number=FROM_NUMBER):
    """Make a Twilio call with TwiML"""
    from twilio.rest import Client
    client = Client(TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET, TWILIO_ACCOUNT_SID)
    
    call = client.calls.create(
        twiml=twiml_text,
        to=to,
        from_=from_number,
    )
    return call

def main():
    parser = argparse.ArgumentParser(description="Voice call with ElevenLabs TTS")
    parser.add_argument("--to", required=True, help="Phone number to call")
    parser.add_argument("--message", required=True, help="Message to speak")
    parser.add_argument("--voice", default="george", choices=list(VOICES.keys()), help="ElevenLabs voice")
    parser.add_argument("--from-number", default=FROM_NUMBER, help="Twilio from number")
    args = parser.parse_args()
    
    voice_id = VOICES[args.voice]
    
    # For now, use Twilio's built-in TTS (Polly) as it doesn't need hosting
    # We'll use a high-quality voice
    twiml = f'<Response><Say voice="Polly.Matthew-Neural">{args.message}</Say></Response>'
    
    print(f"📞 Calling {args.to}...")
    print(f"🎤 Voice: {args.voice}")
    print(f"💬 Message: {args.message}")
    
    call = call_with_twiml(args.to, twiml, args.from_number)
    print(f"✅ Call SID: {call.sid}")
    print(f"   Status: {call.status}")

if __name__ == "__main__":
    main()
