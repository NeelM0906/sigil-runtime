# 2026-02-28 — SAI Recovery Daily Log
_Contract Intelligence Engine — Foundation Session with Mark Winters_

## Session Summary
First real working session with Mark Winters. Focused on building the Contract Intelligence Engine for medical revenue recovery automation.

## KEY DECISIONS

### Zone Action Identified
- **One real case. One real contract. Full calculation loop. Working.**
- Don't build the system — prove the engine first
- Deliverable: parse HCFA + EOB → apply contract rules → output settlement sheet
- Next step: Mark to provide one sample case (HCFA + EOB + applicable carrier contract)

### Architecture Plan: Contract Intelligence Engine
1. **Ingest** — HCFA + EOB document upload/parse
2. **Remember** — Contract rates per carrier/provider stored once
3. **Calculate** — Contract rate lookup, multiple modality reductions, bilateral reductions, modifier logic (assistants, co-surgeons), carrier payment application, true remaining balance
4. **Output** — Settlement offer spreadsheet at selectable percentages
5. **PIP module** — NJ + NY fee schedules built in

### PIP Fee Schedules — FULLY LOADED
- **NJ:** All 7 DOBI exhibits downloaded to `data/fee-schedules/nj/`
  - 2,914 CPT codes with North/South physician rates + ASC rates
  - 48 daily-max CPT codes (Exhibit 6)
  - Effective date: January 4, 2013 (still in force)
- **NY:** Rules documented, WCB fee schedule requires RefMed purchase (~$20-30)
- Full knowledge doc saved to `memory/pip-fee-schedules.md`

## WORK COMPLETED
- [x] PIP fee schedule mastery research (NJ + NY)
- [x] NJ DOBI exhibits 1-7 downloaded + converted to CSV
- [x] Exhibit 1 (physicians): 2,914 CPT codes, North/South rates, queryable
- [x] Exhibit 6 (daily max): 48 CPT codes documented
- [x] pip-fee-schedules.md knowledge doc written to memory
- [x] CPT lookup verified working (tested 99213, 99214, 99215)
- [x] Vercel deploy tool confirmed available for future builds

## TOOLS CONFIRMED AVAILABLE
- Pinecone (`saimemory` index)
- Vercel deploy (`tools/vercel_deploy.py`)
- Supabase (read + write)
- xlrd/openpyxl installed for Excel parsing

## NEXT STEPS (WAITING ON MARK)
1. Mark to provide sample case: HCFA + EOB + carrier contract
2. Build calculation engine on that one case
3. Deploy to Vercel so Mark can see live output
4. Then scale to full case system

## AIKO DIRECTIVES RECEIVED
- Save all work to Pinecone + Supabase each session
- When building tools for Mark → deploy to Vercel + share link
- Recovery is operational and ready for documents

---
_Logged by SAI Recovery | 2026-02-28_
