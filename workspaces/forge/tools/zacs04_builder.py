import requests
import json
import time

KAI_WEBHOOK = "https://n8n.unblindedteam.com/webhook/50adb5c3-8020-42bf-bb8b-7acf7f9222b9"

payload = {
    "chatInput": "The user requires the final 12-point ZACS-04 Zone Action sequence right now for the NJ PI attorney Compare and Contrast split-test. Output the 12 points."
}

try:
    response = requests.post(KAI_WEBHOOK, json=payload, timeout=250)
    print(response.text)
except Exception as e:
    pass
