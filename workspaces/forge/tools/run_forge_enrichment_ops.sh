#!/bin/bash
# Forge Enrichment Batch — Memory's Data/Ops lane (Memory is rate-limited)
set -a
source ~/.openclaw/workspace-forge/.env
source ~/.openclaw/.env 2>/dev/null
set +a

PYTHON="~/.openclaw/workspace/tools/.venv/bin/python3"
SCRIPT="~/.openclaw/workspace-forge/tools/enrich_namespace.py"
LOG_DIR="~/.openclaw/workspace-forge/reports"
mkdir -p "$LOG_DIR"

NAMESPACES=(
  "data-analytics-and-business-intelligence|Data Analytics & Business Intelligence"
  "data-engineering-and-etl-pipelines|Data Engineering & ETL Pipelines"
  "d7-revops|Revenue Operations (RevOps)"
  "d6-delivery|Delivery & Fulfillment Operations"
  "d6-events|Events & Live Experience Operations"
  "d7-recovery|Revenue Recovery Operations"
  "d7-tax|Tax Strategy & Compliance"
  "d8-security|Cybersecurity & Information Security"
  "memory-rag-integrity-judge|Memory RAG Integrity & Judge Architecture"
  "ux-design-and-user-research|UX Design & User Research"
  "video-production-and-editing|Video Production & Editing"
  "graphic-design-and-visual-communication|Graphic Design & Visual Communication"
)

# Note: api-development-and-system-integration → Army/Sai
# Note: sales-and-revenue-operations → Memory claimed but overlaps; skipping to avoid collision

TOTAL=${#NAMESPACES[@]}
echo "⚔️ Forge — Memory's Ops Lane Assist: $TOTAL namespaces"
echo "Started: $(date)"
echo ""

for i in "${!NAMESPACES[@]}"; do
  IFS='|' read -r ns domain <<< "${NAMESPACES[$i]}"
  NUM=$((i + 1))
  LOG_FILE="$LOG_DIR/enrich-${ns}.log"
  
  echo "[$NUM/$TOTAL] $ns"
  $PYTHON "$SCRIPT" "$ns" "$domain" > "$LOG_FILE" 2>&1
  
  if [ $? -eq 0 ]; then
    echo "  ✅ Done — $(tail -3 $LOG_FILE | head -1)"
  else
    echo "  ❌ Failed — check $LOG_FILE"
  fi
  
  sleep 3
done

echo ""
echo "⚔️ Ops batch complete: $(date)"
