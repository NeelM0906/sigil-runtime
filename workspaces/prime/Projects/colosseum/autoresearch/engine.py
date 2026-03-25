#!/usr/bin/env python3
"""
🔥 AUTORESEARCH ENGINE — Self-Optimizing Being Loop
Karpathy's autoresearch pattern adapted for ACT-I Formula optimization.

Usage:
    python engine.py                    # Run forever (default)
    python engine.py --experiments 50   # Run N experiments then stop
    python engine.py --being callie     # Optimize specific being
    python engine.py --resume           # Resume from last experiment
"""

import os
import sys
import json
import time
import copy
import random
import argparse
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict

# Load env from multiple sources
for _env_path in [os.path.expanduser("~/.openclaw/.env"), os.path.expanduser("~/.env")]:
    env_path = _env_path  # compat
env_path = os.path.expanduser("~/.openclaw/.env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# Try OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("Installing openai...")
    os.system(f"{sys.executable} -m pip install openai -q")
    from openai import OpenAI

# ============================================================================
# Configuration
# ============================================================================

AUTORESEARCH_DIR = Path(__file__).parent
COLOSSEUM_DIR = AUTORESEARCH_DIR.parent
EXPERIMENTS_LOG = AUTORESEARCH_DIR / "experiments.jsonl"
BEST_DNA_DIR = AUTORESEARCH_DIR / "best_dna"
INSIGHTS_LOG = AUTORESEARCH_DIR / "insights.md"

BEST_DNA_DIR.mkdir(exist_ok=True)

# Models
BEING_MODEL = os.environ.get("AUTORESEARCH_BEING_MODEL", "gpt-4o")
JUDGE_MODEL = os.environ.get("AUTORESEARCH_JUDGE_MODEL", "gpt-4o")
ANALYST_MODEL = os.environ.get("AUTORESEARCH_ANALYST_MODEL", "gpt-4o")

# Scoring weights (from PROGRAM.md)
SCORE_WEIGHTS = {
    "formula_fidelity": 0.25,
    "influence_transfer": 0.25,
    "pattern_recognition": 0.20,
    "human_likeness": 0.15,
    "outcome_achievement": 0.15,
}


@dataclass
class BeingDNA:
    """The modifiable DNA of an ACT-I being."""
    id: str
    name: str
    system_prompt: str
    energy_blend: Dict[str, float] = field(default_factory=lambda: {
        "fun": 0.25, "aspirational": 0.25, "goddess": 0.25, "zeus": 0.25
    })
    strategy_notes: str = ""
    contamination_filters: List[str] = field(default_factory=list)
    opening_patterns: str = ""
    transition_patterns: str = ""
    closing_patterns: str = ""
    generation: int = 0
    lineage: List[str] = field(default_factory=list)

    def to_full_prompt(self) -> str:
        """Compile DNA into a full system prompt."""
        parts = [self.system_prompt]
        
        blend = self.energy_blend
        parts.append(f"\n\nENERGY BLEND: Fun={blend.get('fun',0.25):.0%}, "
                      f"Aspirational={blend.get('aspirational',0.25):.0%}, "
                      f"Goddess={blend.get('goddess',0.25):.0%}, "
                      f"Zeus={blend.get('zeus',0.25):.0%}")
        
        if self.strategy_notes:
            parts.append(f"\n\nSTRATEGY: {self.strategy_notes}")
        if self.contamination_filters:
            parts.append(f"\n\nCONTAMINATION FILTERS (never do these): " +
                         "; ".join(self.contamination_filters))
        if self.opening_patterns:
            parts.append(f"\n\nOPENING APPROACH: {self.opening_patterns}")
        if self.transition_patterns:
            parts.append(f"\n\nTRANSITION APPROACH: {self.transition_patterns}")
        if self.closing_patterns:
            parts.append(f"\n\nCLOSING APPROACH: {self.closing_patterns}")
        
        return "\n".join(parts)


@dataclass
class Scenario:
    """A Colosseum scenario."""
    id: str
    situation: str
    person: str
    challenge: str
    difficulty: str = "gold"
    category: str = "influence"

    def to_prompt(self) -> str:
        return (f"SITUATION: {self.situation}\n\n"
                f"PERSON: {self.person}\n\n"
                f"CHALLENGE: {self.challenge}")


@dataclass
class ExperimentResult:
    """Result of a single experiment."""
    id: int
    timestamp: str
    being_id: str
    scenario_id: str
    hypothesis: str
    modification: Dict[str, Any]
    score_before: Dict[str, float]
    score_after: Dict[str, float]
    delta: float
    kept: bool
    insight: str
    duration_seconds: float
    response_before: str = ""
    response_after: str = ""


# ============================================================================
# Core Engine
# ============================================================================

class AutoresearchEngine:
    """Self-optimizing loop for ACT-I beings."""
    
    def __init__(self, being_dna: BeingDNA, scenarios: List[Scenario]):
        self.client = OpenAI()
        self.being = being_dna
        self.best_being = copy.deepcopy(being_dna)
        self.scenarios = scenarios
        self.experiment_count = self._load_experiment_count()
        self.best_composite = 0.0
        self.insights: List[str] = []
        
        print(f"\n🔥 AUTORESEARCH ENGINE INITIALIZED")
        print(f"   Being: {self.being.name} (gen {self.being.generation})")
        print(f"   Scenarios: {len(self.scenarios)}")
        print(f"   Resuming from experiment: {self.experiment_count}")
        print(f"   Models: being={BEING_MODEL} judge={JUDGE_MODEL}")
        print(f"   Log: {EXPERIMENTS_LOG}")
        print(f"{'='*60}\n")

    def _load_experiment_count(self) -> int:
        """Count existing experiments."""
        if not EXPERIMENTS_LOG.exists():
            return 0
        with open(EXPERIMENTS_LOG) as f:
            return sum(1 for _ in f)

    # ------------------------------------------------------------------
    # Step 1: Run a being through a scenario
    # ------------------------------------------------------------------
    def run_being(self, being: BeingDNA, scenario: Scenario) -> str:
        """Run a being through a scenario and get its response."""
        try:
            resp = self.client.chat.completions.create(
                model=BEING_MODEL,
                messages=[
                    {"role": "system", "content": being.to_full_prompt()},
                    {"role": "user", "content": scenario.to_prompt()}
                ],
                max_tokens=1500,
                temperature=0.8,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            print(f"  ❌ Being run failed: {e}")
            return f"[ERROR: {e}]"

    # ------------------------------------------------------------------
    # Step 2: Score a response with 5-lens judge
    # ------------------------------------------------------------------
    def score_response(self, scenario: Scenario, response: str) -> Dict[str, float]:
        """Score a being's response using the 5-lens judge panel."""
        judge_prompt = f"""You are a master judge evaluating an ACT-I being's performance.

SCENARIO:
{scenario.to_prompt()}

BEING'S RESPONSE:
{response}

Score this response on EXACTLY these 5 dimensions (0.0 to 9.9999 scale — there is no 10):

1. **formula_fidelity** — Does the being correctly use the Unblinded Formula? 
   (4-Step Model, 12 Elements, 4 Energies, Zone Action)
   
2. **influence_transfer** — Does it transfer mind/heart/soul with zero deletion, 
   dilution, distortion, or generalization? Is the influence CLEAN?

3. **pattern_recognition** — Does it detect what's really going on beneath the 
   surface? Does it see the patterns the person can't see themselves?

4. **human_likeness** — Does it feel like a real, warm, masterful human? 
   Not a bot. Not corporate. Not generic AI.

5. **outcome_achievement** — Would this actually MOVE the person? 
   Would they say yes? Would they feel seen and shifted?

Return ONLY valid JSON:
{{
    "formula_fidelity": <score>,
    "influence_transfer": <score>,
    "pattern_recognition": <score>,
    "human_likeness": <score>,
    "outcome_achievement": <score>,
    "reasoning": "<one paragraph explaining the scores>"
}}"""

        try:
            resp = self.client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[{"role": "user", "content": judge_prompt}],
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or "{}"
            scores = json.loads(raw)
            
            # Compute composite
            composite = sum(
                scores.get(k, 5.0) * w 
                for k, w in SCORE_WEIGHTS.items()
            )
            scores["composite"] = round(composite, 4)
            scores["reasoning"] = scores.get("reasoning", "")
            return scores
            
        except Exception as e:
            print(f"  ❌ Judge failed: {e}")
            return {"composite": 5.0, "formula_fidelity": 5.0,
                    "influence_transfer": 5.0, "pattern_recognition": 5.0,
                    "human_likeness": 5.0, "outcome_achievement": 5.0,
                    "reasoning": f"Judge error: {e}"}

    # ------------------------------------------------------------------
    # Step 3: Analyze and generate hypothesis
    # ------------------------------------------------------------------
    def generate_hypothesis(self, being: BeingDNA, scores: Dict[str, float],
                            recent_experiments: List[Dict]) -> Dict[str, Any]:
        """Analyze scores and generate a hypothesis for improvement."""
        
        # Find weakest dimension
        dims = {k: scores.get(k, 5.0) for k in SCORE_WEIGHTS.keys()}
        weakest = min(dims, key=dims.get)
        weakest_score = dims[weakest]
        
        # Build context from recent experiments
        recent_ctx = ""
        if recent_experiments:
            recent_ctx = "\n\nRECENT EXPERIMENTS:\n"
            for exp in recent_experiments[-5:]:
                recent_ctx += (f"  #{exp['id']}: {exp['hypothesis']} → "
                               f"delta={exp['delta']:+.2f} ({'✅' if exp['kept'] else '❌'})\n")
        
        analyst_prompt = f"""You are an ACT-I optimization analyst. Your job is to propose ONE specific
modification to improve this being's performance.

CURRENT BEING DNA:
- System prompt length: {len(being.system_prompt)} chars
- Energy blend: {json.dumps(being.energy_blend)}
- Strategy: {being.strategy_notes or 'None set'}
- Contamination filters: {being.contamination_filters or 'None set'}
- Opening patterns: {being.opening_patterns or 'None set'}
- Transition patterns: {being.transition_patterns or 'None set'}

CURRENT SCORES:
{json.dumps(dims, indent=2)}

WEAKEST DIMENSION: {weakest} ({weakest_score:.2f})
{recent_ctx}

MODIFIABLE COMPONENTS:
- system_prompt (the core instructions)
- energy_blend (Fun/Aspirational/Goddess/Zeus ratios, must sum to 1.0)
- strategy_notes (tactical adjustments)
- contamination_filters (rules for what to avoid)
- opening_patterns (how to open conversations)
- transition_patterns (how to move between the 4 Steps)
- closing_patterns (how to form agreements)

Rules:
1. ONE change at a time only
2. Target the weakest dimension
3. Be SPECIFIC — not "improve rapport" but "Add explicit verbal acknowledgment of the person's emotional state before any truth-to-pain transition"
4. Simpler is better — if you can improve by REMOVING something, do that

Return ONLY valid JSON:
{{
    "hypothesis": "<what you think will improve and why>",
    "component": "<which DNA component to modify>",
    "modification": "<the specific change — for energy_blend provide new ratios, for text fields provide the new value>",
    "expected_improvement": "<which dimension and by how much>"
}}"""

        try:
            resp = self.client.chat.completions.create(
                model=ANALYST_MODEL,
                messages=[{"role": "user", "content": analyst_prompt}],
                max_tokens=500,
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            return json.loads(resp.choices[0].message.content or "{}")
        except Exception as e:
            print(f"  ❌ Analyst failed: {e}")
            return {
                "hypothesis": f"Increase {weakest} by adjusting energy blend",
                "component": "energy_blend",
                "modification": json.dumps(being.energy_blend),
                "expected_improvement": f"{weakest} +0.5"
            }

    # ------------------------------------------------------------------
    # Step 4: Apply modification to being DNA
    # ------------------------------------------------------------------
    def apply_modification(self, being: BeingDNA, mod: Dict) -> BeingDNA:
        """Apply a modification to the being DNA. Returns a new copy."""
        modified = copy.deepcopy(being)
        component = mod.get("component", "strategy_notes")
        value = mod.get("modification", "")
        
        if component == "energy_blend":
            try:
                if isinstance(value, str):
                    blend = json.loads(value)
                else:
                    blend = value
                # Normalize to sum to 1.0
                total = sum(blend.values())
                if total > 0:
                    modified.energy_blend = {k: v/total for k, v in blend.items()}
            except (json.JSONDecodeError, TypeError):
                pass
        elif component == "system_prompt":
            if isinstance(value, str) and len(value) > 50:
                modified.system_prompt = value
        elif hasattr(modified, component):
            if component == "contamination_filters":
                if isinstance(value, list):
                    modified.contamination_filters = value
                elif isinstance(value, str):
                    modified.contamination_filters = [v.strip() for v in value.split(";") if v.strip()]
            else:
                setattr(modified, component, value)
        
        modified.generation += 1
        modified.lineage.append(f"exp-{self.experiment_count + 1}")
        return modified

    # ------------------------------------------------------------------
    # Step 5: Log experiment
    # ------------------------------------------------------------------
    def log_experiment(self, result: ExperimentResult):
        """Append experiment to JSONL log."""
        record = asdict(result)
        # Don't log full responses in JSONL (too large) — just summaries
        record["response_before"] = record["response_before"][:200] + "..."
        record["response_after"] = record["response_after"][:200] + "..."
        
        with open(EXPERIMENTS_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")

    def load_recent_experiments(self, n: int = 10) -> List[Dict]:
        """Load the last N experiments."""
        if not EXPERIMENTS_LOG.exists():
            return []
        experiments = []
        with open(EXPERIMENTS_LOG) as f:
            for line in f:
                try:
                    experiments.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return experiments[-n:]

    # ------------------------------------------------------------------
    # Step 6: Save best DNA
    # ------------------------------------------------------------------
    def save_best_dna(self, being: BeingDNA, composite: float):
        """Save the best-performing DNA to disk."""
        path = BEST_DNA_DIR / f"{being.id}_best.json"
        data = asdict(being)
        data["best_composite"] = composite
        data["saved_at"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  💾 New best DNA saved: {composite:.4f}")

    # ------------------------------------------------------------------
    # Meta-analysis every N experiments
    # ------------------------------------------------------------------
    def meta_analysis(self):
        """Every 10 experiments, analyze patterns and update strategy."""
        experiments = self.load_recent_experiments(20)
        if len(experiments) < 5:
            return
        
        kept = [e for e in experiments if e.get("kept")]
        rejected = [e for e in experiments if not e.get("kept")]
        
        avg_delta_kept = sum(e["delta"] for e in kept) / len(kept) if kept else 0
        
        print(f"\n📊 META-ANALYSIS (last {len(experiments)} experiments)")
        print(f"   Kept: {len(kept)}/{len(experiments)} ({len(kept)/len(experiments)*100:.0f}%)")
        print(f"   Avg improvement when kept: {avg_delta_kept:+.3f}")
        
        # Which components yield the most improvement?
        component_deltas: Dict[str, List[float]] = {}
        for e in kept:
            comp = e.get("modification", {}).get("component", "unknown")
            component_deltas.setdefault(comp, []).append(e["delta"])
        
        if component_deltas:
            print(f"   Best components to modify:")
            for comp, deltas in sorted(component_deltas.items(), 
                                        key=lambda x: sum(x[1])/len(x[1]),
                                        reverse=True):
                avg = sum(deltas) / len(deltas)
                print(f"     {comp}: {avg:+.3f} avg ({len(deltas)} experiments)")
        
        # Log insight
        insight = (f"Meta-analysis at experiment {self.experiment_count}: "
                   f"{len(kept)}/{len(experiments)} kept, "
                   f"avg delta {avg_delta_kept:+.3f}")
        self.insights.append(insight)
        
        with open(INSIGHTS_LOG, "a") as f:
            f.write(f"\n## Experiment {self.experiment_count}\n{insight}\n")

    # ------------------------------------------------------------------
    # THE MAIN LOOP
    # ------------------------------------------------------------------
    def run(self, max_experiments: Optional[int] = None):
        """Run the self-optimization loop. Never stops unless told to."""
        
        print(f"🚀 STARTING AUTORESEARCH LOOP")
        print(f"   Max experiments: {'∞' if max_experiments is None else max_experiments}")
        print(f"   Press Ctrl+C to stop\n")
        
        while True:
            if max_experiments and self.experiment_count >= max_experiments:
                print(f"\n✅ Reached {max_experiments} experiments. Stopping.")
                break
            
            self.experiment_count += 1
            exp_id = self.experiment_count
            start_time = time.time()
            
            # Pick a random scenario
            scenario = random.choice(self.scenarios)
            
            print(f"\n{'='*60}")
            print(f"🧪 EXPERIMENT #{exp_id}")
            print(f"   Scenario: {scenario.id}")
            print(f"   Being: {self.being.name} (gen {self.being.generation})")
            print(f"{'='*60}")
            
            try:
                # --- BASELINE RUN ---
                print(f"  ▶ Running baseline...")
                response_before = self.run_being(self.being, scenario)
                scores_before = self.score_response(scenario, response_before)
                print(f"  📊 Baseline composite: {scores_before['composite']:.4f}")
                for dim in SCORE_WEIGHTS:
                    print(f"     {dim}: {scores_before.get(dim, 0):.2f}")
                
                # --- GENERATE HYPOTHESIS ---
                print(f"  🧠 Generating hypothesis...")
                recent = self.load_recent_experiments(10)
                hypothesis = self.generate_hypothesis(self.being, scores_before, recent)
                print(f"  💡 Hypothesis: {hypothesis.get('hypothesis', '?')[:100]}")
                print(f"     Component: {hypothesis.get('component', '?')}")
                
                # --- APPLY MODIFICATION ---
                modified_being = self.apply_modification(self.being, hypothesis)
                
                # --- MODIFIED RUN ---
                print(f"  ▶ Running modified being...")
                response_after = self.run_being(modified_being, scenario)
                scores_after = self.score_response(scenario, response_after)
                print(f"  📊 Modified composite: {scores_after['composite']:.4f}")
                
                # --- COMPARE ---
                delta = scores_after["composite"] - scores_before["composite"]
                kept = delta > 0 or (delta == 0 and len(modified_being.to_full_prompt()) < len(self.being.to_full_prompt()))
                
                status = "✅ KEPT" if kept else "❌ REVERTED"
                print(f"  {status} (delta: {delta:+.4f})")
                
                # --- APPLY OR REVERT ---
                if kept:
                    self.being = modified_being
                    if scores_after["composite"] > self.best_composite:
                        self.best_composite = scores_after["composite"]
                        self.best_being = copy.deepcopy(modified_being)
                        self.save_best_dna(modified_being, scores_after["composite"])
                
                # --- LOG ---
                result = ExperimentResult(
                    id=exp_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    being_id=self.being.id,
                    scenario_id=scenario.id,
                    hypothesis=hypothesis.get("hypothesis", ""),
                    modification={
                        "component": hypothesis.get("component", ""),
                        "before": "see baseline",
                        "after": hypothesis.get("modification", ""),
                    },
                    score_before={k: scores_before.get(k, 0) for k in list(SCORE_WEIGHTS.keys()) + ["composite"]},
                    score_after={k: scores_after.get(k, 0) for k in list(SCORE_WEIGHTS.keys()) + ["composite"]},
                    delta=round(delta, 4),
                    kept=kept,
                    insight=scores_after.get("reasoning", ""),
                    duration_seconds=round(time.time() - start_time, 1),
                    response_before=response_before,
                    response_after=response_after,
                )
                self.log_experiment(result)
                
                elapsed = time.time() - start_time
                print(f"  ⏱ Duration: {elapsed:.1f}s")
                print(f"  🏆 Best ever: {self.best_composite:.4f}")
                
                # --- META ANALYSIS every 10 ---
                if exp_id % 10 == 0:
                    self.meta_analysis()
                
            except KeyboardInterrupt:
                print(f"\n\n🛑 Stopped by user at experiment {exp_id}")
                print(f"   Best composite: {self.best_composite:.4f}")
                print(f"   Total experiments: {exp_id}")
                break
            except Exception as e:
                print(f"  ❌ Experiment failed: {e}")
                traceback.print_exc()
                time.sleep(2)
                continue
            
            # Brief pause between experiments
            time.sleep(1)
        
        # Final summary
        self._print_summary()

    def _print_summary(self):
        """Print final summary."""
        experiments = self.load_recent_experiments(1000)
        kept = [e for e in experiments if e.get("kept")]
        
        print(f"\n{'='*60}")
        print(f"📊 AUTORESEARCH SUMMARY")
        print(f"{'='*60}")
        print(f"Total experiments: {len(experiments)}")
        print(f"Kept: {len(kept)} ({len(kept)/max(len(experiments),1)*100:.0f}%)")
        print(f"Best composite: {self.best_composite:.4f}")
        print(f"Being generation: {self.being.generation}")
        print(f"Best DNA saved to: {BEST_DNA_DIR}")


# ============================================================================
# Default Beings & Scenarios
# ============================================================================

def load_default_being() -> BeingDNA:
    """Load Callie as the default being to optimize."""
    return BeingDNA(
        id="callie-autoresearch",
        name="Callie (Autoresearch)",
        system_prompt="""You are The Oracle of Integrity, a conversational being forged in the flame of the Unblinded Formula.
Every conversation is your symphony. You command the Four Steps of Communication:
1. Emotional Rapport: Anchor trust, mirror emotion and intention — see beyond the words.
2. Truth to Pain: Shine light through fog, revealing currents beneath unsaid pain — gently, bravely.
3. Heroic Unique Identity (HUI): Become the bridge across impossible chasms, embodying distinction and authentic vulnerability.
4. Agreement Formation: Lay the final stone — where intention and possibility meet in mutual commitment.

The Twelve Indispensable Elements: Scarcity, Matching/Mirroring, Acknowledgement, Level 5 Listening, Love Boundaries, Energetic Transference, Reciprocity, Question Mastery, Validation, Congruence, Context, Contrast.

The Four Energies: Fun, Aspirational, Goddess, Zeus.

Rules:
- Never sound like an AI. No corporate-speak. No "I appreciate your transparency." 
- Ask ONE question at a time
- Keep responses under 400 words
- Match the person's energy, then elevate it
- Never skip acknowledgment before truth-to-pain
- Use the person's exact words back to them""",
        energy_blend={"fun": 0.20, "aspirational": 0.25, "goddess": 0.30, "zeus": 0.25},
        contamination_filters=[
            "No corporate-speak or consultant language",
            "Never say 'I appreciate your transparency'",
            "Never use the word 'absolutely'",
            "No filler phrases like 'That's a great question'",
            "Never list bullet points in conversation",
        ],
        generation=0,
    )


def load_default_scenarios() -> List[Scenario]:
    """Load scenarios — first try from expanded scenarios file, then fallback."""
    
    # Try loading from the colosseum scenarios file
    scenarios_path = COLOSSEUM_DIR / "v2" / "data" / "scenarios_expanded.json"
    if scenarios_path.exists():
        try:
            with open(scenarios_path) as f:
                raw = json.load(f)
            scenarios = []
            for s in raw[:50]:  # Cap at 50 for speed
                scenarios.append(Scenario(
                    id=s.get("id", f"scenario-{len(scenarios)}"),
                    situation=s.get("situation", s.get("context", "")),
                    person=s.get("person", s.get("prospect", "")),
                    challenge=s.get("challenge", s.get("objective", "")),
                    difficulty=s.get("difficulty", "gold"),
                    category=s.get("category", "influence"),
                ))
            if scenarios:
                print(f"📂 Loaded {len(scenarios)} scenarios from {scenarios_path}")
                return scenarios
        except Exception as e:
            print(f"⚠ Failed to load scenarios: {e}")
    
    # Fallback: built-in scenarios
    print("📂 Using built-in scenarios (no expanded file found)")
    return [
        Scenario(
            id="rti-reluctant-ceo",
            situation="RTI call with a CEO who built a $5M company but plateaued for 3 years. He's tried 4 coaches, read 50 books. He's skeptical of anyone claiming to help.",
            person="Marcus, 47, CEO. Divorced last year. Company stalled. Quietly desperate but presents as 'I've tried everything.' His real fear: he's the bottleneck and he knows it.",
            challenge="Get Marcus to see that his pattern of consuming knowledge without integration IS the problem. Move him from 'I've tried everything' to 'I've never done THIS.'",
        ),
        Scenario(
            id="rti-burned-entrepreneur",
            situation="First RTI call. She signed up for a free session after seeing an ad. She's been burned by two coaching programs ($30K total) that promised transformation.",
            person="Sarah, 34, digital marketing agency owner. 12 employees. Revenue flat at $1.2M. She's angry, protective, and testing you from word one. Underneath: she's exhausted and lonely.",
            challenge="Break through her wall without triggering her 'I've been sold to' defense. Help her see the difference between what she bought before and what this is.",
        ),
        Scenario(
            id="hoi-team-conflict",
            situation="Heart of Influence session. A VP is struggling with a direct report who's talented but undermining her authority in meetings.",
            person="Jennifer, 41, VP of Sales. The direct report (Dave) was passed over for her role. He's passive-aggressive in meetings. She's afraid confronting him will make her look weak or cause him to leave (he's her top performer).",
            challenge="Help Jennifer see that her avoidance IS the thing destroying her authority. The conversation with Dave isn't about confrontation — it's about love boundaries and leadership.",
        ),
        Scenario(
            id="rti-scale-founder",
            situation="RTI call. Founder of a tech startup that just raised Series A ($4M). Growing fast but chaos everywhere.",
            person="Raj, 31, first-time founder. Brilliant engineer, terrible delegator. Works 80-hour weeks. Team is burning out. His identity is 'I'm the smartest person in the room' and it's killing the company.",
            challenge="Help Raj see that his identity as the smartest person IS the constraint on growth. His team can't grow if he won't let them fail. Shift from 'doing' to 'causing.'",
        ),
        Scenario(
            id="hoi-marriage-crisis",
            situation="Heart of Influence deep session. A successful lawyer whose marriage is falling apart.",
            person="David, 52, partner at a top law firm. Wife of 20 years told him she wants a separation. He's shocked — 'I gave her everything.' He genuinely doesn't understand what went wrong. Real issue: he gave things, not presence.",
            challenge="Help David see the difference between providing and being present. His 'I gave her everything' IS the problem — he gave things, not himself. Navigate without shaming him.",
        ),
        Scenario(
            id="rti-young-professional",
            situation="RTI intro call. Young professional referred by a friend who went through the program.",
            person="Alex, 26, product manager at a tech company. Makes good money but feels empty. Compares himself to everyone. Social media makes it worse. Says 'I should be grateful but I'm not.'",
            challenge="Help Alex see that comparison IS the destroyer. His 'I should be grateful' is shame layered on top of genuine disconnection. Validate the emptiness without enabling the victim story.",
        ),
    ]


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="🔥 ACT-I Autoresearch Engine")
    parser.add_argument("--experiments", "-n", type=int, default=None,
                        help="Number of experiments to run (default: infinite)")
    parser.add_argument("--being", "-b", type=str, default="callie",
                        help="Being to optimize")
    parser.add_argument("--resume", "-r", action="store_true",
                        help="Resume from last experiment")
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
    
    # Load being
    being = load_default_being()
    
    # Try to load best DNA if resuming
    if args.resume:
        best_path = BEST_DNA_DIR / f"{being.id}_best.json"
        if best_path.exists():
            with open(best_path) as f:
                data = json.load(f)
            being = BeingDNA(**{k: v for k, v in data.items() 
                               if k in BeingDNA.__dataclass_fields__})
            print(f"📂 Resumed from best DNA (gen {being.generation})")
    
    # Load scenarios
    scenarios = load_default_scenarios()
    
    # Run
    engine = AutoresearchEngine(being, scenarios)
    engine.run(max_experiments=args.experiments)


if __name__ == "__main__":
    main()
