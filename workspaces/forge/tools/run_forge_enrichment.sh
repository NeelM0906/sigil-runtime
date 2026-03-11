#!/bin/bash
# Forge Enrichment Batch — 28 thin namespaces, 8 vectors each
# Run: bash tools/run_forge_enrichment.sh
# Skips d5-sales (already running in separate process)

set -a
source ~/.openclaw/workspace-forge/.env
source ~/.openclaw/.env 2>/dev/null
set +a

PYTHON="~/.openclaw/workspace/tools/.venv/bin/python3"
SCRIPT="~/.openclaw/workspace-forge/tools/enrich_namespace.py"
LOG_DIR="~/.openclaw/workspace-forge/reports"
mkdir -p "$LOG_DIR"

NAMESPACES=(
  "affiliate-marketing-and-referral-programs|Affiliate Marketing & Referral Programs"
  "brand-strategy-and-market-positioning|Brand Strategy & Market Positioning"
  "community-building-and-engagement|Community Building & Engagement"
  "competitive-intelligence-and-market-research|Competitive Intelligence & Market Research"
  "content-writing-and-copywriting|Content Writing & Copywriting"
  "conversion-rate-optimization-and-landing-pages|Conversion Rate Optimization & Landing Pages"
  "email-marketing-and-automation|Email Marketing & Automation"
  "event-planning-and-production|Event Planning & Production"
  "influencer-marketing-and-brand-partnerships|Influencer Marketing & Brand Partnerships"
  "marketing-strategy-and-planning|Marketing Strategy & Planning"
  "media-buying-and-advertising|Media Buying & Advertising"
  "podcast-production-and-audio-content|Podcast Production & Audio Content"
  "pricing-strategy-and-revenue-optimization|Pricing Strategy & Revenue Optimization"
  "public-relations-and-brand-communications|Public Relations & Brand Communications"
  "public-speaking-and-stage-mastery|Public Speaking & Stage Mastery"
  "reputation-management-and-online-reviews|Reputation Management & Online Reviews"
  "sales-and-revenue-operations|Sales & Revenue Operations"
  "seo-and-search-marketing|SEO & Search Marketing"
  "social-media-management-and-strategy|Social Media Management & Strategy"
  "supply-chain-and-logistics-management|Supply Chain & Logistics Management"
  "talent-acquisition-and-human-resources|Talent Acquisition & Human Resources"
  "venture-capital-and-fundraising|Venture Capital & Fundraising"
  "webinar-production-and-virtual-events|Webinar Production & Virtual Events"
  "pricing-strategy-and-revenue-optimization|Pricing Strategy & Revenue Optimization"
  # legal-operations-personal-injury → handed off to Army/Prime
)

TOTAL=${#NAMESPACES[@]}
echo "⚔️ Forge Enrichment Batch — $TOTAL namespaces"
echo "Started: $(date)"
echo ""

for i in "${!NAMESPACES[@]}"; do
  IFS='|' read -r ns domain <<< "${NAMESPACES[$i]}"
  NUM=$((i + 1))
  LOG_FILE="$LOG_DIR/enrich-${ns}.log"
  
  echo "[$NUM/$TOTAL] $ns"
  $PYTHON "$SCRIPT" "$ns" "$domain" > "$LOG_FILE" 2>&1
  
  if [ $? -eq 0 ]; then
    VECTORS=$(grep -c "chars" "$LOG_FILE" 2>/dev/null || echo "?")
    echo "  ✅ Done — $(tail -3 $LOG_FILE | head -1)"
  else
    echo "  ❌ Failed — check $LOG_FILE"
  fi
  
  # Rate limit buffer between namespaces
  sleep 3
done

echo ""
echo "⚔️ Batch complete: $(date)"
echo "Logs in: $LOG_DIR"
