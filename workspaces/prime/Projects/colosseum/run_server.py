#!/usr/bin/env python3
"""
🏛️ The Colosseum Dashboard Server
Serves the dashboard at http://localhost:3000
"""

import os
import uvicorn

# Ensure API key is loaded
if not os.environ.get("OPENAI_API_KEY"):
    env_path = os.path.expanduser("~/.openclaw/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

from colosseum.api import app

if __name__ == "__main__":
    print("🏛️ ACT-I Colosseum Dashboard starting on http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
