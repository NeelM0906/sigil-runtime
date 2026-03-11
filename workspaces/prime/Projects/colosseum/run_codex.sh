#!/bin/bash
source ~/.openclaw/.env 2>/dev/null
export OPENAI_API_KEY
echo "Key starts with: ${OPENAI_API_KEY:0:10}"
cd ./workspaces/prime/Projects/colosseum
codex exec --full-auto "Read SPEC.md carefully. Build the entire Colosseum framework as specified. Start with requirements.txt, then build each module in order: scenarios.py, beings.py, arena.py, judge.py, evolution.py, tournament.py, api.py. Then build run_tournament.py and run_server.py. Include the dashboard HTML template. Make sure everything works together. After building all files, commit everything to git.

When completely finished, run: openclaw system event --text 'Done: Colosseum framework built' --mode now"
