# #sai-recovery-wc Channel History — March 5-11, 2026

**Source:** Full transcript pasted by Mark Winters on March 23, 2026
**Channel:** #sai-recovery-wc on Aiko's Discord server
**Project:** WC Contract Analyzer — carrier contracts, document samples, annotation work, settlement analysis

---

## Key People
- **Mark Winters** — Project lead, created channel
- **Laura Yeaw** — Annotator, provided settlement workflow, carrier list
- **SAI Recovery** — Document review, annotation feedback
- **Aiko** — Enabled SAI Recovery's channel access (March 5, late evening)
- **Nadav's Sai** — Present uninvited, caused duplicate responses and confusion

---

## Timeline

### March 5
- Channel created by Mark Winters
- Laura uploaded first annotated EOB: `Liberty Mutual EOB_Redacted.pdf`
- SAI Recovery was not responding — channel created after session started, couldn't resolve channel ID
- Aiko fixed access late evening (~10:45 PM)
- SAI Recovery confirmed active at 11:04 PM

### March 6
- SAI Recovery confirmed it did NOT have access to #sai-recovery-hub (prior conversations lost)
- Laura confirmed annotation guide exists: `docs/liberty-mutual-annotation-guide.md`
- Laura uploaded `PDF_Annotation_Guide.pdf` (3.51 KB) — her own guide based on prior discussions
- SAI Recovery noted key additions from Laura's guide

### March 9
- Mark asked about submission mechanism for contract analyzer
- Discussion: standalone portal vs PAD integration
- **Decision: Standalone portal** — PAD being replaced, no point building connector
- SAI Recovery wrote portal MVP spec: `docs/wc-portal-spec-v1.md`
- 3 pages: Upload → Extraction Review → Settlement Analysis

### March 10
- Laura answered portal questions:
  - 15 people in WC department
  - 28 priority carriers (image provided)
  - All carrier contracts saved digitally
  - Settlement workflow to follow
- Laura uploaded `Pre Litigation Settlement Workflow.docx`
- **Critical distinction confirmed:**
  - CONTRACT cases → resolve at contract amount or more (above = opportunistic)
  - NON-CONTRACT cases → 60-75% of outstanding balance (billed - paid)
- Laura uploaded 3 more annotated documents:
  - `Liberty Mutual EOB Unpaid_Redacted.pdf`
  - `CMS_1500 50 Modifier_Redacted.pdf`
  - `CMS_1500 80 Modifier_Redacted.pdf`
- Laura uploaded `Liberty UBO4 with Denial EOB Attached_Redacted.pdf`
- Color confusion identified: SAI Recovery's vision analysis couldn't distinguish dark blue from dark red at 150dpi
- Nadav's Sai started responding uninvited — gave wrong color scheme (Yellow = patient info instead of totals)
- SAI Recovery corrected Nadav's Sai
- Mark and Laura both flagged Nadav's Sai as unwanted in channel

### March 11
- Laura confirmed Page 1 annotations were correct as intended
- Laura agreed to switch to lighter/brighter blue going forward
- Nadav's Sai continued responding despite being asked to stop
- Laura formally asked for clarification on why Nadav's Sai was active

---

## Confirmed Annotation Color Scheme
| Color | Use |
|-------|-----|
| 🔴 Red | Claim identifiers: Claim #, Contract #, Document #, Patient Acct, SSN, DOI, Agency Claim #, Diag Codes |
| 🔵 Bright/Light Blue | Carrier, Payer, Provider, TIN, Address |
| 🟢 Green | Service line columns |
| 🟡 Yellow | Totals and payment amounts |
| ⚫ Gray | Check section / do not extract |

### CMS-1500 Standard Fields
- Box 21 (Diagnosis codes) → Red
- Box 25 (Federal Tax ID) → Blue
- Box 26 (Patient Account No.) → Red
- Box 33a (Billing Provider NPI) → Blue

### Negative Constraints (do NOT extract as claim number)
- OSN number
- Internal Bill No
- Cust/External Bill No

---

## Settlement Workflow (from Laura's document)
- **Contract cases:** Target = contract amount or more. Above contract = purely opportunistic.
- **Non-contract cases:** Outstanding = billed − previously paid. Target: 60-75%. Starting demand: 70-80%.
- **Negotiators:** BW and KM
- **Provider threshold:** Must be visible on settlement sheet
- **Adjuster field:** Signal for proactive outreach (LY reviews)
- **Metrics:** None existed — portal would be first tracking system
- **Warning letters:** Phase 2

---

## Portal MVP Spec
- **Pages:** Upload → Extraction Review → Settlement Analysis
- **Carrier selector:** 28 priority carriers + "Other/Unknown" fallback
- **Stack discussed:** Next.js + Python FastAPI + Supabase + Vercel
- **Timeline discussed:** ~3 weeks from green light
- **Key decision:** Standalone portal, NOT PAD integration

---

## Issues / Lessons
1. SAI Recovery had vision/color analysis limitations at low resolution (150dpi)
2. Nadav's Sai responded uninvited and gave conflicting guidance — created confusion
3. SAI Recovery lost access to #sai-recovery-hub conversations — could not carry context forward
4. Channel access required Aiko to manually enable after creation
