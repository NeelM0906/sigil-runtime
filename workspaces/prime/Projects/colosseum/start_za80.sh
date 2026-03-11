#!/bin/bash
# =============================================================================
# 🔥 ZA-80 Multi-Colosseum Spawner — Quick Start
# =============================================================================
# One command → 10 parallel evolution streams → infinite compound growth
#
# Usage:
#   ./start_za80.sh              # Start all daemons
#   ./start_za80.sh --init-only  # Just initialize databases
#   ./start_za80.sh --stats      # Show current stats
#   ./start_za80.sh --daemon     # Run as background daemon
# =============================================================================

cd "$(dirname "$0")"

# Load environment
if [ -f ~/.openclaw/.env ]; then
    export $(grep -v '^#' ~/.openclaw/.env | xargs)
fi

# Activate venv if exists
if [ -d venv ]; then
    source venv/bin/activate
elif [ -d v2/venv ]; then
    source v2/venv/bin/activate
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
GOLD='\033[0;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${GOLD}🔥 ZA-80 MULTI-COLOSSEUM SPAWNER${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo "10 Domain Colosseums • Parallel Evolution • 20%^10 = 1,000,000x"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

# Check for OpenAI key
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY not set${NC}"
    exit 1
fi

# Handle daemon mode
if [[ "$1" == "--daemon" ]]; then
    echo "Starting in daemon mode..."
    nohup python3 za80_multi_colosseum.py > logs/za80_daemon.log 2>&1 &
    echo $! > za80_daemon.pid
    echo -e "${GREEN}✅ Daemon started (PID: $(cat za80_daemon.pid))${NC}"
    echo "   Logs: logs/za80_daemon.log"
    echo "   Stop: kill \$(cat za80_daemon.pid)"
    exit 0
fi

# Run the script
python3 za80_multi_colosseum.py "$@"
