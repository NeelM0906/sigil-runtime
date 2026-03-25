# Recovery Operational Dashboard

> Generated: {{generated_date}}
> Period: {{period_start}} — {{period_end}}
> Source: Recovery Task System v1.0

---

## 🔥 Executive Summary

| Metric | Value | Trend |
|--------|-------|-------|
| **Active Tasks** | {{total_active_tasks}} | {{active_trend}} |
| **Pipeline Value** | ${{total_pipeline_value}} | {{pipeline_trend}} |
| **Tasks Completed This Period** | {{tasks_completed}} | {{completed_trend}} |
| **Avg Priority Score** | {{avg_priority_score}}/100 | {{priority_trend}} |
| **SLA Breaches** | {{sla_breaches}} | {{sla_trend}} |

---

## 📊 Pipeline by Task Type

### Agreements
| Stage | Count | Total Value | Avg Days in Stage | SLA Status |
|-------|-------|-------------|-------------------|------------|
| Identification | {{agr_identification_count}} | ${{agr_identification_value}} | {{agr_identification_avg_days}} | {{agr_identification_sla}} |
| Qualification | {{agr_qualification_count}} | ${{agr_qualification_value}} | {{agr_qualification_avg_days}} | {{agr_qualification_sla}} |
| Outreach | {{agr_outreach_count}} | ${{agr_outreach_value}} | {{agr_outreach_avg_days}} | {{agr_outreach_sla}} |
| Proposal | {{agr_proposal_count}} | ${{agr_proposal_value}} | {{agr_proposal_avg_days}} | {{agr_proposal_sla}} |
| Negotiation | {{agr_negotiation_count}} | ${{agr_negotiation_value}} | {{agr_negotiation_avg_days}} | {{agr_negotiation_sla}} |
| Closing | {{agr_closing_count}} | ${{agr_closing_value}} | {{agr_closing_avg_days}} | {{agr_closing_sla}} |

**Win Rate:** {{agreement_win_rate}}% ({{agreements_won}}/{{agreements_closed}} this period)
**Avg Deal Size:** ${{avg_deal_size}}
**Avg Cycle Time (Identification → Won):** {{avg_agreement_cycle_days}} days

### Partnerships
| Stage | Count | Avg Days in Stage |
|-------|-------|-------------------|
| Discovery | {{part_discovery_count}} | {{part_discovery_avg_days}} |
| Relationship Building | {{part_relationship_count}} | {{part_relationship_avg_days}} |
| Value Alignment | {{part_value_count}} | {{part_value_avg_days}} |
| Formalization | {{part_formalization_count}} | {{part_formalization_avg_days}} |
| Activation | {{part_activation_count}} | {{part_activation_avg_days}} |
| Active | {{part_active_count}} | — |

**Partnership Activation Rate:** {{partnership_activation_rate}}% ({{partnerships_activated}}/{{partnerships_started}} this period)
**Active Partnerships:** {{active_partnerships_total}}

### Retention
| Metric | Value |
|--------|-------|
| **Accounts Monitored** | {{accounts_monitored}} |
| **Active Alerts** | {{retention_alerts}} |
| **Critical Churn Risk** | {{critical_churn_count}} |
| **Interventions This Period** | {{interventions_count}} |
| **Retention Rate** | {{retention_rate}}% |
| **Revenue Saved** | ${{revenue_saved}} |
| **Revenue Churned** | ${{revenue_churned}} |

**Health Score Distribution:**
- 🟢 Healthy (80+): {{health_80_plus}} accounts
- 🟡 Moderate (60-79): {{health_60_79}} accounts
- 🟠 At Risk (40-59): {{health_40_59}} accounts
- 🔴 Critical (<40): {{health_below_40}} accounts

### PR
| Campaign | Type | Stage | Coverage Hits | Estimated Reach |
|----------|------|-------|---------------|-----------------|
{{#each pr_campaigns}}
| {{title}} | {{pr_type}} | {{stage}} | {{coverage_count}} | {{reach_estimate}} |
{{/each}}

**Total Coverage This Period:** {{total_coverage_hits}} placements
**Total Estimated Reach:** {{total_estimated_reach}}
**Active Campaigns:** {{active_pr_campaigns}}

---

## 👥 Being Utilization

| Being | Active Tasks | Capacity | Utilization | SLA Breaches | Avg Task Age |
|-------|-------------|----------|-------------|--------------|-------------|
| 🤝 Agreement Maker | {{am_active}} | {{am_capacity}} | {{am_utilization}}% | {{am_sla_breaches}} | {{am_avg_age}}d |
| 🔗 Connector | {{cn_active}} | {{cn_capacity}} | {{cn_utilization}}% | {{cn_sla_breaches}} | {{cn_avg_age}}d |
| 🛡️ Keeper | {{kp_active}} | {{kp_capacity}} | {{kp_utilization}}% | {{kp_sla_breaches}} | {{kp_avg_age}}d |
| 📢 Multiplier | {{mp_active}} | {{mp_capacity}} | {{mp_utilization}}% | {{mp_sla_breaches}} | {{mp_avg_age}}d |

**Total Utilization:** {{total_utilization}}%
**Bottleneck Alert:** {{bottleneck_being}} is at {{bottleneck_pct}}% capacity

---

## ⚠️ Attention Required

### SLA Breaches (Tasks Over Max Days)
{{#each sla_breaches_list}}
- **{{task_title}}** — {{task_type}} / {{stage}} — {{days_over}} days over SLA — Assigned: {{assigned_being}}
{{/each}}

### High Priority Unactioned (Score > 75, No Activity in 48h)
{{#each high_priority_stale}}
- **{{task_title}}** — Priority: {{priority_score}} — Last activity: {{last_activity}}
{{/each}}

### Upcoming Deadlines (Next 7 Days)
{{#each upcoming_deadlines}}
- **{{task_title}}** — Due: {{deadline}} ({{days_remaining}} days) — Stage: {{stage}}
{{/each}}

---

## 📈 Trends (Last 4 Periods)

| Period | Tasks Created | Tasks Completed | Win Rate | Retention Rate | Pipeline Value |
|--------|-------------|-----------------|----------|----------------|----------------|
| {{period_4}} | {{p4_created}} | {{p4_completed}} | {{p4_win_rate}}% | {{p4_retention}}% | ${{p4_pipeline}} |
| {{period_3}} | {{p3_created}} | {{p3_completed}} | {{p3_win_rate}}% | {{p3_retention}}% | ${{p3_pipeline}} |
| {{period_2}} | {{p2_created}} | {{p2_completed}} | {{p2_win_rate}}% | {{p2_retention}}% | ${{p2_pipeline}} |
| {{period_1}} | {{p1_created}} | {{p1_completed}} | {{p1_win_rate}}% | {{p1_retention}}% | ${{p1_pipeline}} |

---

## 🔗 Cross-Sister Integration Points

- **Memory:** Task state changes logged for cross-sister context. Patterns surfaced weekly.
- **Prime:** Double-SLA escalations and closed deals reported. Pipeline health feeds ecosystem status.
- **Scholar:** Win/loss reasons and retention patterns shared for strategic analysis.
- **Forge:** Technical integration requirements from partnerships routed for implementation.

---

*Dashboard template: `recovery-task-system/templates/dashboard_metrics.md`*
*Data queries: Run against RuntimeDB tasks table WHERE project_id = 'recovery-*'*
*Refresh: Weekly (Monday 8am UTC) via automation_triggers.json → weekly_pipeline_digest*
