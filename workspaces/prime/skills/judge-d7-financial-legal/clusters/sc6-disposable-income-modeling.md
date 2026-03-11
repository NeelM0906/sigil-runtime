# SC6: Disposable Income Modeling — Cluster Judge
**Inherits from: judge-d7-financial-legal (Domain Judge)**
**Positions: ~47** (margin analysis, profit maximization, cost structure optimization, pricing elasticity, contribution margin, break-even modeling)

## Cluster-Specific Scoring Criteria

### 1. Margin Architecture
- **Godzilla:** Contribution margin tracked per product/service/client segment — not just blended. Knows which customers are profitable at the unit level and which are subsidized. Margin expansion opportunities identified quarterly with specific action plans. Gross → operating → net margin waterfall documented and tracked.
- **Komodo:** Overall margins tracked monthly. Major cost drivers identified. Pricing covers costs with documented margin.
- **Ant:** "We're profitable" based on bank balance growing. No unit economics. No segment analysis. Cross-subsidization invisible.

### 2. Cost Structure Clarity
- **Godzilla:** Fixed vs. variable costs mapped precisely. Every fixed cost has a "what would it take to make this variable?" analysis. Step-function costs identified — knows exactly where the next capacity cliff is. Overhead allocation method chosen deliberately (not inherited from QuickBooks default).
- **Komodo:** Major fixed and variable costs categorized. Overhead tracked. Cost reduction reviewed annually.
- **Ant:** All costs feel "fixed." No visibility into cost behavior. "We need all of this" without evidence.

### 3. Break-Even Intelligence
- **Godzilla:** Break-even calculated per product line, per channel, per customer segment. Sensitivity analysis: "If price drops 5%, break-even shifts by X units." Time-to-break-even for new initiatives tracked against projection. Cash break-even distinguished from accounting break-even.
- **Komodo:** Company-level break-even known. Reviewed when pricing changes. New projects have break-even projections.
- **Ant:** Break-even is "somewhere around $X" based on gut feel. New initiatives launched without break-even analysis.

### 4. Profit Maximization Strategy
- **Godzilla:** Revenue optimization AND cost optimization treated as two independent levers — not just "cut costs." Pricing elasticity tested (strata: R&D optimal at 1.7% of sales as reinvestment benchmark). Customer lifetime value compared against acquisition cost with payback period. Identifies the 20% of offerings producing 80% of profit — and doubles down.
- **Komodo:** Revenue and cost both managed. Major profit drivers identified. 80/20 awareness at product level.
- **Ant:** Profit maximization = "raise prices" or "cut headcount." No analysis. No elasticity testing. No LTV/CAC framework.

## Strata Anchors
- R&D optimal spend: 1.7% of sales — below = underinvesting, above = likely diminishing returns (eeistratabrain)
- RQ (Research Quotient): % revenue increase per 1% R&D increase. Distribution: 1/3 under, 2/3 over, 5% optimal (eeistratabrain)
- Revenue per customer 20% below industry average = diagnostic trigger (eeistratabrain)
- Growth rate decline from 15% → <1% in 5 years = structural problem, not market cycle (eeistratabrain)
- Single method acceptable when confidence is high — prevents over-engineering analysis (eeistratabrain)

## Position Modifier Examples
```json
{
  "margin-analyst": { "weight_override": { "margin_architecture": 1.5, "cost_structure": 1.2 } },
  "pricing-strategist": { "weight_override": { "profit_maximization": 1.5, "break_even": 1.2 } },
  "cost-optimization-lead": { "weight_override": { "cost_structure": 1.5, "margin_architecture": 1.0 } },
  "unit-economics-analyst": { "weight_override": { "break_even": 1.5, "margin_architecture": 1.3 } }
}
```
