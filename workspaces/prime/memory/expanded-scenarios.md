# Expanded Colosseum Scenarios Report
**Date:** 2026-02-23
**Created by:** Sai Miner 4

## Summary
Created **108 company-specific scenarios** for the Colosseum training system. Saved to `./workspaces/prime/Projects/colosseum/v2/data/scenarios_expanded.json`.

## Breakdown by Company

### Callagy Recovery (36 scenarios)
**Categories covered:**
- **Provider Objections (9):** From basic "why contingency" to hospital procurement committees to national health system RFP
- **Insurance Carrier Negotiations (9):** Basic payment follow-ups through multi-state settlement negotiations
- **IDR Attribution Positioning (4):** Explaining IDR, countering skepticism, expert witness prep, landmark case strategy
- **No-Win-No-Fee Conversations (5):** First discovery calls through PE acquisition due diligence
- **Medical Practice Post-Plan Discovery (5):** Finding hidden revenue through proactive revenue protection systems

**Highlight scenarios:**
- `cr_platinum_carrier_negotiation_1`: Multi-state $8M settlement negotiation with carrier's legal team
- `cr_platinum_provider_objection_1`: 20-minute CEO conversation with $2B health system
- `cr_gold_carrier_negotiation_2`: Negotiate $2.1M global settlement

### Unblinded (36 scenarios)
**Categories covered:**
- **Immersion Enrollment (9):** First webinar follow-up through famous skeptic conversion
- **Coaching Resistance (8):** "I already know this" through client facing business failure
- **Shared Experience Design (5):** 2-hour mixers to signature 500-person annual events
- **Influence Mastery Teaching (7):** 4-Step Communication through media training for major podcast
- **Ecosystem Merger Opportunities (7):** Identifying partners through business school strategic partnerships

**Highlight scenarios:**
- `ub_platinum_coaching_resistance_1`: Coaching client through potential business failure/bankruptcy
- `ub_platinum_shared_experience_1`: Design the flagship annual 500-person event
- `ub_gold_influence_mastery_1`: Coach client through $2M negotiation tomorrow

### ACT-I (36 scenarios)
**Categories covered:**
- **Product Demos (8):** Small business demos through Fortune 100 executive team and live conference main stage
- **Enterprise Sales (8):** First discovery calls through closing $5M deals
- **Technical Objection Handling (6):** Chatbot skepticism through regulated bank security reviews
- **Agents-Building-Agents Explanation (5):** Simple explanations through industry keynote for 2,000 people
- **Partnership Pitches (9):** Integration partners through Fortune 500 joint ventures

**Highlight scenarios:**
- `acti_platinum_enterprise_sales_1`: Close $5M 3-year enterprise deal in final negotiations
- `acti_platinum_product_demo_2`: Live demo on main stage at 5,000 person conference
- `acti_gold_partnership_pitch_1`: Strategic alliance negotiation with major cloud provider

## Difficulty Distribution

| Level    | Count | Description |
|----------|-------|-------------|
| Bronze   | 27    | Foundational skills, clear success paths |
| Silver   | 27    | Multi-faceted challenges, requires adaptation |
| Gold     | 27    | Complex stakeholder dynamics, high stakes |
| Platinum | 27    | Career-defining moments, multiple failure modes |

## Scenario Format
Each scenario follows the original Colosseum format:
```json
{
  "title": "Descriptive title",
  "company": "Callagy Recovery | Unblinded | ACT-I",
  "difficulty": "bronze | silver | gold | platinum",
  "category": "specific category",
  "situation": "Context and challenge",
  "person": {
    "name": "Who you're interacting with",
    "role": "Their position/context",
    "concern": "What they're worried about",
    "hot_button": "What will unlock them"
  },
  "success_criteria": "Clear win condition"
}
```

## Key Design Decisions
1. **Balanced distribution** across all three companies (36 each)
2. **Real company contexts** - scenarios reference actual business models (contingency recovery, immersion programs, AI beings)
3. **Progressive difficulty** - Bronze teaches fundamentals, Platinum tests mastery under pressure
4. **Named characters** - Creates immersive role-play scenarios
5. **Clear success criteria** - Enables objective scoring by judges

## Integration Notes
- These extend the existing `scenarios.json` (38 scenarios)
- Combined total: **146 scenarios** available for Colosseum training
- Categories can be used to filter by training focus
- Difficulty levels enable progressive skill development

## Files
- **Source:** `./workspaces/prime/Projects/colosseum/v2/data/scenarios_expanded.json`
- **Existing:** `./workspaces/prime/Projects/colosseum/v2/data/scenarios.json`
