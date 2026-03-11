#!/bin/bash
# ACT-I Mastery Database Builder — Overnight Cron Runner
# Runs every 2 hours, processes 5 clusters per run
# 80 clusters ÷ 5 per run = 16 runs to complete all clusters

set -e

WORKSPACE="~/.openclaw/workspace-forge"
VENV="~/.openclaw/workspace/tools/.venv/bin/python3"
SCRIPT="$WORKSPACE/tools/mastery_researcher.py"
LOG="$WORKSPACE/reports/mastery-database/research-cron.log"
TRACKER="$WORKSPACE/reports/mastery-database/progress-tracker.json"

# Load env
source "$WORKSPACE/.env"
export OPENROUTER_API_KEY=[REDACTED]

cd "$WORKSPACE"

echo "[$(date)] Starting mastery research run..." >> "$LOG"

# Get next 5 clusters to research (skip already completed)
COMPLETED=$(ls reports/mastery-database/*-mastery.json 2>/dev/null | wc -l | tr -d ' ')
echo "[$(date)] Completed: $COMPLETED / 80 clusters" >> "$LOG"

# Run the next batch
$VENV "$SCRIPT" --limit 5 >> "$LOG" 2>&1

echo "[$(date)] Run complete." >> "$LOG"
