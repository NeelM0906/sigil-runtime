# SC2: Tax Strategy — Cluster Judge
**Inherits from: judge-d7-financial-legal (Domain Judge)**
**Positions: ~45** (entity structuring, compliance management, tax optimization, multi-state nexus, R&D credit, international tax)

## Cluster-Specific Scoring Criteria

### 1. Entity Structure Optimization
- **Godzilla:** Entity structure designed at inception with exit strategy built in (not retrofitted). Shares vs. assets analysis completed. Legal form adjustment follows strata's 6-step sequence. Structure optimizes for tax efficiency, liability protection, AND operational simplicity simultaneously.
- **Komodo:** Appropriate entity type for business stage. Basic liability protection in place. Annual review of structure adequacy.
- **Ant:** Entity chosen by default (friend's accountant said LLC). No exit planning. No awareness that shares vs. assets = different valuations.

### 2. Compliance Discipline
- **Godzilla:** Zero late filings across all jurisdictions. Multi-state nexus tracked automatically. Estimated payments calibrated quarterly to avoid both penalties AND excessive overpayment (cash flow optimization). Audit trail complete — every position defensible.
- **Komodo:** All filings on time. Standard deductions properly documented. Responds to notices within 30 days.
- **Ant:** Extension-dependent. Estimated payments are guesses. Shoebox of receipts. "My accountant handles it" with no oversight.

### 3. Strategic Tax Reduction
- **Godzilla:** R&D credits identified and documented with contemporaneous records. Cost segregation studies completed on real estate. Retirement vehicle contribution maximized with Roth conversion ladder mapped. QBI deduction optimized through entity structure. Effective rate tracked against statutory rate with gap analysis.
- **Komodo:** Standard deductions and credits captured. Retirement contributions made. Aware of QBI rules.
- **Ant:** Leaves money on the table annually. Doesn't know effective tax rate. "I just want to not get audited."

### 4. Deal Structuring Tax Impact
- **Godzilla:** Every material transaction analyzed for tax consequences BEFORE execution. 24-pitfall taxonomy awareness (strata: 60-70% deal failure rate baseline). Specialist advice at structuring phase, not implementation. Purchase price allocation optimized.
- **Komodo:** Tax impact considered in major deals. Specialist consulted for transactions >$500K.
- **Ant:** Tax consequences discovered after closing. "We'll figure out the tax part later."

## Strata Anchors
- Exit strategy belongs at STRUCTURING phase, not implementation (eeistratabrain/PwC framework)
- 24 deal pitfalls across 4 categories → 60-70% failure rate (eeistratabrain)
- Entity/legal form adjustment: shares vs. assets = different value, same economics (eeistratabrain, category 30.8h)
- 6-step sequence + 7 evidence quality criteria + 8 adjustment categories (eeistratabrain)
- R&D optimal spend: 1.7% of sales (eeistratabrain)

## Position Modifier Examples
```json
{
  "entity-structuring-specialist": { "weight_override": { "entity_structure": 1.5, "deal_structuring": 1.3 } },
  "compliance-manager": { "weight_override": { "compliance_discipline": 1.5, "strategic_reduction": 0.8 } },
  "r-and-d-credit-specialist": { "weight_override": { "strategic_reduction": 1.5, "compliance_discipline": 1.2 } }
}
```
