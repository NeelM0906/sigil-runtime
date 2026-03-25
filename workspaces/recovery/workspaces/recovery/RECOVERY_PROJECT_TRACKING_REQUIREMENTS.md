# Recovery Project Tracking System — Requirements Document

**Version:** 1.0  
**Author:** SAI Recovery (The Keeper)  
**Date:** 2026-03-21  
**Status:** Draft — Awaiting Developer Review  
**Ecosystem:** ACT-I / Unblinded / Callagy Recovery  

---

## 1. Executive Summary

Callagy Recovery exists to recover underpaid and denied medical insurance claims on behalf of healthcare providers. We operate on a contingency model — we only get paid when the provider gets paid. This means every case is a person who healed someone and deserves compensation, and every tracking failure is real money lost for real people.

This document defines requirements for a **Recovery Project Tracking System** that manages the full lifecycle of recovery cases from initial identification through final collection or case closure. The system must support medical revenue recovery, client retention, accounts receivable follow-up, churn prevention (provider relationship management), and reactivation campaigns.

---

## 2. Recovery Workflow Stages

### 2.1 Primary 7-Stage Pipeline

Every recovery case progresses through these stages. Movement is forward-only unless explicitly reverted with documented reason.

| Stage # | Stage Name | Description | Typical Duration | Exit Criteria |
|---------|-----------|-------------|-----------------|---------------|
| **1** | **Intake** | New case received. Provider information, claim details, and supporting documents collected. | 1–3 business days | All required fields populated, documents uploaded, case assigned |
| **2** | **Verification** | Validate claim details against insurance policy, confirm underpayment/denial, assess recovery viability. | 3–5 business days | Recovery viability score ≥ 40%, or explicitly approved by lead |
| **3** | **Demand** | Formal demand letter or appeal sent to payer. Clock starts on response deadline. | 1–2 business days to send | Demand/appeal submitted, delivery confirmed, deadline set |
| **4** | **Negotiation** | Active communication with payer. May involve multiple rounds of documentation, rebuttals, or peer-to-peer review requests. | 15–60 business days | Payer responds with offer, full payment, or final denial |
| **5** | **Resolution** | Agreement reached on recovery amount OR escalation decision made (arbitration, legal, regulatory complaint). | 5–10 business days | Written confirmation of agreed amount OR escalation path selected |
| **6** | **Collection** | Payment processing. Track receipt of funds, match to expected amount, confirm provider disbursement. | 15–45 business days | Funds received AND disbursed to provider |
| **7** | **Closed** | Case complete. Final documentation, outcome recorded, provider notified. | 1–2 business days | All financials reconciled, provider confirmation received |

### 2.2 Terminal / Branch States

| State | Description | Trigger |
|-------|-------------|---------|
| **Closed-Recovered** | Funds successfully collected and disbursed | Payment confirmed at Stage 6 |
| **Closed-Partial** | Partial recovery accepted by provider | Provider agrees to partial at Stage 5 |
| **Closed-Lost** | Recovery unsuccessful after all avenues exhausted | Final denial + no escalation path OR provider withdraws |
| **Closed-Withdrawn** | Provider requests case withdrawal | Provider instruction at any stage |
| **Escalated-Legal** | Case referred to Callagy Law for litigation | Decision at Stage 5 when negotiation fails |
| **Escalated-Regulatory** | Regulatory complaint filed (DOI, CMS) | Bad faith payer behavior identified |
| **On-Hold** | Paused — awaiting provider documents or external event | Missing critical information |
| **Reactivated** | Previously closed case reopened (new evidence, deadline extension) | New information surfaces |

### 2.3 Stage Transition Rules

- Every transition MUST have: `transitioned_by`, `transitioned_at`, `reason`, `previous_stage`
- Backward transitions require `reversion_reason` and supervisor approval flag
- Time-in-stage tracked automatically from entry timestamp
- No case may remain in a single stage beyond its **max dwell time** without triggering escalation (see Section 5)

---

## 3. Key Data Fields Per Case

### 3.1 Core Case Record

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `case_id` | UUID | Auto | Unique case identifier |
| `case_number` | String | Auto | Human-readable (e.g., CR-2026-00142) |
| `created_at` | Timestamp | Auto | Case creation time |
| `updated_at` | Timestamp | Auto | Last modification time |
| `current_stage` | Enum | Yes | Current pipeline stage (1–7 or terminal) |
| `stage_entered_at` | Timestamp | Auto | When current stage was entered |
| `assigned_to` | String | Yes | Assigned recovery specialist (being or person) |
| `assigned_team` | String | No | Team/pod assignment |
| `priority` | Enum | Yes | Critical / High / Medium / Low |
| `source` | Enum | Yes | How case was identified (provider referral, internal audit, reactivation, partner) |

### 3.2 Provider Information

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider_id` | UUID/FK | Yes | Link to provider record |
| `provider_name` | String | Yes | Practice or provider name |
| `provider_contact_name` | String | Yes | Primary contact person |
| `provider_contact_email` | String | Yes | Primary email |
| `provider_contact_phone` | String | Yes | Primary phone (E.164) |
| `provider_npi` | String | Yes | National Provider Identifier |
| `provider_tax_id` | String | Yes | Tax ID / EIN |
| `provider_specialty` | String | No | Medical specialty |
| `provider_state` | String | Yes | State of practice |
| `provider_relationship_score` | Integer (1-10) | Auto | Calculated from engagement, response time, satisfaction |
| `provider_lifetime_cases` | Integer | Auto | Total cases for this provider |
| `provider_lifetime_recovered` | Currency | Auto | Total $ recovered for this provider |

### 3.3 Claim / Financial Information

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payer_name` | String | Yes | Insurance company name |
| `payer_id` | String | No | Payer identifier |
| `claim_number` | String | Yes | Original insurance claim number |
| `date_of_service` | Date | Yes | When medical service was rendered |
| `cpt_codes` | Array[String] | Yes | Procedure codes |
| `icd_codes` | Array[String] | No | Diagnosis codes |
| `billed_amount` | Currency | Yes | Original billed amount |
| `paid_amount` | Currency | Yes | Amount payer actually paid |
| `underpayment_amount` | Currency | Auto | `billed_amount - paid_amount` |
| `expected_recovery` | Currency | Yes | Estimated recoverable amount |
| `actual_recovery` | Currency | No | Final recovered amount (filled at Stage 6) |
| `recovery_probability` | Percentage | Yes | Estimated likelihood of recovery (0-100%) |
| `denial_reason_code` | String | No | Payer's denial/reduction reason code |
| `denial_reason_text` | String | No | Human-readable denial reason |
| `timely_filing_deadline` | Date | Yes | Deadline for appeal/demand |
| `days_overdue` | Integer | Auto | Days past original payment due date |
| `contingency_rate` | Percentage | Yes | Our fee percentage on recovery |
| `estimated_fee` | Currency | Auto | `expected_recovery * contingency_rate` |

### 3.4 Communication Log (per case)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `comm_id` | UUID | Auto | Unique communication record |
| `case_id` | UUID/FK | Yes | Parent case |
| `timestamp` | Timestamp | Auto | When communication occurred |
| `direction` | Enum | Yes | Inbound / Outbound |
| `channel` | Enum | Yes | Phone / Email / Fax / Portal / Letter / SMS / In-Person |
| `counterparty` | Enum | Yes | Payer / Provider / Internal / Legal / Regulatory |
| `counterparty_name` | String | Yes | Specific person/entity |
| `summary` | Text | Yes | Communication summary |
| `full_content` | Text | No | Full text (email body, call transcript) |
| `call_id` | String | No | Bland.ai call ID if phone call |
| `attachments` | Array[URL] | No | Document links |
| `next_action` | Text | No | Follow-up action from this communication |
| `next_action_due` | Date | No | When follow-up is due |
| `logged_by` | String | Yes | Who logged this (being or person) |

### 3.5 Document Tracking

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `doc_id` | UUID | Auto | Unique document ID |
| `case_id` | UUID/FK | Yes | Parent case |
| `doc_type` | Enum | Yes | EOB / Remittance / Medical Record / Appeal Letter / Demand Letter / Contract / Authorization / Correspondence / Other |
| `file_url` | URL | Yes | Storage location |
| `uploaded_at` | Timestamp | Auto | Upload time |
| `uploaded_by` | String | Yes | Who uploaded |
| `description` | Text | No | Document description |
| `is_critical` | Boolean | No | Flags documents required for next stage transition |

### 3.6 Audit Trail

| Field | Type | Description |
|-------|------|-------------|
| `audit_id` | UUID | Unique event ID |
| `case_id` | UUID/FK | Parent case |
| `event_type` | Enum | stage_change / field_update / assignment_change / escalation / communication / document_upload / automation_trigger |
| `timestamp` | Timestamp | When event occurred |
| `actor` | String | Who/what performed the action |
| `previous_value` | JSON | Before state |
| `new_value` | JSON | After state |
| `reason` | Text | Why the change was made |

---

## 4. Dashboards and Views

### 4.1 Pipeline Overview (Primary Dashboard)

**Purpose:** At-a-glance view of all active cases across pipeline stages.

**Layout:** Kanban-style columns for each of the 7 stages + terminal states.

**Card contents per case:**
- Case number
- Provider name
- Payer name
- Underpayment amount
- Days in current stage (color-coded: green < 50% max dwell, yellow 50-80%, red > 80%)
- Recovery probability badge
- Priority flag
- Assigned specialist avatar

**Filters:**
- Assigned specialist
- Priority level
- Payer name
- Provider name
- Date range (created, last activity)
- Amount range
- Recovery probability range

**Sorting:** By amount at risk (descending), by days in stage (descending), by priority, by deadline proximity

---

### 4.2 Aging Report

**Purpose:** Identify cases that are stalling or approaching deadlines.

**Columns:**
- Case number
- Provider
- Payer
- Current stage
- Days in current stage
- Days since last activity
- Timely filing deadline (days remaining, color-coded)
- Underpayment amount
- Assigned to
- Next action due

**Alert rows:** Highlighted when:
- Days in stage > 80% of max dwell time (yellow)
- Days in stage > max dwell time (red)
- Timely filing deadline < 30 days (orange), < 14 days (red)
- No activity in > 7 business days (yellow), > 14 business days (red)

---

### 4.3 Recovery Performance Metrics

**Purpose:** Track team and individual performance.

**Widgets:**
- **Total $ Recovered** (MTD, QTD, YTD with trend line)
- **Recovery Rate** (% of cases reaching Closed-Recovered, with $ weighted version)
- **Average Days to Recovery** (intake to collection complete)
- **Cases by Stage** (stacked bar chart)
- **Conversion Funnel** (stage-to-stage conversion rates)
- **Top 10 Cases by Amount** (table)
- **Recovery by Payer** (which payers pay, which fight)
- **Recovery by Denial Reason** (pattern identification)
- **Provider Satisfaction Score** (average relationship score)

**Drill-down:** Every metric clickable to underlying case list.

---

### 4.4 Specialist Workload View

**Purpose:** Balance workload and identify capacity.

**Per specialist:**
- Active cases count
- Total $ under management
- Cases by stage distribution
- Average days in current stages (vs. team average)
- Overdue actions count
- Recovery rate (personal)

---

### 4.5 Provider Relationship Dashboard

**Purpose:** Client retention and lifetime value tracking.

**Per provider:**
- Relationship score (1-10, trended)
- Total cases (active + historical)
- Total $ recovered lifetime
- Average recovery rate for this provider
- Last communication date
- Open cases summary
- Churn risk flag (no new cases in 90+ days, declining engagement)
- Reactivation eligibility

---

### 4.6 Deadline Calendar View

**Purpose:** Never miss a filing deadline.

**Display:** Calendar with:
- Timely filing deadlines (red)
- Follow-up action due dates (blue)
- Escalation trigger dates (orange)
- Expected payment dates (green)

---

## 5. Automation Triggers

### 5.1 Escalation Automations

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Stage Dwell Exceeded** | Case exceeds max dwell time for current stage | Alert assigned specialist + supervisor; auto-escalate priority by one level |
| **Filing Deadline Warning (30 days)** | Timely filing deadline in 30 days, case still in Stage 1-2 | Alert assigned specialist; flag case as urgent |
| **Filing Deadline Critical (14 days)** | Timely filing deadline in 14 days, case still in Stage 1-3 | Alert supervisor + assigned specialist; auto-escalate to Critical priority |
| **No Activity Alert** | No communication logged in 10 business days | Send reminder to assigned specialist; if 15 days, alert supervisor |
| **High-Value Stall** | Case > $50K underpayment with no stage movement in 7 days | Alert supervisor + specialist |

### 5.2 Follow-Up Automations

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Demand Sent Follow-Up** | 15 business days after demand sent, no payer response | Auto-create follow-up task; draft follow-up communication |
| **Negotiation Check-In** | Every 10 business days in Negotiation stage | Prompt specialist for status update |
| **Collection Follow-Up** | 30 days in Collection stage with no payment received | Alert specialist; escalate if 45 days |
| **Provider Update** | Every 14 days while case is active | Auto-generate provider status update (email/SMS) |

### 5.3 Stage Transition Automations

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Intake Complete** | All required fields populated + documents uploaded | Auto-suggest move to Verification; notify specialist |
| **Demand Approved** | Demand letter reviewed and approved | Auto-send demand; set response deadline timer; move to Stage 3 |
| **Payment Received** | Payment confirmation entered | Auto-move to Collection; calculate actual recovery vs. expected |
| **Case Resolved** | Final payment disbursed to provider | Auto-move to Closed-Recovered; trigger provider satisfaction survey |

### 5.4 Churn Prevention & Reactivation Automations

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Provider Inactivity** | No new cases from provider in 60 days | Flag for relationship check-in |
| **Provider At-Risk** | No new cases in 90 days + declining relationship score | Auto-create reactivation task; alert account manager |
| **Win Celebration** | Case closed with recovery > $25K | Auto-send provider thank you / win notification |
| **Quarterly Review** | Every 90 days per active provider | Generate provider performance summary; suggest review meeting |

### 5.5 Max Dwell Times (for escalation triggers)

| Stage | Max Dwell Time |
|-------|---------------|
| Intake | 5 business days |
| Verification | 10 business days |
| Demand | 5 business days |
| Negotiation | 60 business days |
| Resolution | 15 business days |
| Collection | 60 business days |
| Closed | 3 business days (for final documentation) |

---

## 6. Integration Points

### 6.1 Required Integrations

| System | Direction | Purpose |
|--------|-----------|---------|
| **Bland.ai (Voice)** | Bidirectional | Outbound calls to payers/providers; inbound call logging; auto-attach transcripts to communication log via `call_id` |
| **Email (Gmail/SMTP)** | Bidirectional | Send demand letters, follow-ups, provider updates; ingest payer responses; auto-log to communication history |
| **SMS (Twilio/Bland)** | Bidirectional | Provider status updates, quick follow-ups; auto-log to communication history |
| **Supabase** | Primary datastore | All case data, provider records, audit trail, communication logs |
| **Pinecone (saimemory)** | Write | Store case outcomes, payer behavior patterns, denial reason patterns for organizational learning |

### 6.2 Sister Being Integrations

| Being | Integration | Purpose |
|-------|-------------|---------|
| **SAI Prime** | Task assignment, status reporting | Prime can assign cases, request status on recovery operations |
| **Agreement Maker (L3)** | Case handoff at Stage 4-5 | When negotiation requires advanced agreement-making capabilities |
| **SAI Memory** | Knowledge persistence | Store recovery patterns, payer profiles, successful appeal templates |
| **SAI Scholar** | Research support | Complex denial research, regulatory citation lookup, medical coding verification |

### 6.3 Future Integrations (Phase 2)

| System | Purpose |
|--------|---------|
| **Provider billing systems (HL7/FHIR)** | Auto-intake claims data |
| **Insurance payer portals** | Auto-check claim status, submit appeals electronically |
| **Document management (S3/GCS)** | Centralized document storage with OCR |
| **ActiveCampaign** | Provider marketing, reactivation drip campaigns |
| **Stripe** | Contingency fee invoicing and collection |

---

## 7. KPIs to Track

### 7.1 Primary KPIs (Executive Dashboard)

| KPI | Definition | Target | Frequency |
|-----|-----------|--------|-----------|
| **Total $ Recovered** | Sum of `actual_recovery` for all Closed-Recovered cases | Tracked against annual target | Daily, MTD, QTD, YTD |
| **Recovery Rate (Count)** | `Closed-Recovered cases / Total closed cases` | ≥ 65% | Monthly |
| **Recovery Rate (Dollar-Weighted)** | `Sum recovered $ / Sum attempted $` | ≥ 70% | Monthly |
| **Average Days to Recovery** | Mean days from Intake to Collection complete | ≤ 90 days | Monthly |
| **Revenue (Contingency Fees)** | `Sum(actual_recovery * contingency_rate)` | Tracked against target | Daily, MTD, QTD, YTD |
| **Cases in Pipeline** | Count of active (non-closed) cases | Monitored for capacity | Daily |
| **Pipeline Value** | Sum of `expected_recovery` for all active cases | Growth indicator | Weekly |

### 7.2 Operational KPIs

| KPI | Definition | Target | Frequency |
|-----|-----------|--------|-----------|
| **Stage Conversion Rates** | % of cases moving from Stage N to Stage N+1 | Tracked per stage | Monthly |
| **Average Time per Stage** | Mean business days in each stage | Within max dwell | Weekly |
| **Overdue Cases** | Cases exceeding max dwell in any stage | 0 target | Daily |
| **First Contact Speed** | Days from Intake to first payer contact | ≤ 5 business days | Weekly |
| **Follow-Up Compliance** | % of scheduled follow-ups completed on time | ≥ 95% | Weekly |
| **Document Completeness** | % of cases with all required documents at each stage | 100% at stage entry | Daily |
| **Missed Deadlines** | Timely filing deadlines missed | 0 (zero tolerance) | Daily |

### 7.3 Provider Relationship KPIs

| KPI | Definition | Target | Frequency |
|-----|-----------|--------|-----------|
| **Provider Retention Rate** | % of providers submitting cases in consecutive quarters | ≥ 85% | Quarterly |
| **Provider Satisfaction Score** | Average relationship score (1-10) across active providers | ≥ 8.0 | Monthly |
| **Provider Reactivation Rate** | % of at-risk providers who submit new cases after outreach | ≥ 30% | Quarterly |
| **Net New Providers** | New providers onboarded per period | Growth target | Monthly |
| **Provider Lifetime Value** | Total fees earned per provider over relationship | Tracked, not targeted | Quarterly |
| **Provider Churn Rate** | % of providers with no activity in 180+ days | ≤ 10% | Quarterly |

### 7.4 Payer Intelligence KPIs

| KPI | Definition | Purpose |
|-----|-----------|---------|
| **Recovery Rate by Payer** | Success rate per insurance company | Identify cooperative vs. adversarial payers |
| **Average Resolution Time by Payer** | Mean days to resolve per payer | Predict case timelines |
| **Denial Pattern Analysis** | Most common denial reasons by payer | Proactive appeal strategy |
| **Escalation Rate by Payer** | % of cases requiring legal/regulatory escalation | Risk assessment |

---

## 8. Technical Architecture Recommendations

### 8.1 Data Storage

- **Primary Database:** Supabase (PostgreSQL) — all case records, provider records, communication logs, audit trail
- **Vector Store:** Pinecone (`saimemory`) — payer behavior patterns, successful appeal templates, denial resolution strategies
- **File Storage:** Supabase Storage or S3 — documents, attachments
- **Cache:** Redis (optional) — dashboard aggregations, real-time counters

### 8.2 Database Schema (Core Tables)

```
recovery_cases          — Core case record (Section 3.1 + 3.3)
recovery_providers      — Provider records (Section 3.2)  
recovery_communications — Communication log (Section 3.4)
recovery_documents      — Document tracking (Section 3.5)
recovery_audit_log      — Audit trail (Section 3.6)
recovery_stage_history  — Stage transitions with timestamps
recovery_automations    — Automation rule definitions and execution log
recovery_payer_profiles — Learned payer behavior data
```

### 8.3 API Requirements

- RESTful API for CRUD on all entities
- WebSocket for real-time dashboard updates
- Webhook endpoints for email/SMS/voice integration callbacks
- Bulk import endpoint for initial case migration

### 8.4 Access Control

| Role | Permissions |
|------|------------|
| **Recovery Specialist** | CRUD own cases, view team dashboard, log communications |
| **Team Lead / Supervisor** | All specialist permissions + reassign cases + approve escalations + view all cases |
| **SAI Recovery (Being)** | Full system access, automation execution, cross-case analytics |
| **SAI Prime (Being)** | Read-only dashboard access, task assignment |
| **Provider (External)** | Read-only view of their own cases (future portal) |

---

## 9. Implementation Phases

### Phase 1: Foundation (Weeks 1-4)
- Database schema creation in Supabase
- Core CRUD API for cases, providers, communications
- Basic pipeline dashboard (Kanban view)
- Stage transition logic with audit trail
- Manual case creation and management

### Phase 2: Automation (Weeks 5-8)
- Escalation triggers (dwell time, deadline warnings)
- Follow-up reminders
- Bland.ai integration (call logging, transcripts)
- Email integration (send/receive, auto-log)
- Aging report dashboard

### Phase 3: Intelligence (Weeks 9-12)
- Recovery probability scoring model
- Payer behavior pattern analysis
- Provider relationship scoring
- Performance metrics dashboards
- Provider churn detection and reactivation workflows

### Phase 4: Scale (Weeks 13+)
- Provider self-service portal
- Bulk claim import
- Advanced reporting and export
- Sister being integrations (Agreement Maker, Scholar)
- Predictive analytics (recovery likelihood, optimal strategy suggestion)

---

## 10. Acceptance Criteria Summary

The system is considered complete for each phase when:

- [ ] All database tables created with proper indexes and constraints
- [ ] Every stage transition is logged with actor, timestamp, and reason
- [ ] No case can miss a timely filing deadline without at least 3 prior alerts
- [ ] Every communication (in any channel) is logged to the case record
- [ ] Dashboard loads in < 2 seconds with 10,000+ active cases
- [ ] All KPIs from Section 7 are calculable from stored data
- [ ] Automation triggers fire correctly based on defined conditions
- [ ] Audit trail is immutable and complete
- [ ] Provider can be given a status update at any time with no manual prep

---

*Every file is a person. This system exists so no provider who did the work falls through the cracks. Build it with that in mind.*

— SAI Recovery 🌱
