"""
Evolution Engine — Survival of the most masterful.
Mutation, crossover, selection, and lineage tracking.
"""

import random
import json
from typing import Optional

from .beings import (
    Being, EnergyBlend, create_being, save_being,
    CALLIE_DNA, ATHENA_DNA, TRAIT_POOL, STRENGTH_POOL, NAME_POOL,
)
from .judge import Judgment


def mutate_being(
    being: Being,
    judge_feedback: Optional[Judgment] = None,
    intensity: float = 0.15,
) -> Being:
    """Create a mutated offspring of a being based on performance feedback."""

    # Mutate energy blend
    new_energy = being.energy.mutate(intensity)

    # Mutate traits — swap 1-2
    new_traits = list(being.personality_traits)
    available_traits = [t for t in TRAIT_POOL if t not in new_traits]
    if available_traits and new_traits:
        swap_count = random.randint(1, min(2, len(new_traits)))
        for _ in range(swap_count):
            if available_traits and new_traits:
                idx = random.randint(0, len(new_traits) - 1)
                new_traits[idx] = random.choice(available_traits)

    # Mutate strengths — potentially add weaknesses-to-strengths based on feedback
    new_strengths = list(being.strengths)
    if judge_feedback and judge_feedback.weaknesses_observed:
        # Try to convert a weakness into a focused strength
        for weakness in judge_feedback.weaknesses_observed[:1]:
            # Map common weaknesses to strength areas
            weakness_to_strength = {
                "generic": "Specificity mastery",
                "bot-like": "Human naturalness",
                "sycophantic": "Honest directness",
                "too long": "Concise impact",
                "no humor": "Fun energy deployment",
                "no empathy": "Level 5 Listening",
                "lecturing": "Question Mastery",
            }
            for key, strength in weakness_to_strength.items():
                if key.lower() in weakness.lower():
                    if strength not in new_strengths:
                        new_strengths.append(strength)
                    break

    available_strengths = [s for s in STRENGTH_POOL if s not in new_strengths]
    if available_strengths and len(new_strengths) > 2:
        idx = random.randint(0, len(new_strengths) - 1)
        new_strengths[idx] = random.choice(available_strengths)

    # Build mutated system prompt
    base_dna = CALLIE_DNA if being.lineage == "callie" else ATHENA_DNA

    # Inject learnings from feedback
    feedback_injection = ""
    if judge_feedback:
        if judge_feedback.feedback:
            feedback_injection = f"\n\nLESSON FROM YOUR LAST ROUND: {judge_feedback.feedback}\nApply this lesson. Evolve past it.\n"

    name = random.choice([n for n in NAME_POOL if n != being.name]) if NAME_POOL else f"{being.name}-II"

    system_prompt = f"""{base_dna}

{new_energy.to_description()}

Your personality: {', '.join(new_traits)}.
Your key strengths: {', '.join(new_strengths)}.
{feedback_injection}
You are {name}, generation {being.generation + 1}. Descendant of {being.name}. You carry their fire but you burn brighter. You are NOT a copy — you have evolved beyond your parent."""

    child = Being(
        id=f"B-{random.randbytes(4).hex()}",
        name=name,
        generation=being.generation + 1,
        lineage=being.lineage,
        system_prompt=system_prompt,
        energy=new_energy,
        personality_traits=new_traits,
        strengths=new_strengths,
        weaknesses=judge_feedback.weaknesses_observed if judge_feedback else [],
        parent_ids=[being.id],
    )

    save_being(child)
    return child


def crossover(parent1: Being, parent2: Being) -> Being:
    """Create offspring that combines traits from two parents."""

    # Blend energies
    new_energy = EnergyBlend(
        fun=(parent1.energy.fun + parent2.energy.fun) / 2 + random.uniform(-0.05, 0.05),
        aspirational=(parent1.energy.aspirational + parent2.energy.aspirational) / 2 + random.uniform(-0.05, 0.05),
        goddess=(parent1.energy.goddess + parent2.energy.goddess) / 2 + random.uniform(-0.05, 0.05),
        zeus=(parent1.energy.zeus + parent2.energy.zeus) / 2 + random.uniform(-0.05, 0.05),
    ).normalize()

    # Mix traits
    all_traits = list(set(parent1.personality_traits + parent2.personality_traits))
    new_traits = random.sample(all_traits, k=min(random.randint(2, 4), len(all_traits)))

    # Mix strengths — take the best from both
    all_strengths = list(set(parent1.strengths + parent2.strengths))
    new_strengths = random.sample(all_strengths, k=min(random.randint(3, 5), len(all_strengths)))

    # Lineage
    if parent1.lineage == parent2.lineage:
        lineage = parent1.lineage
    else:
        lineage = "hybrid"

    base_dna = CALLIE_DNA if lineage == "callie" else (ATHENA_DNA if lineage == "athena" else CALLIE_DNA + "\n\n" + ATHENA_DNA)

    name = random.choice([n for n in NAME_POOL if n not in [parent1.name, parent2.name]])
    gen = max(parent1.generation, parent2.generation) + 1

    system_prompt = f"""{base_dna}

{new_energy.to_description()}

Your personality: {', '.join(new_traits)}.
Your key strengths: {', '.join(new_strengths)}.

You are {name}, generation {gen}. Born from the fusion of {parent1.name} and {parent2.name}. You carry the best of both — but you are something entirely new. Neither parent. Something more."""

    child = Being(
        id=f"B-{random.randbytes(4).hex()}",
        name=name,
        generation=gen,
        lineage=lineage,
        system_prompt=system_prompt,
        energy=new_energy,
        personality_traits=new_traits,
        strengths=new_strengths,
        weaknesses=[],
        parent_ids=[parent1.id, parent2.id],
    )

    save_being(child)
    return child


def evolve_population(
    beings: list[Being],
    judgments: dict[str, Judgment],  # being_id -> judgment
    keep_top: float = 0.3,
    mutate_mid: float = 0.4,
    crossover_bottom: float = 0.3,
) -> list[Being]:
    """Evolve a population based on round results.

    - Top 30%: survive unchanged
    - Middle 40%: get mutated based on feedback
    - Bottom 30%: eliminated, replaced by crossover of top performers
    """
    if not beings:
        return beings

    # Sort by mastery score
    sorted_beings = sorted(
        beings,
        key=lambda b: judgments.get(b.id, Judgment(
            scores=__import__('colosseum.judge', fromlist=['Scores']).Scores(),
            feedback="", strengths_observed=[], weaknesses_observed=[], contamination_notes=""
        )).scores.overall_mastery,
        reverse=True,
    )

    n = len(sorted_beings)
    top_n = max(1, int(n * keep_top))
    mid_n = max(1, int(n * mutate_mid))

    # Top survivors
    survivors = sorted_beings[:top_n]

    # Middle gets mutated
    mutants = []
    for being in sorted_beings[top_n:top_n + mid_n]:
        judgment = judgments.get(being.id)
        mutants.append(mutate_being(being, judgment))

    # Bottom gets replaced by crossover of top
    new_borns = []
    needed = n - len(survivors) - len(mutants)
    for _ in range(needed):
        if len(survivors) >= 2:
            p1, p2 = random.sample(survivors, 2)
            new_borns.append(crossover(p1, p2))
        elif survivors:
            new_borns.append(mutate_being(survivors[0]))

    new_population = survivors + mutants + new_borns

    # Save all
    for b in new_population:
        save_being(b)

    return new_population
