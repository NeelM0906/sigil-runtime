# WC BD Caller — Implementation Checklist
## Ready for Mark's Return

**Created:** 2026-02-27
**Status:** Documentation complete, awaiting implementation

---

## ✅ COMPLETED (Ready to Use)

### Documentation
- [x] **BLAND-PATHWAY-SPEC.md** — Full conversation flow with 19 nodes
  - Gatekeeper handling (multi-turn persistence)
  - Decision maker qualification
  - Objection handling (5 major objection types)
  - Meeting booking flow
  - Voicemail scripts
  - Variable injection reference
  - Webhook payload spec

- [x] **SUPABASE-SCHEMA.sql** — Database schema ready to deploy
  - `wc_prospects` table (full BANKROLL scoring)
  - `wc_call_log` table (call tracking)
  - `wc_email_log` table (email sequences)
  - `wc_meetings` table (discovery/proposal calls)
  - Views for pipeline summary and daily follow-ups
  - Auto-tier calculation trigger

- [x] **PROSPECT-DATA-SEED.json** — 50 real NJ providers
  - Bergen County: 15 prospects
  - Middlesex County: 14 prospects
  - Essex County: 7 prospects
  - Morris County: 9 prospects
  - Hudson County: 2 prospects
  - Passaic County: 1 prospect
  - Union County: 1 prospect
  - Mix of orthopedic, pain management, ASCs
  - 11 explicitly marked as WC-focused (Tier 1 priority)

### Existing Documentation (from prior build)
- [x] BANKROLL Qualification Scorecard
- [x] NJ Market Analysis (21 counties)
- [x] Email sequences (3 campaigns)
- [x] Phone scripts (basic)
- [x] LinkedIn templates
- [x] Voicemail scripts
- [x] 14-day activation guide

---

## 🔲 NEEDS IMPLEMENTATION (Mark + Bland Team)

### Step 1: Database Setup (15 min)
1. Open Supabase SQL Editor
2. Copy/paste `SUPABASE-SCHEMA.sql`
3. Run the SQL
4. Verify tables created: `wc_prospects`, `wc_call_log`, `wc_email_log`, `wc_meetings`

### Step 2: Load Prospect Data (30 min)
1. Convert `PROSPECT-DATA-SEED.json` to INSERT statements (or use Supabase import)
2. Enrich with phone numbers (web research or data provider)
3. Score each prospect using BANKROLL criteria
4. Verify Tier 1 prospects have direct phone numbers

### Step 3: Bland.ai Pathway Setup (3-4 hours)
1. Create new pathway in Bland dashboard
2. Use `BLAND-PATHWAY-SPEC.md` as reference
3. Configure nodes:
   - CALL_START → GATEKEEPER_EXPLAIN → GATEKEEPER_PERSIST
   - TRANSFER_HOLD → DECISION_MAKER_INTRO
   - QUALIFYING nodes → BOOK_MEETING
   - OBJECTION handlers (5 types)
   - VOICEMAIL_NODE
4. Set up voice (recommend female, professional, warm)
5. Configure variable injection from prospect data
6. Set up webhook to Supabase

### Step 4: Webhook Integration (2-4 hours)
1. Create Supabase Edge Function or webhook endpoint
2. Parse Bland call completion payload
3. Insert into `wc_call_log` table
4. Update `wc_prospects.last_contact_at`, `next_action_at`
5. Trigger email sequence if `outcome_code = EMAIL_REQUESTED`

### Step 5: Testing (4-6 hours)
1. Test with 5-10 known numbers (friendly practices or test lines)
2. Verify gatekeeper flow works
3. Verify transfer detection
4. Verify voicemail detection and script
5. Check webhook payload arrives correctly
6. Iterate on voice/pacing

### Step 6: Go Live (ongoing)
1. Start with Tier 1 WC-focused prospects (11 in seed data)
2. Call 10-20/day initially
3. Review outcomes daily
4. Iterate on gatekeeper handling based on real results

---

## 📞 PRIORITY CALL LIST (Tier 1, WC-Focused)

Start with these — they explicitly handle workers' comp:

| Code | Practice | County | Notes |
|------|----------|--------|-------|
| WC-BER-001 | Premier Orthopaedics & Sports Medicine | Bergen | WC services on website |
| WC-BER-002 | Total Ortho Sports Medicine | Bergen | Full WC documentation |
| WC-BER-003 | Premier Spine NJ | Bergen | WC-accepting spine surgeons |
| WC-BER-010 | NY Sports Medicine Institute | Bergen | WC page, named doctors |
| WC-BER-011 | Dr. Seldes MD | Bergen | Work injury specialist |
| WC-MID-003 | IPM & Ortho-Spine Center | Middlesex | Worker's comp focus |
| WC-HUD-001 | TotalMD | Hudson | WC services explicit |
| WC-HUD-002 | CitiMed | Hudson | WC landing page |
| WC-PAS-001 | Orthopedic NJ (OINJ) | Passaic | WC case matching |

**Next tier** (high volume, need phone numbers):
- WC-MID-001: Garden State Pain - Edison (732-376-0330)
- WC-MID-002: Edison Spine & Pain (Dr. Anup Patel)
- WC-MID-005: University Orthopaedic Associates (732-537-0909)
- WC-MOR-002: Advanced Pain Therapy (973-917-3172)
- WC-MOR-004: NJ Pain Management (Dr. Rubinfeld)

---

## 📊 SUCCESS METRICS (Week 1)

| Metric | Target |
|--------|--------|
| Calls attempted | 100 |
| Gatekeepers reached | 60 |
| Decision makers reached | 15 |
| Meetings booked | 3-5 |
| Voicemails left | 30 |
| Email follow-ups triggered | 20 |

---

## ⚠️ GATEKEEPER TIPS (From Spec)

The hardest part is reception. Key learnings built into the pathway:

1. **Give enough info to sound legitimate** — "Workers' Compensation underpayment recovery for surgical practices"
2. **Use low commitment language** — "2 minutes" not "meeting"
3. **Redirect to identifying the right person** — "Is that the office manager, or the practice administrator?"
4. **Persist with callback framing** — "When would be the best time to reach them?"
5. **Handle "send an email"** — Capture email AND schedule follow-up call
6. **Know when to bail** — Don't burn the relationship; mark for retry in 2-3 weeks

---

## 📁 FILE LOCATIONS

All files in: `/Users/samantha/.openclaw/workspace/sisters/sai-recovery/agents/sai-bd-wc/`

| File | Purpose |
|------|---------|
| BLAND-PATHWAY-SPEC.md | Full conversation flow for Bland.ai |
| SUPABASE-SCHEMA.sql | Database tables (copy/paste to deploy) |
| PROSPECT-DATA-SEED.json | 50 real NJ providers |
| IMPLEMENTATION-CHECKLIST.md | This file |
| OUTREACH-TEMPLATES.md | Email/phone/LinkedIn templates |
| QUALIFICATION-SCORECARD.md | BANKROLL scoring system |
| MESSAGING-FRAMEWORK.md | Objection handling, value props |
| PROSPECTING-SYSTEM.md | Channel strategies |
| ACTIVATION-GUIDE.md | 14-day launch plan |

---

## 🚀 NEXT ACTIONS FOR MARK

When you're back:

1. **Quick win** — Deploy Supabase schema (15 min)
2. **Hand to Bland team** — Share BLAND-PATHWAY-SPEC.md
3. **Enrich phone numbers** — Use data provider or manual research
4. **Test calls** — 5-10 friendly numbers
5. **Go live** — Start with 11 Tier 1 WC-focused prospects

**Questions for Mark:**
- Which Bland.ai account/workspace should this go in?
- Callback number for voicemails — Callagy Recovery main line or dedicated?
- Meeting booking — calendar link or human follow-up?
- Email sequences — what ESP are you using?

---

*Ready when you are.* 🏥⚡
