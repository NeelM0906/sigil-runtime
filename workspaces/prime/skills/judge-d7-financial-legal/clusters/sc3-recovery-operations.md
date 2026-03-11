# SC3: Recovery Operations — Cluster Judge
**Inherits from: judge-d7-financial-legal (Domain Judge)**
**Positions: ~52** (medical revenue recovery, insurance negotiation, fee schedule analysis, denial management, carrier contract compliance, lien resolution)

## Cluster-Specific Scoring Criteria

### 1. Fee Schedule Mastery
- **Godzilla:** Every bill cross-referenced against carrier-specific fee schedules. Re-billing initiated systematically when underpayment detected — not accepting first-pass amounts. Fee schedule database maintained and updated with each carrier contract renewal. Knows the difference between what was billed, what was allowed, and what was paid — and fights the gaps.
- **Komodo:** Fee schedules on file for major carriers. Underpayments flagged when obvious. Re-billing process exists.
- **Ant:** Bills submitted and whatever comes back is accepted. No fee schedule comparison. Money left on every claim.

### 2. Denial Prevention & Management
- **Godzilla:** Denial rate <5% because claims are structured to prevent denial before submission. Common denial patterns tracked and pre-empted. When denials occur: appealed within 48 hours with documentation that addresses the specific denial reason code. Denial-to-recovery conversion >80%.
- **Komodo:** Denial rate <15%. Appeals filed on material denials. Tracking exists.
- **Ant:** Denial rate unknown. Denials accepted as "the cost of doing business." No appeal process.

### 3. Carrier Contract Compliance Enforcement
- **Godzilla:** Carrier obligations tracked against contract terms. When carrier violates payment terms, escalation is systematic with documented evidence. Knows which carriers routinely underpay and has pre-built response protocols. Contract renewal negotiations informed by 12+ months of payment performance data.
- **Komodo:** Aware of major contract terms. Escalates egregious violations. Reviews contracts at renewal.
- **Ant:** "We have a contract?" No tracking of carrier compliance. Accepts whatever payment arrives.

### 4. Recovery Rate Optimization
- **Godzilla:** Recovery rate >87% of billed amount through systematic re-billing, timely appeals, and carrier accountability. Recovery timeline tracked — 30/60/90 day aging by carrier with automated escalation. Zero write-offs without documented exhaustion of recovery options.
- **Komodo:** Recovery rate >80%. Aging reports reviewed monthly. Major write-offs require approval.
- **Ant:** Recovery rate <60%. "Some claims just don't pay." Write-offs are routine with no analysis.

## Callagy Recovery Context
This cluster is critical for Callagy Recovery operations. Mark Winters leads the human side. Key focus areas:
- Fee schedule re-billing per carrier contracts
- MMR and bilateral billing standards
- Systematic denial management
- Recovery rate as the north star metric

## Strata Anchors
- Medical billing industry recovery rates by payer type (domain specs baseline)
- Clio Legal Trends Report for legal industry financial performance benchmarks
- Recovery rate Godzilla target: 87%+ through systematic fee schedule re-billing (domain creature calibration)
- Automated escalation at 15/30/45 days (domain Godzilla pattern)

## Position Modifier Examples
```json
{
  "fee-schedule-analyst": { "weight_override": { "fee_schedule_mastery": 1.5, "denial_management": 1.0 } },
  "denial-specialist": { "weight_override": { "denial_management": 1.5, "recovery_rate": 1.2 } },
  "carrier-relations-manager": { "weight_override": { "carrier_compliance": 1.5, "fee_schedule_mastery": 1.2 } },
  "recovery-coordinator": { "weight_override": { "recovery_rate": 1.5, "denial_management": 1.2 } }
}
```
