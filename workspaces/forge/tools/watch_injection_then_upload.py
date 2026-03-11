#!/usr/bin/env python3
"""
Watches position injection log. When 2696/2696 is reached (or process exits),
automatically triggers Batch 1 cluster judge upload.
"""

import subprocess
import time
import re
import os
from pathlib import Path

LOG = Path("~/.openclaw/workspace-forge/reports/position-inject-full-run.log")
UPLOAD_SCRIPT = Path("~/.openclaw/workspace-forge/tools/upload_cluster_judges_batch1.py")
PYTHON = Path("~/.openclaw/workspace-forge/tools/.venv/bin/python3")
TARGET = 2696

def get_current_count():
    try:
        text = LOG.read_text()
        # Find last [NNNN/2696] pattern
        matches = re.findall(r'\[(\d+)/2696\]', text)
        if matches:
            return int(matches[-1])
    except:
        pass
    return 0

def injection_process_alive():
    result = subprocess.run(
        ["pgrep", "-f", "build_position_knowledge.py"],
        capture_output=True
    )
    return result.returncode == 0

print("⚔️  Watching injection log... target: 2696/2696")
print(f"   Log: {LOG}")
print()

while True:
    count = get_current_count()
    alive = injection_process_alive()

    if count >= TARGET:
        print(f"✅ Injection complete! {count}/{TARGET}")
        break
    elif not alive:
        print(f"⚠️  Injection process exited at {count}/{TARGET} — triggering upload anyway")
        break
    else:
        print(f"   [{count}/{TARGET}] running...", end='\r')
        time.sleep(30)

print()
print("🚀 Triggering Batch 1 cluster judge upload to acti-judges...")
print()

env = os.environ.copy()
result = subprocess.run(
    [str(PYTHON), str(UPLOAD_SCRIPT)],
    env=env
)

if result.returncode == 0:
    print("\n✅ Batch 1 upload triggered successfully.")
else:
    print(f"\n❌ Upload script exited with code {result.returncode}")
