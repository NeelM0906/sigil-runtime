# HIPAA COMPLIANCE REQUIREMENTS — CALLAGY RECOVERY AI PLATFORM
**Source:** Discord channel, Mark Winters + SAI Recovery — March 19, 2026
**Status:** Pre-implementation (three blockers must be resolved before PHI enters system)

---

## THREE MANDATORY PRE-GO-LIVE ACTIONS

1. **BAA signed** with AI provider (Anthropic/Azure OpenAI)
2. **Security officer** named and documented
3. **Formal risk analysis** completed and signed

**Until all three are done: ZERO PHI in the system. No exceptions.**

---

## FIVE HIPAA SAFEGUARD CATEGORIES

### 1. ADMINISTRATIVE SAFEGUARDS
- Security Officer designated → Mark names before go-live (OPEN)
- Workforce training → Concept Team trained on PHI handling
- Access management → Every team member's access level defined and documented
- Risk analysis → Formal written risk assessment (OPEN)
- BAAs → Signed with AI provider before any PHI touches system (OPEN)
- Incident response procedures → Escalation matrix, SLA, security contact (OPEN)
- Quarterly review → Built into governance calendar

### 2. PHYSICAL SAFEGUARDS
- Facility access controls → PAD and Python VM on physically secured hardware
- Workstation security → Controlled workstations only
- Device and media controls → No PHI on personal devices; no data exports without authorization
- No cloud PHI processing → AI runs on local machine

### 3. TECHNICAL SAFEGUARDS
- Access controls → System-defined, minimum necessary per being/task
- Unique user IDs → Every process has unique identifier in audit log
- Automatic logoff → Session timeout enforced
- Encryption at rest → AES-256 on all PHI storage
- Encryption in transit → TLS 1.2+ on all connections including internal
- Audit logs → Every read/write logged: timestamp, operation type, data scope, process ID — immutable, append-only, stored separately

### 4. ORGANIZATIONAL REQUIREMENTS
- BAA with AI provider → Required before go-live
- BAA with any cloud storage/logging service touching PHI
- Policies and procedures documented

### 5. BREACH NOTIFICATION RULES
- Discovery → Auto-suspend triggered on anomaly; forensic state preserved
- Within 60 days → Notify HHS if breach confirmed
- 500+ individuals → Notify HHS + local media within 60 days
- Affected individuals → Notified without unreasonable delay
- Documentation → Full incident log

---

## PHI IDENTIFIERS IN OUR SYSTEM

| Identifier | Where It Appears |
|-----------|-----------------|
| Patient name | EOB, HCFI, PAD case record |
| Date of birth | PAD case record |
| Dates of service | CPT code records, EOB |
| Geographic data | State, zip in case records |
| Phone numbers | Case contact info |
| Account/claim numbers | Claim numbers, DISP numbers tied to patient |
| Health plan beneficiary numbers | Group numbers, member IDs |
| Medical record numbers | Case identifiers |
| Certificate/license numbers | NPI, Tax ID |
| Diagnosis/treatment info | CPT codes, ICD codes, treatment details |

---

## REQUIRED DATABASE PROTECTIONS (Danny's Build Checklist)

**Danny Lopez committed: "Will take care of most this within a week or less" — March 19, 2026**

| Protection | Status |
|-----------|--------|
| Unique credentials per being/user | To configure |
| Role-based access (minimum necessary) | To configure |
| AES-256 encryption at rest | To implement |
| TLS 1.2+ on all connections | To confirm |
| Append-only audit log (separate storage) | To build |
| 6-year log retention | To configure |
| Firewall: PAD port restricted to VM IP only | To configure |
| Non-standard database port | Optional but recommended |
| MFA for staff PAD access | To implement |
| Service accounts for beings (no human login) | To configure |
| Failed login lockout + alerting | To configure |
| Encrypted daily backups | To confirm |
| Recovery testing procedure | To document |
| Strong passwords (16+ char, rotated 90 days) | To configure |
| Failed login lockout (5 attempts) | To configure |

### Additional Database Rules
- No direct database edits — all writes through application layer
- Input validation — beings validate data before writing
- Referential integrity — constraints prevent orphaned records
- Backups tested quarterly
- Retention policy documented

---

**Reference:** 45 CFR Parts 160, 162, and 164 (HIPAA Security and Privacy Rules)
