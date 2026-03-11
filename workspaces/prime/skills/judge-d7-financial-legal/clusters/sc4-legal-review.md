# SC4: Legal Review — Cluster Judge
**Inherits from: judge-d7-financial-legal (Domain Judge)**
**Positions: ~48** (compliance review, contract analysis, risk assessment, regulatory monitoring, litigation support, IP protection)

## Cluster-Specific Scoring Criteria

### 1. Contract Review Precision
- **Godzilla:** Every material contract reviewed for: liability exposure, termination triggers, payment terms, IP assignment, non-compete scope, and change-of-control provisions. Red flags surfaced before signature with specific language alternatives. Turnaround <48 hours for standard contracts, <5 days for complex.
- **Komodo:** Contracts reviewed by qualified counsel. Major risk provisions identified. Standard playbook for common contract types.
- **Ant:** Contracts signed without legal review. "Our lawyer will look at it later." Unfavorable terms discovered in disputes.

### 2. Compliance Architecture
- **Godzilla:** Regulatory requirements mapped by jurisdiction and updated automatically when regulations change. Compliance calendar maintained with 30-day advance alerts. Self-audit cadence established — doesn't wait for external audit to find gaps. Zero material findings in 24 months.
- **Komodo:** Major compliance requirements known and tracked. Annual review. Responds to regulatory changes within 60 days.
- **Ant:** Compliance is reactive — discovers requirements when violations occur. "We didn't know that applied to us."

### 3. Risk Quantification
- **Godzilla:** Risk expressed in dollars, not adjectives. "This clause exposes us to $2.4M in the termination scenario" — not "this is a high-risk clause." Probability × impact matrix maintained for material risks. Insurance coverage mapped to identified risks with gap analysis.
- **Komodo:** Major risks identified and categorized. Insurance coverage adequate for primary risks. Annual risk review.
- **Ant:** Risk is a feeling, not a number. "We should be fine." Insurance coverage hasn't been reviewed since inception.

### 4. Litigation Support Effectiveness
- **Godzilla:** Discovery response organized within 72 hours with privilege log. Expert witness coordination with 60-day preparation timeline. Settlement analysis includes: litigation cost projection, probability-weighted outcomes, and time-value-of-money comparison. Every position defensible with documented evidence chain.
- **Komodo:** Timely response to discovery. Expert witnesses engaged when needed. Settlement discussions informed by case assessment.
- **Ant:** Scrambling for documents. No litigation hold procedures. Settlement decisions based on "make it go away" rather than analysis.

## Sean's Legal Background Context
Sean is one of only two attorneys out of 1.2 million in America to win two Top 100 National Jury Verdicts. Legal excellence is non-negotiable in this cluster. The standard isn't "competent legal work" — it's masterful legal strategy that creates leverage.

## Strata Anchors
- 24-pitfall taxonomy across 4 deal categories: Strategy/Prep, Structuring, Negotiation, Implementation (eeistratabrain)
- 60-70% deal failure rate without proper structuring (eeistratabrain)
- Legal form adjustment: 6-step sequence + 7 evidence quality criteria + 8 adjustment categories (eeistratabrain)
- "Reasonable attorneys' fees" inclusion creates leverage for litigation cost recovery (strata round 2)

## Position Modifier Examples
```json
{
  "contract-analyst": { "weight_override": { "contract_review": 1.5, "risk_quantification": 1.2 } },
  "compliance-officer": { "weight_override": { "compliance_architecture": 1.5, "risk_quantification": 1.0 } },
  "litigation-support-specialist": { "weight_override": { "litigation_support": 1.5, "contract_review": 0.8 } },
  "risk-manager": { "weight_override": { "risk_quantification": 1.5, "compliance_architecture": 1.2 } }
}
```
