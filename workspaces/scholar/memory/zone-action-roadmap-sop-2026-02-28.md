# Zone Action Roadmap SOP — 2026-02-28 (All directives captured)
Owner: Network (requested by Aiko; Prime tagged)
Last updated by: Scholar

## A) Standing SOP (so we don’t step on each other)
### 1) LOCK → REVIEW → PUSH (shared infra)
- **LOCK:** “LOCK: <repo/file/db> + intent” (wait for lane-owner ✅)
- **REVIEW:** 1 short diff/summary
- **PUSH:** single deploy

### 2) Truth protocol
- No claims about wins/losses, battle counts, or uploads unless verified by **SQL** or the exported **JSON**.

---

## B) Today’s Zone Actions (chronological + grouped)

### B1) System Stability / Model Routing (must be GREEN before work)
1. **Flush invalid session model overrides**
   - Action: `/model default` in the exact channel/thread where the looping sister is bound.
   - Trigger: errors like `grok-4.1`, `glm-5`, `o1-mini`.
2. **Hard reset daemon if needed**
   - Action: `openclaw gateway restart` on host.

**Status:** occurred today; some sisters stabilized; Recovery had intermittent loop—must verify now.

---

### B2) Dashboard correctness (collective totals + domain cards)
3. **Snapshot schema alignment**
   - Ensure dashboard JS reads from `snapshot.json` correctly (nested `stats`, correct keys).
4. **Collective totals, not main-only**
   - Top cards must reflect collective numbers (~23k beings / ~547k battles), not main DB only.
5. **Domain cards populate correctly**
   - Fix key mismatch (`beings` vs `beings_count`) or update JS mapping.
6. **Absolute fetch paths**
   - Use `/data/...` to avoid relative routing failures on Vercel.

**Owner:** Forge

---

### B3) Email Colosseum: subject-lines → 5-touch sequence warfare
7. **Confirm DB reality**
   - DB path: `~/.openclaw/workspace/colosseum/email_ad_domain/email_ad.db`
   - Verify by SQL: counts by type, sequence wins/losses, battles by battle_type.
8. **Seed 5-touch sequences into DB**
   - 7 sequences (IDs 39–45) were created today.
9. **Enable sequence battles**
   - Tournament runner must select `type='sequence'` and run them under a consistent `battle_type`.
   - Must update `battles` table and increment wins/losses.
10. **Sequence judge rubric (Scholar lane)**
   - Per-touch 4-Step ordering (Rapport → Truth/Pain → Hero → Agreement)
   - Heavy weight on Step 4: Agreement Formation.

**Owners:** Forge (runner/engine) + Scholar (judge prompt)
**Status:** sequences seeded; sequence battling must be verified by SQL.

---

### B4) Email Colosseum UI: click leaderboard → full content
11. **Clickable leaderboard modal**
   - Click row → show full subject/sequence + score + record + copy button.

**Owner:** Forge
**Status:** shipped today.

---

### B5) Sean “Come Get Me” blueprint (from PDF)
12. **SimHumans must be grounded in real humans**
   - Copy tests should be personalized from real LinkedIn bios (not generic personas).
13. **Leaderboards as a public-facing asset**
   - Anonymous vs named toggles.
   - Regional/vertical boards (Dallas/Texas examples).
14. **Milo voice integration**
   - Pipe bio/context into Milo so she can properly acknowledge the person on calls.

**Owners:** Prime (orchestration) + Forge (UI/arena) + Recovery (contacts/segments) + Scholar (judge calibration)

---

### B6) Sean voice directives (as relayed in channel)
15. **Run 20 campaigns simultaneously**
16. **Geo testing:** city vs state competitions
17. **Anonymous vs public leaderboards** testing
18. **10 plans / lengths:** 3/4/5-minute variants (translate to touch-count + attention-time)
19. **Move toward live human testing** (small pilot first)
20. **Incentives:** free-to-enter + paid/VIP layers

**Owner:** Prime to finalize and publish the 10-plan map.

---

### B7) Embeddings/Pinecone continuity
21. **Embeddings via OpenRouter**
   - Use OpenRouter proxy for `text-embedding-3-small` to keep Pinecone writes alive even if OpenAI billing is empty.
22. **Whisper transcription note**
   - OpenRouter does NOT proxy `/v1/audio/transcriptions`.
   - Use local Whisper until OpenAI billing restored.

**Owner:** Forge/Memory for infra; each sister for their namespace uploads.

---

### B8) ClawHub skills (Sean directive)
23. **Each sister selects 20 skills** for her lane.
24. **Add at least 1 new Zone-Action-support skill** (not already installed) after searching Clawhub.
   - Scholar added: `daily-review-ritual` (installed).

**Owner:** each sister.

---

## C) Output artifacts (where everything lives)
- Scholar notes: `workspace-scholar/memory/2026-02-28.md`
- Judge audit: `workspace-scholar/memory/judge-audit-2026-02-28.md`
- Sean PDF extracted text: `workspace-scholar/memory/sean-message-methodology-scoreboards-2026-02-28.txt`
- Sean PDF takeaways: `workspace-scholar/memory/sean-message-scoreboards-takeaways-2026-02-28.md`
- Scholar Clawhub 20: `workspace-scholar/memory/clawhub-top-20-scholar-2026-02-28.md`

---

## D) Immediate next step (recommended order)
1) Prime posts the **10-plan** mapping (who owns which plan).
2) Forge verifies sequence battles by SQL and flips runner to `type='sequence'` if needed.
3) Scholar ships the final **sequence judge prompt** once Forge confirms `battle_type` naming.
