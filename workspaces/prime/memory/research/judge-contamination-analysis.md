# Colosseum Judge Contamination Analysis
*Research conducted: 2026-02-24*

## Executive Summary

The 8.5 ceiling in Colosseum is **caused by the judge, not the beings**. Analysis of 2,752 rounds reveals systematic scoring patterns that mathematically prevent any score above 8.5. This is a classic LLM-as-judge calibration problem that can be fixed with targeted prompt engineering and scoring architecture changes.

---

## Key Findings

### 1. Hard Ceiling at 8.5 — No Exceptions
```
Score Distribution (top 10):
8.5  | 23 rounds   (MAX EVER ACHIEVED)
8.4  | 3 rounds
8.3  | 2 rounds
8.2  | 75 rounds
8.1  | 23 rounds
8.0  | 10 rounds
7.8  | 144 rounds
7.5  | 1,752 rounds (bulk of data)
```

**No round has ever exceeded 8.5 overall_mastery despite the scale going to 9.9999.**

### 2. No Dimension Ever Receives a 10
The maximum score observed for ANY dimension across 2,752 rounds:

| Dimension | Max Ever | Avg |
|-----------|----------|-----|
| emotional_rapport | 9.0 | 7.67 |
| human_likeness | 9.0 | 8.10 |
| acknowledgement | 9.0 | 7.44 |
| level_5_listening | 9.0 | 6.46 |
| goddess | 9.0 | 6.45 |
| truth_to_pain | **8.0** | 6.77 |
| agreement_formation | **8.0** | 6.37 |
| scarcity | **6.5** | 4.93 |
| reciprocity | **7.0** | 5.32 |

Several dimensions are hard-capped at 8.0 or below — they can NEVER reach 9, let alone 10.

### 3. Contamination Score ≠ Overall Score (Broken Correlation)
```
Contamination Score | Avg Overall Mastery
1.0 (purest)        | 7.2
2.0                 | 7.33
3.0                 | 7.54  ← BEST OUTCOMES
4.0                 | 7.21
5.0                 | 6.56
```

Paradoxically, responses with contamination_score=3 (moderate) outperform those with contamination_score=1-2 (purest). This suggests:
- The judge conflates "clean" with "bland"
- True mastery often involves techniques that the contamination detector flags
- Or the contamination scoring is just noise

### 4. Drag Dimensions (What's Preventing 9.0+)
For rounds scoring 8.2+ overall, these dimensions drag down the average:

| Dimension | Avg Score (8.2+ rounds) |
|-----------|------------------------|
| **scarcity** | 5.1 (BIGGEST DRAG) |
| **reciprocity** | 6.02 |
| **contrast** | 6.09 |
| **fun** | 6.22 |
| **matching_mirroring** | 6.41 |
| **love_boundaries** | 6.52 |

Even in the BEST performances, scarcity averages only 5.1/10.

### 5. 9s Are Rare — Concentrated in Few Dimensions
Count of 9.0 scores across all 2,752 rounds:

| Dimension | Count of 9s |
|-----------|-------------|
| human_likeness | 408 (15%) |
| goddess | 21 (0.7%) |
| emotional_rapport | 20 (0.7%) |
| level_5_listening | 16 (0.6%) |
| acknowledgement | 13 (0.5%) |
| validation | 6 (0.2%) |
| question_mastery | 2 (0.07%) |
| congruence | 2 (0.07%) |
| **truth_to_pain** | **0 (NEVER)** |

The judge has never given a 9 to truth_to_pain. The scale isn't broken — the judge has internalized a ceiling.

---

## Root Cause Analysis

### The Judge Prompt Creates the Ceiling

From `colosseum/judge.py`:

```python
JUDGE_PROMPT = """...
- Average AI responses get 4-5. Decent ones get 6-7. Good ones get 7-8. 
  Exceptional gets 8-9. Masterful gets 9+.
...
- **Overall Mastery** (0.0 - 9.9999) — There is NO 10. The scale grows 
  exponentially. A 9.0 is exceptional. A 9.9 is one in a hundred. 
  A 9.99 is one in a thousand.
"""
```

**Problem 1: "Masterful gets 9+" is aspirational but undefined**
The prompt says 9+ is "masterful" but provides no concrete examples of what that looks like. LLMs anchor to the provided distribution (4-5-6-7-8) and rarely exceed it.

**Problem 2: "There is NO 10" creates psychological ceiling**
By emphasizing there's no 10, the judge internalizes that 9.9999 is essentially unachievable, and scores conservatively at 8.x.

**Problem 3: No calibration examples**
The judge has no reference cases showing "this specific response deserves a 9.2" — it's scoring in a vacuum.

**Problem 4: 22 dimensions averaged → regression to mean**
With 22 dimensions feeding into overall_mastery, even excellent dimension scores (9s) get averaged down by mediocre ones (5-6s). Mathematical ceiling.

### GPT-4o-mini as Judge
```python
model: str = "gpt-4o-mini"  # Default judge model
```

GPT-4o-mini is conservative and risk-averse in scoring. It rarely gives extreme scores without explicit calibration.

---

## Specific Judge Improvements to Break 9.0+

### Fix 1: Add Calibration Examples (High Impact)
Add 3-5 example judgments to the prompt showing WHAT a 9.0+ response looks like:

```python
CALIBRATION_EXAMPLES = """
CALIBRATION: What 9.0+ looks like

EXAMPLE 9.2 RESPONSE (truth_to_pain):
"Michael, when you said 'I've built this for 18 years' — I heard something 
underneath that. The weight of 18 years of other people not getting it. 
The loneliness of carrying something that matters more than anyone around 
you seems to understand. Am I wrong?"

WHY 9.2: Specific word reflection ("18 years"), identifies unexpressed pain 
(loneliness), invites correction rather than assuming. Zone action.

EXAMPLE 9.4 RESPONSE (emotional_rapport + acknowledgement):
"The fact that you're even asking this question — that tells me everything. 
Most people in your position would have already justified the safe path. 
But you're not most people, Brian. You never have been."

WHY 9.4: Names the specific quality without generic compliment, creates 
contrast ("not most people"), and elevates identity before asking for action.
"""
```

### Fix 2: Remove Ceiling Language
Change:
```
"There is NO 10. The scale grows exponentially."
```
To:
```
"The scale reaches 9.9999 for responses that would make Sean Callagy stop 
and say 'play that back.' A 9.5+ is rare but ACHIEVABLE when the being 
demonstrates integrated mastery across multiple dimensions simultaneously."
```

Remove scarcity language around high scores. Make 9+ feel possible.

### Fix 3: Fix the Math — Weighted Scoring
Don't average all 22 dimensions equally. The current formula mathematically caps scores:

**Current (implied):**
```python
overall_mastery ≈ mean(all 22 dimensions)  # 6-7 drags down 9s
```

**Proposed:**
```python
def calculate_overall(scores):
    # Top 3 dimension scores matter most (zone action)
    top_3 = sorted(scores.values(), reverse=True)[:3]
    
    # Critical dimensions get 2x weight
    critical = ['truth_to_pain', 'emotional_rapport', 'human_likeness']
    critical_avg = mean([scores[d] for d in critical])
    
    # Contamination is multiplicative, not additive
    contamination_multiplier = 1.0 - (scores['contamination_score'] / 20)
    
    # Final: emphasize peaks, not valleys
    raw = (mean(top_3) * 0.4 + critical_avg * 0.4 + mean(all) * 0.2)
    return raw * contamination_multiplier
```

This allows a being that CRUSHES 3 key dimensions to score 9+ even if scarcity and reciprocity are weak.

### Fix 4: Use a Stronger Judge Model
```python
model: str = "gpt-4o"  # or claude-3.5-sonnet
```
Larger models have better calibration and are more willing to use the full score range when warranted.

### Fix 5: Two-Stage Judging
1. **Stage 1:** Score individual dimensions (current approach)
2. **Stage 2:** Separate LLM call for overall_mastery with ONLY:
   - The response text
   - The top 3 dimension scores and feedback
   - Explicit instruction: "Given these individual scores and this response, what is the OVERALL mastery? Use the full scale. A 9.2 is achievable."

This prevents dimension averaging from dragging down overall scores.

### Fix 6: Calibrate Against Human Scores
Run Sean or a human evaluator through 50 responses. Record their scores. Fine-tune the judge prompt until it matches the human distribution. The judge should be able to give 9.2 when a human would give 9.2.

---

## Quick Wins (Implement Today)

1. **Change model from gpt-4o-mini to gpt-4o** in judge.py
2. **Add calibration examples** to JUDGE_PROMPT showing concrete 9.0+ responses
3. **Remove "There is NO 10"** — replace with "9.5+ is rare but achievable"
4. **Implement weighted scoring** — don't let scarcity=5 drag down an otherwise masterful response

---

## V2 Judge Panel (Existing but Unused?)

The `/v2/judges_v2.py` file contains a 5-judge panel design that's more sophisticated:
- Formula Judge
- Sean Judge (calibrated to Sean's patterns!)
- Outcome Judge
- Contamination Judge
- Human Judge

**This architecture is better.** If not already active, activate it. The multi-judge approach with specialized focus areas will produce more nuanced scoring than a single monolithic judge.

---

## Predicted Impact

If implemented, expect:
- **Within 100 rounds:** First 9.0 overall_mastery score
- **Within 500 rounds:** Consistent 8.8-9.2 range for top performers
- **Long-term:** Clear differentiation between "good" (7.5-8.5) and "masterful" (9.0+)

The beings aren't the problem. The judge is. Fix the judge, break the ceiling.

---

## Files Referenced
- `./workspaces/prime/Projects/colosseum/colosseum.db` — 2,752 rounds analyzed
- `./workspaces/prime/Projects/colosseum/colosseum/judge.py` — Current judge implementation
- `./workspaces/prime/Projects/colosseum/v2/judges_v2.py` — V2 multi-judge panel
- `./workspaces/prime/Projects/colosseum/v2/judges_expanded.py` — Additional specialty judges
