# Contract Analysis Test Cases — Ground Truth Benchmarks

**Source:** Mark Winters (Telegram uploads)
**Analyst:** Courtney Carloni (manual pre-litigation analysis)
**Purpose:** Benchmark for automating contract rate analysis

---

## Case 1: Princeton / Qualcare — 2025-18831
- **Carrier:** Qualcare
- **Type:** ER (outpatient emergency)
- **Contract Rule:** ER cases reimbursed at 85% of billed charges
- **Billed:** $4,467.00
- **85% Calculation:** $3,796.95
- **Carrier Paid:** $2,902.80
- **Outstanding Balance:** $894.15
- **Files:** Princeton_Qualcare_2025-18831.pdf, 2025-18831 Treatment.xlsx

---

## Case 2: Princeton / Qualcare — 2025-18877
- **Carrier:** Qualcare
- **Type:** ER
- **Contract Rule:** ER cases reimbursed at 85% of billed charges
- **Billed:** $23,158.00
- **85% Calculation:** $19,684.30
- **Carrier Paid:** $9,263.20
- **Outstanding Balance:** $10,421.10
- **Note:** Qualcare requires all cases be appealed to carrier first; carrier refers to Qualcare if needed
- **Files:** Princeton_Qualcare2_2025-18877.pdf, 2025-18877 Treatment.xlsx

---

## Case 3: CHN Insurance — 2022-6069
- **Carrier:** CHN
- **Contract:** CHN rates from 2007
- **Rule:** All outpatient charges (not same day surgery) at 85% of billed
- **Outstanding Balance (per provider appeal):** $6,527.99
- **Note:** ER section says 85% with max $465, but carrier paid more
- **Files:** chn_hck_Redacted.pdf, 2022-6069 Treatment.xlsx

---

## Case 4: Qualcare — 2024-25661
- **Carrier:** Qualcare
- **Type:** INPATIENT
- **Contract Rule:** DRG code-based reimbursement
- **DRG Code:** 514
- **Contract Rate (5/1/23):** $24,351.00
- **Carrier Paid:** $8,400.00
- **Outstanding Balance:** $15,951.00
- **Files:** q__HCK_Redacted.pdf, 2024-25661 Treatment.xlsx

---

## Case 5: NPA / Qualcare — 2025-22760 (Northeast Pain Associates)
- **Carrier:** Qualcare
- **Analysis:** Not yet provided
- **Files:** NorthEast_Pain_Associates_271560430.pdf, NAPQ_Redacted.pdf, 2025-22760 Treatment.xlsx

---

## Case 6: CAS / Qualcare — 2024-29043 (Center for Ambulatory Surgery)
- **Carrier:** Qualcare
- **Note:** LARGEST CONTRACT PROVIDER
- **Contract:** Legacy contract, two 3% increases (Mar 2023, Sep 2023)
- **All procedures under legacy:** $4,693.00
- **Updated rate:** $2,978.80
- **MPR:** Applies to all codes regardless of coding
- **Implants:** 60% of billed charges
- **Total PPO:** $10,284.01
- **Carrier Paid:** $7,039.50
- **Outstanding Balance:** $3,244.51
- **Files:** CAS_Q2_Redacted.pdf

---

## Case 7: CAS / Qualcare — 2024-28344
- **Carrier:** Qualcare
- **Contract:** Legacy, grouper rate 1 = $2,671.00
- **MPR:** Applies to all codes regardless of coding
- **Escalation:** Two 3% increases (Mar 2023, Sep 2023)
- **DOS 7/2/24:** Total PPO $4,250.49 | Paid $4,006.50 | Balance $243.99
- **DOS 7/30/24:** Total PPO $2,833.66 | Paid $2,671.00 | Balance $162.66
- **Files:** CAS_Q_Redacted.pdf

---

## Case 8: Qualcare (CarePoint — Bayonne/Christ/Hoboken) — 2023-32105
- **Carrier:** Qualcare
- **Contract Rule:** 15% of billed charges (SIMPLEST contract)
- **Contract Termination:** 11/28/24
- **Billed Charges → 15%:** $2,053.05
- **Total PPO:** $2,053.05
- **Carrier Paid:** $1,127.21
- **Outstanding Balance:** $925.84
- **Sent to:** Lucrezia, Betsy, Jennifer at Qualcare
- **Files:** CONFIDENTIAL QN Fee Schedule 11.29.23_compressed-1.pdf, RWJ 3_ increase amendment.PDF, 2023-32105_Treatment.xlsx, BayonneQ_Redacted.pdf, June 2021 WC Rates addndum BMC.pdf, June 2021 WC Contract (no rates) addendum BMC.pdf, RE CarePoint - Qualcare PPO Termination.msg, 2023-32105_Treatment-1.xlsx

---

## Contract Analysis Formula (General)

```
1. Identify claim type (ER, inpatient, outpatient surgery, etc.)
2. Match to contract provision for that claim type
3. Apply base rate (% of billed / DRG lookup / grouper rate / fee schedule)
4. Apply escalation clauses (annual % increases with effective dates)
5. Apply MPR (Multiple Procedure Reduction) if applicable
6. Calculate implant costs separately if applicable
7. Sum = Total PPO owed
8. Total PPO − Carrier Payment = Outstanding Balance (recovery target)
```

---

## Carriers Represented
| Carrier | Cases | Contract Complexity |
|---------|-------|-------------------|
| **Qualcare** | 18831, 18877, 25661, 22760, 29043, 28344, 32105 | Low (% of billed) to High (DRG + grouper + escalation + MPR + implants) |
| **CHN** | 6069 | Medium (% of billed with ER max cap exception) |

---

*These cases are the ground truth for building automated contract analysis. Any system we build must match Courtney Carloni's manual results.*
