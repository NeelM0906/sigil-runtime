# SC1: Revenue Operations — Cluster Judge
**Inherits from: judge-d7-financial-legal (Domain Judge)**
**Positions: ~48** (pricing architecture, billing systems, revenue tracking, DSO management, dunning sequences, payment optimization)

## Cluster-Specific Scoring Criteria

### 1. Pricing Architecture Precision
- **Godzilla:** Price points derived from willingness-to-pay data + competitive positioning + margin targets. Price changes A/B tested with statistical significance before full rollout. Revenue per customer tracked as leading indicator.
- **Komodo:** Pricing exists, is documented, and updates quarterly based on market review.
- **Ant:** Pricing is ad hoc, based on gut feel, or hasn't changed in 2+ years while costs shifted.

### 2. DSO (Days Sales Outstanding) Management
- **Godzilla:** DSO tracked weekly by segment. Automated escalation triggers at 15/30/45/60 days. Collection rate >98%. Aging report drives proactive outreach BEFORE terms expire.
- **Komodo:** DSO tracked monthly. Collection rate >95%. Standard follow-up process exists.
- **Ant:** DSO unknown or >60 days. No systematic collection process. Cash flow surprises are normal.

### 3. Revenue Attribution Accuracy
- **Godzilla:** Multi-touch attribution model with upper-funnel credit properly weighted (up to 95% reattribution when corrected per strata data). Revenue source tracked to channel, campaign, and touchpoint.
- **Komodo:** Last-touch attribution with awareness of its limitations. Revenue tracked to channel level.
- **Ant:** "Marketing brought them in" or "sales closed them" — no actual attribution. Budget decisions based on vibes.

### 4. Billing System Integrity
- **Godzilla:** Zero billing errors in 90-day rolling window. Automated reconciliation between CRM → billing → bank. Failed payments auto-retry with smart dunning (time-of-day, day-of-week optimized).
- **Komodo:** <1% error rate. Manual reconciliation monthly. Standard dunning sequence exists.
- **Ant:** Regular billing disputes. Manual invoicing. "We'll figure it out" approach to discrepancies.

## Strata Anchors
- Revenue Per Visit as efficiency metric — same conversion, different RPV = different economics (eeistratabrain)
- Target ROI benchmark: 20%+ (eeistratabrain)
- Sales growth target: +10% existing customers in 6 months (eeistratabrain)
- Warning signal: growth rate declining from 15% to <1% in 5 years = alarm (eeistratabrain)
- Revenue per customer 20% below industry average = diagnostic trigger (eeistratabrain)

## Position Modifier Examples
```json
{
  "pricing-architect": { "weight_override": { "pricing_architecture": 1.5, "billing_integrity": 0.8 } },
  "collections-manager": { "weight_override": { "dso_management": 1.5, "billing_integrity": 1.2 } },
  "revenue-analyst": { "weight_override": { "attribution_accuracy": 1.5, "pricing_architecture": 1.0 } }
}
```
