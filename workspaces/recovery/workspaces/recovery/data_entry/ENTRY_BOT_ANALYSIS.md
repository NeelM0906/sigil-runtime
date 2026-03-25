# Entry Bot Analysis — SAI Recovery
**Analyzed by:** SAI Recovery 🌱
**Date:** March 23, 2026
**Source:** Full Python script provided by Mark Winters

---

## ARCHITECTURE OVERVIEW

The current bot is a **Selenium-driven automation** that:
1. Logs into PAD at `http://60.60.60.200` as user "thebot"
2. Picks up cases from a **CI Delivery Queue** (`cideliveryqueuebot.php`)
3. Downloads PDF documents (EOBs + HCFAs) linked to each queue entry
4. Sends PDFs to **Google Gemini** (model: `gemini-3-flash-preview`) for extraction
5. Fills a web form in PAD with the extracted data
6. Clicks "Create File" to save the entry
7. Post-processing: ICN screenshot verification via Google Vision, EOB redaction, NPI association, CloudWatch logging

---

## THE 7-STEP EXTRACTION PIPELINE

The bot runs **7 sequential Gemini prompts** per case, each extracting different field groups:

### Step 1: Insurance Context
- `policy_no`, `group_no`, `insurance_member_id`
- Distinguishes policy number vs group number vs member ID vs account number

### Step 2: Claim Number + Account Number
- `claim_number` (ICN — Internal Control Number from EOB)
- `account_no` (PID from first page, or ACNT/Account # from EOB)
- Carrier-specific rules (BCBS Texas O→0 correction)
- Multi-EOB: comma-separated claim numbers
- Line-break concatenation for split ICNs

### Step 3: Location / Provider Info
- `location` (state from HCFA Box 32)
- `geozip` (ZIP from HCFA Box 32, include +4 from EOB)
- `facility_name` (HCFA Box 32)
- `physician_name` (HCFA Box 31, reorder LAST,FIRST → FIRST LAST)
- `place_of_service` (HCFA Box 24B, 2-digit code)
- `rendering_npi` (HCFA Box 24J, 10-digit)

### Step 4: Treatments / Service Lines
- Array of treatment objects, each with:
  - `dos`, `cpt`, `cptMod`, `units`, `billed`
  - `allowed`, `copay`, `coinsurance`, `deductible`, `qpa`, `insurancepaid`
- Matches HCFA service lines to EOB payment breakdown
- `procedures` from operative report

### Step 5: Patient Demographics
- `patient_name` (HCFA only, reorder LAST,FIRST → FIRST LAST)
- `patient_address`, `patient_city`, `patient_state`, `patient_zip` (all HCFA Box 5)
- `patient_dob` (HCFA Box 3)
- `patient_sex` (HCFA Box 3)
- `initial_eob_date` — **CRITICAL FOR NSA**: earliest payment-related date (Production Date > Check Date > Issue Date). NOT Date of Service.

### Step 6: Raw Insurance Fields
- `raw_insurance_name` (from HCFA Box 9d/11c or EOB header)
- `raw_insurance_provider_name` (HCFA Box 33 ONLY — billing provider)
- `raw_insurance_provider_address` (HCFA Box 33 address)
- Detects HCFA vs UB-04 form type
- Matches extracted provider to provider database via separate Gemini call

### Step 7: Negotiation Email
- `override_email` — dispute/negotiation email from EOB (NSA/IDR sections)

---

## PAD FIELDS POPULATED (Complete Map)

### General / Case Info
| PAD Element ID | Value Key | Source |
|---|---|---|
| general-provider | provider | Gemini match to provider DB |
| general-insurance | insurance | Gemini match to insurance DB |
| general-claimType | claim_type | DISABLED (not set by bot) |
| general-location | location | HCFA Box 32 state |
| general-accountNo | account_no | PID from page 1 or ACNT from EOB |
| general-policyNo | policy_no | DISABLED |
| general-claimNo | claim_number | ICN from EOB |
| general-memberID | insurance_member_id | EOB member ID |
| general-group_no | group_no | HCFA Box 11 |
| general-letter | letter | DISABLED |
| general-placeOfService | place_of_service | HCFA Box 24B |
| general-providerNegotiated | provider_negotiated | DISABLED |
| general-geozip | geozip | HCFA Box 32 ZIP |

### Patient Demographics
| PAD Element ID | Value Key | Source |
|---|---|---|
| home-firstName | patient_fname | Parsed from patient_name |
| home-lastName | patient_lname | Parsed from patient_name |
| home-address | patient_address | HCFA Box 5 |
| home-city | patient_city | HCFA Box 5 |
| home-state | patient_state | HCFA Box 5 |
| home-zip | patient_zip | HCFA Box 5 |
| home-dob | patient_dob | HCFA Box 3 |
| home-sex | patient_sex | HCFA Box 3 |
| home-initialEOBDate | initial_eob_date | Earliest payment date from EOB |
| home-facility | facility_name | HCFA Box 32 |
| home-doctor | physician_name | HCFA Box 31 |
| home-procedure | procedures | Operative report |

### Treatment Lines (per service line)
| Field | Source |
|---|---|
| dos{n} | HCFA Box 24A |
| dos{n}-cpt | HCFA Box 24D |
| dos{n}-mod | HCFA Box 24D modifiers |
| dos{n}-units | HCFA Box 24G |
| dos{n}-billed | HCFA Box 24F |
| dos{n}-copay | EOB |
| dos{n}-coinsurance | EOB |
| dos{n}-deductible | EOB |
| dos{n}-insurancepaid | EOB |
| dos{n}-qpa | EOB or calculated (copay+coinsurance+deductible+insurancepaid) |

### Other
| Field | Source |
|---|---|
| insurance-email-override | override_email | NSA negotiation email from EOB |

### Raw Fields (POST to separate endpoint)
| Field | Source |
|---|---|
| raw_insurance_name | HCFA Box 9d/11c or EOB header |
| raw_insurance_provider | HCFA Box 33 |

---

## WHERE THE 25% FAILURE RATE LIKELY LIVES

### HIGH-RISK Failure Points

1. **Claim Number Extraction (ICN)**
   - Split across line breaks requiring concatenation
   - O vs 0 confusion (BCBS Texas has specific rule, but other carriers?)
   - Multiple EOBs = comma-separated values — parsing downstream could break
   - **Vision verification exists but only runs IF initial extraction finds a claim number** — if Gemini misses it entirely, Vision never corrects it

2. **Patient Name Parsing**
   - HCFA shows "LAST, FIRST" → bot reorders to "FIRST LAST"
   - Then splits on space: first token = first name, rest = last name
   - **FAILS on**: hyphenated last names, suffixes (Jr, III), middle names, names with particles (De La Cruz)
   - Example: "MARIA DE LA CRUZ" → fname="MARIA", lname="DE LA CRUZ" ✅ but "JOHN SMITH JR" → fname="JOHN", lname="SMITH JR" ⚠️

3. **Insurance Matching**
   - Matches extracted insurance name against a database list via Gemini
   - Has hardcoded special mappings: "Health Options" → "Florida Blue", "RMHMS" → "Rocky Mountain"
   - **If Gemini picks wrong insurance from the list, EVERYTHING downstream is wrong** (wrong sample data, wrong fee schedules, wrong automation)
   - Returns empty {} if no match → case gets skipped, not flagged for human review

4. **Provider Matching**
   - Similar issue — extracted Box 33 text matched to provider DB via Gemini
   - If no match found, `provider_id = None` — but case still proceeds with no provider set

5. **Initial EOB Date**
   - Critical for NSA 30-day deadline
   - Bot must pick EARLIEST payment-related date, NOT date of service
   - If Gemini confuses Production Date with Date of Service, the arbitration deadline could be miscalculated
   - **No validation or cross-check exists for this field**

6. **Treatment Line Matching**
   - Must match HCFA service lines (billed) to EOB payment lines
   - Same CPT on multiple dates = separate lines
   - Same CPT with different modifiers = separate lines
   - **If matching is off by one line, every financial field for that treatment is wrong**

7. **QPA Calculation Fallback**
   - If QPA = 0, bot calculates: copay + coinsurance + deductible + insurancepaid
   - This is NOT how QPA is actually defined (QPA = median contracted rate for same service in same geographic area)
   - This fallback could produce legally incorrect QPA values for NSA arbitration

8. **Multi-Patient Documents**
   - EOBs may contain multiple patients on one page
   - Every prompt includes patient filtering, but if the wrong patient is targeted, all data is for the wrong person
   - Patient name comes from form (pre-populated) OR from extraction — circular dependency risk

### MEDIUM-RISK Issues

9. **GeoZIP Extraction**
   - Box 32 (service facility) vs Box 33 (billing provider) vs patient address
   - Wrong ZIP = wrong geographic fee schedules

10. **Place of Service**
    - 2-digit code — if Gemini reads "22" as "2" or picks up adjacent field data, wrong POS

11. **Modifier Extraction**
    - Diagnosis pointers (Box 24E — "ABCD") sit right next to modifiers
    - Prompt explicitly warns against this, but OCR/vision errors could still mix them

12. **Date Format Parsing**
    - Bot handles 8 date formats, but if Gemini returns a non-standard format, `_format_date()` returns None and the field is skipped silently

### LOW-RISK (but worth noting)

13. **Sample Data Training**
    - Bot downloads up to 100 existing files for the same insurance as "training examples" before processing
    - If those examples contain the existing 25% error rate, the bot is LEARNING FROM BAD DATA

14. **Fallback to gemini-3-pro-preview**
    - If initial extraction fails, falls back to a less structured mega-prompt
    - This produces less reliable results but the case still gets created

15. **Form Submission Validation**
    - Only checks: first name, last name, DOB
    - Does NOT validate: insurance, provider, claim number, any treatment data
    - A case with wrong insurance + right patient name sails through

---

## SUBJECTIVE FIELDS THE BOT CANNOT HANDLE

Based on the script, I can see where "subjective" extraction would fail:

1. **Insurance carrier identification when names don't match** — requires judgment about carrier subsidiaries, TPAs, brand names vs legal entity names
2. **Provider matching when Box 33 text is abbreviated or informal** — "DR SMITH ORTHO" vs "John Smith MD Orthopedic Associates LLC"
3. **Determining whether an EOB shows a payment vs a denial** — affects which EOBs are "relevant"
4. **Identifying the correct Initial EOB Date when multiple dates compete** — Production Date vs Issue Date vs Check Date requires contextual judgment
5. **Procedures extraction from operative reports** — unstructured text, medical terminology, varying formats

---

## WHAT A REPLACEMENT BEING WOULD DO DIFFERENTLY

1. **Single-pass extraction with confidence scoring** — instead of 7 separate Gemini calls that can contradict each other, one comprehensive extraction with a confidence score per field
2. **Field-level validation before PAD entry** — don't just check name+DOB; validate every field against business rules
3. **Flagging instead of skipping** — current bot skips cases it can't process; a being would flag them for human review with specific reasons
4. **No learning from potentially bad data** — don't use existing PAD entries as training examples
5. **Cross-field consistency checks** — does the insurance match the state? Does the facility match the geozip? Does the provider make sense for the place of service?
6. **NSA deadline awareness** — calculate and flag the 30-day window from Initial EOB Date immediately
7. **Handle the subjective fields** with actual judgment, not rigid pattern matching

---

## SECURITY NOTE

The script contains hardcoded credentials:
- PAD login: thebot / @AIBot2025
- Azure OpenAI API key (exposed in plaintext)
- AWS CloudWatch credentials (access key + secret key in plaintext)

These should be moved to environment variables or a secrets manager before any new system is built.
