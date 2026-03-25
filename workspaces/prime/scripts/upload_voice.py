import requests

filepath = '/Users/studio2/Projects/sigil-runtime/workspaces/prime/sai_voice_message.mp3'

# Upload to file.io (temporary file hosting, 1 download)
with open(filepath, 'rb') as f:
    r = requests.post('https://file.io', files={'file': ('sai_voice_message.mp3', f, 'audio/mpeg')})

if r.status_code == 200:
    data = r.json()
    print(f"Link: {data.get('link', 'no link')}")
    print(f"Expires: {data.get('expires', 'unknown')}")
else:
    print(f"Error: {r.status_code} {r.text[:300]}")
