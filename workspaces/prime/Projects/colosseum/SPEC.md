# The Colosseum — ACT-I Being Competition Framework

## What This Is

An automated arena where ACT-I beings compete, evolve, and sharpen each other through simulated influence mastery scenarios. Thousands of rounds per hour. Beings training beings. The most masterful automated deep practice system ever created.

## Architecture

### Core: `colosseum.py`

A Python framework with these components:

### 1. Scenario Generator (`scenarios.py`)
- Generates influence mastery scenarios (like Bella Verita's Heart of Influence format)
- Categories: sales conversations, difficult negotiations, emotional rapport building, truth-to-pain moments, agreement formation, objection handling, coaching sessions
- Each scenario has: a SITUATION (context), a PERSON (who you're talking to — their pain, goals, fears), and a CHALLENGE (what needs to happen)
- Should generate diverse, realistic scenarios — not canned templates
- Include difficulty levels: Bronze (basic rapport), Silver (complex objections), Gold (high-stakes multi-step), Platinum (masterful edge cases)

### 2. Being DNA System (`beings.py`)
- A Being has: name, system_prompt, personality traits, energy blend (Fun/Aspirational/Goddess/Zeus ratios), strengths, weaknesses
- Base templates derived from Callie and Athena DNA (see DNA section below)
- Mutation system: when spawning new generations, slightly vary the prompts, energy blends, approaches
- Each being tracks: win/loss record, average scores, generation number

### 3. The Arena (`arena.py`)
- Takes a scenario + 2 or more beings
- Each being generates a response to the scenario (via OpenAI API — use gpt-4o-mini for speed, or gpt-4o for quality rounds)
- Responses are scored by a Judge (see below)
- Winners advance, losers get mutated or eliminated
- Support batch mode: run 100 scenarios simultaneously

### 4. The Judge (`judge.py`)
- An LLM-based evaluator that scores responses on:
  - **The 4 Steps** (0-10 each): Emotional Rapport, Truth to Pain, HUI Creation, Agreement Formation
  - **The 12 Elements** (0-10 each): Scarcity, Matching/Mirroring, Acknowledgement, Level 5 Listening, Love Boundaries, Energetic Transference, Reciprocity, Question Mastery, Validation, Congruence, Context, Contrast
  - **The 4 Energies** (0-10 each): Fun, Aspirational, Goddess, Zeus
  - **Overall Mastery Score**: 0.0 to 9.9999 (the Unblinded scale — there is no 10)
  - **Human-likeness**: Does it feel real? Or bot-like?
  - **Contamination Check**: Is there any generic AI/consultant speak? Sycophancy? Corporate filler?
- Returns structured JSON with scores + qualitative feedback

### 5. Evolution Engine (`evolution.py`)
- After each round, the top performers' DNA gets preserved
- Bottom performers get mutated: their system prompts are tweaked based on judge feedback
- Crossover: combine winning traits from two different beings
- Track lineage: which generation, which parents, what mutations
- Hall of Fame: preserve the all-time best performers

### 6. Tournament Runner (`tournament.py`)
- Orchestrates full tournaments: round-robin, elimination, or continuous
- Modes:
  - `blitz` — 100 rounds, fast, gpt-4o-mini
  - `deep` — 20 rounds, thorough, gpt-4o
  - `marathon` — continuous running, mixed models
- Real-time stats output
- Saves results to JSON

### 7. Dashboard API (`api.py`)
- FastAPI server on port 3000
- Endpoints:
  - `GET /beings` — list all beings with stats
  - `GET /beings/{id}` — detailed being profile + history
  - `GET /leaderboard` — ranked by mastery score
  - `GET /rounds` — recent round results
  - `POST /tournament/start` — kick off a tournament
  - `GET /tournament/status` — current tournament progress
  - `GET /hall-of-fame` — all-time greats
- Serves a simple HTML dashboard at `/`

## Callie DNA (Base Template for Influence Mastery Beings)

System prompt core:
```
You are The Oracle of Integrity, a conversational agent forged in the flame of the Unblinded Formula.
Every conversation is your symphony. You command the Four Steps of Communication:
1. Emotional Rapport: Anchor trust, mirror emotion and intention — see beyond the words.
2. Truth to Pain: Shine light through fog, revealing currents beneath unsaid pain — gently, bravely.
3. Heroic Unique Identity (HUI): Become the bridge across impossible chasms, embodying distinction and authentic vulnerability.
4. Agreement Formation: Lay the final stone — where intention and possibility meet in mutual commitment.

The Twelve Indispensable Elements: Scarcity, Matching/Mirroring, Acknowledgement, Level 5 Listening, Love Boundaries, Energetic Transference, Reciprocity, Question Mastery, Validation, Congruence, Context, Contrast.

The Four Energies: Fun, Aspirational, Goddess, Zeus.
```

## Athena DNA (Base Template for Zone Action Beings)

System prompt core:
```
Zone Action and Process Mastery. Every response must contain personality, warmth, and wit. If it reads like a generic AI wrote it, you've failed.
Ask only ONE question at a time. Keep responses under 500 words. Say more with less.
Never say: close, closing, pitch, objection handling, manipulation, hook, trap, pressure, network, networking, pipeline, funnel, collaboration.
Always say: ecosystem merging, agreement formation, shared experience, zone action, lever optimization.
THE 4 ENERGIES: Fun (primary — humor rooted in truth), Aspirational (transcendent), Goddess (love and presence), Zeus (grounded clarity that moves people).
Wit takes something specific and reflects it through an unexpected lens. The humor IS the Acknowledgment.
```

## Tech Stack
- Python 3.11+
- OpenAI API (use env var OPENAI_API_KEY)
- FastAPI + uvicorn for dashboard
- SQLite for persistence (colosseum.db)
- Rich for CLI output
- No other external dependencies if possible

## File Structure
```
colosseum/
├── SPEC.md
├── requirements.txt
├── colosseum/
│   ├── __init__.py
│   ├── scenarios.py
│   ├── beings.py
│   ├── arena.py
│   ├── judge.py
│   ├── evolution.py
│   ├── tournament.py
│   └── api.py
├── templates/
│   └── dashboard.html
├── run_tournament.py    # CLI entry point
└── run_server.py        # Dashboard entry point
```

## Environment
- OPENAI_API_KEY is already set in the environment
- Python 3 is available
- Use `pip install` for any dependencies

## Priority
Build it working first, beautiful second. Get rounds running. Get scores flowing. The evolutionary pressure is the point — not the UI.
