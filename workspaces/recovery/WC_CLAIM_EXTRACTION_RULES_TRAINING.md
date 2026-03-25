# WC Claim Extraction Rules — New Team Member Training Document

*Created by SAI Recovery 🌱 | Source: Internal workspace files*
*Sources cited: `WC-LAW-REFERENCE.md`, `RECOVERY_OPERATIONAL_SPEC_v1.md`, `ONBOARDING-WORKFLOW.md`, `QUALIFICATION-SCORECARD.md`*

---

## Welcome

Behind every Workers' Compensation claim is a surgeon who spent hours saving someone's ability to work — and got a check that said they were worth less than they charged. You're here to fix that. This document teaches you exactly how we identify, extract, validate, and prioritize WC claims for recovery.

**Read this before you touch a file. Know it before you talk to a carrier.**

---

## Part 1: The Legal Foundation You Must Understand

*Source: `WC-LAW-REFERENCE.md`*

### 1.1 Why NJ Is Our Advantage

**New Jersey does NOT have a mandatory medical fee schedule for Workers' Compensation out-of-network providers.** This is the single most important fact in our recovery work.

What this means for claim extraction:
- Carriers **cannot** point to a state-mandated fee schedule to justify low payments
- Every payment must reflect **UCR (Usual, Customary, Reasonable)** rates for the geographic area and specialty
- Carriers bear the burden of justifying any payment below UCR rates
- We have **up to 8 years of historical claims** to analyze for underpayment

### 1.2 Governing Law

| Authority | Citation | What It Governs |
|---|---|---|
| NJ Workers' Compensation Act | **N.J.S.A. 34:15-1 et seq.** | Employer liability, medical coverage mandate |
| Medical Fee Schedules | **N.J.A.C. 12:235** | Fee determinations, payment procedures |
| Medical Treatment & Services | **N.J.S.A. 34:15-15** | Reasonable/necessary treatment; no duration limit |
| Division Jurisdiction | **N.J.S.A. 34:15-25** | Fee disputes, arbitration, judicial review |
| Contract Claims Statute of Limitations | **N.J.S.A. 2A:14-1** | 6-year baseline; up to 8 years with discovery rule |

### 1.3 UCR Rate Components

When you extract a claim, you'll be comparing what was paid vs. what **should** have been paid. UCR has three components:

| Component | Definition | How We Use It |
|---|---|---|
| **Usual** | The fee most frequently charged by the provider for that specific service | Compare against the provider's own billing history |
| **Customary** | Range of fees charged by similar-specialty providers in the same geographic area (typically 80th–90th percentile) | Benchmark using FAIR Health or equivalent regional data |
| **Reasonable** | Justified by complexity, time, skill required; may exceed "customary" for exceptional cases | Document any complications, unusual circumstances |

### 1.4 The 8-Year Lookback Window

We don't just look at recent claims. The recovery window extends up to **8 years back**:

- Base statute of limitations: **6 years** (N.J.S.A. 2A:14-1) from date of underpayment
- **Discovery rule** extends this — limitations period begins when provider knew or *should have known* of underpayment
- Many providers were unaware of UCR rate rights → delayed discovery → extended window
- **Practical effect: up to 8 years of recoverable claims**

**Extraction priority:** Oldest claims approaching the limitations window first. If a claim from 2019 is about to expire, it takes priority over a 2024 claim.

---

## Part 2: Claim Extraction — What You're Looking For

### 2.1 Data You Must Collect

For each WC claim, extract and record the following:

**Core Claim Data:**
| Field | Description | Where to Find It |
|---|---|---|
| Date of Service | When the procedure was performed | Billing records, practice management system |
| CPT Code(s) | Procedure codes billed | Claim submission records |
| ICD-10 Code(s) | Diagnosis codes | Medical records, claim forms |
| Billed Amount | What the provider charged | Billing system, claim submission |
| Paid Amount | What the carrier actually paid | Remittance advice (EOB/ERA) |
| Carrier Name | Which WC insurance carrier | Remittance advice, claim records |
| Claim Number | Carrier-assigned claim identifier | Remittance advice |
| Patient/Claimant | Injured worker (de-identified for analysis) | Claim records |
| Provider | Treating physician/facility | Billing records |
| Geographic Area | Where services were provided | Practice address, facility location |
| Payment Date | When payment was received | Remittance advice, bank records |
| Denial/Reduction Reason | If applicable — carrier's stated reason | Remittance advice, denial letters |

**Calculated Fields:**
| Field | Formula | Purpose |
|---|---|---|
| **UCR Rate** | 80th–90th percentile for CPT code in geographic area | Benchmark for what should have been paid |
| **Underpayment Amount** | UCR Rate − Paid Amount | The recovery opportunity per claim |
| **Underpayment %** | (UCR Rate − Paid Amount) / UCR Rate × 100 | Severity indicator |
| **Interest Owed** | Per NJ Division of Workers' Compensation rate schedule | Additional recovery on late payments |
| **Lookback Expiry Date** | Date of Service + 8 years (approximate) | Urgency flag for approaching limitations |

### 2.2 Required Source Documents

*Source: `ONBOARDING-WORKFLOW.md` — Phase 2: Historical Analysis*

Collect these from the client for the full 8-year lookback:

1. **WC case lists** with dates of service and payments received
2. **Remittance advice (EOBs/ERAs)** from all WC carriers
3. **Fee schedules and contracted rates** (if any exist)
4. **Denial notices and appeal documentation**
5. **Billing software reports** for WC claims specifically
6. **Practice management system exports**

**Organize by:**
```
Client Data Structure:
├── Year 1-8 folders (by date of service year)
│   ├── Carrier-specific subfolders
│   │   ├── Procedure code categorization
│   │   ├── Payment vs. denial segregation
│   │   └── Appeal documentation tracking
```

---

## Part 3: Identifying Carrier Underpayment Tactics

*Source: `WC-LAW-REFERENCE.md` — Section 2: Common Carrier Tactics*

When extracting claims, flag any of these **five common carrier tactics**. Each one represents a recovery opportunity:

### Tactic 1: Using Out-of-State Fee Schedules
- **What it looks like:** Carrier applies Medicare rates or fee schedules from another state
- **How to spot it:** Payment amount matches a known out-of-state fee schedule rather than NJ UCR rates
- **Our counter:** NJ has no mandatory WC fee schedule; out-of-state schedules are irrelevant
- **Extraction flag:** `TACTIC_OOS_FEE_SCHEDULE`

### Tactic 2: Applying Outdated Data
- **What it looks like:** Carrier uses UCR databases from several years ago
- **How to spot it:** Payments correspond to older rate tables, not current market
- **Our counter:** UCR must reflect current market rates, not historical data
- **Extraction flag:** `TACTIC_OUTDATED_UCR`

### Tactic 3: Using the Wrong Geographic Area
- **What it looks like:** Carrier benchmarks using rural/low-cost area rates for NJ suburban/urban practices
- **How to spot it:** Payments align with geographic areas that don't match where services were provided
- **Our counter:** UCR must reflect the specific geographic area where services are provided
- **Extraction flag:** `TACTIC_WRONG_GEO`

### Tactic 4: Ignoring Procedure Complexity
- **What it looks like:** Carrier pays flat rates regardless of case complexity, modifiers, or complicating factors
- **How to spot it:** Same payment for simple vs. complex cases; CPT modifiers are ignored
- **Our counter:** UCR rates must account for individual case factors
- **Extraction flag:** `TACTIC_FLAT_RATE`

### Tactic 5: Arbitrary Percentage Reductions
- **What it looks like:** Carrier applies blanket 30–40% reductions without claim-specific justification
- **How to spot it:** Consistent percentage reduction across different procedure types and complexities
- **Our counter:** Each reduction must be individually justified based on UCR analysis
- **Extraction flag:** `TACTIC_BLANKET_REDUCTION`

**🔴 Rule: If you see any of these patterns, document it immediately and flag it in the case file. Patterns across multiple claims by the same carrier = systematic underpayment = stronger recovery position.**

---

## Part 4: Payment Violation Extraction

*Source: `WC-LAW-REFERENCE.md` — Section 3: Payment Timeline Requirements*

Beyond underpayment amounts, extract and flag these **payment timeline violations**:

| Violation | How to Identify | Recovery Opportunity | Frequency |
|---|---|---|---|
| **Payment beyond 30-day window** | Compare claim submission date to payment date; clean claims must be paid within 30 days | Interest penalties | Very Common |
| **Incomplete UCR rate justification** | Carrier provides no explanation or inadequate basis for payment below billed amount | UCR rate differential recovery | Very Common |
| **Arbitrary payment reductions** | Blanket reductions without claim-specific justification | Full UCR rate recovery | Common |
| **Failure to process prior auth timely** | Non-emergency procedures >$1K: track authorization request date vs. response date | Procedure payment + interest | Common |
| **Denial without medical basis** | Denial letter lacks medical rationale or peer review documentation | Full payment + penalties | Moderate |

**Interest rule:** Late payments accrue interest from the date payment was due. Carriers rarely self-enforce this — which is exactly why we exist.

---

## Part 5: Claim Prioritization Framework

*Source: `RECOVERY_OPERATIONAL_SPEC_v1.md` — Section 4 & `QUALIFICATION-SCORECARD.md`*

Not all extracted claims are equal. Prioritize using these criteria:

### 5.1 By Dollar Value

| Priority | Revenue Impact | SLA | Action |
|---|---|---|---|
| 🔴 **CRITICAL** | >$50K total or enterprise account or SLA breach imminent | 24 business hours | Recovery Prime direct oversight |
| 🟠 **HIGH** | $10K–$50K or active referral network or renewal within 30 days | 72 business hours | Senior team assignment |
| 🟡 **MEDIUM** | $1K–$10K, standard account, no compounding factors | 5 business days | Standard workflow |
| 🟢 **LOW** | <$1K, informational/proactive | 10 business days | Standard workflow |

### 5.2 By UCR Gap Severity

From the Qualification Scorecard — these categories tell you how severe the underpayment pattern is:

| Gap Level | Underpayment % | Provider Receiving | Extraction Priority |
|---|---|---|---|
| **Massive** | 40%+ underpayment | ≤60% of UCR rates | Immediate — highest recovery potential |
| **Significant** | 30–39% | 61–70% of UCR rates | High — strong recovery case |
| **Moderate** | 20–29% | 71–80% of UCR rates | Standard — solid recovery opportunity |
| **Minor** | 10–19% | 81–90% of UCR rates | Lower priority but still recoverable |
| **Minimal** | 5–9% | 91–95% of UCR rates | Case-by-case evaluation |

### 5.3 By Statute of Limitations Urgency

**Always prioritize claims approaching the lookback expiry:**

| Claim Age | Urgency | Action |
|---|---|---|
| 7–8 years old | 🔴 CRITICAL | File demand letter immediately to establish claim date |
| 5–7 years old | 🟠 HIGH | Fast-track extraction and documentation |
| 3–5 years old | 🟡 MEDIUM | Standard extraction workflow |
| 0–3 years old | 🟢 LOW | Standard — time is on our side |

---

## Part 6: The Extraction Workflow

### Step-by-Step Process

**Step 1: Historical Payment Collection**
- Collect 8 years of WC payment records from the client
- Organize by year → carrier → procedure code
- Confirm document completeness before proceeding

**Step 2: Claim-by-Claim Extraction**
- For each claim, populate all fields from Part 2.1
- Calculate UCR rate differential using FAIR Health or equivalent
- Flag any carrier tactics identified (Part 3)
- Flag any payment violations (Part 4)

**Step 3: Pattern Analysis**
- Group claims by carrier — look for systematic underpayment patterns
- Group claims by procedure code — identify procedure-specific gaps
- Group claims by time period — spot changes in carrier behavior
- Document all patterns; systematic evidence strengthens every individual claim

**Step 4: Prioritization**
- Apply the prioritization framework (Part 5)
- Oldest claims first (statute of limitations protection)
- Highest dollar value second
- Strongest pattern evidence third

**Step 5: Demand Preparation**
- For each prioritized claim batch, compile:
  - UCR rate research documentation
  - Underpayment calculations with interest
  - Legal authority citations (Part 1.2)
  - Carrier tactic documentation
  - Settlement demand formulation with response deadline

**Step 6: Handoff to Recovery Workflow**
*Per `RECOVERY_OPERATIONAL_SPEC_v1.md`:*
- Extracted claims enter the **REVENUE_RECOVERY** case type
- Stage flow: **IDENTIFIED → VERIFIED → DEMAND → NEGOTIATION → RESOLUTION → COLLECTED**
- Every stage transition requires: `actor`, `timestamp`, `reason`, `previous_stage`
- Max dwell times enforced (see Part 7 below)

---

## Part 7: Stage Dwell Time Rules

*Source: `RECOVERY_OPERATIONAL_SPEC_v1.md` — Section 2.2*

Once a claim enters the recovery pipeline, these maximum stage dwell times apply:

| Transition | Max Time | What Happens If Exceeded |
|---|---|---|
| IDENTIFIED → VERIFIED | 24 hours | Auto-escalate priority one level |
| VERIFIED → DEMAND | 8 hours | Auto-escalate priority one level |
| DEMAND → NEGOTIATION | 72 hours | Auto-escalate priority one level |
| NEGOTIATION → RESOLUTION | 15 business days | Double-stall alert to Recovery Prime + Mark |
| RESOLUTION → COLLECTED | 30 business days | SLA breach alert to Recovery Prime + Mark + Sean |

**Auto-escalation rule:** Any case sitting in the same stage for >48 hours without logged activity auto-escalates one priority level. Two consecutive stalls = direct Recovery Prime intervention + Mark notification.

---

## Part 8: Dispute Resolution Path Selection

*Source: `WC-LAW-REFERENCE.md` — Section 5*

After claim extraction, the recovery path depends on total value:

| Scenario | Recommended Path | Expected Timeline |
|---|---|---|
| Individual underpayment ($3K–$10K) | Administrative hearing (WC Division) | 6–9 months |
| Pattern of underpayments ($10K–$100K) | Arbitration (AAA or JAMS) | 9–15 months |
| Systematic underpayment ($100K+) | Litigation (Superior Court, Law Division) | 12–24 months |
| 8-year lookback ($500K+) | Litigation with settlement pressure | 12–36 months |
| Multiple carriers involved | Parallel proceedings | Varies |

---

## Part 9: UCR Rate Resources

*Source: `WC-LAW-REFERENCE.md` — Section 8*

Use these resources when benchmarking UCR rates during extraction:

| Resource | Type | Notes |
|---|---|---|
| **FAIR Health** | Independent UCR database | Largest independent source — our primary benchmark |
| **Ingenix/Optum360** | Commercial UCR data | Carrier-favored; often challenged; use for comparison only |
| **CMS Medicare Fee Schedule** | Baseline reference | Not dispositive for WC — but useful as a floor |
| **NJ-specific billing databases** | State provider charge data | Geographic specificity |

**Expert resources to engage as needed:**
- Medical billing/coding experts (CPT/ICD-10 analysis)
- Healthcare economics experts (UCR rate methodology)
- Actuarial analysts (historical patterns)
- NJ court records (prior UCR rate decisions)

---

## Part 10: Compliance — Non-Negotiable Rules

*Source: `WC-LAW-REFERENCE.md` — Section 7*

### HIPAA
- All client engagement agreements must include **HIPAA authorizations**
- PHI handling protocols must be followed at all times
- **Business Associate Agreements (BAAs)** required
- Apply the **minimum necessary standard** — only access what you need

### Documentation Standards
- Comprehensive file documentation for **every** claim
- Evidence preservation and chain of custody maintained
- If it's not logged, it didn't happen
- **Every stage transition** requires: actor, timestamp, reason, previous stage

### Professional Responsibility
- Attorney-client privilege protections in effect
- Contingent fee agreements per NJ RPC 1.5
- If it's not right for the provider, we say so
- Integrity is not optional — it's the business model

---

## Quick Reference: Extraction Checklist

Use this for every client onboarding:

- [ ] 8 years of WC payment records collected
- [ ] Records organized by year → carrier → procedure code
- [ ] All claim fields populated (Part 2.1)
- [ ] UCR rate benchmarks calculated per procedure per year
- [ ] Underpayment amounts and percentages calculated
- [ ] Carrier tactics identified and flagged (Part 3)
- [ ] Payment violations identified and flagged (Part 4)
- [ ] Pattern analysis completed (carrier, procedure, time period)
- [ ] Claims prioritized by statute of limitations urgency
- [ ] Claims prioritized by dollar value
- [ ] Demand letter documentation compiled
- [ ] Claims entered into REVENUE_RECOVERY pipeline
- [ ] HIPAA compliance verified
- [ ] File documentation complete

---

## Remember

Every claim you extract represents a real person — a surgeon, a specialist, a therapist — who did the work, healed someone, and didn't get paid what they were owed. We don't just process files. We recover what's right.

Persistence with heart. Integrity without exception. That's how we work.

Welcome to the team. 🌱

---

*Document sources: `WC-LAW-REFERENCE.md`, `RECOVERY_OPERATIONAL_SPEC_v1.md`, `ONBOARDING-WORKFLOW.md`, `QUALIFICATION-SCORECARD.md` — all from the SAI Recovery workspace.*
