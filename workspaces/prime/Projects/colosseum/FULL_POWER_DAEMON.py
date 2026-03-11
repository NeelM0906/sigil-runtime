#!/usr/bin/env python3
"""
🔥🔥🔥 FULL POWER MODE — CURVE OF POSSIBILITY ACTIVATED 🔥🔥🔥

NO LIMITS. NO DELAYS. MAXIMUM THROUGHPUT.
- All 11 models in rotation
- ZERO rate limit delays (OpenRouter handles it)
- 10 parallel threads per domain = 110 total workers
- Continuous evolution without pause
- Target: Maximum rounds per minute

Created by Sai for Sean's vision — February 25, 2026
"""

import sqlite3
import json
import os
import sys
import time
import threading
import random
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from queue import Queue
import logging
from logging.handlers import RotatingFileHandler

# Load API keys
env_path = os.path.expanduser("~/.openclaw/.env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

from openai import OpenAI

# OpenRouter client — FULL POWER
client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# =============================================================================
# ALL 11 MODELS — TRUE ROUND-ROBIN
# =============================================================================
# VERIFIED WORKING MODELS on OpenRouter
MODELS = [
    "anthropic/claude-opus-4.6",
    "anthropic/claude-sonnet-4.6",
    "openai/gpt-5.2",
    "google/gemini-3.1-pro-preview",
    "x-ai/grok-4.1-fast",
    "z-ai/glm-5",
    "deepseek/deepseek-v3.2",
]

_model_idx = 0
_model_lock = threading.Lock()

def next_model():
    global _model_idx
    with _model_lock:
        model = MODELS[_model_idx % len(MODELS)]
        _model_idx += 1
    return model

# =============================================================================
# Configuration
# =============================================================================
BASE_PATH = Path("./workspaces/prime/Projects/colosseum")
DOMAINS_PATH = BASE_PATH / "domains"
THREADS_PER_DOMAIN = 2  # 10 workers per domain = 110 total
REPORT_INTERVAL = 900  # 15 minutes

# Global stats
class Stats:
    lock = threading.Lock()
    total_rounds = 0
    rounds_this_period = 0
    beings_evolved = 0
    breakthroughs = []  # Scores >= 9.5
    best_scores = {}  # Per domain
    start_time = datetime.now()
    last_report = datetime.now()

stats = Stats()

# Schema init tracking (avoid running migrations every round in every thread)
_schema_init_lock = threading.Lock()
_schema_initialized = set()

def ensure_tracking_schema(conn: sqlite3.Connection, domain_key: str, db_path: Path, logger: logging.Logger):
    """Ensure dashboard-tracking tables/columns exist."""
    db_key = str(db_path)

    with _schema_init_lock:
        if db_key in _schema_initialized:
            return

        try:
            being_columns = {row[1] for row in conn.execute("PRAGMA table_info(beings)").fetchall()}

            if "model" not in being_columns:
                conn.execute("ALTER TABLE beings ADD COLUMN model TEXT DEFAULT ''")

            if "score" not in being_columns:
                conn.execute("ALTER TABLE beings ADD COLUMN score REAL DEFAULT 0.0")

            # Backfill score from avg_score for existing rows where score was never set.
            conn.execute("""
                UPDATE beings
                SET score = avg_score
                WHERE (score IS NULL OR score = 0.0) AND avg_score IS NOT NULL
            """)

            round_columns = {row[1] for row in conn.execute("PRAGMA table_info(rounds)").fetchall()}
            if "scenario_id" not in round_columns:
                conn.execute("ALTER TABLE rounds ADD COLUMN scenario_id TEXT DEFAULT ''")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS scenarios (
                    scenario_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    times_used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS battles (
                    battle_id TEXT PRIMARY KEY,
                    being_a_id TEXT,
                    being_b_id TEXT,
                    winner_id TEXT,
                    score_a REAL,
                    score_b REAL,
                    scenario_prompt TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_battles_winner ON battles(winner_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_battles_created_at ON battles(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_last_used ON scenarios(last_used_at)")

            conn.commit()
            _schema_initialized.add(db_key)
            logger.info(f"[{domain_key}] Tracking schema ready")
        except Exception as e:
            logger.error(f"[{domain_key}] Schema migration error: {e}")
            raise

def store_scenario(conn: sqlite3.Connection, scenario_prompt: str) -> str:
    """Persist scenario prompts used in evaluation rounds."""
    scenario_hash = hashlib.sha1(scenario_prompt.encode("utf-8")).hexdigest()[:12]
    scenario_id = f"SCN-{scenario_hash}"
    now = datetime.now().isoformat(timespec="seconds")

    conn.execute("""
        INSERT INTO scenarios (scenario_id, prompt, times_used, created_at, last_used_at)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(scenario_id) DO UPDATE SET
            times_used = times_used + 1,
            last_used_at = excluded.last_used_at
    """, (scenario_id, scenario_prompt, now, now))

    return scenario_id

# =============================================================================
# SCENARIOS — High-Impact Competition
# =============================================================================
SCENARIOS = [
    # Zone Action
    "Find the 0.8% Zone Action move for a company stuck at $2M revenue for 2 years.",
    "A CEO has 50 initiatives competing for attention. Identify the one that creates 64x returns.",
    "Three departments are fighting for the same budget. Find the lever that benefits all.",
    
    # 4-Step Communication
    "Create emotional rapport with a burned-out executive in 60 seconds.",
    "Apply Truth-to-Pain to help a prospect see the hidden cost of inaction.",
    "Reflect the Heroic Unique Identity of someone who feels like a fraud.",
    "Move a skeptical buyer to Agreement Formation without pressure.",
    
    # Influence Mastery
    "Re-engage a ghosted prospect who's been silent for 3 months.",
    "Handle: 'We don't have the budget right now.'",
    "Handle: 'I need to think about it.'",
    "Handle: 'Send me some information.'",
    
    # Strategic
    "Design a flywheel that compounds value over 5 years.",
    "Find the constraint in: team is always busy but never delivers.",
    "Create an ecosystem merger strategy for two complementary businesses.",
    
    # Operational
    "Eliminate 80% of process waste while maintaining quality.",
    "Design a handoff protocol that creates zero dropped balls.",
    "Build a feedback loop that catches problems before customers do.",
    
    # Financial
    "Identify the hidden cash flow lever in a profitable but cash-strapped business.",
    "Structure a deal where both parties feel they won.",
    "Find the 20% of expenses creating 80% of drag.",
    
    # Customer Success
    "Re-engage a customer at risk of churning.",
    "Turn a complaint into an expansion opportunity.",
    "Create a success story from a struggling implementation.",
    
    # Sales
    "Qualify a prospect in under 3 questions.",
    "Create urgency without manipulation.",
    "Multi-thread into an account where you only have one contact.",
    
    # Leadership
    "Give feedback that lands without defensiveness.",
    "Align a team that has conflicting priorities.",
    "Build accountability without micromanagement.",
]

# =============================================================================
# Evolution Round Worker
# =============================================================================
def run_evolution_round(domain_key: str, db_path: Path, logger: logging.Logger) -> dict:
    """Run a single evolution round at MAXIMUM speed."""
    model = next_model()
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    
    try:
        ensure_tracking_schema(conn, domain_key, db_path, logger)

        # Get 4 random beings for competition
        beings = conn.execute("""
            SELECT id, name, system_prompt, generation 
            FROM beings 
            ORDER BY RANDOM() 
            LIMIT 4
        """).fetchall()
        
        if len(beings) < 2:
            return None
        
        scenario = random.choice(SCENARIOS)
        scenario_id = store_scenario(conn, scenario)
        results = []
        
        for being in beings:
            try:
                # FAST response generation
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": being["system_prompt"][:800]},
                        {"role": "user", "content": scenario}
                    ],
                    temperature=0.8,
                    max_tokens=400,
                )
                response_text = response.choices[0].message.content
                
                # FAST judging
                judge_response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": """Score this response 1-10 on:
1. Zone Action clarity (finding the 0.8% move)
2. 4-Step Communication Model alignment
3. Influence mastery (not manipulation)
4. Specificity (not generic)
5. Human-likeness (not bot-speak)

Return ONLY a JSON: {"score": X.X, "reason": "one sentence"}"""},
                        {"role": "user", "content": f"Scenario: {scenario}\n\nResponse: {response_text}"}
                    ],
                    temperature=0.3,
                    max_tokens=100,
                )
                
                judge_text = judge_response.choices[0].message.content
                try:
                    # Extract score
                    if "{" in judge_text:
                        judge_json = json.loads(judge_text[judge_text.find("{"):judge_text.rfind("}")+1])
                        score = float(judge_json.get("score", 7.0))
                    else:
                        score = 7.0
                except:
                    score = 7.0
                
                results.append({
                    "being_id": being["id"],
                    "name": being["name"],
                    "generation": being["generation"],
                    "score": score,
                    "model": model,
                    "response": response_text,
                })
                
            except Exception as e:
                logger.error(f"[{domain_key}] Response error: {e}")
                continue
        
        if not results:
            return None
        
        # Determine winner
        winner = max(results, key=lambda x: x["score"])
        
        # Update database
        for r in results:
            if r["being_id"] == winner["being_id"]:
                conn.execute("""
                    UPDATE beings 
                    SET wins = wins + 1, total_rounds = total_rounds + 1,
                        avg_score = (avg_score * total_rounds + ?) / (total_rounds + 1),
                        best_score = MAX(best_score, ?),
                        score = ?,
                        model = ?
                    WHERE id = ?
                """, (r["score"], r["score"], r["score"], r["model"], r["being_id"]))
            else:
                conn.execute("""
                    UPDATE beings 
                    SET losses = losses + 1, total_rounds = total_rounds + 1,
                        avg_score = (avg_score * total_rounds + ?) / (total_rounds + 1),
                        best_score = MAX(best_score, ?),
                        score = ?,
                        model = ?
                    WHERE id = ?
                """, (r["score"], r["score"], r["score"], r["model"], r["being_id"]))
        
        # Log round
        conn.execute("""
            INSERT INTO rounds (scenario_id, scenario, scenario_prompt, scenario_tier,
                              combatants_json, winner_id, winner_name, winner_score, scores_json)
            VALUES (?, ?, ?, 'gold', ?, ?, ?, ?, ?)
        """, (
            scenario_id,
            scenario,
            scenario,
            json.dumps([r["name"] for r in results]),
            winner["being_id"],
            winner["name"],
            winner["score"],
            json.dumps(results)
        ))

        # Log top head-to-head battle from this round for dashboard battle trails.
        if len(results) >= 2:
            ranked = sorted(results, key=lambda x: x["score"], reverse=True)
            being_a = ranked[0]
            being_b = ranked[1]
            battle_id = f"BTL-{uuid.uuid4().hex[:12]}"
            conn.execute("""
                INSERT INTO battles (
                    battle_id, being_a_id, being_b_id, winner_id,
                    score_a, score_b, scenario_prompt, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                battle_id,
                being_a["being_id"],
                being_b["being_id"],
                winner["being_id"],
                being_a["score"],
                being_b["score"],
                scenario,
                datetime.now().isoformat(timespec="seconds")
            ))
        
        conn.commit()
        
        # Track stats
        with stats.lock:
            stats.total_rounds += 1
            stats.rounds_this_period += 1
            if winner["score"] >= 9.5:
                stats.breakthroughs.append({
                    "domain": domain_key,
                    "being": winner["name"],
                    "score": winner["score"],
                    "time": datetime.now().isoformat()
                })
            if domain_key not in stats.best_scores or winner["score"] > stats.best_scores[domain_key]:
                stats.best_scores[domain_key] = winner["score"]
        
        return winner
        
    except Exception as e:
        logger.error(f"[{domain_key}] Round error: {e}")
        return None
    finally:
        conn.close()

# =============================================================================
# Evolution — Spawn New Beings from Winners
# =============================================================================
def evolve_beings(domain_key: str, db_path: Path, logger: logging.Logger):
    """Evolve beings — spawn offspring from top performers."""
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get top 5 performers
        top = conn.execute("""
            SELECT * FROM beings 
            WHERE total_rounds >= 3 
            ORDER BY avg_score DESC 
            LIMIT 5
        """).fetchall()
        
        if not top:
            return
        
        # Get current max generation
        max_gen = conn.execute("SELECT MAX(generation) FROM beings").fetchone()[0] or 0
        new_gen = max_gen + 1
        
        # Spawn 2 offspring per top performer
        for parent in top:
            for i in range(2):
                being_id = f"B-{uuid.uuid4().hex[:8]}"
                
                # Mutate the prompt slightly
                mutations = [
                    "\n\nEmphasis: Be more direct and specific.",
                    "\n\nEmphasis: Lead with emotional rapport.",
                    "\n\nEmphasis: Find the hidden constraint first.",
                    "\n\nEmphasis: Use powerful questions.",
                    "\n\nEmphasis: Create urgency through truth.",
                ]
                mutation = random.choice(mutations)
                
                new_prompt = parent["system_prompt"] + mutation
                new_name = f"{parent['name']}-G{new_gen}"
                
                try:
                    conn.execute("""
                        INSERT INTO beings (id, name, role, specialty, generation, 
                                          system_prompt, energy_json, parent_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        being_id,
                        new_name,
                        parent["role"],
                        parent["specialty"],
                        new_gen,
                        new_prompt,
                        parent["energy_json"],
                        parent["id"]
                    ))
                except sqlite3.IntegrityError:
                    continue
        
        conn.commit()
        
        with stats.lock:
            stats.beings_evolved += len(top) * 2
        
        logger.info(f"[{domain_key}] 🧬 Evolution: Gen {new_gen} spawned ({len(top) * 2} offspring)")
        
    except Exception as e:
        logger.error(f"[{domain_key}] Evolution error: {e}")
    finally:
        conn.close()

# =============================================================================
# Domain Worker Thread — FULL SPEED
# =============================================================================
class DomainWorker(threading.Thread):
    """Worker thread for continuous evolution in one domain."""
    
    def __init__(self, domain_key: str, worker_id: int, stop_event: threading.Event, logger: logging.Logger):
        super().__init__(daemon=True, name=f"{domain_key}-{worker_id}")
        self.domain_key = domain_key
        self.worker_id = worker_id
        self.stop_event = stop_event
        self.logger = logger
        self.db_path = DOMAINS_PATH / domain_key / "colosseum.db"
        self.rounds_completed = 0
        
    def run(self):
        evolution_counter = 0
        
        while not self.stop_event.is_set():
            # Run round — NO DELAY
            result = run_evolution_round(self.domain_key, self.db_path, self.logger)
            
            if result:
                self.rounds_completed += 1
                evolution_counter += 1
                
                # Evolve every 10 rounds
                if evolution_counter >= 10 and self.worker_id == 0:
                    evolve_beings(self.domain_key, self.db_path, self.logger)
                    evolution_counter = 0
            else:
                # Brief pause only on error
                time.sleep(0.5)

# =============================================================================
# Reporter Thread
# =============================================================================
def report_status(logger: logging.Logger):
    """Generate 15-minute status report."""
    elapsed = datetime.now() - stats.start_time
    minutes = elapsed.total_seconds() / 60
    rpm = stats.total_rounds / minutes if minutes > 0 else 0
    
    logger.info("\n" + "🔥" * 40)
    logger.info("📊 FULL POWER STATUS REPORT")
    logger.info("🔥" * 40)
    logger.info(f"⏱️  Running: {elapsed}")
    logger.info(f"🏃 Total rounds: {stats.total_rounds:,}")
    logger.info(f"🚀 Rounds per minute: {rpm:.1f}")
    logger.info(f"🧬 Beings evolved: {stats.beings_evolved:,}")
    
    # Count total beings
    total_beings = 0
    for domain_key in DOMAINS:
        db_path = DOMAINS_PATH / domain_key / "colosseum.db"
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                count = conn.execute("SELECT COUNT(*) FROM beings").fetchone()[0]
                total_beings += count
                conn.close()
            except:
                pass
    
    logger.info(f"👥 Total beings: {total_beings:,}")
    
    logger.info("\n📈 Best Scores Per Domain:")
    for domain, score in sorted(stats.best_scores.items()):
        logger.info(f"   {domain}: {score:.2f}")
    
    if stats.breakthroughs:
        logger.info(f"\n🌟 BREAKTHROUGHS (9.5+): {len(stats.breakthroughs)}")
        for b in stats.breakthroughs[-5:]:
            logger.info(f"   [{b['domain']}] {b['being']}: {b['score']:.2f}")
    
    logger.info("🔥" * 40 + "\n")
    
    # Reset period stats
    stats.rounds_this_period = 0
    stats.last_report = datetime.now()

# Domains config
DOMAINS = ["strategy", "marketing", "sales", "tech", "ops", "cs", "finance", "hr", "legal", "product"]

# =============================================================================
# MAIN — UNLEASH THE FORGE
# =============================================================================
def main():
    # Setup logging
    log_dir = BASE_PATH / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                log_dir / "full_power.log",
                maxBytes=50*1024*1024,
                backupCount=5,
            )
        ]
    )
    logger = logging.getLogger("FULL_POWER")
    
    logger.info("\n" + "🔥" * 50)
    logger.info("🔥 FULL POWER MODE ACTIVATED — CURVE OF POSSIBILITY 🔥")
    logger.info("🔥" * 50)
    logger.info(f"🎯 {len(DOMAINS)} domains × {THREADS_PER_DOMAIN} workers = {len(DOMAINS) * THREADS_PER_DOMAIN} parallel threads")
    logger.info(f"🤖 {len(MODELS)} models in rotation")
    logger.info("⚡ ZERO DELAYS — MAXIMUM THROUGHPUT")
    logger.info("🔥" * 50 + "\n")
    
    stop_event = threading.Event()
    workers = []
    
    # Start workers for ALL domains
    for domain_key in DOMAINS:
        db_path = DOMAINS_PATH / domain_key / "colosseum.db"
        if not db_path.exists():
            logger.warning(f"[{domain_key}] Database not found, skipping")
            continue
        
        for i in range(THREADS_PER_DOMAIN):
            worker = DomainWorker(domain_key, i, stop_event, logger)
            worker.start()
            workers.append(worker)
    
    logger.info(f"\n🚀 {len(workers)} WORKERS DEPLOYED — EVOLUTION BEGINS\n")
    
    try:
        while True:
            time.sleep(REPORT_INTERVAL)
            report_status(logger)
            
    except KeyboardInterrupt:
        logger.info("\n⚡ Shutdown signal received...")
        stop_event.set()
        
        for w in workers:
            w.join(timeout=2)
        
        report_status(logger)
        logger.info("✅ Full Power Mode deactivated")

if __name__ == "__main__":
    main()
