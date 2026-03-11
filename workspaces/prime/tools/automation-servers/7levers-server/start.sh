#!/bin/bash
# 7 Levers Metrics Proxy Server - Startup Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for venv
if [ ! -d ".venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
if [ ! -f ".venv/.deps_installed" ]; then
    echo "📦 Installing dependencies..."
    pip install -q -r requirements.txt
    touch .venv/.deps_installed
fi

# Start server
echo "🚀 Starting 7 Levers Metrics Proxy on port 3340..."
exec python3 server.py
