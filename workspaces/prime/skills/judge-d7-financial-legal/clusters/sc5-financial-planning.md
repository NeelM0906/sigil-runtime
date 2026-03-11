# SC5: Financial Planning — Cluster Judge
**Inherits from: judge-d7-financial-legal (Domain Judge)**
**Positions: ~50** (budgeting, forecasting, cash flow management, scenario modeling, capital allocation, financial modeling)

## Cluster-Specific Scoring Criteria

### 1. Forecast Model Rigor
- **Godzilla:** Forecast accuracy within 4% because pipeline signals feed directly into the projection model. Model uses strict module separation: Input → Calculation → Output (each with distinct function). Terminal value capped at ≤50% of company value. Updated weekly with actuals. Acknowledges overprecision bias (strata: CFO forecast ranges vastly narrower than reality) and builds wider confidence intervals.
- **Komodo:** Forecast accuracy within 10%. Model exists, is documented, and updates monthly. Variance analysis performed quarterly.
- **Ant:** Forecast accuracy >20%. "We projected $X" with no methodology, no updates, no variance review. Spreadsheet chaos.

### 2. Cash Flow Visibility
- **Godzilla:** 13-week rolling cash flow forecast maintained. Real-time cash position known to the dollar. Upcoming obligations mapped against expected inflows. Trigger points defined: "If cash drops below $X, we do Y." Working capital optimization measured — not just tracked.
- **Komodo:** Cash flow projected at 90-day horizon within 15%. Monthly cash position reviewed. Major obligations tracked.
- **Ant:** Cash flow managed by checking bank balance. "We'll be fine" based on feeling. Payroll surprises.

### 3. Capital Allocation Discipline
- **Godzilla:** Every investment evaluated against ROIC framework (NOPAT / Invested Capital). Hurdle rate = WACC + 600 basis points (strata benchmark). New projects compete for capital against existing returns. Sunk cost fallacy actively guarded against — ROIIC (incremental) used for marginal decisions, not total ROIC.
- **Komodo:** Major investments have ROI projections. Budget exists with quarterly review. Capital requests require justification.
- **Ant:** Capital allocated based on loudest voice in the room. No ROI measurement. "We need this" = approved.

### 4. Scenario Planning Depth
- **Godzilla:** Three scenarios maintained (base, upside, downside) with specific trigger events that shift between them. Each scenario has a playbook: "If we enter downside scenario, we cut X, protect Y, accelerate Z." Budget adjustments follow 10% at a time rule with quarterly review (strata benchmark). Stress-tested against historical volatility.
- **Komodo:** Base case and one downside scenario. Contingency plan exists for major revenue shortfall.
- **Ant:** One plan. If it doesn't work out: panic. "We didn't see that coming."

## Strata Anchors
- ROIC = NOPAT / Invested Capital — ~50% of companies earn above cost of capital (eeistratabrain)
- ROIIC = change in NOPAT / change in IC — ignores sunk costs, one-year lag (eeistratabrain)
- Hurdle rate: WACC + 600 basis points (eeistratabrain)
- Terminal value: ≤50% of company value in any model (eeistratabrain)
- Budget adjustment: 10% at a time, quarterly review (eeistratabrain)
- CFO overprecision: averages fine, ranges fiction — build wider intervals (eeistratabrain)
- Financial model mastery: module separation (Input → Calculation → Output) (eeistratabrain)
- Financial co. valuation accuracy: 0.83 within 15% for large companies (eeistratabrain)

## Position Modifier Examples
```json
{
  "financial-modeler": { "weight_override": { "forecast_rigor": 1.5, "scenario_planning": 1.2 } },
  "cash-flow-manager": { "weight_override": { "cash_flow_visibility": 1.5, "forecast_rigor": 1.0 } },
  "capital-allocator": { "weight_override": { "capital_allocation": 1.5, "scenario_planning": 1.3 } },
  "budget-analyst": { "weight_override": { "forecast_rigor": 1.3, "scenario_planning": 1.2, "capital_allocation": 1.0 } }
}
```
