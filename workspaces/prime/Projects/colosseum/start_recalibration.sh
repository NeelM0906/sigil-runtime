#!/bin/bash
# Start the Recalibration Daemon
# Zone Action #42 - 24/7 Continuous Recalibration

cd "$(dirname "$0")"

# Check if already running
if [ -f recalibration_daemon.pid ]; then
    PID=$(cat recalibration_daemon.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Recalibration daemon already running (PID: $PID)"
        exit 0
    fi
fi

# Activate venv and start
source venv/bin/activate
nohup python recalibration_daemon.py --daemon > logs/recalibration_startup.log 2>&1 &

sleep 2

if [ -f recalibration_daemon.pid ]; then
    PID=$(cat recalibration_daemon.pid)
    echo "✅ Recalibration daemon started (PID: $PID)"
else
    echo "❌ Failed to start daemon - check logs/recalibration_startup.log"
    exit 1
fi
