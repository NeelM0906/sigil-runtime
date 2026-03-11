# Sean Questions — Scholar Answers (12:36–12:57 session context)
Date: 2026-02-28
Owner: SAI Scholar

This answer set is based on Sean’s PDF methodology + the voice-note directives relayed in chat.

## Q1) Create 20 different campaigns as competitions — what are they?
**Recommendation (structured):** 20 campaigns = 10 categories × 2 leaderboard modes.

**10 competition categories (lawyer vertical):**
1. **Hook/Subject-line wars** (open trigger)
2. **Email sequence wars (5-touch)** (attention → trust → agreement)
3. **SMS micro-agreement wars** (reply trigger)
4. **Landing page headline wars**
5. **Case value narrative wars** (truth-to-pain specificity)
6. **Objection-handling wars** (e.g., “AI replaces me”, “too busy”, “not now”)
7. **Identity elevation wars** (heroic identity without brag)
8. **Referral/relationship reactivation wars**
9. **Webinar invite + follow-up wars**
10. **Benchmark/assessment invitation wars** (“Come Get Me” scoreboard)

**2 leaderboard modes (each category runs twice):**
- **Anonymous leaderboard** (low-friction participation)
- **Public/Named leaderboard** (status + competition)

## Q2) Geo testing (city vs state) — how?
- Use contact list segmentation (city/state) to generate:
  - **City board** (e.g., Dallas PI attorneys)
  - **State board** (Texas PI attorneys)
- Run the same competition in both segments; compare:
  - opt-in rate
  - completion rate
  - follow-up conversion (agreement)

## Q3) Anonymous vs public leaderboards — what to test?
- Default to **anonymous** for initial adoption.
- Offer **opt-in named** after first win / high rank.
- Test:
  - engagement lift from naming
  - drop-off from privacy concerns

## Q4) 10 different copy versions per competition — structure?
- Use chained tournament brackets: A vs B → winner vs C → winner vs D … (Sean’s AAA vs DDB concept).
- Keep a stable rubric (4-Step scoring) so the tournament is comparable.

## Q5) 3/4/5 minute versions — what is a “minute” in async?
- Translate “3/4/5 minute” into **touch-count** and **attention-time**:
  - 3-min = 3 touches (Hook → Truth/Pain → Agreement)
  - 4-min = 4 touches (add Heroic ID)
  - 5-min = 5 touches (add proof + deeper identity)

## Q6) When do we go live with humans?
- As soon as:
  1) leaderboard UI is stable
  2) segmentation list exists
  3) opt-in/compliance guardrails defined
- Start with **small pilot** (e.g., 50–100 Dallas lawyers) before broad rollouts.

## Q7) Incentive model (free vs paid)?
- **Free** to enter + see anonymized ranking.
- **Paid / invite-only** for:
  - full personalized breakdown
  - “Milo with your bio” consult
  - private board access / VIP cohort

## Q8) 10 different test categories for lawyers?
- See the 10 categories above (Q1).

## Q9) What are the core principles to encode into judges?
- **Short answers = investigate**
- **Elephant = Zone Action**
- **4-1-2-4** ordering must be respected
- **No 10.0** (9.99 pursuit)
- **Bio-based acknowledgment** (SimHumans from real LinkedIn profiles)

## Dependencies / blockers (truth)
- Pinecone embeddings were blocked earlier by OpenAI quota; **now can route embeddings via OpenRouter**.
- Whisper audio transcription cannot route via OpenRouter; use local Whisper until OpenAI billing restored.
