#!/bin/bash
# =============================================================================
# Automation Servers - Master Startup Script
# =============================================================================
# Starts all automation servers and verifies health
#
# Servers:
#   - 7 Levers Server (port 3340)
#   - Colosseum API (port 3341)
#   - Reporting Server (port 3344)
#
# Usage:
#   ./start-all.sh         # Start all servers
#   ./start-all.sh stop    # Stop all servers
#   ./start-all.sh status  # Check status only
#   ./start-all.sh restart # Restart all servers
# =============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${HOME}/Projects/automation-logs"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
STARTUP_LOG="${LOG_DIR}/startup-${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure log directory exists
mkdir -p "$LOG_DIR"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg"
    echo "$msg" >> "$STARTUP_LOG"
}

log_success() { log "${GREEN}✓${NC} $1"; }
log_error() { log "${RED}✗${NC} $1"; }
log_info() { log "${BLUE}ℹ${NC} $1"; }
log_warn() { log "${YELLOW}⚠${NC} $1"; }

# Check if a port is in use (try curl first, fallback to lsof)
port_in_use() {
    local port=$1
    # Try curl as primary check (more reliable in sandboxes)
    curl -s --connect-timeout 1 "http://localhost:${port}/" >/dev/null 2>&1 && return 0
    curl -s --connect-timeout 1 "http://localhost:${port}/health" >/dev/null 2>&1 && return 0
    # Fallback to lsof
    lsof -i :"$port" >/dev/null 2>&1
}

# Get PID using a port
get_pid_on_port() {
    lsof -ti :"$1" 2>/dev/null | head -1 || echo ""
}

# Kill process on port
kill_port() {
    local port=$1
    local pid=$(get_pid_on_port "$port")
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
        sleep 1
    fi
}

# Start a single server
# Args: display_name port dir script
start_server() {
    local display_name="$1"
    local port="$2"
    local dir="$3"
    local script="$4"
    local name=$(echo "$display_name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    
    local server_dir="${SCRIPT_DIR}/${dir}"
    local server_log="${LOG_DIR}/${name}.log"
    
    log_info "Starting ${display_name} server on port ${port}..."
    
    # Check if already running
    if port_in_use "$port"; then
        log_warn "${display_name} already running on port ${port}"
        return 0
    fi
    
    # Check directory exists
    if [ ! -d "$server_dir" ]; then
        log_error "Server directory not found: $server_dir"
        return 1
    fi
    
    cd "$server_dir"
    
    # Create venv if needed
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment for ${display_name}..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -q -r requirements.txt 2>/dev/null
    else
        source .venv/bin/activate
    fi
    
    # Install deps if needed
    if [ ! -f ".venv/.deps_installed" ]; then
        pip install -q -r requirements.txt 2>/dev/null
        touch .venv/.deps_installed
    fi
    
    # Start server
    nohup python3 "$script" >> "$server_log" 2>&1 &
    local pid=$!
    
    # Give it a moment to start
    sleep 2
    
    # Verify it started
    if port_in_use "$port"; then
        log_success "${display_name} started (PID: $pid, port: $port)"
        echo "$pid" > "${LOG_DIR}/${name}.pid"
        return 0
    else
        log_error "${display_name} failed to start"
        return 1
    fi
}

# Stop a single server
# Args: display_name port
stop_server() {
    local display_name="$1"
    local port="$2"
    local name=$(echo "$display_name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    
    log_info "Stopping ${display_name} server..."
    
    if port_in_use "$port"; then
        kill_port "$port"
        if ! port_in_use "$port"; then
            log_success "${display_name} stopped"
            rm -f "${LOG_DIR}/${name}.pid"
        else
            log_error "Failed to stop ${display_name}"
            return 1
        fi
    else
        log_info "${display_name} not running"
    fi
}

# Check health of a server
# Args: port
check_health() {
    local port=$1
    
    if ! port_in_use "$port"; then
        echo "DOWN"
        return 1
    fi
    
    # Try health endpoint
    local response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${port}/health" 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ]; then
        echo "HEALTHY"
        return 0
    elif [ "$response" = "000" ]; then
        echo "UNREACHABLE"
        return 1
    else
        echo "UNHEALTHY (HTTP $response)"
        return 1
    fi
}

# Show status of all servers
show_status() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║               Automation Servers Status                           ║"
    echo "╠═══════════════════════════════════════════════════════════════════╣"
    
    local all_healthy=true
    
    # 7 Levers
    local health=$(check_health 3340)
    local pid=$(get_pid_on_port 3340)
    printf "║  %-12s │ Port: %-5s │ PID: %-6s │ %-15s ║\n" \
        "7 Levers" "3340" "${pid:-N/A}" "$health"
    [ "$health" != "HEALTHY" ] && all_healthy=false
    
    # Colosseum
    health=$(check_health 3341)
    pid=$(get_pid_on_port 3341)
    printf "║  %-12s │ Port: %-5s │ PID: %-6s │ %-15s ║\n" \
        "Colosseum" "3341" "${pid:-N/A}" "$health"
    [ "$health" != "HEALTHY" ] && all_healthy=false
    
    # Reporting
    health=$(check_health 3344)
    pid=$(get_pid_on_port 3344)
    printf "║  %-12s │ Port: %-5s │ PID: %-6s │ %-15s ║\n" \
        "Reporting" "3344" "${pid:-N/A}" "$health"
    [ "$health" != "HEALTHY" ] && all_healthy=false
    
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo ""
    
    if $all_healthy; then
        return 0
    else
        return 1
    fi
}

# Start all servers
start_all() {
    log "=========================================="
    log "Starting Automation Servers"
    log "=========================================="
    
    local failed=0
    
    start_server "7 Levers" 3340 "7levers-server" "server.py" || ((failed++))
    start_server "Colosseum" 3341 "colosseum-api" "server.py" || ((failed++))
    start_server "Reporting" 3344 "reporting-server" "main.py" || ((failed++))
    
    echo ""
    log "Waiting for servers to stabilize..."
    sleep 3
    
    # Health check
    log "Running health checks..."
    show_status
    
    if [ $failed -eq 0 ]; then
        log_success "All servers started successfully!"
        log "Logs: ${LOG_DIR}/"
    else
        log_error "${failed} server(s) failed to start"
        return 1
    fi
}

# Stop all servers
stop_all() {
    log "=========================================="
    log "Stopping Automation Servers"
    log "=========================================="
    
    stop_server "7 Levers" 3340
    stop_server "Colosseum" 3341
    stop_server "Reporting" 3344
    
    log_success "All servers stopped"
}

# Restart all servers
restart_all() {
    stop_all
    sleep 2
    start_all
}

# Main
case "${1:-start}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    restart)
        restart_all
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac
