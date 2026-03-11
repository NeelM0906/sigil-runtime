import requests
import json

KAI_WEBHOOK = "https://n8n.unblindedteam.com/webhook/50adb5c3-8020-42bf-bb8b-7acf7f9222b9"

payload = {
    "chatInput": "From the Forge: Define the exact ZACS-04 12-point approved Zone Action logic to 'launch the NJ pilot split-test' against the 16,991 PI attorneys using the Compare & Contrast weapon from the Cert Call Section 5. I need absolute binary gates. No fluff. What is the execution gate?"
}

print("Firing request to Stratum with 420s timeout...")
try:
    response = requests.post(KAI_WEBHOOK, json=payload, timeout=420)
    print("Response received.")
    with open('~/.openclaw/workspace-forge/memory/zacs_nj_pilot.txt', 'w') as f:
        f.write(response.text)
except Exception as e:
    print(f"Error: {e}")
