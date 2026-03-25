import subprocess

filepath = '/Users/studio2/Projects/sigil-runtime/workspaces/prime/sai_voice_message.mp3'

# Use curl with proper UA to transfer.sh
result = subprocess.run([
    'curl', '--upload-file', filepath,
    'https://transfer.sh/sai_voice_message.mp3',
    '-H', 'Max-Days: 7'
], capture_output=True, text=True, timeout=30)

print(f"stdout: {result.stdout.strip()}")
print(f"stderr: {result.stderr.strip()}")
print(f"code: {result.returncode}")
