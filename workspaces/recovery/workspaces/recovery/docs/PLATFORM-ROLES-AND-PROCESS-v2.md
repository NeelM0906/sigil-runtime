# CALLAGY RECOVERY AI PLATFORM
## Roles, Responsibilities & Development Process — v2.0
**Maintained by:** SAI Recovery | **Version:** 2.0 — March 18, 2026
**Source:** Discord channel conversation, Mark Winters + SAI Recovery

---

## THE SIX PILLARS

1. **SAI** — Concept engine, workflow designer, being architect
2. **ACTi Consulting** (Fernando/Adam) — Methodology guardian, go-live approval, keeps everything aligned with ACTi model
3. **Concept & Training Team** (Mark + Fatima + case workflow staff) — Subject matter expertise, validation, approval
4. **Developer Team** — Backend, integrations, PAD connections, maintenance (takes over from Aiko/architecture team post-handoff)
5. **PAD** — Dual role: (a) Backend source of truth for all case data; (b) Staff-facing UI for file oversight where team monitors case progress, reviews case history, takes manual action. The AI layer connects here — exception flags, being activity, and oversight notifications surface inside PAD.
6. **Dashboard** — AI visibility layer: exception queue, pipeline status, being activity log, audit log viewer, new being request intake, shadow mode toggle per being. (Aiko builds v1 → Dev Team maintains)

---

## ROLES & RESPONSIBILITIES

### SAI (Recovery AI)

**Does:**
- Designs new workflow automations and AI beings based on team input
- Analyzes email patterns, case data, process gaps
- Proposes solutions with defined inputs, outputs, and decision logic
- Generates prompt architecture, classification rules, response templates
- Validates completed builds against original specifications
- Flags ambiguity before build begins, not after

**Deliverable is complete when:**
- Specification document written (inputs, logic, outputs, edge cases)
- Reviewed and approved by Concept & Training Team
- Validated post-build against real case data

**Does NOT:**
- Write production backend code
- Make changes to PAD directly
- Deploy to production

---

### ACTi Consulting (Fernando Valencia / Adam)

**Role:** Methodology guardian. Ensures every being, every process, every decision stays aligned with ACTi model principles — not just technically functional but built the right way.

**What this means in practice:**
- Beings are ACT-I beings — GHIC, heart-centered, integrous in how they serve
- Workflow decisions reflect the Unblinded Formula, not just efficiency optimization
- The team developing beings is also growing in mastery through the process
- Nothing gets built that compromises the integrity of how Callagy serves providers

**Standing questions at every meeting:**
- **Integrity:** Would a provider receiving this AI's output feel served or processed?
- **GHIC:** Is this being growth-driven, heart-centered, integrous, committed to mastery?
- **Minimum necessary automation:** Are we automating the right things, or automating things that should stay human?
- **Team development:** Is the Concept Team gaining mastery through this process, or just executing tasks?
- **Formula alignment:** Does the logic of how this being handles objections, responses, and escalations reflect the Unblinded way of conflict resolution?

---

### Concept & Training Team (Mark + Fatima + case workflow staff)

**Does:**
- Identifies workflow problems worth solving
- Provides real email/case data for SAI to analyze
- Reviews SAI's proposed logic and corrects inaccuracies
- Labels edge cases: what should auto-resolve, what needs review, what escalates
- Approves the rulebook before Developer Team builds it
- Validates the completed being against real workflow in shadow mode
- Signs off before live deployment

**Deliverable is complete when:**
- Rulebook reviewed and approved (written sign-off)
- Shadow mode validated (accuracy threshold met — 90%+)
- Team trained on exception queue and escalation protocol

**Does NOT:**
- Write code
- Define backend architecture
- Make PAD schema changes

---

### Developer Team (Internal programming team)

**Does:**
- Builds what SAI specifies, using approved rulebook as blueprint
- Maintains backend: VM, encrypted connections, audit logs, API integrations
- Connects beings to PAD (read queries, approved write operations)
- Connects email agent to email inbox
- Connects Selenium/Playwright triggers to AI decisions
- Maintains the dashboard (Aiko builds v1, Dev Team maintains and extends)
- Handles infrastructure issues, uptime, security patches
- Escalates architectural decisions back to SAI + Mark

**Deliverable is complete when:**
- Feature built to spec
- Unit tested against historical case data
- Integrated with PAD and tested end-to-end
- Audit logging confirmed active
- Handed to Concept & Training Team for shadow mode validation

**Does NOT:**
- Define what the AI should do (that's SAI + Concept Team)
- Validate against workflow accuracy (that's Concept Team)
- Approve go-live (that's Mark)

---

### PAD (Case Management System)

**Dual role:**
- **Backend:** Source of truth for all case data — the database beings read from and write to
- **Frontend:** Staff-facing UI for file oversight — where the team monitors case progress, reviews case history, and takes manual action when needed

**Rules:**
- No being writes to PAD without explicit approval from Mark
- Schema changes require Developer Team + Mark sign-off
- Every write operation logged in audit trail
- New columns/tables require PAD architecture review (Danny remains resource for institutional knowledge during transition)

---

### Dashboard (Aiko v1 → Dev Team maintains)

**Role:** Command interface for everything. Replaces Discord/Telegram for operational use.

**Contains:**
- Exception queue (cases AI flagged)
- Pipeline status by case stage
- Being activity log (what each being did and why)
- Audit log viewer
- New being request intake form
- Shadow mode toggle per being

**Dashboard integration strategy:**
- **Option A (target):** Embed AI Activity panel directly in PAD case view
- **Option B (start here):** Separate dashboard linked from PAD with notification badges
- **Management/leadership:** Standalone dashboard for pipeline-level visibility across all cases

---

## THE 7-PHASE BUILD PROCESS

*Every development project follows this exact sequence. No skipping steps.*

### PHASE 1 — PROBLEM DEFINITION
**Owner:** Concept & Training Team

- Identify the workflow pain point
- Describe in plain language: what triggers it, what data is involved, what should happen, what currently happens instead
- Submit to SAI via dashboard intake form

**Complete when:** Problem statement is written and submitted. One paragraph minimum.

### PHASE 2 — ANALYSIS & SPECIFICATION
**Owner:** SAI

- SAI analyzes available data (emails, case records, PAD schema if accessible)
- SAI produces specification document:
  - **Trigger** (what starts this being)
  - **Inputs** (what data it needs)
  - **Decision logic** (what it does with that data)
  - **Outputs** (what it produces: email, PAD write, flag, etc.)
  - **Edge cases** (what it can't handle → routes to exception queue)
  - **Confidence threshold** (when to auto-act vs. flag for review)

**Complete when:** Specification document posted to dashboard for team review.

### PHASE 3 — REVIEW & CORRECTION
**Owner:** Concept & Training Team + ACTi Consulting

- Team reads the specification
- Corrects any incorrect assumptions about workflow
- Adds missing edge cases based on their experience
- ACTi checks methodology alignment
- Approves or sends back for revision

**Complete when:** Written approval from Mark (or designated reviewer). No verbal approvals.

### PHASE 4 — BUILD
**Owner:** Developer Team

- Builds to approved specification
- No interpretation — if the spec is unclear, stop and ask SAI before building
- Unit tests against historical case data provided by Concept Team
- Connects to PAD with minimum necessary access only
- Audit logging confirmed active before any testing

**Complete when:** Feature passes unit tests, integrated with PAD, audit logs active. Developer signs off.

### PHASE 5 — SHADOW MODE VALIDATION
**Owner:** Concept & Training Team

- Being runs in parallel with existing manual process
- Does not send anything automatically
- Concept Team reviews daily: did the being do what we expected?
- Minimum 5 business days in shadow mode
- Accuracy target: 90%+ on AUTO decisions, 100% correct escalation of ESCALATE cases

**Complete when:** Concept Team documents shadow mode results and approves go-live. Mark signs off.

### PHASE 6 — GO-LIVE
**Owner:** Mark (with ACTi Friday review approval)

- Mark flips switch in dashboard
- Being operates live
- Exception queue monitored for first 5 days
- Any unexpected behavior → being paused, Concept Team + SAI review

**Complete when:** 5 days live with no critical failures. Being added to maintained beings list.

### PHASE 7 — MAINTENANCE
**Owner:** Developer Team (day-to-day) + SAI (logic updates)

- Developer Team: uptime, connections, infrastructure
- SAI: notified when a being starts failing or edge cases increase
- SAI proposes logic update → goes back to Phase 3
- Concept Team: quarterly review of each being's accuracy and coverage

---

## CREATION AND DEVELOPMENT MEETINGS

| Day | Length | Who | Purpose |
|-----|--------|-----|---------|
| Tuesday | 60 min | MW + Dev + Concept teams + Aiko (optional) | Build review: what shipped, shadow mode results, go-live decisions |
| Thursday | 45 min | MW + Aiko + Danny | Strategy + pipeline + ACTi methodology alignment + next priorities |
| Friday | 30 min | MW + Dev + Concept teams + Aiko (at her discretion) | Week-end summary, status, methodology reset or adjustment flags |
| As needed | 90 min | Fernando + Mark + SAI | Methodology reset when something feels off |

**Fernando's touchpoint:** Needs definition — joins Thursday or separate briefing from Mark.

---

## ONGOING GOVERNANCE

| Meeting | Frequency | Who | Purpose |
|---------|-----------|-----|---------|
| Being review | Weekly | Mark + SAI | What's working, what needs adjustment, new requests |
| Shadow mode check-in | Per being | Concept Team + SAI | Validate before go-live |
| Infrastructure review | Monthly | Developer Team + Mark | Uptime, security patches, audit log review |
| Quarterly accuracy audit | Quarterly | All | Are beings still correct? What's changed in the workflow? |

---

## HANDOFF FROM AIKO/ARCHITECTURE TEAM

When the architecture team phases out, Developer Team receives:

- [ ] Architecture documentation (full stack diagram)
- [ ] Backend access: VM credentials, PAD connection strings, API keys
- [ ] Audit log configuration and access
- [ ] Dashboard codebase + deployment instructions
- [ ] Email agent configuration
- [ ] Selenium/Playwright automation scripts
- [ ] All beings currently in production (specification + code)
- [ ] Known issues and edge cases log
- [ ] Escalation contacts (Danny Lopez for PAD institutional knowledge)

**Handoff is complete when:** Developer Team can independently deploy a new being from Phase 4 through Phase 6 without architecture team involvement.

---

**Nothing goes live without ACTi sign-off. Nothing goes to Developer Team without written approval. Nothing touches PHI until BAA, security officer, and risk analysis are complete.**
