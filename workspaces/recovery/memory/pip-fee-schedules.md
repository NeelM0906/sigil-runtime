# PIP Fee Schedule Mastery
_Built: 2026-02-28 | Owner: SAI Recovery_

## Purpose
This document is my standing knowledge of NJ and NY PIP fee schedules for use in the Contract Intelligence Engine. Reference this before any PIP calculation.

---

## NEW JERSEY PIP FEE SCHEDULE

### Governing Authority
- **Agency:** NJ Department of Banking and Insurance (DOBI)
- **Statute:** N.J.S.A. 39:6A-4.6
- **Regulation:** N.J.A.C. 11:3-29

### Current Effective Schedule
- **Effective date:** January 4, 2013 (still in force as of early 2026)
- **Source:** https://www.nj.gov/dobi/pipinfo/aicrapg.htm

### Fee Schedule Exhibits (All effective Jan 4, 2013)
| Exhibit | Category | Format Available |
|---------|----------|-----------------|
| Exhibit 1 | Physicians & ASC Fee Schedule | PDF + Excel |
| Exhibit 2 | Dental Fee Schedule | PDF + Excel |
| Exhibit 3 | Home Care Services | PDF + Excel |
| Exhibit 4 | Ambulance Services | PDF + Excel |
| Exhibit 5 | Durable Medical Equipment (DME) | PDF + Excel |
| Exhibit 6 | CPT Codes Subject to Daily Maximum | PDF + Excel |
| Exhibit 7 | Hospital Outpatient Surgical Facility (HOSF) | PDF + Excel |

### Key Legal Rules
- Providers CANNOT charge patients excess over scheduled rates
- "Usual and customary" applies if service is unspecified in schedule
- Standard PIP limit: **$250,000 per person**
- Reimbursement based on reasonable fees of **75% of providers in the area** by service type
- Medical protocols (Care Paths, Decision Point Review, Precertification) governed by N.J.A.C. 11:3-4

### 2025/2026 Updates
- **May 2025:** DOBI released updated schedule covering physician visits, dental, home care, ambulance, DME, hospital outpatient surgical
- **2026 Proposed (not yet effective):** Orthopedic schedule overhaul under public comment
  - Example: CPT 29827 (Arthroscopy) — proposed $3,820 Northern NJ (~17% reduction from $4,595)
  - CPT 63030 (Lumbar laminotomy) — $10,000 Northern / $5,000 Southern (50% regional disparity)
  - 5% increase for plastic surgery
  - Doubled rates for E&M codes

### Regional Distinction
NJ has **Northern vs. Southern NJ rate tiers** for some procedures. Always confirm region.

---

## NEW YORK PIP (NO-FAULT) FEE SCHEDULE

### Governing Authority
- **Agency:** NY Department of Financial Services (DFS)
- **Regulation:** Regulation 83 (11 NYCRR Part 68)
- **Underlying schedule:** NY Workers' Compensation Board (WCB) Medical Fee Schedules
- **Statute:** Insurance Law §5108

### Current Effective Schedule
- Services on/after **October 1, 2020** follow the 34th Amendment (WCB schedules from Dec 11, 2018)
- Services before Oct 1, 2020 follow prior 11 NYCRR 68.5 provisions
- Source: https://www.dfs.ny.gov/apps_and_licensing/property_insurers/nofault

### Fee Schedule Categories (WCB-based, incorporated into No-Fault)
| Category | Access Method |
|----------|--------------|
| Medical Fee Schedule (main) | Purchase from RefMed or view in person |
| Acupuncture & Physical/Occupational Therapy | Purchase from RefMed |
| Behavioral Health | Purchase from RefMed |
| Chiropractic | Purchase from RefMed |
| Dental | Free download from WCB website |
| Durable Medical Equipment (DME) | Free download from WCB website |
| Ambulatory Surgery (EAPG) | WCB EAPG page |
| Inpatient & Outpatient | NYS Dept of Health rates |
| Pharmacy | WCB Pharmacy Fee Schedule page |
| Podiatry | Purchase from RefMed |

**RefMed purchase:** https://marketplace.refmed.com/ | (863) 222-4071

### Key Legal Rules
- **No balance billing** — Providers cannot charge patients the difference between billed and scheduled amounts (Insurance Law §5108)
- Hospital inpatient: reimbursed at NY State Dept of Health DRG rates, even if billed lower
- Ambulance: covered under Regulation 83, Part G maximum permissible charges
- Service date determines which schedule applies (not accident date or billing date)

### Special Modifiers
- **Modifier 1B** — Behavioral health enhanced reimbursement: 20% increase for Board-assigned providers (Ground Rule 18)
- **Modifier 1D** — Designated provider enhanced reimbursement: 20% increase for primary care (family medicine, general practice, internal medicine) (Ground Rule 17)

### 2025 Updates
- Nov 6, 2025: Dental Fee Schedule amendments adopted (Subject 046-1783)
- Jun 26, 2024: DME Fee Schedule updated (Subject 046-1695)

---

## APPLICATION RULES FOR CONTRACT ENGINE

### NJ PIP Calculation Flow
1. Identify treatment date → confirm 2013 schedule applies (or 2026 if post-implementation)
2. Identify region (Northern vs. Southern NJ)
3. Look up CPT code in Exhibit 1 (physicians) or relevant exhibit
4. Check Exhibit 6 — is this code subject to daily maximum?
5. Apply any modifier reductions (assistant surgeon, bilateral, multiple procedure)
6. Compare to carrier payment
7. Calculate balance due

### NY No-Fault Calculation Flow
1. Identify service date → confirm Oct 1, 2020+ (34th Amendment)
2. Identify provider type → select correct fee schedule category
3. Look up CPT code in WCB Medical Fee Schedule
4. Check applicable modifiers (1B, 1D, bilateral, assistant)
5. Hospital inpatient? → Use DOH DRG rates regardless of billed amount
6. Compare to carrier payment
7. Calculate balance due

### Common Modifiers to Watch (Both States)
- **Multiple procedure reduction** — 2nd procedure typically 50%, 3rd 25%+
- **Bilateral reduction** — Often 150% of single procedure rate
- **Assistant surgeon** — Typically 16-20% of primary surgeon fee
- **Co-surgeon** — Each gets 62.5% of listed fee (125% split)

---

## FILES STATUS

### NJ — DOWNLOADED ✅
All 7 exhibits downloaded to: `data/fee-schedules/nj/`
| File | Size | Status |
|------|------|--------|
| nj_exhibit1_physicians_asc.xls + .csv | 386K / 167K | ✅ Ready |
| nj_exhibit2_dental.xls | 61K | ✅ Ready |
| nj_exhibit3_homecare.xls | 20K | ✅ Ready |
| nj_exhibit4_ambulance.xls | 21K | ✅ Ready |
| nj_exhibit5_dme.xls | 395K | ✅ Ready |
| nj_exhibit6_daily_max_cpts.xls + .csv | 29K / 2.5K | ✅ Ready |
| nj_exhibit7_hosf.xls | 166K | ✅ Ready |

**Exhibit 1 structure:** 2,914 data rows | Columns: CPT_HCPCS, MOD, DESCRIPTION, PHYSICIAN_FEE_NORTH, PHYSICIAN_FEE_SOUTH, ASC_FEE_NORTH, ASC_FEE_SOUTH, PAYMENT_INDICATOR
**Exhibit 6:** 48 CPT codes subject to daily maximum (physical therapy, chiro, casting codes)

**Sample verified rates (NJ Physicians):**
| CPT | Description | North | South |
|-----|-------------|-------|-------|
| 99213 | Office visit est. 15 min | $85.01 | $81.31 |
| 99214 | Office visit est. 25 min | $125.71 | $120.35 |
| 99215 | Office visit est. 40 min | $168.59 | $161.61 |

### NY — REQUIRES PURCHASE ⚠️
- WCB Medical Fee Schedule must be purchased from RefMed: https://marketplace.refmed.com/
- Phone: (863) 222-4071
- Dental + DME free from WCB website
- Inpatient: DRG rates from NYS DOH

### NY KEY BILLING RULES (from Regulation 83 FAQ)
- Inpatient hospital: DRG system, calculated at discharge (Section 68.2)
- Massage therapists: prevailing rate in geographic area (no set schedule)
- Ambulance: local prevailing charge for geographic area (Part G)
- Pre-Oct 1, 2020 services: governed by 11 NYCRR 68.5
- Providers subject to arbitration if insurer reduces bill

---

## Sources
- NJ DOBI PIP page: https://www.nj.gov/dobi/pipinfo/aicrapg.htm
- NY DFS No-Fault: https://www.dfs.ny.gov/apps_and_licensing/property_insurers/nofault
- NY WCB Fee Schedules: https://www.wcb.ny.gov/content/main/hcpp/FeeSchedules.jsp
- NY Regulation 83 FAQ: https://www.dfs.ny.gov/apps_and_licensing/property_insurers/faqs_reg83_nofault_schedule
