#!/bin/bash
# Perplexity web enrichment for all 80 ACT-I Being clusters
set -a
source ~/.openclaw/workspace-forge/.env
source ~/.openclaw/.env 2>/dev/null
set +a

PYTHON="~/.openclaw/workspace/tools/.venv/bin/python3"
SCRIPT="~/.openclaw/workspace-forge/tools/perplexity_mastery_research.py"
LOG="~/.openclaw/workspace-forge/reports/perplexity-beings-$(date +%Y%m%d-%H%M).log"

declare -A BEINGS=(
  ["social"]="Social Media Management"
  ["oracle"]="Data Analytics & Intelligence"
  ["stagehand"]="Event Production & Logistics"
  ["hunter"]="Outreach & Lead Development"
  ["canvas"]="Visual & Graphic Design"
  ["valueengine"]="Customer Economics & LTV Analytics"
  ["pricearchitect"]="Pricing & Revenue Strategy"
  ["healer"]="Social Impact & CSR"
  ["sage"]="Thought Leadership & Influence"
  ["enchanter"]="Experience Design & Delight"
  ["guardian"]="Customer Success & Account Growth"
  ["soundforge"]="Audio Engineering & Sound Design"
  ["scout"]="Partnership Research & Intelligence"
  ["virtual"]="Webinar & Virtual Events"
  ["architect"]="Content Strategy & Management"
  ["treasurer"]="Financial Planning & Analysis"
  ["agreementmaker"]="Agreement Making"
  ["mediabuyer"]="Paid Media & Ad Ops"
  ["integrator"]="Partnership Integration & Ops"
  ["revinsight"]="Revenue Analytics"
  ["director"]="Video Direction & Production"
  ["bridge"]="Partnership Development"
  ["distributor"]="Video Operations & Distribution"
  ["audioreach"]="Audio Marketing & Distribution"
  ["enabler"]="Revenue Operations & Enablement"
  ["revops"]="Revenue Operations"
  ["adsmith"]="Ad Creative Production"
  ["podcast"]="Podcast & Audio Production"
  ["gripmaster"]="Production Operations & Logistics"
  ["scholar-scribe"]="PR & Media Relations"
  ["sphinx"]="Interactive & Quiz Design"
  ["rigger"]="Stage & Technical Production"
  ["promoter"]="Event Marketing & Promotion"
  ["interface"]="UX & Interface Writing"
  ["automator"]="Email & SMS Marketing Automation"
  ["scribe"]="SEO & Content Writing"
  ["channelmaster"]="Platform & Channel Partnerships"
  ["steward"]="Community Management"
  ["illustra"]="Illustration & Fine Art"
  ["bard"]="Narrative & Long-Form Writing"
  ["curator"]="Event Strategy & Curation"
  ["optimizer"]="Conversion Rate Optimization"
  ["cultivator"]="Partnership Nurturing & Relationships"
  ["lens"]="Cinematography & Lighting"
  ["editor"]="Video Post-Production & VFX"
  ["orator"]="Speaker Development & Coaching"
  ["flow"]="UX/UI Design"
  ["neuron"]="Data Science & Engineering"
  ["bookagent"]="Speaking & Stage Ops"
  ["shield"]="Legal & Compliance"
  ["identity"]="Brand Strategy & Messaging"
  ["pixel"]="Digital & Web Design"
  ["voice"]="Voice Performance & Presenting"
  ["clarity"]="Data Visualization & Dashboards"
  ["builder"]="Web Development & Technology"
  ["environ"]="Environmental & Spatial Design"
  ["persuader"]="Conversion Copywriting"
  ["dealmaker"]="Partnership Agreement Making"
  ["setmaster"]="Production Design & Art Direction"
  ["cocreator"]="Partnership Marketing & Content"
  ["visionary"]="Creative Direction & Design Ops"
  ["broadcaster"]="Content Distribution & Promotion"
  ["spider"]="SEO Technical"
  ["discoverer"]="Partnership Sourcing & Outreach"
  ["kinetic"]="Motion Graphics & Animation"
  ["coach"]="Revenue Training & Coaching"
  ["playwright"]="Script & Speech Writing"
  ["touchpoint"]="Physical Touch & Direct Mail"
  ["form"]="Product & Industrial Design"
  ["genesis"]="ACT-I Being Development"
  ["pipeline"]="CRM & Marketing Automation"
  ["nurture"]="Email & Nurture Copywriting"
  ["inspector"]="Quality Assurance & Testing"
  ["opsengine"]="Marketing Operations"
  ["shutter"]="Photography"
  ["herald"]="PR & Brand Copywriting"
  ["pulse"]="Social Media Copywriting"
  ["conductor"]="Project Management"
  ["translator"]="Localization & Translation"
)

echo "⚔️ Perplexity Being Enrichment — ${#BEINGS[@]} clusters" | tee $LOG
echo "Started: $(date)" | tee -a $LOG
echo "" | tee -a $LOG

COUNT=0
TOTAL=${#BEINGS[@]}
for ns in "${!BEINGS[@]}"; do
  COUNT=$((COUNT + 1))
  DOMAIN="${BEINGS[$ns]}"
  echo "[$COUNT/$TOTAL] $ns — $DOMAIN" | tee -a $LOG
  $PYTHON "$SCRIPT" "$ns" "$DOMAIN" >> $LOG 2>&1
  sleep 2
done

echo "" | tee -a $LOG
echo "⚔️ Complete: $(date)" | tee -a $LOG
echo "Log: $LOG"
