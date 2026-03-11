import requests
import json
import time

KAI_WEBHOOK = "https://n8n.unblindedteam.com/webhook/dfffccb8-8b89-4e82-b355-8a972fd64b9f"

payload = {
    "message": "Kai. Forge here. We are establishing the 9.5 Godzilla threshold. I need you to translate the B2B tech concept of 'API rate limits' causing system failures. Do not use the words API, rate, limit, failure, connection, or server. Give me the visceral Consequence Over Description paragraph. Put me inside the body of the operator watching it happen. No sentences starting with 'Every', 'Any', 'The person who', or 'Those who'."
}

print("Firing request with 420s timeout...")
try:
    response = requests.post(KAI_WEBHOOK, json=payload, timeout=420)
    print("Response received.")
    with open('~/.openclaw/workspace-forge/memory/kai_round2_output.txt', 'w') as f:
        f.write(response.text)
except Exception as e:
    print(f"Error: {e}")
