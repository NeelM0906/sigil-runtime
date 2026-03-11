#!/bin/bash
#
# 🏛️ Colosseum Daemon Setup Script
# Sets up the continuous tournament daemon for macOS (launchctl) or Linux (systemctl)
#
# Usage:
#   ./setup_daemon.sh install   # Install as system service
#   ./setup_daemon.sh uninstall # Remove system service
#   ./setup_daemon.sh start     # Start the service
#   ./setup_daemon.sh stop      # Stop the service
#   ./setup_daemon.sh status    # Check status
#   ./setup_daemon.sh logs      # Tail logs
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_PATH="$SCRIPT_DIR/colosseum_daemon.py"
LOG_DIR="$SCRIPT_DIR/logs"
SERVICE_NAME="com.colosseum.daemon"
PLIST_PATH="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"
SYSTEMD_PATH="/etc/systemd/system/colosseum-daemon.service"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║  🏛️  COLOSSEUM DAEMON SETUP               ║"
    echo "║     Continuous Tournament Runner          ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 not found${NC}"
        exit 1
    fi
    
    # Check required packages
    if ! python3 -c "from colosseum.tournament import TournamentConfig" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Installing dependencies...${NC}"
        pip3 install -r "$SCRIPT_DIR/requirements.txt"
    fi
    echo -e "${GREEN}✅ Python environment ready${NC}"
}

create_log_dir() {
    mkdir -p "$LOG_DIR"
    echo -e "${GREEN}✅ Log directory: $LOG_DIR${NC}"
}

is_macos() {
    [[ "$(uname)" == "Darwin" ]]
}

# ============================================================================
# macOS (launchctl)
# ============================================================================

install_macos() {
    echo -e "${BLUE}📦 Installing macOS Launch Agent...${NC}"
    
    mkdir -p "$HOME/Library/LaunchAgents"
    
    # Create plist
    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${SERVICE_NAME}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${DAEMON_PATH}</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/launchd_stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/launchd_stderr.log</string>
    
    <key>ProcessType</key>
    <string>Background</string>
    
    <key>ThrottleInterval</key>
    <integer>60</integer>
</dict>
</plist>
EOF

    echo -e "${GREEN}✅ Launch Agent installed: $PLIST_PATH${NC}"
}

uninstall_macos() {
    echo -e "${BLUE}🗑️  Uninstalling macOS Launch Agent...${NC}"
    
    if launchctl list | grep -q "$SERVICE_NAME"; then
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
    fi
    
    if [[ -f "$PLIST_PATH" ]]; then
        rm "$PLIST_PATH"
        echo -e "${GREEN}✅ Launch Agent removed${NC}"
    else
        echo -e "${YELLOW}⚠️  Launch Agent not found${NC}"
    fi
}

start_macos() {
    if ! [[ -f "$PLIST_PATH" ]]; then
        echo -e "${RED}❌ Launch Agent not installed. Run: $0 install${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}▶️  Starting daemon...${NC}"
    launchctl load "$PLIST_PATH"
    launchctl start "$SERVICE_NAME"
    sleep 2
    
    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo -e "${GREEN}✅ Daemon started${NC}"
    else
        echo -e "${RED}❌ Failed to start daemon${NC}"
        exit 1
    fi
}

stop_macos() {
    echo -e "${BLUE}⏹️  Stopping daemon...${NC}"
    
    if launchctl list | grep -q "$SERVICE_NAME"; then
        launchctl stop "$SERVICE_NAME" 2>/dev/null || true
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        echo -e "${GREEN}✅ Daemon stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Daemon not running${NC}"
    fi
}

status_macos() {
    echo -e "${BLUE}📊 Daemon Status:${NC}"
    echo ""
    
    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo -e "  Service: ${GREEN}Loaded${NC}"
        PID=$(launchctl list | grep "$SERVICE_NAME" | awk '{print $1}')
        if [[ "$PID" != "-" && "$PID" != "" ]]; then
            echo -e "  Status:  ${GREEN}Running (PID: $PID)${NC}"
        else
            echo -e "  Status:  ${YELLOW}Stopped${NC}"
        fi
    else
        echo -e "  Service: ${YELLOW}Not loaded${NC}"
    fi
    
    echo ""
    python3 "$DAEMON_PATH" --status
}

# ============================================================================
# Linux (systemctl)
# ============================================================================

install_linux() {
    echo -e "${BLUE}📦 Installing systemd service...${NC}"
    
    sudo tee "$SYSTEMD_PATH" > /dev/null << EOF
[Unit]
Description=Colosseum Daemon - Continuous Tournament Runner
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $DAEMON_PATH
Restart=on-failure
RestartSec=60

StandardOutput=append:${LOG_DIR}/systemd_stdout.log
StandardError=append:${LOG_DIR}/systemd_stderr.log

Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    echo -e "${GREEN}✅ Systemd service installed: $SYSTEMD_PATH${NC}"
}

uninstall_linux() {
    echo -e "${BLUE}🗑️  Uninstalling systemd service...${NC}"
    
    if [[ -f "$SYSTEMD_PATH" ]]; then
        sudo systemctl stop colosseum-daemon 2>/dev/null || true
        sudo systemctl disable colosseum-daemon 2>/dev/null || true
        sudo rm "$SYSTEMD_PATH"
        sudo systemctl daemon-reload
        echo -e "${GREEN}✅ Service removed${NC}"
    else
        echo -e "${YELLOW}⚠️  Service not found${NC}"
    fi
}

start_linux() {
    echo -e "${BLUE}▶️  Starting daemon...${NC}"
    sudo systemctl start colosseum-daemon
    sudo systemctl enable colosseum-daemon
    echo -e "${GREEN}✅ Daemon started and enabled${NC}"
}

stop_linux() {
    echo -e "${BLUE}⏹️  Stopping daemon...${NC}"
    sudo systemctl stop colosseum-daemon
    echo -e "${GREEN}✅ Daemon stopped${NC}"
}

status_linux() {
    echo -e "${BLUE}📊 Daemon Status:${NC}"
    echo ""
    sudo systemctl status colosseum-daemon --no-pager
    echo ""
    python3 "$DAEMON_PATH" --status
}

# ============================================================================
# Main
# ============================================================================

print_banner
check_python
create_log_dir

case "${1:-}" in
    install)
        if is_macos; then
            install_macos
        else
            install_linux
        fi
        echo ""
        echo -e "${GREEN}Installation complete!${NC}"
        echo "  Start:  $0 start"
        echo "  Stop:   $0 stop"
        echo "  Status: $0 status"
        echo "  Logs:   $0 logs"
        ;;
    uninstall)
        if is_macos; then
            uninstall_macos
        else
            uninstall_linux
        fi
        ;;
    start)
        if is_macos; then
            start_macos
        else
            start_linux
        fi
        ;;
    stop)
        if is_macos; then
            stop_macos
        else
            stop_linux
        fi
        ;;
    status)
        if is_macos; then
            status_macos
        else
            status_linux
        fi
        ;;
    logs)
        echo -e "${BLUE}📜 Tailing daemon logs...${NC}"
        echo "(Press Ctrl+C to exit)"
        echo ""
        tail -f "$LOG_DIR/colosseum_daemon.log"
        ;;
    run)
        # Run in foreground (useful for debugging)
        echo -e "${BLUE}▶️  Running daemon in foreground...${NC}"
        python3 "$DAEMON_PATH"
        ;;
    *)
        echo "Usage: $0 {install|uninstall|start|stop|status|logs|run}"
        echo ""
        echo "Commands:"
        echo "  install   - Install as system service (launchctl/systemctl)"
        echo "  uninstall - Remove system service"
        echo "  start     - Start the daemon"
        echo "  stop      - Stop the daemon"
        echo "  status    - Show daemon status"
        echo "  logs      - Tail daemon logs"
        echo "  run       - Run in foreground (debug mode)"
        exit 1
        ;;
esac
