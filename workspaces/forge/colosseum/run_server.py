#!/usr/bin/env python3
"""
🏛️ The Colosseum Dashboard Server
Serves the dashboard at http://localhost:3000
"""

import os
import uvicorn
from pathlib import Path

from bomba_sr.openclaw.script_support import load_portable_env

load_portable_env(Path(__file__))

from colosseum.api import app

if __name__ == "__main__":
    print("🏛️ ACT-I Colosseum Dashboard starting on http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level="info")
