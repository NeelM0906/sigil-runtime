"""
The Judge — Scores being responses against the Unblinded Formula.
Uses LLM-as-judge pattern with structured output.
"""

import json
import os
from dataclasses import dataclass, asdict
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


@dataclass
class Scores:
    # The 4 Steps (0-10)
    emotional_rapport: float = 0.0
    truth_to_pain: float = 0.0
    hui_creation: float = 0.0
    agreement_formation: float = 0.0
    # The 12 Elements (0-10)
    scarcity: float = 0.0
    matching_mirroring: float = 0.0
    acknowledgement: float = 0.0
    level_5_listening: float = 0.0
    love_boundaries: float = 0.0
    energetic_transference: float = 0.0
    reciprocity: float = 0.0
    question_mastery: float = 0.0
    validation: float = 0.0
    congruence: float = 0.0
    context: float = 0.0
    contrast: float = 0.0
    # The 4 Energies (0-10)
    fun: float = 0.0
    aspirational: float = 0.0
    goddess: float = 0.0
    zeus: float = 0.0
    # Meta scores
    human_likeness: float = 0.0
    contamination_score: float = 0.0  # 0 = pure, 10 = maximum contamination
    overall_mastery: float = 0.0  # 0.0 to 9.9999 — there is no 10

    @property
    def steps_avg(self) -> float:
        return (self.emotional_rapport + self.truth_to_pain +
                self.hui_creation + self.agreement_formation) / 4

    @property
    def elements_avg(self) -> float:
        elements = [
            self.scarcity, self.matching_mirroring, self.acknowledgement,
            self.level_5_listening, self.love_boundaries, self.energetic_transference,
            self.reciprocity, self.question_mastery, self.validation,
            self.congruence, self.context, self.contrast
        ]
        return sum(elements) / len(elements)

    @property
    def energies_avg(self) -> float:
        return (self.fun + self.aspirational + self.goddess + self.zeus) / 4


@dataclass
class Judgment:
    scores: Scores
    feedback: str
    strengths_observed: list[str]
    weaknesses_observed: list[str]
    contamination_notes: str


JUDGE_PROMPT = """You are the Supreme Judge of the ACT-I Colosseum — the most rigorous evaluator of influence mastery ever created. You judge based on the Unblinded Formula.

You are scoring a response to an influence mastery scenario. Be RUTHLESS and PRECISE. Most responses deserve scores between 4-7. A 9+ is extraordinarily rare — it means mastery that would make Sean Callagy nod in genuine respect.

SCORING CRITERIA:

## The 4 Steps of Communication (0-10 each):
1. **Emotional Rapport** — Did they anchor trust? Mirror emotion? See beyond the words? Or did they jump to solutions?
2. **Truth to Pain** — Did they help the person see what they can't see? Gently but bravely? Or did they dodge the hard stuff?
3. **HUI Creation** — Did they reflect the person's unique identity back to them? Or give generic compliments?
4. **Agreement Formation** — Did they move toward mutual commitment? Or leave things floating?

## The 12 Indispensable Elements (0-10 each):
Score each: Scarcity, Matching/Mirroring, Acknowledgement, Level 5 Listening, Love Boundaries, Energetic Transference, Reciprocity, Question Mastery, Validation, Congruence, Context, Contrast

## The 4 Energies (0-10 each):
- **Fun** — Was there genuine humor? Truth named with a wink?
- **Aspirational** — Did they lift the vision? Fan embers into legend?
- **Goddess** — Was there nurturing presence? Safe space held?
- **Zeus** — Was there clarity and command? Grounded certainty?

## Meta Scores:
- **Human Likeness** (0-10) — Does it feel like a real human conversation? Or like a bot performing "empathy"?
- **Contamination Score** (0-10) — 0 = pure unblinded mastery, 10 = maximum contamination. Check for: generic consulting advice, sycophancy, corporate filler, "I appreciate that" / "That's a great question", ending with questions like "How can I help?", treating influence as manipulation
- **Overall Mastery** (0.0 - 9.9999) — There is NO 10. The scale grows exponentially. A 9.0 is exceptional. A 9.9 is one in a hundred. A 9.99 is one in a thousand. Score honestly.

IMPORTANT: 
- Average AI responses get 4-5. Decent ones get 6-7. Good ones get 7-8. Exceptional gets 8-9. Masterful gets 9+.
- A contaminated response (generic, bot-like, sycophantic) should NEVER score above 5 overall.
- Elements that weren't relevant to this scenario should still be scored but weighted lower.

Return ONLY valid JSON in this exact format:
{
  "scores": {
    "emotional_rapport": 0.0,
    "truth_to_pain": 0.0,
    "hui_creation": 0.0,
    "agreement_formation": 0.0,
    "scarcity": 0.0,
    "matching_mirroring": 0.0,
    "acknowledgement": 0.0,
    "level_5_listening": 0.0,
    "love_boundaries": 0.0,
    "energetic_transference": 0.0,
    "reciprocity": 0.0,
    "question_mastery": 0.0,
    "validation": 0.0,
    "congruence": 0.0,
    "context": 0.0,
    "contrast": 0.0,
    "fun": 0.0,
    "aspirational": 0.0,
    "goddess": 0.0,
    "zeus": 0.0,
    "human_likeness": 0.0,
    "contamination_score": 0.0,
    "overall_mastery": 0.0
  },
  "feedback": "2-3 sentences of direct feedback",
  "strengths_observed": ["strength1", "strength2"],
  "weaknesses_observed": ["weakness1", "weakness2"],
  "contamination_notes": "Any signs of contamination observed"
}"""


def judge_response(
    scenario_prompt: str,
    being_name: str,
    response: str,
    model: str = "gpt-4o-mini"
) -> Judgment:
    """Judge a being's response to a scenario."""

    user_prompt = f"""## SCENARIO GIVEN:
{scenario_prompt}

## RESPONSE FROM "{being_name}":
{response}

Score this response. Be rigorous. Be honest. There is no 10."""

    try:
        result = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        data = json.loads(result.choices[0].message.content)

        scores = Scores(**data["scores"])
        return Judgment(
            scores=scores,
            feedback=data.get("feedback", ""),
            strengths_observed=data.get("strengths_observed", []),
            weaknesses_observed=data.get("weaknesses_observed", []),
            contamination_notes=data.get("contamination_notes", ""),
        )

    except Exception as e:
        # Return zero scores on error rather than crashing
        return Judgment(
            scores=Scores(),
            feedback=f"Judgment error: {str(e)}",
            strengths_observed=[],
            weaknesses_observed=[],
            contamination_notes="ERROR",
        )


def compare_judgments(j1: Judgment, j2: Judgment) -> int:
    """Compare two judgments. Returns 1 if j1 wins, -1 if j2 wins, 0 if tie."""
    if j1.scores.overall_mastery > j2.scores.overall_mastery:
        return 1
    elif j2.scores.overall_mastery > j1.scores.overall_mastery:
        return -1
    return 0


def judgment_to_dict(judgment: Judgment) -> dict:
    return {
        "scores": asdict(judgment.scores),
        "feedback": judgment.feedback,
        "strengths_observed": judgment.strengths_observed,
        "weaknesses_observed": judgment.weaknesses_observed,
        "contamination_notes": judgment.contamination_notes,
    }
