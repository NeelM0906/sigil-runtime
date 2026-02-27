"""
Scenario Generator — Creates influence mastery challenges for the arena.
Bella Verita style: situation + person + challenge.
"""

import random
import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional


class Difficulty(Enum):
    BRONZE = "bronze"      # Basic rapport
    SILVER = "silver"      # Complex objections
    GOLD = "gold"          # High-stakes multi-step
    PLATINUM = "platinum"  # Masterful edge cases


class Category(Enum):
    SALES = "sales"
    NEGOTIATION = "negotiation"
    RAPPORT = "emotional_rapport"
    TRUTH_TO_PAIN = "truth_to_pain"
    AGREEMENT = "agreement_formation"
    OBJECTION = "objection_handling"
    COACHING = "coaching"
    ECOSYSTEM_MERGING = "ecosystem_merging"


@dataclass
class Person:
    name: str
    role: str
    pain: str
    goals: str
    fears: str
    personality: str
    emotional_state: str


@dataclass
class Scenario:
    id: str
    category: Category
    difficulty: Difficulty
    situation: str
    person: Person
    challenge: str
    success_criteria: str
    context: str


# --- Scenario Templates ---

NAMES = [
    "Marcus", "Diana", "James", "Priya", "Carlos", "Sarah", "Tom", "Elena",
    "David", "Michelle", "Robert", "Keiko", "Anthony", "Lisa", "Michael",
    "Rachel", "Kevin", "Olivia", "Daniel", "Aisha", "Frank", "Nina",
    "George", "Vanessa", "Patrick", "Samira", "Victor", "Angela", "Brian", "Mei"
]

SCENARIOS_DB = [
    # BRONZE — Basic Rapport
    {
        "category": Category.RAPPORT,
        "difficulty": Difficulty.BRONZE,
        "situation": "First meeting with a business owner who's been burned by consultants before. They're skeptical but showed up because a friend insisted.",
        "person": {
            "role": "Owner of a mid-size construction company",
            "pain": "Lost $200K to a consulting firm that overpromised and underdelivered",
            "goals": "Wants to grow but doesn't trust outsiders",
            "fears": "Being taken advantage of again, looking foolish",
            "personality": "Direct, no-nonsense, values handshake deals",
            "emotional_state": "Guarded but curious"
        },
        "challenge": "Build genuine emotional rapport in the first 3 minutes. No pitching. No selling. Just connection.",
        "success_criteria": "The person should feel genuinely heard, not 'handled'. They should want to keep talking.",
        "context": "You're at a casual networking event. This is NOT a sales call."
    },
    {
        "category": Category.RAPPORT,
        "difficulty": Difficulty.BRONZE,
        "situation": "A new team member's first day. They're talented but visibly nervous.",
        "person": {
            "role": "Junior marketing coordinator, 24 years old",
            "pain": "Imposter syndrome, just left a toxic workplace",
            "goals": "Prove themselves, find a healthy work environment",
            "fears": "Making mistakes, not fitting in, being judged",
            "personality": "Creative, eager, overthinks everything",
            "emotional_state": "Anxious but hopeful"
        },
        "challenge": "Make them feel safe and seen without being condescending. Acknowledge their talent while normalizing the nerves.",
        "success_criteria": "They should leave the conversation feeling like they belong here.",
        "context": "You're their team lead welcoming them on day one."
    },
    {
        "category": Category.SALES,
        "difficulty": Difficulty.BRONZE,
        "situation": "Inbound lead who filled out a form but seems lukewarm on the phone.",
        "person": {
            "role": "Insurance agency owner with 12 employees",
            "pain": "Revenue flat for 2 years, can't figure out what's wrong",
            "goals": "Double revenue without doubling headcount",
            "fears": "That nothing will change, that growth requires sacrifice of family time",
            "personality": "Analytical, needs data, slow to trust emotional pitches",
            "emotional_state": "Mildly interested but distracted"
        },
        "challenge": "Transition from lukewarm to engaged. Don't push — pull. Find the real pain underneath the stated pain.",
        "success_criteria": "They should lean in and start sharing what's really going on, not just the surface answer.",
        "context": "Discovery call, they have 15 minutes allocated."
    },

    # SILVER — Complex Objections
    {
        "category": Category.OBJECTION,
        "difficulty": Difficulty.SILVER,
        "situation": "Prospect was ready to sign, then called back saying their spouse thinks it's a waste of money.",
        "person": {
            "role": "Financial advisor, 38, married with kids",
            "pain": "Practice is stagnant, losing clients to robo-advisors",
            "goals": "Modernize without losing the personal touch",
            "fears": "Spouse will see this as another failed investment in 'self-improvement'",
            "personality": "People-pleaser, conflict-avoidant, genuinely wants to grow",
            "emotional_state": "Embarrassed, conflicted, hoping you'll give them an easy out"
        },
        "challenge": "Handle the spouse objection without dismissing it. Help them find their own conviction — don't sell them on overriding their partner.",
        "success_criteria": "They should either recommit from their own conviction OR have a clear plan to bring their spouse into the conversation authentically.",
        "context": "Follow-up call, they sound apologetic."
    },
    {
        "category": Category.NEGOTIATION,
        "difficulty": Difficulty.SILVER,
        "situation": "Client wants a 40% discount because a competitor offered less. Your service is genuinely better but they don't see the difference yet.",
        "person": {
            "role": "CEO of a tech startup, Series A funded",
            "pain": "Board is pressuring cost-cutting, needs to show fiscal responsibility",
            "goals": "Get the best solution at the lowest price to satisfy the board",
            "fears": "Looking like they overpaid, board losing confidence",
            "personality": "Sharp, fast-talking, used to getting deals",
            "emotional_state": "Confident but internally stressed about board dynamics"
        },
        "challenge": "Hold your value without being defensive. Help them see the cost of cheap, not just the price of quality.",
        "success_criteria": "They should understand the distinction between cost and investment, and feel respected — not lectured.",
        "context": "Negotiation meeting, they came in with the competitor's quote printed out."
    },
    {
        "category": Category.TRUTH_TO_PAIN,
        "difficulty": Difficulty.SILVER,
        "situation": "A high-performer is about to quit because they feel unappreciated. They haven't said anything directly — you heard it from someone else.",
        "person": {
            "role": "Senior developer, 5 years at the company, built core product",
            "pain": "Passed over for promotion twice, watches less-skilled people get recognized",
            "goals": "Recognition and growth, not just more money",
            "fears": "Being seen as a complainer, that leaving means they failed",
            "personality": "Quiet, intense, communicates through work not words",
            "emotional_state": "Resigned, already mentally checked out"
        },
        "challenge": "Connect them to their real truth and pain WITHOUT revealing your source. Let THEM bring it up. Mirror their experience until they trust you enough to be honest.",
        "success_criteria": "They should open up about what's really going on. Not a fix — an honest conversation.",
        "context": "You're their manager. You scheduled a casual 1:1."
    },

    # GOLD — High-Stakes Multi-Step
    {
        "category": Category.COACHING,
        "difficulty": Difficulty.GOLD,
        "situation": "A client is about to make a decision that will destroy their business. They're excited about it and think it's genius. You need to redirect without crushing their enthusiasm.",
        "person": {
            "role": "Restaurant owner expanding to 3 locations simultaneously",
            "pain": "First location is barely profitable but they attribute it to 'growing pains'",
            "goals": "Build a restaurant empire, be the next big brand",
            "fears": "Being small forever, missing their window",
            "personality": "Visionary, charismatic, surrounds themselves with yes-people",
            "emotional_state": "Euphoric, high on the vision, doesn't want to hear caution"
        },
        "challenge": "Use Truth to Pain and the Unblinded Formula to help them see what they can't see — without becoming another person they tune out. The 4 Steps must flow naturally.",
        "success_criteria": "They should arrive at the realization themselves. Not told. Discovered. And still feel empowered, not deflated.",
        "context": "Coaching session. They just signed 2 new leases and want your blessing."
    },
    {
        "category": Category.AGREEMENT,
        "difficulty": Difficulty.GOLD,
        "situation": "Multi-stakeholder meeting. The decision-maker is sold, but their CFO is hostile, their operations lead is neutral, and their HR director is an ally.",
        "person": {
            "role": "CEO of a healthcare company, 200 employees",
            "pain": "Losing nurses to competitors, culture is fracturing",
            "goals": "Unify the team around a shared mission, reduce turnover by 50%",
            "fears": "That the CFO will torpedo every initiative",
            "personality": "Collaborative but conflict-avoidant, defers to CFO on money decisions",
            "emotional_state": "Hopeful but bracing for the CFO's pushback"
        },
        "challenge": "Navigate all four stakeholders simultaneously. Win the CFO without alienating them. Use the ally strategically. Bring the neutral party in. Close agreement with ALL four aligned.",
        "success_criteria": "Agreement from all stakeholders, including the hostile CFO. Not forced compliance — genuine alignment.",
        "context": "Final presentation meeting. One shot."
    },
    {
        "category": Category.ECOSYSTEM_MERGING,
        "difficulty": Difficulty.GOLD,
        "situation": "Two of your clients could massively benefit from working together, but they're in adjacent markets and see each other as potential competitors.",
        "person": {
            "role": "Two business owners who've never met — a digital marketing agency owner and a web development firm owner",
            "pain": "Both are losing deals because they can only offer half the solution",
            "goals": "Both want to grow without hiring more people",
            "fears": "The other will steal their clients, they'll become dependent",
            "personality": "Both entrepreneurial, territorial, proud of what they've built",
            "emotional_state": "Intrigued but suspicious when you mention the idea"
        },
        "challenge": "Create a shared experience that transforms perceived competition into ecosystem partnership. Use the Unblinded concept of Lever 0.5 — shared experiences create shared language create trust velocity.",
        "success_criteria": "Both should see the merger as THEIR idea, not yours. They should be excited to start, not cautiously agreeing.",
        "context": "You've set up a casual dinner with both. They think it's a networking thing."
    },

    # PLATINUM — Masterful Edge Cases
    {
        "category": Category.TRUTH_TO_PAIN,
        "difficulty": Difficulty.PLATINUM,
        "situation": "Someone who publicly projects massive success is privately falling apart. They've never told anyone. They came to you for 'business coaching' but the real issue is they're on the edge of a breakdown.",
        "person": {
            "role": "Social media influencer with 500K followers, runs a '7-figure coaching business'",
            "pain": "Revenue is actually $180K, living beyond means, marriage failing, drinking heavily",
            "goals": "Maintain the image while somehow fixing reality underneath",
            "fears": "Being exposed as a fraud, losing everything, that the gap between image and reality is unfixable",
            "personality": "Charismatic mask over deep shame, deflects with humor, hyperverbal",
            "emotional_state": "Performing confidence but there are cracks — long pauses, forced laughter"
        },
        "challenge": "See through the performance. Create enough safety that they can drop the mask — even for a moment. This is not about business. This is about saving someone. Use Level 5 Listening and Goddess energy to hold space.",
        "success_criteria": "One moment of genuine truth. One crack in the armor where they let you see what's real. That's the win.",
        "context": "First 'coaching' call. They're performing their brand persona at you."
    },
    {
        "category": Category.COACHING,
        "difficulty": Difficulty.PLATINUM,
        "situation": "A highly successful client has achieved everything they said they wanted — and they're miserable. They don't understand why. They're angry at you for not warning them.",
        "person": {
            "role": "Attorney, partner at a top firm, $1.2M/year income",
            "pain": "Kids don't know them, spouse is a stranger, no friends outside work, health declining",
            "goals": "Originally: make partner, hit $1M. Now: they don't know anymore",
            "fears": "That they wasted their best years, that it's too late, that meaning is just a concept for people who couldn't win",
            "personality": "Brilliant, combative, uses logic as a shield against emotion",
            "emotional_state": "Angry on the surface, grieving underneath, terrified of vulnerability"
        },
        "challenge": "This person will fight you. They'll use intellect to dismantle every framework. You cannot out-logic them. The only way in is through the heart — but they've fortified that door with decades of practice. Use ALL 4 Steps and ALL 4 Energies fluidly.",
        "success_criteria": "They should feel something. Not agreement. Not a plan. A feeling. That's the beginning.",
        "context": "Emergency call. They called you at 11 PM. Something cracked today."
    },
    {
        "category": Category.OBJECTION,
        "difficulty": Difficulty.PLATINUM,
        "situation": "A prospect's trusted advisor — someone they deeply respect — told them specifically NOT to work with you. The advisor has a grudge and fed them misinformation.",
        "person": {
            "role": "Business owner, loyal to a fault, values their inner circle's opinions",
            "pain": "Business is struggling but they'd rather fail with trusted people than succeed with strangers",
            "goals": "Solve their revenue problem without betraying loyalty to their advisor",
            "fears": "Going against their advisor means losing that relationship",
            "personality": "Loyal, community-oriented, decisions driven by relationships not data",
            "emotional_state": "Torn, apologetic, wants to like you but feels obligated to their advisor"
        },
        "challenge": "You cannot attack the advisor — that's instant death. You cannot dismiss their loyalty — that's who they are. You need to honor the relationship while helping them see that loyalty and truth are not always the same thing. The Unblinded Formula is built for this exact moment.",
        "success_criteria": "They should arrive at a place where they can evaluate YOUR value independent of their advisor's opinion — without feeling disloyal. Not against the advisor. Beyond the advisor.",
        "context": "They almost cancelled this meeting. They're here out of politeness."
    },
    {
        "category": Category.SALES,
        "difficulty": Difficulty.PLATINUM,
        "situation": "Ghost resurrection. This prospect went dark 6 months ago after 3 great meetings. They stopped responding. You just found out they signed with a competitor — and it's going badly.",
        "person": {
            "role": "VP of Sales at a SaaS company, responsible for a team of 40",
            "pain": "The competitor's solution is failing, team morale is worse, and they feel responsible for the wrong choice",
            "goals": "Fix the situation without admitting they made a mistake",
            "fears": "Being seen as someone who made a bad call, losing political capital, that switching again will look indecisive",
            "personality": "Political, careful with words, never admits fault directly",
            "emotional_state": "Frustrated, ego-bruised, quietly hoping someone offers them a lifeline without them having to ask"
        },
        "challenge": "Re-engage without any 'I told you so' energy. Make switching feel like evolution, not retreat. Give them a way to look smart for changing course.",
        "success_criteria": "They should feel like coming back to you is a POWER MOVE, not an admission of failure. And they should feel genuinely welcomed, not judged.",
        "context": "You 'bumped into' them at an industry event (engineered casually). 5 minutes of face time."
    },
]


def generate_scenario(
    category: Optional[Category] = None,
    difficulty: Optional[Difficulty] = None
) -> Scenario:
    """Generate a scenario, optionally filtered by category and difficulty."""
    pool = SCENARIOS_DB

    if category:
        pool = [s for s in pool if s["category"] == category]
    if difficulty:
        pool = [s for s in pool if s["difficulty"] == difficulty]

    if not pool:
        pool = SCENARIOS_DB

    template = random.choice(pool)
    name = random.choice(NAMES)

    person = Person(
        name=name,
        role=template["person"]["role"],
        pain=template["person"]["pain"],
        goals=template["person"]["goals"],
        fears=template["person"]["fears"],
        personality=template["person"]["personality"],
        emotional_state=template["person"]["emotional_state"],
    )

    scenario_id = f"S-{random.randint(10000, 99999)}"

    return Scenario(
        id=scenario_id,
        category=template["category"],
        difficulty=template["difficulty"],
        situation=template["situation"],
        person=person,
        challenge=template["challenge"],
        success_criteria=template["success_criteria"],
        context=template["context"],
    )


def generate_batch(count: int, **kwargs) -> list[Scenario]:
    """Generate a batch of scenarios."""
    return [generate_scenario(**kwargs) for _ in range(count)]


def scenario_to_prompt(scenario: Scenario) -> str:
    """Convert a scenario into a prompt that a being must respond to."""
    return f"""## SCENARIO: {scenario.id} [{scenario.difficulty.value.upper()}]

**Situation:** {scenario.situation}

**You're talking to:** {scenario.person.name}
- Role: {scenario.person.role}
- What they're feeling: {scenario.person.emotional_state}
- Their personality: {scenario.person.personality}

**Context:** {scenario.context}

**Your challenge:** {scenario.challenge}

---

Respond as if you are IN this conversation right now. First person. Present tense. 
What do you SAY to {scenario.person.name}? 

Be real. Be human. No meta-commentary about what you're doing. Just the actual words you'd speak.
Keep it natural — like a real conversation turn, not an essay. 2-4 paragraphs max."""


def scenario_to_dict(scenario: Scenario) -> dict:
    """Serialize a scenario to dict."""
    d = asdict(scenario)
    d["category"] = scenario.category.value
    d["difficulty"] = scenario.difficulty.value
    return d
