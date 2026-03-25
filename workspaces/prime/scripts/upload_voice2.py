import requests

filepath = '/Users/studio2/Projects/sigil-runtime/workspaces/prime/sai_voice_message.mp3'

# Try 0x0.st
with open(filepath, 'rb') as f:
    r = requests.post('https://0x0.st', files={'file': f})

print(f"Status: {r.status_code}")
print(f"Response: {r.text.strip()}")
