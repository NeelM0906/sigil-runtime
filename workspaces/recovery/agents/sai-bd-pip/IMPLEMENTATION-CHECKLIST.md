# PIP BD Caller — Implementation Checklist
## Ready for Mark's Return

**Created:** 2026-02-27
**Status:** Documentation complete, awaiting implementation
**Adapted from:** WC BD Caller (same structure, PIP legal context)

---

## ✅ COMPLETED (Ready to Use)

### Documentation
- [x] **BLAND-PATHWAY-SPEC.md** — Full 19-node conversation flow
  - NJ-specific scripts (60-day payment, interest)
  - NY-specific scripts (30-day payment, 2% monthly interest)
  - Gatekeeper handling (same as WC)
  - Decision maker qualification
  - 5 objection types with PIP-specific responses
  - Meeting booking flow
  - Variable injection for state-specific language

- [x] **SUPABASE-SCHEMA.sql** — Database schema ready to deploy
  - `pip_prospects` table (PIP-specific scoring)
  - `pip_call_log` table
  - `pip_email_log` table
  - `pip_meetings` table
  - Auto-tier calculation
  - NJ/NY filtered views

### Existing Documentation (from prior build)
- [x] PIP-LAW-REFERENCE.md — NJ & NY PIP law details
- [x] STRATEGY.md — Market analysis, target profiles
- [x] OUTREACH-PLAYBOOK.md — 7-touch campaign templates
- [x] LEAD-QUALIFICATION.md — Scoring criteria
- [x] PROSPECTING.md — Target identification

---

## 🔲 NEEDS IMPLEMENTATION

### Step 1: Database Setup (15 min)
1. Open Supabase SQL Editor
2. Copy/paste `SUPABASE-SCHEMA.sql`
3. Run the SQL
4. Verify tables: `pip_prospects`, `pip_call_log`, etc.

### Step 2: Populate Prospect Data (2-4 hours)
**NJ Targets:**
- Emergency medicine groups (150+ practices)
- Orthopedic trauma practices (80+ practices)
- Urgent care centers treating auto accidents

**NY Targets:**
- Emergency medicine groups (200+ practices)
- Orthopedic trauma practices (120+ practices)
- NYC metro, Long Island, Hudson Valley focus

**Data needed per prospect:**
- Practice name, address, phone
- Specialty (EM, ortho, urgent care)
- State (NJ or NY) — critical for script selection
- Decision maker name/title
- Estimated auto accident volume

### Step 3: Bland.ai Pathway Setup (3-4 hours)
1. Create new pathway in Bland dashboard
2. Use `BLAND-PATHWAY-SPEC.md` as reference
3. **Critical:** Configure state-based variable injection
   - NJ prospects → 60-day language, "interest"
   - NY prospects → 30-day language, "2% monthly"
4. Configure voice (same as WC)
5. Set up webhook to Supabase

### Step 4: Webhook Integration (2-4 hours)
Same as WC — parse Bland payload, insert to `pip_call_log`, update prospect

### Step 5: Testing (4-6 hours)
- Test NJ-specific flow
- Test NY-specific flow
- Verify state variable injection works
- Check all objection branches

### Step 6: Go Live
Start with high-volume EM groups in North Jersey + NYC metro

---

## 🔑 KEY DIFFERENCES FROM WC CALLER

| Aspect | WC | PIP |
|--------|----|----|
| Legal hook | UCR underpayment, 8-year lookback | Payment timeline violation, interest |
| Timeline | Historical recovery | Outstanding AR recovery |
| Target | Surgical practices | EM, ortho trauma, urgent care |
| States | NJ only | NJ + NY (different laws) |
| Variable injection | Specialty only | Specialty + State |

---

## 📋 PRIORITY PROSPECTS

### NJ Emergency Medicine (Tier 1)
- Hospital-based ED groups
- Freestanding emergency centers
- Urgent care chains with high auto accident volume

### NY No-Fault (Tier 1)
- NYC metro ED groups
- Long Island trauma practices
- Large orthopedic groups with motor vehicle injury focus

---

## 📁 FILE LOCATIONS

All files in: `/agents/sai-bd-pip/`

| File | Purpose |
|------|---------|
| BLAND-PATHWAY-SPEC.md | Full conversation flow for Bland.ai |
| SUPABASE-SCHEMA.sql | Database tables |
| PIP-LAW-REFERENCE.md | NJ/NY PIP law reference |
| STRATEGY.md | Market analysis, targets |
| OUTREACH-PLAYBOOK.md | Email/phone templates |
| IMPLEMENTATION-CHECKLIST.md | This file |

---

## 🚀 DEPLOYMENT ORDER

1. **WC BD Caller** — Deploy first (NJ WC practices)
2. **PIP BD Caller** — Deploy second (NJ + NY PIP practices)
3. **Federal IDR** — Deploy third (operations system)

Both BD callers can share Bland infrastructure — just different pathways.

---

*Ready when you are.* 🏥⚡
