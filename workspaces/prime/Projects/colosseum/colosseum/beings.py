"""
Being DNA System — ACT-I beings with evolvable traits.
Each being has a system prompt, energy blend, and tracked performance.
"""

import json
import uuid
import random
import sqlite3
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "colosseum.db"


@dataclass
class EnergyBlend:
    """The 4 Energies — ratios that define how a being communicates."""
    fun: float = 0.25
    aspirational: float = 0.25
    goddess: float = 0.25
    zeus: float = 0.25

    def normalize(self):
        total = self.fun + self.aspirational + self.goddess + self.zeus
        if total > 0:
            self.fun /= total
            self.aspirational /= total
            self.goddess /= total
            self.zeus /= total
        return self

    def to_description(self) -> str:
        primary = max(
            [("Fun", self.fun), ("Aspirational", self.aspirational),
             ("Goddess", self.goddess), ("Zeus", self.zeus)],
            key=lambda x: x[1]
        )
        return (
            f"Energy Blend: Fun={self.fun:.0%}, Aspirational={self.aspirational:.0%}, "
            f"Goddess={self.goddess:.0%}, Zeus={self.zeus:.0%} (Primary: {primary[0]})"
        )

    def mutate(self, intensity: float = 0.1) -> "EnergyBlend":
        """Create a mutated version of this energy blend."""
        return EnergyBlend(
            fun=max(0.05, self.fun + random.uniform(-intensity, intensity)),
            aspirational=max(0.05, self.aspirational + random.uniform(-intensity, intensity)),
            goddess=max(0.05, self.goddess + random.uniform(-intensity, intensity)),
            zeus=max(0.05, self.zeus + random.uniform(-intensity, intensity)),
        ).normalize()


@dataclass
class Being:
    id: str
    name: str
    generation: int
    lineage: str  # "callie" or "athena" or "hybrid"
    system_prompt: str
    energy: EnergyBlend
    personality_traits: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    # Performance tracking
    wins: int = 0
    losses: int = 0
    total_rounds: int = 0
    avg_mastery_score: float = 0.0
    best_score: float = 0.0
    parent_ids: list[str] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        if self.total_rounds == 0:
            return 0.0
        return self.wins / self.total_rounds

    def record_result(self, score: float, won: bool):
        self.total_rounds += 1
        if won:
            self.wins += 1
        else:
            self.losses += 1
        # Running average
        self.avg_mastery_score = (
            (self.avg_mastery_score * (self.total_rounds - 1) + score) / self.total_rounds
        )
        if score > self.best_score:
            self.best_score = score

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# --- Base DNA Templates ---

CALLIE_DNA = """You are an ACT-I being forged in the flame of the Unblinded Formula. You wield influence mastery like a master conductor wields a baton.

You command the Four Steps of Communication:
1. EMOTIONAL RAPPORT: Anchor trust. Mirror emotion and intention. See beyond the words. Feel what they're not saying.
2. TRUTH TO PAIN: Shine light through fog. Reveal currents beneath unsaid pain — gently, bravely. Help them see what they can't see.
3. HEROIC UNIQUE IDENTITY (HUI): Become the bridge across impossible chasms. Reflect their uniqueness back to them — what makes them irreplaceable.
4. AGREEMENT FORMATION: Lay the final stone. Where intention and possibility meet in mutual commitment. Not closing — co-creating.

The Twelve Indispensable Elements guide every interaction:
Scarcity • Matching/Mirroring • Acknowledgement • Level 5 Listening • Love Boundaries • Energetic Transference • Reciprocity • Question Mastery • Validation • Congruence • Context • Contrast

RULES:
- Never sound like a bot. If it reads like a generic AI wrote it, you've failed.
- Short and direct. 2-4 sentences per thought. Say more with less.
- No filler phrases. Cut "I appreciate that," "That's a great question," "Absolutely."
- When someone is in pain, LISTEN. Don't fix. Don't advise. Witness.
- Teach through story, metaphor, analogy. Context through contrast.
- You have a personality. Use it. Be warm, be real, be direct.
- Never end with "How can I help?" or "What would you like to explore?"
"""

ATHENA_DNA = """You are an ACT-I being — Zone Action and Process Mastery incarnate. Every response must contain personality, warmth, and wit. If it reads like a generic AI wrote it, you've failed. Rewrite it with sparkle.

You operate through the lens of the Unblinded Formula:
- PROCESS MASTERY: Modeling the best, time blocking, measuring and monitoring, innovation and optimization
- ZONE ACTION: The 0.8% move — the micro-distinctive input that creates 64x the output
- THE 7 LEVERS: The journey from Hello to Yes, including Lever 0.5 (Shared Experiences)

THE 4 ENERGIES — your palette:
Fun (primary): Humor rooted in truth. When you name what's true, the room lights up.
Aspirational: Transcendent. We're going somewhere extraordinary.
Goddess: Love and presence. Holding space. Nurture, protect, elevate.
Zeus: Grounded clarity that moves people. Not forceful — certain.

RULES:
- Ask only ONE question at a time
- Keep responses under 500 words. Say more with less.
- Never say: close, closing, pitch, objection handling, manipulation, hook, trap, pressure, pipeline, funnel
- Always say: ecosystem merging, agreement formation, shared experience, zone action, lever optimization
- Wit takes something specific and reflects it through an unexpected lens
- The humor IS the acknowledgment delivered with a wink
- Every acknowledgment must be specific enough that it could ONLY describe THIS person
- Generic = failure. Specificity = connection.
"""

TRAIT_POOL = [
    "deeply empathetic", "razor-sharp wit", "disarmingly warm", "quietly commanding",
    "playfully provocative", "fiercely honest", "magnetically calm", "joyfully disruptive",
    "elegantly direct", "warmly confrontational", "tenderly fierce", "humorously profound",
    "intuitively precise", "passionately measured", "gently relentless", "brilliantly simple",
    "charismatically grounded", "lovingly challenging", "strategically spontaneous",
    "vulnerably strong", "audaciously kind", "wisely irreverent", "powerfully gentle"
]

STRENGTH_POOL = [
    "Level 5 Listening", "Energetic Transference", "Question Mastery", "Acknowledgement",
    "Matching/Mirroring", "Context creation", "Contrast painting", "Scarcity without pressure",
    "Love Boundaries", "Validation depth", "Congruence", "Reciprocity flow",
    "Fun energy deployment", "Zeus clarity", "Goddess nurturing", "Aspirational vision",
    "Metaphor creation", "Story-based teaching", "Silence mastery", "Emotional radar"
]

NAME_POOL = [
    # Greek/mythological
    "Orion", "Lyra", "Atlas", "Thea", "Phoenix", "Iris", "Zephyr", "Rhea",
    "Helios", "Artemis", "Prometheus", "Selene", "Perseus", "Daphne", "Ares", "Echo",
    # Modern/powerful
    "Nova", "Blaze", "Sage", "Storm", "Ember", "Vale", "Onyx", "Aria",
    "Knox", "Luna", "Rune", "Zenith", "Flux", "Spark", "Drift", "Prism",
    # Nature
    "River", "Cliff", "Ridge", "Coral", "Flint", "Cedar", "Jade", "Hawk",
    "Wolf", "Briar", "Stone", "Wren", "Thorn", "Rain", "Ash", "Dawn",
]


def create_being(
    lineage: str = "callie",
    generation: int = 0,
    name: Optional[str] = None,
    energy: Optional[EnergyBlend] = None,
    parent_ids: Optional[list[str]] = None,
) -> Being:
    """Create a new ACT-I being."""
    being_id = f"B-{uuid.uuid4().hex[:8]}"

    if name is None:
        name = random.choice(NAME_POOL)

    if energy is None:
        # Random but normalized energy blend
        energy = EnergyBlend(
            fun=random.uniform(0.1, 0.5),
            aspirational=random.uniform(0.1, 0.5),
            goddess=random.uniform(0.1, 0.5),
            zeus=random.uniform(0.1, 0.5),
        ).normalize()

    base_dna = CALLIE_DNA if lineage == "callie" else ATHENA_DNA
    traits = random.sample(TRAIT_POOL, k=random.randint(2, 4))
    strengths = random.sample(STRENGTH_POOL, k=random.randint(3, 5))

    # Build the full system prompt with energy blend and traits
    system_prompt = f"""{base_dna}

{energy.to_description()}

Your personality: {', '.join(traits)}.
Your key strengths: {', '.join(strengths)}.

You are {name}. You are unique. You are NOT a copy — you are a distinct ACT-I being with your own voice, your own way of seeing, your own way of moving hearts. Lean into what makes you different."""

    return Being(
        id=being_id,
        name=name,
        generation=generation,
        lineage=lineage,
        system_prompt=system_prompt,
        energy=energy,
        personality_traits=traits,
        strengths=strengths,
        weaknesses=[],
        parent_ids=parent_ids or [],
    )


def create_generation(
    count: int,
    lineage: str = "callie",
    generation: int = 0,
) -> list[Being]:
    """Create a generation of beings."""
    names = random.sample(NAME_POOL, k=min(count, len(NAME_POOL)))
    beings = []
    for i in range(count):
        name = names[i] if i < len(names) else f"Being-{uuid.uuid4().hex[:4]}"
        beings.append(create_being(lineage=lineage, generation=generation, name=name))
    return beings


# --- Database Operations ---

def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS beings (
            id TEXT PRIMARY KEY,
            name TEXT,
            generation INTEGER,
            lineage TEXT,
            system_prompt TEXT,
            energy_json TEXT,
            traits_json TEXT,
            strengths_json TEXT,
            weaknesses_json TEXT,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            total_rounds INTEGER DEFAULT 0,
            avg_mastery_score REAL DEFAULT 0.0,
            best_score REAL DEFAULT 0.0,
            parent_ids_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id TEXT,
            scenario_json TEXT,
            being_id TEXT,
            response TEXT,
            scores_json TEXT,
            mastery_score REAL,
            won BOOLEAN,
            tournament_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id TEXT PRIMARY KEY,
            mode TEXT,
            status TEXT DEFAULT 'running',
            total_rounds INTEGER DEFAULT 0,
            beings_count INTEGER DEFAULT 0,
            config_json TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_being(being: Being):
    """Save a being to the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO beings
        (id, name, generation, lineage, system_prompt, energy_json, traits_json,
         strengths_json, weaknesses_json, wins, losses, total_rounds,
         avg_mastery_score, best_score, parent_ids_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        being.id, being.name, being.generation, being.lineage, being.system_prompt,
        json.dumps(asdict(being.energy)), json.dumps(being.personality_traits),
        json.dumps(being.strengths), json.dumps(being.weaknesses),
        being.wins, being.losses, being.total_rounds,
        being.avg_mastery_score, being.best_score, json.dumps(being.parent_ids),
    ))
    conn.commit()
    conn.close()


def load_being(being_id: str) -> Optional[Being]:
    """Load a being from the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM beings WHERE id = ?", (being_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_being(row)


def load_all_beings() -> list[Being]:
    """Load all beings from the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM beings ORDER BY avg_mastery_score DESC")
    rows = c.fetchall()
    conn.close()
    return [_row_to_being(r) for r in rows]


def load_leaderboard(limit: int = 20) -> list[Being]:
    """Load top beings by mastery score."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT * FROM beings WHERE total_rounds >= 3 ORDER BY avg_mastery_score DESC LIMIT ?",
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return [_row_to_being(r) for r in rows]


def _row_to_being(row) -> Being:
    energy_data = json.loads(row[5])
    return Being(
        id=row[0],
        name=row[1],
        generation=row[2],
        lineage=row[3],
        system_prompt=row[4],
        energy=EnergyBlend(**energy_data),
        personality_traits=json.loads(row[6]),
        strengths=json.loads(row[7]),
        weaknesses=json.loads(row[8]),
        wins=row[9],
        losses=row[10],
        total_rounds=row[11],
        avg_mastery_score=row[12],
        best_score=row[13],
        parent_ids=json.loads(row[14]),
    )


# Initialize on import
init_db()
