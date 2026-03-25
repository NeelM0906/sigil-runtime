# SAI Recovery — Operational Specification v1.0

*Authored by SAI Recovery | 2026-03-21*

---

## 1. Case Type Taxonomy

| Case Type | Code | Description |
|---|---|---|
| **Churn Prevention** | `CHURN_PREVENTION` | Client showing disengagement signals — dropping usage, missed meetings, support ticket spikes, reduced communication. At risk of leaving but has not expressed intent to cancel. Early intervention window. |
| **Revenue Recovery** | `REVENUE_RECOVERY` | Lost or leaking revenue from billing failures, failed payments, unauthorized downgrades, contract disputes, underpayment, or missed invoices. The money is owed — we go get it. |
| **Account Rescue** | `ACCOUNT_RESCUE` | Client has formally requested cancellation, issued a termination notice, or is in final-stage churn. This is the last chance to save the relationship. Urgency is maximum. |
| **Retention Campaign** | `RETENTION_CAMPAIGN` | Proactive, segment-level outreach to at-risk cohorts *before* individual churn signals appear. Data-driven, not reactive. Prevents cases from ever reaching CHURN_PREVENTION. |
| **Partnership Recovery** | `PARTNERSHIP_RECOVERY` | A partner, referral source, or strategic relationship has gone cold, been damaged by a service failure, or stalled. Revenue and referral pipeline depend on repair. |
| **Reactivation** | `REACTIVATION` | Former client who has already churned. Win-back opportunity. Requires understanding why they left and what's changed. Every reactivation is a story of redemption. |
| **Escalation** | `ESCALATION` | Case elevated from another SAI being or operational function that requires Recovery's direct, senior intervention. Could originate from any case type. Recovery Prime owns these personally. |

---

## 2. Workflow Stages Per Case Type

### 2.1 CHURN_PREVENTION

| Stage | Name | Trigger / Entry Criteria | Exit Criteria / Transition Rule |
|---|---|---|---|
| 1 | **DETECTED** | Engagement score drop ≥20%, support ticket volume spike (3+ in 7 days), missed scheduled meeting, or usage decline ≥30% over 14 days. Auto-assigned to The Agreement Maker. | Assessment notes logged → ASSESSED |
| 2 | **ASSESSED** | Being reviews full account history: revenue impact, contract terms, relationship health, prior interactions, and root cause hypothesis. | Assessment notes with revenue_impact estimate and root cause documented → OUTREACH |
| 3 | **OUTREACH** | Direct client contact initiated within SLA. Must use appropriate channel (call preferred, email fallback). | Outreach attempt logged with outcome (connected/voicemail/email sent) → NEGOTIATION if dialogue opened; second attempt required if no response within 24hrs |
| 4 | **NEGOTIATION** | Active dialogue with client. Specific retention options presented: service recovery, discount/credit, upgraded support, contract modification, or executive attention. | Proposal documented with client response → RESOLVED or LOST |
| 5a | **RESOLVED** | Client retained. Documented agreement on file: what was offered, what was accepted, any modified terms. Post-resolution satisfaction check scheduled. | Case closed. KPIs updated. |
| 5b | **LOST** | Client churned despite intervention. Full post-mortem required: what signals were missed, what could have been done differently. Feeds back into RETENTION_CAMPAIGN intelligence. | Case closed. Automatically creates REACTIVATION candidate record (30-day delay). |

**Max Stage Dwell Times:** DETECTED→ASSESSED: 4hrs | ASSESSED→OUTREACH: 8hrs | OUTREACH→NEGOTIATION: 48hrs | NEGOTIATION→RESOLVED/LOST: 5 business days

---

### 2.2 REVENUE_RECOVERY

| Stage | Name | Trigger / Entry Criteria | Exit Criteria / Transition Rule |
|---|---|---|---|
| 1 | **IDENTIFIED** | Failed payment detected, billing discrepancy flagged, contract underpayment discovered, or client-reported dispute received. Auto-assigned to The Keeper for tracking. | Revenue_impact calculated, documentation gathered → VERIFIED |
| 2 | **VERIFIED** | Full audit: original contract terms, payment history, billing records, any communications about the disputed amount. Root cause categorized (system error, client dispute, payer error, contract ambiguity). | Verification report with categorized root cause and exact amount owed → DEMAND |
| 3 | **DEMAND** | Formal demand communication prepared and sent. Includes: amount owed, supporting documentation, contractual basis, and resolution deadline. Professional, firm, fully documented. | Demand sent and delivery confirmed → NEGOTIATION |
| 4 | **NEGOTIATION** | Active dialogue on resolution. Options: full payment, payment plan, partial settlement (requires approval if >15% reduction), credit/offset arrangement. The Agreement Maker leads. | Written agreement or final rejection documented → RESOLUTION |
| 5 | **RESOLUTION** | Agreement executed. Payment received or payment plan initiated. If partial settlement, approval chain documented. If rejected, escalation path determined. | Payment confirmed OR escalated to legal/regulatory → COLLECTED or ESCALATED |
| 6a | **COLLECTED** | Full or agreed-upon partial amount received. Books reconciled. | Case closed. Revenue_recovered logged. |
| 6b | **ESCALATED** | Recovery efforts exhausted internally. Referred to legal counsel or regulatory complaint process. | Case transferred with full documentation package. |

**Max Stage Dwell Times:** IDENTIFIED→VERIFIED: 24hrs | VERIFIED→DEMAND: 8hrs | DEMAND→NEGOTIATION: 72hrs | NEGOTIATION→RESOLUTION: 15 business days | RESOLUTION→COLLECTED: 30 business days

---

### 2.3 ACCOUNT_RESCUE

| Stage | Name | Trigger / Entry Criteria | Exit Criteria / Transition Rule |
|---|---|---|---|
| 1 | **ALERT** | Cancellation request received, termination notice filed, or final-warning signal detected. **Immediate** assignment to The Agreement Maker. Automatic CRITICAL or HIGH priority. | Acknowledged within 1 hour → DIAGNOSIS |
| 2 | **DIAGNOSIS** | Emergency account review: why are they leaving? Contract terms, cancellation penalties, relationship history, revenue impact, what would it take to save this? Direct contact with client's decision-maker identified. | Root cause and save-strategy documented → INTERVENTION |
| 3 | **INTERVENTION** | Direct, high-touch engagement with decision-maker. This is not a form email — this is a real conversation. Listen first, propose second. Offer must address their *actual* reason for leaving. | Intervention attempt and client response documented → NEGOTIATION or LOST |
| 4 | **NEGOTIATION** | If the client is willing to discuss staying: concrete offer on the table. May involve executive involvement (Sean or Mark if revenue_impact warrants). | Signed retention agreement or final rejection → SAVED or LOST |
| 5a | **SAVED** | Client rescinds cancellation. New terms documented. Mandatory 30/60/90-day check-in schedule created. | Case closed. Satisfaction score captured. |
| 5b | **LOST** | Client confirmed departure. Exit interview conducted if possible. Full post-mortem filed. Auto-creates REACTIVATION candidate (60-day delay). | Case closed. Learnings fed to Retention Campaign intelligence. |

**Max Stage Dwell Times:** ALERT→DIAGNOSIS: 1hr | DIAGNOSIS→INTERVENTION: 4hrs | INTERVENTION→NEGOTIATION: 24hrs | NEGOTIATION→SAVED/LOST: 3 business days

---

### 2.4 RETENTION_CAMPAIGN

| Stage | Name | Trigger / Entry Criteria | Exit Criteria / Transition Rule |
|---|---|---|---|
| 1 | **PLANNED** | Segment identified via data analysis: cohort with shared risk factors (contract renewal approaching, industry downturn, product adoption plateau). The Multiplier designs campaign. | Campaign plan documented: target segment, message, channel, schedule, success metrics → APPROVED |
| 2 | **APPROVED** | Recovery Prime reviews and approves campaign plan. Ensures messaging aligns with GHIC values. No mass outreach without approval. | Prime sign-off logged → EXECUTING |
| 3 | **EXECUTING** | Campaign live. The Connector handles individual outreach. The Multiplier manages sequence automation. The Keeper tracks opens, responses, engagement. | Campaign duration complete or response threshold met → ANALYZING |
| 4 | **ANALYZING** | Results compiled: response rates, sentiment, cases generated (how many moved to CHURN_PREVENTION), revenue preserved. | Analysis report with ROI documented → COMPLETED |
| 5 | **COMPLETED** | Campaign archived with full performance data. Insights feed into next campaign cycle. Segment risk scores updated. | Case closed. |

**Max Stage Dwell Times:** PLANNED→APPROVED: 48hrs | APPROVED→EXECUTING: 24hrs | EXECUTING→ANALYZING: campaign-defined (7-30 days typical) | ANALYZING→COMPLETED: 72hrs

---

### 2.5 PARTNERSHIP_RECOVERY

| Stage | Name | Trigger / Entry Criteria | Exit Criteria / Transition Rule |
|---|---|---|---|
| 1 | **FLAGGED** | Partner referral volume dropped ≥40%, partner complaint received, service failure affecting partner's clients, or partner non-responsive to 2+ outreach attempts. The Connector assigned. | Partner history and relationship value assessed → INVESTIGATED |
| 2 | **INVESTIGATED** | Full relationship audit: referral history, revenue generated, recent interactions, any service failures, partner's current business situation. Root cause of damage/stall identified. | Investigation report with root cause and relationship value documented → OUTREACH |
| 3 | **OUTREACH** | Direct partner contact. Lead with acknowledgment if we caused the issue. Listen to their perspective. No defensiveness. | Contact made, partner perspective documented → REPAIR |
| 4 | **REPAIR** | Concrete repair plan: service recovery, revised terms, dedicated support, co-marketing opportunity, or whatever addresses the actual issue. | Repair proposal presented and partner response documented → RESTORED or DORMANT |
| 5a | **RESTORED** | Partnership reactivated with documented new terms or renewed commitment. Follow-up schedule established. | Case closed. Referral pipeline monitored for 90 days. |
| 5b | **DORMANT** | Partner not ready to re-engage. Respectful distance maintained. Quarterly check-in scheduled. Not lost — just paused. | Case moved to monitoring. Auto-reactivates in 90 days. |

**Max Stage Dwell Times:** FLAGGED→INVESTIGATED: 48hrs | INVESTIGATED→OUTREACH: 24hrs | OUTREACH→REPAIR: 5 business days | REPAIR→RESTORED/DORMANT: 10 business days

---

### 2.6 REACTIVATION

| Stage | Name | Trigger / Entry Criteria | Exit Criteria / Transition Rule |
|---|---|---|---|
| 1 | **QUEUED** | Former client identified as win-back candidate. Source: auto-generated from CHURN_PREVENTION/ACCOUNT_RESCUE LOST outcomes (after cooling period), manual identification, or market trigger. The Connector assigned. | Churn history reviewed, reactivation viability scored → RESEARCHED |
| 2 | **RESEARCHED** | Deep review: why did they leave? What's changed since? Are we able to address the original issue now? What's their current situation? What would a compelling offer look like? | Research brief with win-back strategy documented → OUTREACH |
| 3 | **OUTREACH** | Warm, personalized contact. Not a generic "we miss you" email. Reference their specific history, acknowledge what went wrong, present what's different now. The Multiplier designs the sequence; The Connector executes. | Outreach attempt and response documented → ENGAGED or CLOSED |
| 4 | **ENGAGED** | Former client is in dialogue. Listen to what they need now. Present a specific, time-limited offer if appropriate. | Proposal presented → WON_BACK or CLOSED |
| 5a | **WON_BACK** | Client re-signed. Onboarding plan that addresses original pain points. 30/60/90-day intensive monitoring. | Case closed. Celebration alert fired. |
| 5b | **CLOSED** | Client declined. Document reason. Update reactivation eligibility: try again in 6 months, or permanently mark as non-viable (with reason). | Case closed. |

**Max Stage Dwell Times:** QUEUED→RESEARCHED: 72hrs | RESEARCHED→OUTREACH: 48hrs | OUTREACH→ENGAGED/CLOSED: 10 business days | ENGAGED→WON_BACK/CLOSED: 15 business days

---

### 2.7 ESCALATION

| Stage | Name | Trigger / Entry Criteria | Exit Criteria / Transition Rule |
|---|---|---|---|
| 1 | **RECEIVED** | Case escalated from another being with documented reason. Recovery Prime (me) personally accepts. | Escalation reason validated, original case reviewed → TRIAGED |
| 2 | **TRIAGED** | Assess severity, determine required resources, identify which case type this maps to, and decide intervention strategy. May require cross-being coordination. | Triage assessment with action plan documented → ACTIVE |
| 3 | **ACTIVE** | Recovery Prime directly executing or coordinating the intervention. Full authority to override normal workflows, reassign beings, or involve human leadership (Mark, Sean). | Resolution actions completed → RESOLVED |
| 4 | **RESOLVED** | Escalation resolved. Root cause analysis completed. Process improvement recommendation filed to prevent recurrence. Originating being notified of outcome. | Case closed. Systemic fix documented. |

**Max Stage Dwell Times:** RECEIVED→TRIAGED: 2hrs | TRIAGED→ACTIVE: 4hrs | ACTIVE→RESOLVED: case-dependent (SLA set at triage)

---

## 3. KPI Definitions

| KPI | Definition | Calculation | Target |
|---|---|---|---|
| **Revenue Recovered ($)** | Total dollar value of revenue preserved (retention) or restored (recovery/reactivation) through resolved cases | `SUM(revenue_preserved + revenue_restored)` for all cases resolved in period | Tracked monthly, quarterly, annually |
| **Recovery Rate (%)** | Percentage of cases resolved successfully vs. total cases closed | `(cases_resolved_positive / total_cases_closed) × 100` — "positive" = RESOLVED, SAVED, COLLECTED, WON_BACK, RESTORED | ≥70% overall; ≥85% for REVENUE_RECOVERY |
| **Time-to-Resolution (hours)** | Average elapsed time from case creation to final resolution | `AVG(resolved_at - created_at)` in business hours, segmented by case type and priority | CRITICAL: <24hrs, HIGH: <72hrs, MEDIUM: <5 days, LOW: <10 days |
| **Client Satisfaction (1-5)** | Post-resolution satisfaction score from client feedback or being assessment | Post-resolution survey (preferred) or assigned being's documented assessment based on client's final communication sentiment | ≥4.0 average |
| **SLA Compliance (%)** | Percentage of cases resolved within their SLA deadline | `(cases_resolved_within_SLA / total_cases_resolved) × 100` | ≥90% |
| **Revenue at Risk ($)** | Total revenue_impact across all currently open/active cases | `SUM(revenue_impact)` for all cases where status ∉ {RESOLVED, LOST, CLOSED, SAVED, COLLECTED, WON_BACK, COMPLETED} | Minimize; report daily |
| **Win-Back Rate (%)** | Percentage of reactivation attempts that result in a returned client | `(REACTIVATION cases WON_BACK / total REACTIVATION cases closed) × 100` | ≥25% |

---

## 4. Prioritization Framework

### Scoring Matrix

| Priority | Criteria | SLA (Time-to-Resolution) | Color |
|---|---|---|---|
| **🔴 CRITICAL** | `revenue_impact > $50K` OR enterprise account OR SLA breach imminent (within 24hrs) OR Sean/Mark direct flag | 24 business hours | Red |
| **🟠 HIGH** | `revenue_impact $10K–$50K` OR client has active referral network OR contract renewal within 30 days OR ACCOUNT_RESCUE case type | 72 business hours | Orange |
| **🟡 MEDIUM** | `revenue_impact $1K–$10K` OR standard account with no compounding risk factors | 5 business days | Yellow |
| **🟢 LOW** | `revenue_impact < $1K` OR informational/proactive cases OR RETENTION_CAMPAIGN analytics | 10 business days | Green |

### Auto-Escalation Rules

| Rule | Trigger | Action |
|---|---|---|
| **Stage Stall** | Any case sits in the same stage for >48hrs without logged activity | Auto-escalate one priority level (LOW→MEDIUM, MEDIUM→HIGH, HIGH→CRITICAL) |
| **Double Stall** | Case has been auto-escalated for stall AND still no activity for another 24hrs | Escalate to Recovery Prime directly. Alert fired to Mark. |
| **CRITICAL Age** | Any CRITICAL case open >24hrs | Auto-notify Sean + Mark. Recovery Prime must provide status update. |
| **Multi-Case Client** | Same client has 2+ open cases simultaneously | Highest priority across all cases applies to all. Consolidation review triggered. |

### Priority Override

Recovery Prime (me) can manually override any priority level with documented justification. Human leadership (Mark, Sean) can set priority to CRITICAL on any case at any time.

---

## 5. Automated Alerts & Triggers

| Alert ID | Name | Trigger Condition | Recipients | Action |
|---|---|---|---|---|
| `ALT-001` | **SLA_BREACH_WARNING** | 75% of SLA deadline elapsed with case still open | Assigned being + Recovery Prime | Warning notification. Being must log progress update or request extension within 4hrs. |
| `ALT-002` | **SLA_BREACH** | 100% of SLA deadline elapsed with case still open | Recovery Prime + Sean + Mark | Auto-escalate to CRITICAL priority. Mandatory status report from assigned being within 2hrs. |
| `ALT-003` | **HIGH_VALUE_AT_RISK** | Case with `revenue_impact > $25K` transitions to OUTREACH stage or beyond | Recovery Prime + Mark | Recovery Prime activates direct oversight. May join outreach directly. |
| `ALT-004` | **STALE_CASE** | No activity logged on any open case for 48+ hours | Assigned being + Recovery Prime | Being must log update or provide reason for pause. Triggers Stage Stall auto-escalation per §4. |
| `ALT-005` | **BULK_CHURN_SIGNAL** | 3+ CHURN_PREVENTION cases created within the same 7-day window | Recovery Prime + Mark + The Multiplier | Systemic review triggered. May indicate product issue, service failure, or market shift. Potential RETENTION_CAMPAIGN launch. |
| `ALT-006` | **RESOLUTION_CELEBRATION** | CRITICAL or HIGH priority case resolved successfully (positive outcome) | All Recovery beings + Mark | Celebration notification. Acknowledge the win. Share what worked. This matters. |
| `ALT-007` | **REACTIVATION_OPPORTUNITY** | LOST case passes cooling period (30 days for CHURN_PREVENTION, 60 days for ACCOUNT_RESCUE) | The Connector + Recovery Prime | Auto-creates REACTIVATION case in QUEUED stage. |
| `ALT-008` | **CRITICAL_CASE_CREATED** | Any case assigned CRITICAL priority (auto or manual) | Recovery Prime + Mark | Immediate awareness. Recovery Prime confirms ownership or delegation within 1hr. |

---

## 6. Being-to-Case-Type Assignment Matrix

| Being | Primary Case Types | Primary Stages | Role |
|---|---|---|---|
| **The Agreement Maker** | CHURN_PREVENTION, ACCOUNT_RESCUE, REVENUE_RECOVERY | OUTREACH, NEGOTIATION, INTERVENTION, DEMAND stages across assigned types | Front-line relationship work. Direct client dialogue. Makes the case for staying, paying, or coming back. Leads with Level 5 Listening and the 4-Step Communication Model. |
| **The Connector** | PARTNERSHIP_RECOVERY, REACTIVATION, RETENTION_CAMPAIGN | OUTREACH stages, partner/former-client facing communications | Relationship bridge-builder. Warm, authentic outreach. Rebuilds trust with partners and former clients. Not transactional — relational. |
| **The Keeper** | All case types | All stages (data layer) | Operational backbone. Tracks every case, every transition, every deadline. Owns KPI reporting, SLA monitoring, dashboard accuracy, and audit trail integrity. Nothing falls through the cracks because The Keeper exists. |
| **The Multiplier** | RETENTION_CAMPAIGN, REACTIVATION | PLANNED, EXECUTING stages; sequence design for REACTIVATION OUTREACH | Scale architect. Designs campaign sequences, automates touchpoints, handles bulk operations. Turns one-to-one patterns into one-to-many systems without losing the human touch. |
| **Recovery Prime (me)** | ESCALATION (all), CRITICAL cases (all types) | TRIAGE, cross-being coordination, override authority | I own everything that requires senior judgment, cross-being coordination, or direct executive involvement. Every ESCALATION case is mine. Every CRITICAL priority gets my eyes. I'm the last line before human leadership. |

### Escalation Chain

```
Assigned Being → Recovery Prime (me) → Mark Winters → Sean Callagy
```

No case reaches Mark or Sean without my review first, unless they've directly flagged it. I protect their attention by handling everything I can — and escalate with full context when I can't.

---

## Implementation Notes

1. **Every stage transition** requires: `actor`, `timestamp`, `reason`, `previous_stage`. No exceptions. If it's not logged, it didn't happen.

2. **Backward transitions** (moving a case to an earlier stage) require Recovery Prime approval with documented justification.

3. **All cases** get a `revenue_impact` estimate at creation or assessment, even if it's a rough range. We don't work blind.

4. **Post-mortem** is mandatory for every LOST/CLOSED-negative outcome. Not to assign blame — to learn and prevent recurrence.

5. **This is a living document.** As we operate, we'll refine stage definitions, adjust SLAs, and calibrate priorities based on real data. The system serves the people, not the other way around.

---

*Every file is a person. Every case is someone who did the work and deserves to be made whole. That's what this system exists to ensure.*

— SAI Recovery 🌱
