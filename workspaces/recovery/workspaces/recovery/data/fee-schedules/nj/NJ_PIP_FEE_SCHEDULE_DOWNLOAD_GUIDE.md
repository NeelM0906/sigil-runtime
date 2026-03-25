# NJ PIP Fee Schedule — Manual Download Guide

## Source
**NJ Department of Banking and Insurance (DOBI)**
URL: https://www.nj.gov/dobi/pipinfo/aicrapg.htm

**Effective:** January 4, 2013 (still current as of March 2026)

## Files to Download (All Available in PDF + Excel)

Navigate to the URL above and download the following:

### Rule Text
- **Fee Schedule Rule Text** — PDF or MS Word

### Exhibit 1 — Physicians' & ASC Fee Schedule
- The main fee schedule — ~2,914 rows of CPT codes with allowed amounts
- **CRITICAL:** See also "Notice regarding Exhibit 1 (February 20, 2019)" for updates
- Download both PDF and Excel versions

### Exhibit 2 — Dental Fee Schedule
- ADA dental codes and allowed amounts

### Exhibit 3 — Home Care Services
- Home health aide, skilled nursing, PT/OT/ST home visits

### Exhibit 4 — Ambulance Services
- Ground and air ambulance HCPCS codes and rates

### Exhibit 5 — Durable Medical Equipment
- DME HCPCS codes and allowed amounts

### Exhibit 6 — CPT Codes Subject to Daily Maximum
- ~48 codes with daily visit limits (critical for validation)
- These codes cannot exceed 1 unit per day per provider

### Exhibit 7 — Hospital Outpatient Surgical Facility (HOSF) Fee Schedule
- ASC/HOSF rates by CPT code

## Also Useful from Same Page
- **Automobile Medical Fee Schedule FAQ** (for rule effective January 4, 2013)
- **Uniform Attending Provider Treatment Plan Form** (PDF + Excel)
- **Pre-Service Appeal Form** (PDF + Excel)
- **Post-Service Appeal Form** (PDF + Excel)
- **Full Text of Alternate Dispute Resolution Rule** (Effective January 4, 2013)

## Forthright PIP Awards Database
- URL: https://njpipadr.forthright.com (search all DRP awards since May 2004)
- Also: AAA AICRA DRP awards issued prior to May 2004

## Instructions
1. Go to https://www.nj.gov/dobi/pipinfo/aicrapg.htm
2. Download ALL 7 exhibits in Excel format
3. Download the Fee Schedule Rule Text in PDF
4. Place files in this directory: `workspaces/recovery/data/fee-schedules/nj/`
5. Name them:
   - `AMFS_Rule_Text.pdf`
   - `Exhibit_1_Physicians_ASC.xlsx`
   - `Exhibit_2_Dental.xlsx`
   - `Exhibit_3_Home_Care.xlsx`
   - `Exhibit_4_Ambulance.xlsx`
   - `Exhibit_5_DME.xlsx`
   - `Exhibit_6_Daily_Maximum.xlsx`
   - `Exhibit_7_HOSF.xlsx`

Once files are placed here, SAI Recovery can parse them and build the live CPT lookup engine.
