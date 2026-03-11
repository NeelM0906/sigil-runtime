#!/bin/bash
# Quick call script
# Usage: ./call.sh +1234567890 [voice]
# Example: ./call.sh +13475222756 george

TO=${1:?Usage: ./call.sh +1234567890 [voice]}
VOICE=${2:-george}

# Change voice if specified
if [ "$VOICE" != "george" ]; then
    curl -s -X POST http://localhost:3334/voice/select -H "Content-Type: application/json" -d "{\"voice\":\"$VOICE\"}" | python3 -m json.tool
fi

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['tunnels'][0]['public_url'])" 2>/dev/null)

if [ -z "$NGROK_URL" ]; then
    echo "❌ ngrok not running!"
    exit 1
fi

echo "📞 Calling $TO with voice: $VOICE"
echo "🌐 Webhook: $NGROK_URL/voice/webhook"

# Load env
source <(grep -v '^#' ~/.openclaw/.env | sed 's/^/export /')

python3 -c "
from twilio.rest import Client
import os
client = Client(os.environ['TWILIO_API_KEY_SID'], os.environ['TWILIO_API_KEY_SECRET'], os.environ['TWILIO_ACCOUNT_SID'])
call = client.calls.create(url='$NGROK_URL/voice/webhook', to='$TO', from_='+19738603823')
print(f'✅ Call SID: {call.sid}')
print(f'   Status: {call.status}')
"
