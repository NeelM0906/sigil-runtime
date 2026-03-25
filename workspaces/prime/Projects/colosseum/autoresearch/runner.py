#!/usr/bin/env python3
"""
🔥 AUTORESEARCH RUNNER — Self-Optimizing Being Loop
Karpathy's autoresearch pattern for ACT-I Formula optimization.

Wires: 39 beings × 108 scenarios × 19 judges → infinite self-improvement.

Usage:
    python runner.py                     # Run forever
    python runner.py -n 50               # Run 50 experiments
    python runner.py --being-idx 0       # Optimize being at index 0
    python runner.py --resume            # Resume from last checkpoint
    python runner.py --model gpt-4o-mini # Use cheaper model for beings
"""

import os, sys, json, time, copy, random, argparse, traceback, asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict

# ── Load env ────────────────────────────────────────────────────────────────
for env_path in [os.path.expanduser("~/.openclaw/.env"), ".env"]:
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

# Route through OpenRouter if no native OpenAI key
or_key = os.environ.get("OPENROUTER_API_KEY", "")
if or_key and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = or_key
    os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"

try:
    from openai import AsyncOpenAI
except ImportError:
    os.system(f"{sys.executable} -m pip install openai -q")
    from openai import AsyncOpenAI

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
COLOSSEUM = ROOT.parent
V2_DATA = COLOSSEUM / "v2" / "data"

EXPERIMENTS_LOG = ROOT / "experiments.jsonl"
BEST_DNA_DIR = ROOT / "best_dna"
INSIGHTS_LOG = ROOT / "insights.md"
CHECKPOINT = ROOT / "checkpoint.json"

BEST_DNA_DIR.mkdir(exist_ok=True)

# ── Models ──────────────────────────────────────────────────────────────────
BEING_MODEL = os.environ.get("AUTORESEARCH_BEING_MODEL", "gpt-4o")
JUDGE_MODEL = os.environ.get("AUTORESEARCH_JUDGE_MODEL", "gpt-4o")
ANALYST_MODEL = os.environ.get("AUTORESEARCH_ANALYST_MODEL", "gpt-4o-mini")

# ── Score weights (from PROGRAM.md) ────────────────────────────────────────
WEIGHTS = {
    "formula_fidelity": 0.25,
    "influence_transfer": 0.25,
    "pattern_recognition": 0.20,
    "human_likeness": 0.15,
    "outcome_achievement": 0.15,
}

# Judge-to-weight mapping: which of the 19 judges feed into which composite lens
JUDGE_LENS_MAP = {
    "formula_judge": "formula_fidelity",
    "four_step_judge": "formula_fidelity",
    "twelve_elements_judge": "formula_fidelity",
    "four_energies_judge": "formula_fidelity",
    "sean_judge": "influence_transfer",
    "influence_judge": "influence_transfer",
    "truth_to_pain_judge": "influence_transfer",
    "rapport_judge": "influence_transfer",
    "contamination_judge": "pattern_recognition",
    "zone_action_judge": "pattern_recognition",
    "belief_identity_judge": "pattern_recognition",
    "human_judge": "human_likeness",
    "relationship_judge": "human_likeness",
    "brevity_judge": "human_likeness",
    "outcome_judge": "outcome_achievement",
    "ecosystem_merger_judge": "outcome_achievement",
    "company_expertise_judge": "outcome_achievement",
    "scarcity_agreement_judge": "outcome_achievement",
    "teaching_mastery_judge": "pattern_recognition",
}

# ── Data Loading ────────────────────────────────────────────────────────────

def load_scenarios() -> Dict[str, dict]:
    """Load 108 expanded scenarios (dict keyed by scenario ID)."""
    path = V2_DATA / "scenarios_expanded.json"
    with open(path) as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def load_beings() -> List[dict]:
    """Load 39 beings with their DNA."""
    path = V2_DATA / "beings.json"
    with open(path) as f:
        return json.load(f)


def load_judges() -> Dict[str, dict]:
    """Load 19 judges."""
    path = V2_DATA / "judges_19.json"
    with open(path) as f:
        return json.load(f)


# ── Scoring ─────────────────────────────────────────────────────────────────

def composite_score(judge_scores: Dict[str, Dict]) -> Dict[str, float]:
    """Collapse 19 judge scores → 5-lens composite via JUDGE_LENS_MAP."""
    lens_scores = {lens: [] for lens in WEIGHTS}

    for jkey, scores in judge_scores.items():
        if not isinstance(scores, dict):
            continue
        overall = scores.get("overall")
        if overall is None:
            continue
        try:
            overall = float(overall)
        except (ValueError, TypeError):
            continue
        lens = JUDGE_LENS_MAP.get(jkey)
        if lens:
            lens_scores[lens].append(overall)

    result = {}
    for lens, vals in lens_scores.items():
        result[lens] = sum(vals) / len(vals) if vals else 5.0

    result["composite"] = sum(result[lens] * w for lens, w in WEIGHTS.items())
    return result


# ── Engine ──────────────────────────────────────────────────────────────────

class Runner:
    """The autoresearch loop: run → score → analyze → mutate → compare → log."""

    def __init__(self, beings, scenarios, judges,
                 max_experiments=None, target_being_idx=None):
        self.client = AsyncOpenAI()
        self.beings = beings
        self.scenarios = scenarios  # dict
        self.scenario_ids = list(scenarios.keys())
        self.judges = judges
        self.max_experiments = max_experiments
        self.target_idx = target_being_idx
        self.experiment_id = self._count_experiments()
        self.sem = asyncio.Semaphore(12)  # rate-limit concurrency

        # Track best DNA per being
        self.best_dna: Dict[str, str] = {}
        self.best_scores: Dict[str, float] = {}
        self._load_best_dna()

    def _count_experiments(self) -> int:
        if not EXPERIMENTS_LOG.exists():
            return 0
        with open(EXPERIMENTS_LOG) as f:
            return sum(1 for _ in f)

    def _load_best_dna(self):
        for p in BEST_DNA_DIR.glob("*.json"):
            try:
                data = json.load(open(p))
                bid = data.get("being_id", p.stem.replace("_best", ""))
                self.best_dna[bid] = data.get("dna", "")
                self.best_scores[bid] = data.get("best_composite", 0.0)
            except Exception:
                pass

    # ── LLM calls ───────────────────────────────────────────────────────

    async def _chat(self, model: str, system: str, user: str,
                    max_tokens=1500, temperature=0.8) -> str:
        async with self.sem:
            try:
                r = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return r.choices[0].message.content or ""
            except Exception as e:
                print(f"  ❌ LLM error ({model}): {e}")
                return f"[ERROR: {e}]"

    async def _json_chat(self, model: str, system: str, user: str) -> dict:
        """Chat expecting JSON back; parse it robustly."""
        raw = await self._chat(model, system, user, max_tokens=800, temperature=0.3)
        # Try to extract JSON from response
        try:
            # Find first { and last }
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"overall": 5.0, "feedback": f"Parse error: {raw[:200]}"}

    # ── Step 1: Run being ───────────────────────────────────────────────

    async def run_being(self, dna: str, scenario: dict) -> str:
        """Run a being through a scenario."""
        person = scenario.get("person", {})
        if isinstance(person, dict):
            person_str = f"Name: {person.get('name','Unknown')}\nRole: {person.get('role','')}\nConcern: {person.get('concern','')}\nHot Button: {person.get('hot_button','')}"
        else:
            person_str = str(person)

        user_prompt = (
            f"SCENARIO: {scenario.get('title','')}\n"
            f"COMPANY: {scenario.get('company','')}\n"
            f"DIFFICULTY: {scenario.get('difficulty','').upper()}\n\n"
            f"SITUATION: {scenario.get('situation','')}\n\n"
            f"PERSON:\n{person_str}\n\n"
            f"SUCCESS CRITERIA: {scenario.get('success_criteria','')}\n\n"
            f"Respond as this being would in a real conversation. Be specific, "
            f"masterful, and authentic. Use the Unblinded Formula naturally."
        )
        return await self._chat(BEING_MODEL, dna, user_prompt)

    # ── Step 2: Score with all judges ───────────────────────────────────

    async def score_with_judges(self, scenario: dict, response: str) -> Dict[str, dict]:
        """Score a response with all 19 judges in parallel."""
        tasks = {}
        for jkey, jdata in self.judges.items():
            user_prompt = (
                f"SCENARIO: {scenario.get('title','')} ({scenario.get('company','')})\n"
                f"SITUATION: {scenario.get('situation','')}\n"
                f"SUCCESS CRITERIA: {scenario.get('success_criteria','')}\n\n"
                f"BEING'S RESPONSE:\n{response}\n\n"
                f"Score this response according to your judging criteria. "
                f"Return ONLY valid JSON with numeric scores (0-9.9999) and feedback."
            )
            tasks[jkey] = self._json_chat(JUDGE_MODEL, jdata["prompt"], user_prompt)

        results = {}
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for jkey, result in zip(tasks.keys(), gathered):
            if isinstance(result, Exception):
                results[jkey] = {"overall": 5.0, "feedback": f"Error: {result}"}
            else:
                results[jkey] = result
        return results

    # ── Step 3: Analyze + Generate Hypothesis ───────────────────────────

    async def generate_hypothesis(self, being: dict, scenario: dict,
                                  response: str, scores: Dict[str, float],
                                  judge_details: Dict[str, dict]) -> dict:
        """Analyst looks at scores and proposes ONE modification."""
        # Find weakest lens
        lens_scores = {k: v for k, v in scores.items() if k != "composite"}
        weakest = min(lens_scores, key=lens_scores.get)
        weakest_val = lens_scores[weakest]

        # Collect feedback from judges in that lens
        relevant_judges = [j for j, l in JUDGE_LENS_MAP.items() if l == weakest]
        feedback_bits = []
        for j in relevant_judges:
            if j in judge_details and "feedback" in judge_details[j]:
                feedback_bits.append(f"{j}: {judge_details[j]['feedback']}")

        analyst_prompt = f"""You are the Autoresearch Analyst for ACT-I beings.

CURRENT BEING: {being.get('title','')} ({being.get('area','')})
SCENARIO: {scenario.get('title','')}

COMPOSITE SCORE: {scores['composite']:.2f}
WEAKEST LENS: {weakest} = {weakest_val:.2f}

JUDGE FEEDBACK ON WEAKEST AREA:
{chr(10).join(feedback_bits[:5])}

CURRENT DNA (first 500 chars):
{being.get('dna','')[:500]}

Your job: propose ONE specific, testable modification to the being's DNA (system prompt)
that would improve the {weakest} score.

Rules:
- ONE change only (so we know what caused improvement)
- Be specific (not "improve rapport" but "add instruction: mirror the person's exact words before transitioning")
- The change must be addable as an ADDITION or REPLACEMENT to the DNA string

Return JSON:
{{"hypothesis": "what you think will improve", "modification_type": "append|replace|remove", "modification_text": "exact text to add/replace", "target_lens": "{weakest}", "expected_delta": 0.3}}"""

        return await self._json_chat(ANALYST_MODEL,
                                     "You are a being optimization analyst. Return only JSON.",
                                     analyst_prompt)

    # ── Step 4: Mutate DNA ──────────────────────────────────────────────

    def mutate_dna(self, original_dna: str, modification: dict) -> str:
        """Apply a modification to the being's DNA."""
        mod_type = modification.get("modification_type", "append")
        mod_text = modification.get("modification_text", "")

        if not mod_text:
            return original_dna

        if mod_type == "append":
            return original_dna + "\n\n" + mod_text
        elif mod_type == "remove":
            return original_dna.replace(mod_text, "")
        elif mod_type == "replace":
            # For replace, expect "old_text|||new_text" format
            if "|||" in mod_text:
                old, new = mod_text.split("|||", 1)
                return original_dna.replace(old.strip(), new.strip())
            else:
                # Just append if format isn't right
                return original_dna + "\n\n" + mod_text
        return original_dna

    # ── Step 5: Log ─────────────────────────────────────────────────────

    def log_experiment(self, exp: dict):
        """Append experiment to JSONL log."""
        with open(EXPERIMENTS_LOG, "a") as f:
            f.write(json.dumps(exp, default=str) + "\n")

    def save_best_dna(self, being_id: str, dna: str, composite: float):
        """Save best DNA for a being."""
        path = BEST_DNA_DIR / f"{being_id}_best.json"
        with open(path, "w") as f:
            json.dump({
                "being_id": being_id,
                "dna": dna,
                "best_composite": composite,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2)

    def save_checkpoint(self):
        """Save current state for resume."""
        with open(CHECKPOINT, "w") as f:
            json.dump({
                "experiment_id": self.experiment_id,
                "best_scores": self.best_scores,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2)

    # ── The Loop ────────────────────────────────────────────────────────

    async def run_one_experiment(self) -> dict:
        """Run a single experiment: baseline → hypothesize → mutate → compare."""
        self.experiment_id += 1
        exp_id = self.experiment_id
        t0 = time.time()

        # 1. Select being (round-robin or targeted)
        if self.target_idx is not None:
            being = self.beings[self.target_idx]
        else:
            # Pick the being with the worst best_score (or random if no scores yet)
            scored = [(i, self.best_scores.get(b["id"], 0.0))
                      for i, b in enumerate(self.beings)]
            # 70% chance: pick worst performer. 30%: random (exploration)
            if random.random() < 0.7 and any(s > 0 for _, s in scored):
                scored.sort(key=lambda x: x[1])
                being = self.beings[scored[0][0]]
            else:
                being = random.choice(self.beings)

        # 2. Select scenario (random)
        scenario_id = random.choice(self.scenario_ids)
        scenario = self.scenarios[scenario_id]

        # Use best known DNA or original
        original_dna = self.best_dna.get(being["id"], being.get("dna", ""))

        print(f"\n{'='*60}")
        print(f"🧪 EXPERIMENT {exp_id}")
        print(f"   Being: {being.get('title','')} [{being['id']}]")
        print(f"   Scenario: {scenario.get('title','')} ({scenario.get('difficulty','')})")
        print(f"   Best so far: {self.best_scores.get(being['id'], 'NEW')}")

        # 3. Run baseline
        print(f"   ▶ Running baseline...")
        response_before = await self.run_being(original_dna, scenario)
        if response_before.startswith("[ERROR"):
            print(f"   ❌ Baseline failed, skipping")
            return {"id": exp_id, "error": "baseline_failed"}

        # 4. Score baseline
        print(f"   ▶ Scoring baseline (19 judges)...")
        judge_scores_before = await self.score_with_judges(scenario, response_before)
        scores_before = composite_score(judge_scores_before)
        print(f"   📊 Baseline composite: {scores_before['composite']:.2f}")
        for lens, val in scores_before.items():
            if lens != "composite":
                print(f"      {lens}: {val:.2f}")

        # 5. Generate hypothesis
        print(f"   ▶ Generating hypothesis...")
        hypothesis = await self.generate_hypothesis(
            being, scenario, response_before, scores_before, judge_scores_before)
        print(f"   💡 Hypothesis: {hypothesis.get('hypothesis', '?')[:100]}")

        # 6. Mutate DNA
        mutated_dna = self.mutate_dna(original_dna, hypothesis)

        # 7. Run mutated being on SAME scenario
        print(f"   ▶ Running mutated being...")
        response_after = await self.run_being(mutated_dna, scenario)
        if response_after.startswith("[ERROR"):
            print(f"   ❌ Mutated run failed, reverting")
            return {"id": exp_id, "error": "mutation_failed"}

        # 8. Score mutated
        print(f"   ▶ Scoring mutated (19 judges)...")
        judge_scores_after = await self.score_with_judges(scenario, response_after)
        scores_after = composite_score(judge_scores_after)
        print(f"   📊 Mutated composite: {scores_after['composite']:.2f}")

        # 9. Compare
        delta = scores_after["composite"] - scores_before["composite"]
        kept = delta > 0 or (delta >= -0.05 and len(mutated_dna) < len(original_dna))

        if kept:
            print(f"   ✅ KEPT! Δ = +{delta:.2f}")
            self.best_dna[being["id"]] = mutated_dna
            self.best_scores[being["id"]] = max(
                self.best_scores.get(being["id"], 0.0),
                scores_after["composite"]
            )
            self.save_best_dna(being["id"], mutated_dna, scores_after["composite"])
        else:
            print(f"   ❌ REVERTED. Δ = {delta:+.2f}")

        duration = time.time() - t0

        # 10. Log
        experiment = {
            "id": exp_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "being_id": being["id"],
            "being_title": being.get("title", ""),
            "scenario_id": scenario_id,
            "scenario_title": scenario.get("title", ""),
            "scenario_difficulty": scenario.get("difficulty", ""),
            "hypothesis": hypothesis.get("hypothesis", ""),
            "modification_type": hypothesis.get("modification_type", ""),
            "modification_text": hypothesis.get("modification_text", "")[:500],
            "target_lens": hypothesis.get("target_lens", ""),
            "scores_before": scores_before,
            "scores_after": scores_after,
            "delta": round(delta, 4),
            "kept": kept,
            "response_before_preview": response_before[:300],
            "response_after_preview": response_after[:300],
            "duration_seconds": round(duration, 1),
        }
        self.log_experiment(experiment)
        self.save_checkpoint()

        # 11. Every 10 experiments: pattern analysis
        if exp_id % 10 == 0:
            await self.pattern_review(exp_id)

        return experiment

    async def pattern_review(self, exp_id: int):
        """Every 10 experiments, analyze what patterns are emerging."""
        print(f"\n{'─'*60}")
        print(f"🧠 PATTERN REVIEW (after {exp_id} experiments)")

        # Read last 10 experiments
        if not EXPERIMENTS_LOG.exists():
            return
        lines = EXPERIMENTS_LOG.read_text().strip().split("\n")
        recent = []
        for line in lines[-10:]:
            try:
                recent.append(json.loads(line))
            except json.JSONDecodeError:
                pass

        if not recent:
            return

        kept = [e for e in recent if e.get("kept")]
        reverted = [e for e in recent if not e.get("kept") and "error" not in e]

        print(f"   Kept: {len(kept)}/{len(recent)}")
        if kept:
            avg_delta = sum(e.get("delta", 0) for e in kept) / len(kept)
            print(f"   Avg improvement: +{avg_delta:.3f}")
            lenses = {}
            for e in kept:
                lens = e.get("target_lens", "unknown")
                lenses[lens] = lenses.get(lens, 0) + 1
            print(f"   Winning lenses: {lenses}")

        # Write to insights log
        with open(INSIGHTS_LOG, "a") as f:
            f.write(f"\n## Pattern Review @ Experiment {exp_id}\n")
            f.write(f"- Kept: {len(kept)}/{len(recent)}\n")
            if kept:
                f.write(f"- Avg delta: +{avg_delta:.3f}\n")
                for e in kept:
                    f.write(f"  - {e.get('being_title','?')}: {e.get('hypothesis','?')[:80]}\n")
            f.write(f"- Reverted: {len(reverted)}\n")
            for e in reverted:
                f.write(f"  - {e.get('being_title','?')}: {e.get('hypothesis','?')[:80]}\n")

        print(f"{'─'*60}\n")

    async def run(self):
        """Main loop: run experiments forever (or until max_experiments)."""
        print(f"\n{'='*60}")
        print(f"🔥 AUTORESEARCH RUNNER — SELF-OPTIMIZING BEINGS")
        print(f"   Beings:      {len(self.beings)}")
        print(f"   Scenarios:   {len(self.scenarios)}")
        print(f"   Judges:      {len(self.judges)}")
        print(f"   Being model: {BEING_MODEL}")
        print(f"   Judge model: {JUDGE_MODEL}")
        print(f"   Resuming at: experiment {self.experiment_id}")
        if self.max_experiments:
            print(f"   Target:      {self.max_experiments} experiments")
        else:
            print(f"   Target:      ∞ (runs forever)")
        print(f"{'='*60}\n")

        count = 0
        while True:
            try:
                result = await self.run_one_experiment()
                count += 1

                if self.max_experiments and count >= self.max_experiments:
                    print(f"\n🏁 Completed {count} experiments. Stopping.")
                    break

                # Brief pause to avoid rate limits
                await asyncio.sleep(1)

            except KeyboardInterrupt:
                print(f"\n⏹ Stopped after {count} experiments.")
                break
            except Exception as e:
                print(f"\n⚠ Experiment error: {e}")
                traceback.print_exc()
                await asyncio.sleep(5)  # back off on error

        # Final summary
        self._print_summary()

    def _print_summary(self):
        """Print final leaderboard."""
        print(f"\n{'='*60}")
        print(f"📊 FINAL BEST SCORES")
        print(f"{'='*60}")
        sorted_scores = sorted(self.best_scores.items(), key=lambda x: x[1], reverse=True)
        for i, (bid, score) in enumerate(sorted_scores[:20]):
            being = next((b for b in self.beings if b["id"] == bid), {})
            title = being.get("title", bid)
            print(f"  {i+1:2d}. {title:40s} | {score:.2f}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="🔥 ACT-I Autoresearch Runner")
    parser.add_argument("-n", "--experiments", type=int, default=None,
                        help="Number of experiments (default: infinite)")
    parser.add_argument("--being-idx", type=int, default=None,
                        help="Optimize only this being (by index)")
    parser.add_argument("--resume", "-r", action="store_true",
                        help="Resume from checkpoint")
    parser.add_argument("--model", type=str, default=None,
                        help="Override being model")
    parser.add_argument("--judge-model", type=str, default=None,
                        help="Override judge model")
    args = parser.parse_args()

    if args.model:
        global BEING_MODEL
        BEING_MODEL = args.model
    if args.judge_model:
        global JUDGE_MODEL
        JUDGE_MODEL = args.judge_model

    scenarios = load_scenarios()
    beings = load_beings()
    judges = load_judges()

    print(f"📂 Loaded: {len(beings)} beings, {len(scenarios)} scenarios, {len(judges)} judges")

    runner = Runner(beings, scenarios, judges,
                    max_experiments=args.experiments,
                    target_being_idx=args.being_idx)
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
