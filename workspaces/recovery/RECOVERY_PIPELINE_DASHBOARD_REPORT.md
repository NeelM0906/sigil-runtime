# 📊 Recovery Pipeline Dashboard Report

**Prepared by:** SAI Recovery 🌱  
**Report Date:** March 22, 2026  
**Report Period:** March 1–22, 2026  
**Status:** DEMO — Illustrative Sample Data  

---

## 1. Executive Summary

| Metric | MTD Value | Target | Status |
|--------|-----------|--------|--------|
| **Total $ Recovered** | $487,320 | $600,000/mo | 🟡 81% to target |
| **Recovery Rate (Count)** | 68% | ≥ 65% | 🟢 On Target |
| **Recovery Rate (Dollar-Weighted)** | 72% | ≥ 70% | 🟢 On Target |
| **Avg Days to Recovery** | 78 days | ≤ 90 days | 🟢 On Target |
| **Contingency Revenue** | $146,196 | $180,000/mo | 🟡 81% to target |
| **Active Pipeline Cases** | 142 | Capacity: 200 | 🟢 Healthy |
| **Pipeline Value (Active)** | $3,214,500 | Growth metric | 📈 +12% vs Feb |
| **Overdue Cases** | 3 | 0 | 🔴 Action Needed |
| **Missed Deadlines** | 0 | 0 (Zero Tolerance) | 🟢 Perfect |

---

## 2. Pipeline Stage Distribution

```
Stage           | Cases | Value          | Avg Days in Stage | Max Dwell | Status
─────────────────────────────────────────────────────────────────────────────────────
1. Intake       |   18  |   $412,000     |     1.2 days      |   3 days  | 🟢
2. Verification |   22  |   $498,300     |     3.8 days      |   5 days  | 🟢
3. Demand       |   14  |   $287,600     |     1.1 days      |   2 days  | 🟢
4. Negotiation  |   51  |   $1,342,100   |    28.4 days      |  60 days  | 🟢
5. Resolution   |   19  |   $387,500     |     6.2 days      |  10 days  | 🟢
6. Collection   |   12  |   $198,400     |    22.1 days      |  45 days  | 🟢
7. Closed       |   6   |   $88,600      |     0.8 days      |   2 days  | 🟢
─────────────────────────────────────────────────────────────────────────────────────
TOTAL ACTIVE    |  142  | $3,214,500     |                   |           |
```

**Bottleneck Alert:** Stage 4 (Negotiation) holds 36% of all active cases. This is expected — it's the longest stage by design (15–60 day typical duration). Current 28.4-day average is healthy.

---

## 3. Priority Breakdown

| Priority | Cases | Pipeline Value | % of Total |
|----------|-------|---------------|------------|
| 🔴 **CRITICAL** (>$50K / Enterprise / SLA Breach) | 8 | $892,000 | 28% |
| 🟠 **HIGH** ($10K–$50K / Referral Network / Renewal ≤30d) | 34 | $1,124,500 | 35% |
| 🟡 **MEDIUM** ($5K–$10K / Active Provider) | 62 | $847,200 | 26% |
| 🟢 **LOW** (<$5K / Standard) | 38 | $350,800 | 11% |

---

## 4. ⚠️ Overdue Cases — Action Required

These 3 cases have exceeded max dwell time in their current stage:

| Case # | Provider | Payer | Stage | Days in Stage | Max Dwell | Value | Action |
|--------|----------|-------|-------|--------------|-----------|-------|--------|
| CR-2026-00087 | Dr. Sarah Chen, MD | Anthem BCBS | 4-Negotiation | 64 days | 60 days | $38,200 | Escalate to Resolution or Legal referral |
| CR-2026-00103 | Metro Spine Associates | UnitedHealthcare | 5-Resolution | 12 days | 10 days | $27,400 | Follow up on written confirmation |
| CR-2026-00118 | Valley Surgical Center | Cigna | 2-Verification | 7 days | 5 days | $14,800 | Missing provider docs — outreach needed |

**Recommended Actions:**
1. **CR-2026-00087:** 4 days overdue. Payer has gone silent. Recommend escalation to peer-to-peer review or regulatory complaint (Anthem has a pattern — see Payer Intelligence below).
2. **CR-2026-00103:** Written agreement reached but payer hasn't sent confirmation letter. Send second request with 48-hour deadline.
3. **CR-2026-00118:** Provider hasn't submitted operative notes. Call provider contact directly — they may need a reminder on what's needed.

---

## 5. Stage Conversion Rates (MTD)

```
Intake → Verification:      94%  (🟢 strong intake quality)
Verification → Demand:      82%  (🟢 good viability filtering)
Demand → Negotiation:       96%  (🟢 demands consistently accepted for review)
Negotiation → Resolution:   71%  (🟡 room for improvement — payer pushback)
Resolution → Collection:    89%  (🟢 agreements holding)
Collection → Closed:        95%  (🟢 payments processing normally)
```

**Key Insight:** The Negotiation → Resolution conversion rate (71%) is our biggest leverage point. Every 5% improvement here = ~$160K additional annual recovery.

---

## 6. Top 10 Payers by Active Cases

| Rank | Payer | Active Cases | Avg Recovery Rate | Avg Days to Resolve | Risk Level |
|------|-------|-------------|-------------------|--------------------|----|
| 1 | UnitedHealthcare | 28 | 74% | 82 days | 🟡 |
| 2 | Anthem BCBS | 22 | 61% | 95 days | 🔴 |
| 3 | Aetna | 18 | 78% | 68 days | 🟢 |
| 4 | Cigna | 16 | 69% | 74 days | 🟡 |
| 5 | Humana | 12 | 82% | 55 days | 🟢 |
| 6 | Medicare Advantage | 11 | 85% | 48 days | 🟢 |
| 7 | Workers' Comp (various) | 10 | 58% | 112 days | 🔴 |
| 8 | BCBS of NJ | 9 | 71% | 76 days | 🟡 |
| 9 | Horizon BCBS | 8 | 73% | 70 days | 🟡 |
| 10 | Oxford Health | 8 | 77% | 62 days | 🟢 |

**Payer Intelligence Flags:**
- 🔴 **Anthem BCBS:** Lowest recovery rate (61%), longest resolution time (95 days). Pattern: delays at peer-to-peer stage, requires escalation threats to move. Consider regulatory complaint strategy.
- 🔴 **Workers' Comp:** Slowest overall (112 days avg). Multi-party coordination required. Recommend dedicated WC specialist assignment.

---

## 7. Provider Relationship Health

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Active Providers (cases in pipeline) | 47 | — | Baseline |
| Provider Retention Rate (Q1) | 87% | ≥ 85% | 🟢 |
| Provider Satisfaction Score (avg) | 8.2 / 10 | ≥ 8.0 | 🟢 |
| Providers At Risk (no contact 60+ days) | 4 | 0 | 🟡 |
| Net New Providers (March MTD) | 3 | 5/mo | 🟡 |
| Provider Churn Rate | 8% | ≤ 10% | 🟢 |

**At-Risk Providers (Reactivation Needed):**
1. **Northeast Orthopedics** — Last case submitted 68 days ago. Previously high-volume (12 cases/quarter). Outreach priority.
2. **Riverside Pain Management** — 71 days. Known frustration with Cigna delays on their cases. Need to show progress.
3. **Dr. Michael Torres** — 63 days. New provider, only 1 case. May not understand full service value yet.
4. **Summit Physical Therapy** — 80 days. Last case was Closed-Lost. Relationship repair needed.

---

## 8. Financial Forecast

| Metric | March Actual (MTD) | March Projected | Q1 Total (Projected) |
|--------|-------------------|-----------------|---------------------|
| Gross Recovery | $487,320 | $638,000 | $1,842,000 |
| Contingency Revenue (30% avg) | $146,196 | $191,400 | $552,600 |
| Cases Closed-Recovered | 23 | 30 | 88 |
| Cases Closed-Lost | 8 | 11 | 29 |
| Win Rate | 74% | 73% | 75% |

**Pipeline-Weighted Forecast (Next 90 Days):**
- **High Confidence (≥70% probability):** $1,180,000 recoverable → ~$354,000 revenue
- **Medium Confidence (40–69%):** $1,420,000 recoverable → ~$426,000 revenue (risk-adjusted)
- **Low Confidence (<40%):** $614,500 recoverable → ~$92,000 revenue (risk-adjusted)

---

## 9. Recommended Actions This Week

| # | Action | Priority | Owner | Deadline |
|---|--------|----------|-------|----------|
| 1 | Resolve 3 overdue cases (Section 4) | 🔴 Critical | SAI Recovery | March 24 |
| 2 | Contact 4 at-risk providers (Section 7) | 🟠 High | Recovery Team | March 26 |
| 3 | Escalate CR-2026-00087 (Anthem) — consider regulatory | 🔴 Critical | SAI Recovery + Legal | March 24 |
| 4 | Audit Negotiation stage cases >45 days for acceleration | 🟠 High | SAI Recovery | March 25 |
| 5 | Prepare Q1 provider satisfaction survey | 🟡 Medium | Recovery Team | March 28 |
| 6 | New provider onboarding: target 2 more to hit 5/mo goal | 🟡 Medium | Recovery Team | March 31 |

---

## 10. Methodology & Data Notes

> ⚠️ **DEMO REPORT:** This report uses illustrative sample data to demonstrate the dashboard format, KPI structure, and reporting cadence defined in the Recovery Project Tracking System requirements (v1.0, 2026-03-21). All case numbers, provider names, dollar amounts, and statistics are representative examples — not live production data.

**Data Sources (when live):**
- Recovery case database (Supabase — `recovery_cases`, `recovery_providers`)
- Communication logs (`recovery_communications`)
- Stage history (`recovery_stage_history`)
- Payer profiles (`recovery_payer_profiles`)

**Report Cadence:** Weekly (Monday AM), with daily overdue alerts.

---

*Every file is a person. Every number on this dashboard represents a provider who healed someone and deserves to be paid. We track with precision because we serve with heart.*

— SAI Recovery 🌱
