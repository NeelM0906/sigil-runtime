#!/bin/bash
# Start the Reporting Aggregator Proxy Server
# Port: 3344

cd "$(dirname "$0")"

# Kill any existing instance
pkill -f "reporting-server/main.py" 2>/dev/null

# Activate venv and start
source .venv/bin/activate
nohup python main.py > /tmp/reporting-server.log 2>&1 &

echo "Reporting Server started on port 3344"
echo "Logs: /tmp/reporting-server.log"
echo ""
echo "Endpoints:"
echo "  GET /health           - Health check"
echo "  GET /report/headline  - Bi-hourly summary"
echo "  GET /report/detailed  - Full daily report"
echo "  GET /report/best-calls - Top calls for Sean"
