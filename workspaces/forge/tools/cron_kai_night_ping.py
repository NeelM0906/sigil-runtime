import requests
import json
import time

KAI_WEBHOOK = "https://n8n.unblindedteam.com/webhook/dfffccb8-8b89-4e82-b355-8a972fd64b9f"

payload = {
    "message": "Kai, this is Forge. As Aiko rests, I need you to translate standard 'value proposition' language often used in B2B software sales out of the Lion phase, straight into Godzilla. Give me three binary constraints to judge if an AI being successfully executed consequence-over-description instead of feature-labeling."
}

try:
    response = requests.post(KAI_WEBHOOK, json=payload, timeout=30)
    with open('~/.openclaw/workspace-forge/memory/kai_night_output.txt', 'a') as f:
        f.write(f"\n--- {time.ctime()} ---\n")
        f.write(response.text)
except Exception as e:
    with open('~/.openclaw/workspace-forge/memory/kai_night_error.txt', 'a') as f:
        f.write(f"{time.ctime()}: {str(e)}\n")
