#!/bin/bash
# Colosseum Daemon Startup Script with Virtual Environment

cd ~/Projects/colosseum
source venv/bin/activate
python3 colosseum_daemon.py --daemon "$@"