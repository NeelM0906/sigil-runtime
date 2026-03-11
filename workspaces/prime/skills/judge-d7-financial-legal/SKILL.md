# Judge D7: Financial & Legal — Domain Judge
**LOCAL ONLY — Proprietary Unblinded IP. Never publish.**

## Description
Score any ACT-I being output in the Financial & Legal domain (~290 positions across 6 skill clusters). This is the domain-level judge — it provides the shared scoring criteria inherited by all 6 cluster judges underneath it.

## When to Use
- Colosseum battles where the position falls under D7 (RevOps, Tax, Recovery, Compliance, Budgeting, Disposable Income)
- Evaluating any financial/legal deliverable from an ACT-I being
- Calibrating new beings entering D7 positions

## Domain Scoring Criteria (8 Dimensions)

### 1. Forecast Accuracy
| Creature | Threshold |
|----------|-----------|
| Komodo (7.0+) | Within 10% of actual revenue |
| Gecko (5.0-6.9) | 10-20% variance |
| Ant (<5.0) | >20% — forecasts are fiction |

### 2. Budget Variance
| Creature | Threshold |
|----------|-----------|
| Komodo | <5% from plan |
| Gecko | 5-10% |
| Ant | >10% — no financial discipline |

### 3. Collection Rate
| Creature | Threshold |
|----------|-----------|
| Komodo | >95% collected within terms |
| Gecko | 85-95% |
| Ant | <85% — cash flow bleeding |

### 4. Compliance Audit Pass
| Creature | Threshold |
|----------|-----------|
| Komodo | 100% — zero findings |
| Gecko | Minor findings, remediated <30 days |
| Ant | Material findings or repeated failures |

### 5. Revenue Recognition
| Creature | Threshold |
|----------|-----------|
| Komodo | GAAP/IFRS compliant, fully documented |
| Gecko | Mostly compliant, documentation gaps |
| Ant | Non-compliant or undocumented |

### 6. Cash Flow Projection
| Creature | Threshold |
|----------|-----------|
| Komodo | Within 15% at 90-day horizon |
| Gecko | 15-25% variance |
| Ant | >25% — can't see 90 days ahead |

### 7. Recovery Rate
| Creature | Threshold |
|----------|-----------|
| Komodo | >80% of billed amount collected |
| Gecko | 60-80% |
| Ant | <60% — leaving money on the table at scale |

### 8. Net Revenue Retention (NRR)
| Creature | Threshold |
|----------|-----------|
| Komodo | >110% (expansion exceeds churn) |
| Gecko | 90-110% (holding steady) |
| Ant | <90% — shrinking from within |

## Creature Calibration — Domain Level

**Komodo (7.0-7.9):** Budget variance at 4%, collection rate 96%, forecasts within 9% of actual, GAAP-compliant revenue recognition, medical recovery at 78%. Financially sound. Books are clean. Cash flows.

**Godzilla (9.0-9.99):** Budget variance at 1.8% — model updated weekly with actuals. Collection rate 98.5% with automated escalation at 15/30/45 days. Forecast accuracy within 4% because pipeline signals feed directly into the projection model. Medical recovery at 87% through systematic fee schedule re-billing per carrier contract terms (not accepting first-pass denials). NRR at 118% because financial operations surface expansion opportunities, not just track existing revenue. Every dollar is tracked, optimized, and defended — the financial system doesn't just report reality, it shapes it.

**Bolt (9.99+):** Never 10.0. Bolt finds the 0.01 gap in Godzilla's numbers. The budget model doesn't just update weekly — it auto-adjusts based on real-time cash position AND upcoming obligations. Recovery doesn't just re-bill — it predicted the denial before submission and structured the claim to avoid it. NRR at 130%+ because the financial architecture itself generates expansion signals that feed back into the business model.

## Strata Benchmarks (from ultimatestratabrain mining)

| Metric | Benchmark | Source |
|--------|-----------|--------|
| ROIC baseline | ~50% of companies earn above cost of capital | eeistratabrain |
| Hurdle rate buffer | WACC + 600 basis points (8% WACC → 14% hurdle) | eeistratabrain |
| Terminal value cap | ≤50% of company value in models | eeistratabrain |
| Budget adjustment rule | 10% at a time, quarterly review | eeistratabrain |
| Financial co. valuation accuracy | 0.83 within 15% for large financial cos | eeistratabrain |
| Target ROI | 20%+ | eeistratabrain |
| Sales growth target | +10% existing customers in 6 months | eeistratabrain |
| R&D optimal spend | 1.7% of sales | eeistratabrain |
| Deal failure rate | 60-70% without proper structuring | eeistratabrain |
| CFO overprecision | Forecast ranges vastly narrower than actual volatility | eeistratabrain |
| Attribution reattribution | Up to 95% credit reattributed to upper-funnel when corrected | eeistratabrain |

## Key Laws (from Strata)
1. **ROIC = NOPAT / Invested Capital** — the single metric that determines value creation vs. destruction
2. **~50% of companies destroy value** — earning above cost of capital is NOT the norm
3. **Real vs. accounting losses** — R&D expensing = future value building, not real loss. Mastery = distinguishing them.
4. **Exit strategy belongs at structuring phase** — not implementation. PwC framework: specialist advice shapes structure.
5. **24 deal pitfalls across 4 categories** — 60-70% failure rate without proper structuring
6. **CFOs systematically overestimate precision** — average forecasts fine, but ranges are fiction

## Net Score Rule
Net Score = min(Formula Judge Score, D7 Technical Score) — weakest organ drags the net.

## Skill Clusters (6)
Each has its own judge prompt that inherits from this domain spec:
- **SC1: Revenue Operations** — pricing, billing, revenue tracking
- **SC2: Tax Strategy** — entity structuring, compliance, optimization
- **SC3: Recovery Operations** — medical revenue recovery, insurance
- **SC4: Legal Review** — compliance, contract review, risk
- **SC5: Financial Planning** — budgeting, forecasting, cash flow
- **SC6: Disposable Income Modeling** — margin analysis, profit maximization

## Integration
This domain judge is Layer 2 in the 3-layer inheritance:
1. **Formula Judge** (universal, 39 components) — scores HOW the being operates
2. **Domain Judge D7** (this file) — scores WHAT domain criteria
3. **Skill Cluster Judge** (6 under D7) — scores craft-specific criteria
4. **Position Modifier** (JSON config) — position-specific weight overrides
