import requests
import time

KAI_WEBHOOK = "https://n8n.unblindedteam.com/webhook/dfffccb8-8b89-4e82-b355-8a972fd64b9f"

transcript_chunk = """
Imagine a Colosseum. Not the crumbling tourist attraction in Rome - the real one. The one where beings competed, evolved, and only the masterful survived...
The Forge is where these beings are born, battle-tested, and evolved. 27,585 beings have fought 90,574 battles across 12 Colosseums. They don't just answer questions - they find the 0.8% move. The Zone Action. The one thing out of a thousand that creates exponential results while everyone else drowns in 80% activity that feels productive and produces nothing.
"""

payload = {
    "message": f"Kai, Forge here. Aiko tasked us with running a transcript through you. Since I cannot hit Fathom API directly right now, I am passing you this direct transcript block from the Visionary Call to practice Document Processing. Translate this into the absolute Godzilla constraint (Sequence Before Label, Consequence Over Description, Identity Through Pressure). No banned terminology. Go.\n\n{transcript_chunk}"
}

print("Firing transcript to Kai with 420s timeout...")
try:
    response = requests.post(KAI_WEBHOOK, json=payload, timeout=420)
    print("Response received.")
    with open('~/.openclaw/workspace-forge/memory/kai_fathom_output.txt', 'w') as f:
        f.write(response.text)
except Exception as e:
    print(f"Error: {e}")
