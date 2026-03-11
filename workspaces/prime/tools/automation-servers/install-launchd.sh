#!/bin/bash
# Install launchd plist for auto-start on boot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.openclaw.automation-servers.plist"
PLIST_SRC="${SCRIPT_DIR}/${PLIST_NAME}"
PLIST_DST="${HOME}/Library/LaunchAgents/${PLIST_NAME}"

echo "Installing automation servers launchd agent..."

# Create LaunchAgents dir if needed
mkdir -p "${HOME}/Library/LaunchAgents"

# Unload if already loaded
launchctl unload "$PLIST_DST" 2>/dev/null

# Copy plist
cp "$PLIST_SRC" "$PLIST_DST"
echo "✓ Copied plist to ${PLIST_DST}"

# Load the agent
launchctl load "$PLIST_DST"
echo "✓ Loaded launchd agent"

echo ""
echo "Automation servers will now start automatically on login."
echo ""
echo "Commands:"
echo "  Start now:  launchctl start ${PLIST_NAME%.plist}"
echo "  Stop:       launchctl stop ${PLIST_NAME%.plist}"
echo "  Uninstall:  launchctl unload ${PLIST_DST} && rm ${PLIST_DST}"
