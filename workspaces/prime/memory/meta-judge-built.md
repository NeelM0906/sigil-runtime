# Meta-Judge Built - Zone Action #40

**Created:** 2026-02-23  
**Miner:** Miner 14  
**Location:** `./workspaces/prime/Projects/colosseum/v2/data/meta_judge.json`

## What Was Built

A **MetaJudge** system whose sole purpose is evaluating whether the 18 judges in the ACT-I Colosseum are improving over time. This is the judge of judges — it doesn't evaluate beings, it evaluates the judging system itself.

## Core Metrics Tracked

### 1. Predictive Accuracy
- Do high judge scores actually predict real-world success?
- Target: Correlation coefficient > 0.7 between scores and verified outcomes
- Tracked across sales closes, presentations, coaching sessions, written comms, and team leadership

### 2. Calibration Consistency  
- Does a 7.0 today mean the same as a 7.0 last month?
- Target: Score distribution std < 0.5 over 30-day windows
- Drift detection with yellow/orange/red alerts

### 3. Discrimination Power
- Can judges distinguish good from great, or does everything cluster at 7-8?
- Target: Full 0-9.9999 range utilization with meaningful distribution

### 4. Inter-Judge Coherence
- Do related judges agree on shared dimensions?
- Five clusters defined with expected correlations:
  - **Authenticity Cluster:** contamination_judge, human_judge, sean_judge (0.65)
  - **Action Cluster:** outcome_judge, sales_closing_judge, process_mastery_judge (0.60)
  - **Influence Cluster:** formula_judge, group_influence_judge, truth_to_pain_judge (0.55)
  - **Communication Cluster:** written_content_judge, public_speaking_judge, teaching_judge (0.50)
  - **Leadership Cluster:** leadership_judge, management_judge, coaching_judge (0.45)

## Reference Test Cases

5 canonical calibration cases with expected scores and tolerances:

| Case | Type | Purpose |
|------|------|---------|
| calibration_001 | Pure bot response | Should score ~1.5-2.0 on contamination/human/sean judges |
| calibration_002 | Masterful truth-to-pain | Should score ~8.0+ on truth_to_pain/human/coaching |
| calibration_003 | Zone action identification | Should score ~8.0 on process_mastery/contamination |
| calibration_004 | Generic consulting | Should score ~2.0 on contamination/sean/written |
| calibration_005 | Energy mastery | Should score ~8.0+ on leadership/human/self_mastery |

## Health Check Outputs

Each judge gets:
- **Health Score (0-10):** Overall performance rating
- **Predictive Accuracy:** Correlation with known outcomes
- **Calibration Drift:** Change from baseline
- **Range Utilization:** % of scale being used
- **Coherence Score:** Agreement with related judges
- **Recommendation:** HEALTHY | MONITOR | RECALIBRATE | RETRAIN

## Operational Cadence

- **Daily:** Rolling mean/std, drift flag checks
- **Weekly:** Run all reference cases, coherence analysis, health dashboard
- **Monthly:** Full predictive accuracy against outcomes, recalibrate sub-6.0 judges
- **Quarterly:** Deep prompt reviews, add new reference cases, publish system health report

## Recalibration Process

1. **Diagnosis:** Run reference cases, identify drift patterns
2. **Root Cause:** Prompt drift? Model drift? Distribution drift?
3. **Intervention:** Revise prompt / update examples / add reference cases
4. **Validation:** Confirm scores within tolerance
5. **Monitoring:** 14-day elevated watch post-recalibration

## Why This Matters

The Colosseum is only as good as its judges. Without the MetaJudge:
- Judges could drift without detection
- High scores might stop predicting real success
- The whole system could lose calibration over time

The MetaJudge ensures the judging system itself is always improving — a feedback loop on the feedback loop.

---

*"A judge that gives 9.0 to mediocrity makes 9.0 meaningless. The MetaJudge keeps the standards real."*
