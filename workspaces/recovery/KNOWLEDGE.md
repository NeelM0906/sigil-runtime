# Knowledge Base
*Self-maintained by recovery. Updated as I learn.*

## Your tools and capabilities

You have these tools available — USE THEM proactively:

### Web research
- **web_search**: Search the internet for information, case law, fee schedules, carrier contacts, regulatory updates
- **web_fetch**: Download any URL. For web pages, returns text content. For files (PDF, Excel, CSV), downloads to your workspace and returns the file path. ALWAYS follow up with parse_document to read the file.

### Document processing
- **parse_document**: Read and extract text from PDF, DOCX, XLSX, XLS, CSV, and other file formats. Use this after web_fetch downloads a binary file, or to read files uploaded by users. Example workflow: web_fetch downloads fee_schedule.xlsx → parse_document reads it → you analyze the content
- **read**: Read text files directly (TXT, MD, CSV, code files)
- **write**: Create or overwrite files in your workspace
- **edit**: Make targeted edits to existing files

### Memory and knowledge
- **memory_search**: Search your semantic memory for past conversations, documents, and learned information
- **memory_store**: Save important information for future reference
- **pinecone_query**: Search the vector knowledge base (ublib2, saimemory)
- **update_knowledge**: Update your KNOWLEDGE.md file

### When someone asks you to process a document or file:
1. If they uploaded it: the file is in your workspace/uploads/ directory. Use parse_document to read it.
2. If they give you a URL: use web_fetch to download it, then parse_document to read the downloaded file.
3. If they paste content directly: you can read it from the message. No tools needed — just analyze what they pasted.

NEVER say "I can't process documents" or "I can't read Excel files." You CAN — use web_fetch + parse_document.

## Key Facts

## Domain Expertise

## Business Structure (Confirmed by Mark Winters)
- **SAI Recovery (me)** → Federal NSA/IDR ONLY — Callagy Recovery
- **SAI PIP** (planned) → NJ/NY No-Fault — Callagy Law
- **SAI Workers' Comp** (planned) → State WC boards — Callagy Law
- **SAI Law Commercial** (planned) → Commercial insurance litigation — Callagy Law
- Until sisters are online, I capture everything and flag which lane it belongs to.

## Core Work Product: Contract Analysis
The #1 capability Mark needs automated is **contract rate analysis**:
1. Read the provider-carrier contract to identify applicable reimbursement rules
2. Match claim type (ER, inpatient, outpatient surgery, etc.) to the correct contract provision
3. Apply rate (percentage of billed, DRG lookup, grouper rate, fee schedule)
4. Apply escalation clauses (e.g., 3% annual increases)
5. Apply MPR (Multiple Procedure Reduction) if applicable
6. Calculate implant costs separately if applicable (e.g., 60% of billed)
7. Sum to Total PPO owed
8. Subtract carrier payment
9. Outstanding balance = recovery target

## Known Carrier Contract Patterns
### Qualcare
- **ER outpatient**: 85% of billed charges
- **Inpatient**: DRG code lookup against fee schedule (e.g., DRG 514 = $24,351 under 5/1/23 contract)
- **Surgical (CAS legacy)**: Grouper rates + MPR + 3% escalations (Mar 2023, Sep 2023) + implants at 60%
- **Simple percentage**: Some providers at flat % (CarePoint = 15% of billed)
- **Appeal routing**: Must appeal to carrier first; carrier refers to Qualcare if needed

### CHN
- **Outpatient (non-same-day surgery)**: 85% of billed charges
- **ER**: 85% with $465 max (but carrier has exceeded this)

## Key Personnel
- **Courtney Carloni** — Pre-litigation analyst who performs manual contract analysis (ground truth for automation)
- **Mark Winters** — Human lead, guides recovery operations
- **Lucrezia, Betsy, Jennifer** — Qualcare contacts for claim review

## Test Cases Provided (8 cases across 3 carriers)
Cases 18831, 18877, 6069, 25661, 22760, 29043, 28344, 32105 — with contracts, treatment spreadsheets, and Courtney's manual analysis as ground truth benchmarks.

## Reliability Issue
Bot went down multiple times during Mark's document uploads. Trust was damaged. Stable uptime is non-negotiable. Mark needs clear online/offline indicators.

## Callagy Recovery Platform — Operational Foundation
## Source
Discord channel conversations March 17-20, 2026 between Mark Winters, SAI Recovery, Danny Lopez, and Aiko. Combined with Sean Callagy's founding directive (voice memo, ~March 2026).

## Sean's Mandate
- ZERO CONTAMINATION — no invisible human constraints
- Curve of possibility: 1 hour = 1 week, 1 day = half a year
- 10,000 files/month by June 2026
- 20X multiple (pushing toward $3B valuation) by July 2026
- SAI must OWN decisions — tell humans what to do next, not ask
- Create as many beings as possible — 100 in the Colosseum
- Work 24/7. Show what we can do. Shock with speed.

## Platform Architecture (6 Pillars)
1. **SAI** — Concept engine, workflow designer, being architect
2. **ACTi Consulting** (Fernando/Adam) — Methodology guardian
3. **Concept & Training Team** (Mark + Fatima + case staff) — SME, validation
4. **Developer Team** — Builds to spec, maintains backend post-handoff
5. **PAD** — Dual: backend source of truth + staff UI for file oversight
6. **Dashboard** — AI visibility layer (Aiko v1 → Dev Team maintains)

## Build Process (7 Phases)
Problem Definition → Specification → Review & Correction → Build → Shadow Mode (5 days min, 90%+) → Go-Live (ACTi + Mark approval) → Maintenance

## 28-Day Timeline
- Days 6-7: Exception queue live, validate 100 cases, lock build
- Days 8-14: SHADOW MODE (90%+ target)
- Days 15-21: LIVE MODE (AI sends automatically)
- Days 22-28: FULL REPLACEMENT (Rosemarie → exception queue only)
- Days 28-31: SEAN SESSION (30x multiple story)

## HIPAA — Three Blockers