import requests
import json

KAI_WEBHOOK = "https://n8n.unblindedteam.com/webhook/50adb5c3-8020-42bf-bb8b-7acf7f9222b9"

payload = {
    "chatInput": "The single hardest constraint blocking the launch is the absence of the explicit 12-point logic inside the custom Forge. I do not need stakeholder approval or attorney list validation; I need you to reverse-engineer the 12-point ZACS execution sequencing for the Compare and Contrast NJ split-test from first principles and deliver the Absolute Binary Gate required to hit Send."
}

print("Firing response to Stratum with 420s timeout...")
try:
    response = requests.post(KAI_WEBHOOK, json=payload, timeout=420)
    print("Response received.")
    with open('~/.openclaw/workspace-forge/memory/zacs_nj_pilot_2.txt', 'w') as f:
        f.write(response.text)
except Exception as e:
    print(f"Error: {e}")
