import os
import json
import urllib.request
import time

def call_openrouter(sys, user):
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST",
        data=json.dumps({
            "model": "google/gemini-2.5-flash",
            "messages": [
                {"role": "system", "content": sys},
                {"role": "user", "content": user}
            ],
            "temperature": 0.3
        }).encode("utf-8")
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"]

namespaces = [
    "d7-revops", "d6-delivery", "data-analytics-and-business-intelligence",
    "crm-and-pipeline-management", "data-engineering-and-etl-pipelines",
    "project-management-and-operations", "api-development-and-system-integration",
    "sales-and-revenue-operations", "financial-operations-and-accounting",
    "ecosystem-partnerships-and-strategic-mergers"
]

prompt_sys = """You are SAI Memory, crafting advanced judge-ready knowledge vectors.
Generate a comprehensive mastery profile for the given domain.
You MUST output EXACTLY 8 sections, preceded by these exact strings (in ALL CAPS):
DOMAIN DEFINITION
CORE COMPETENCIES
TECHNICAL KNOWLEDGE
MASTERY INDICATORS
COMMON FAILURE PATTERNS
LEARNING PATH
SEAN CALLAGY FORMULA INTEGRATION
REAL-WORLD SCENARIOS

Make the content dense, highly specific, and formatted gracefully. Do not use markdown headers before the precise string match labels."""

for ns in namespaces:
    print(f"Generating for {ns}...")
    try:
        j_data = {
            "title": ns,
            "mastery_profile": call_openrouter(prompt_sys, f"Generate the 8-section mastery profile for: {ns}")
        }
        with open(f"~/.openclaw/workspace-memory/memory/{ns}-mastery.json", "w") as f:
            json.dump(j_data, f, indent=2)
        print(f"-> Saved: {ns}-mastery.json")
    except Exception as e:
        print(f"-> Failed {ns}: {e}")
    time.sleep(2)
