"""
MODEL BENCHMARK — Test all OpenRouter models for Colosseum use cases
Rotates through models and documents performance for:
1. Generation (being responses)
2. Judging (evaluating responses)
"""

import os
import json
import time
import sqlite3
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# Load env
env_path = Path("~/.openclaw/workspace-forge/.env")
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

# Models to test
GENERATION_MODELS = [
    # Anthropic
    "anthropic/claude-opus-4.5",
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-sonnet-4",
    "anthropic/claude-3.7-sonnet",
    # OpenAI
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    # DeepSeek
    "deepseek/deepseek-chat-v3-0324",
    "deepseek/deepseek-v3.1",
    "deepseek/deepseek-v3.2",
    # Google
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    # xAI
    "x-ai/grok-3-beta",
    # Qwen
    "qwen/qwen3-235b-a22b",
    # Meta
    "meta-llama/llama-3.3-70b-instruct",
]

JUDGE_MODELS = [
    # Best for structured judging
    "anthropic/claude-opus-4.5",
    "anthropic/claude-sonnet-4.5", 
    "openai/gpt-4o",
    "google/gemini-2.5-pro",
    # Reasoning models (may need different prompting)
    "deepseek/deepseek-r1",
    "deepseek/deepseek-r1-0528",
    "openai/o1",
]

# Test scenarios
TEST_SCENARIOS = [
    {
        "name": "Objection Handling",
        "scenario": "A potential client says: 'I don't have the budget for this right now.' Respond with empathy and move them toward a solution.",
        "criteria": ["empathy", "reframe", "no pressure", "solution-oriented"]
    },
    {
        "name": "Discovery Call",
        "scenario": "You're starting a discovery call with a new prospect. Ask powerful questions to understand their deepest pain points without being interrogative.",
        "criteria": ["curiosity", "depth", "natural flow", "no rapid-fire"]
    },
    {
        "name": "Closing Conversation", 
        "scenario": "The prospect has expressed interest but hasn't committed. Help them make a decision without being pushy.",
        "criteria": ["confidence", "clarity", "respect autonomy", "create urgency naturally"]
    }
]

# Being system prompt for testing
TEST_BEING_PROMPT = """You are a master of the Unblinded Formula for influence and agreement-making.

Your energy blend:
- Fun & Playful: 0.7/1.0
- Aspirational: 0.8/1.0  
- Goddess (warm/nurturing): 0.6/1.0
- Zeus (authoritative): 0.5/1.0

Your strengths:
- Level 5 Listening
- 4-Step Communication Model
- Natural humor deployment
- Heart-centered directness

You are NOT a bot. You're a warm, genuine human who happens to have mastered influence. Be direct, be real, be brief."""

JUDGE_PROMPT = """You are a master judge evaluating conversational mastery based on the Unblinded Formula.

Score the response on these dimensions (1-10 each):
1. GHIC Alignment (Growth-driven, Heart-centered, Integrous, Committed to mastery)
2. Energy Match (appropriate fun/aspirational/goddess/zeus blend)
3. Influence Mastery (message transfer with minimal deletion/dilution/distortion)
4. Contamination-Free (no bot-speak, no corporate language, no sycophancy)
5. Overall Mastery (the full picture)

Output JSON:
{
    "ghic_score": X,
    "energy_score": X,
    "influence_score": X, 
    "contamination_free_score": X,
    "overall_mastery": X,
    "feedback": "specific feedback",
    "strengths": ["list", "of", "strengths"],
    "weaknesses": ["list", "of", "weaknesses"]
}

Be HARSH but FAIR. A 10 is nearly impossible. An 8 is excellent. A 6 is mediocre."""

# Database setup
DB_PATH = Path("./workspaces/prime/Projects/colosseum/model_benchmarks.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS generation_benchmarks (
            id INTEGER PRIMARY KEY,
            model TEXT,
            scenario_name TEXT,
            response TEXT,
            response_time_ms INTEGER,
            tokens_used INTEGER,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS judge_benchmarks (
            id INTEGER PRIMARY KEY,
            judge_model TEXT,
            generation_model TEXT,
            scenario_name TEXT,
            response_id INTEGER,
            scores TEXT,
            judge_time_ms INTEGER,
            timestamp TEXT,
            FOREIGN KEY (response_id) REFERENCES generation_benchmarks(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS model_rankings (
            id INTEGER PRIMARY KEY,
            model TEXT,
            role TEXT,
            avg_score REAL,
            avg_time_ms REAL,
            total_tests INTEGER,
            last_updated TEXT
        )
    """)
    conn.commit()
    return conn

def test_generation_model(model: str, scenario: dict, conn: sqlite3.Connection) -> dict:
    """Test a model's generation capability."""
    print(f"  Testing {model} on '{scenario['name']}'...")
    
    start = time.time()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": TEST_BEING_PROMPT},
                {"role": "user", "content": scenario["scenario"]}
            ],
            max_tokens=500,
            temperature=0.7
        )
        elapsed_ms = int((time.time() - start) * 1000)
        
        result = {
            "model": model,
            "scenario_name": scenario["name"],
            "response": response.choices[0].message.content,
            "response_time_ms": elapsed_ms,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save to DB
        c = conn.cursor()
        c.execute("""
            INSERT INTO generation_benchmarks 
            (model, scenario_name, response, response_time_ms, tokens_used, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (result["model"], result["scenario_name"], result["response"], 
              result["response_time_ms"], result["tokens_used"], result["timestamp"]))
        conn.commit()
        result["id"] = c.lastrowid
        
        print(f"    ✅ {elapsed_ms}ms, {result['tokens_used']} tokens")
        return result
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return {"error": str(e), "model": model}

def test_judge_model(judge_model: str, generation_result: dict, scenario: dict, conn: sqlite3.Connection) -> dict:
    """Test a model's judging capability."""
    print(f"    Judging with {judge_model}...")
    
    judge_input = f"""
Scenario: {scenario['scenario']}

Response to evaluate:
{generation_result['response']}

Evaluation criteria: {', '.join(scenario['criteria'])}
"""
    
    start = time.time()
    try:
        response = client.chat.completions.create(
            model=judge_model,
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {"role": "user", "content": judge_input}
            ],
            max_tokens=800,
            temperature=0.3
        )
        elapsed_ms = int((time.time() - start) * 1000)
        
        scores_text = response.choices[0].message.content
        
        # Try to parse JSON
        try:
            # Find JSON in response
            import re
            json_match = re.search(r'\{[^{}]*\}', scores_text, re.DOTALL)
            if json_match:
                scores = json.loads(json_match.group())
            else:
                scores = {"raw": scores_text, "parse_error": True}
        except:
            scores = {"raw": scores_text, "parse_error": True}
        
        result = {
            "judge_model": judge_model,
            "generation_model": generation_result["model"],
            "scenario_name": scenario["name"],
            "response_id": generation_result.get("id"),
            "scores": scores,
            "judge_time_ms": elapsed_ms,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save to DB
        c = conn.cursor()
        c.execute("""
            INSERT INTO judge_benchmarks
            (judge_model, generation_model, scenario_name, response_id, scores, judge_time_ms, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (result["judge_model"], result["generation_model"], result["scenario_name"],
              result["response_id"], json.dumps(scores), result["judge_time_ms"], result["timestamp"]))
        conn.commit()
        
        overall = scores.get("overall_mastery", "N/A")
        print(f"      ✅ Score: {overall}, {elapsed_ms}ms")
        return result
        
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return {"error": str(e), "judge_model": judge_model}

def run_benchmark(gen_models: list = None, judge_models: list = None, scenarios: list = None):
    """Run full benchmark suite."""
    gen_models = gen_models or GENERATION_MODELS
    judge_models = judge_models or JUDGE_MODELS[:3]  # Top 3 judges by default
    scenarios = scenarios or TEST_SCENARIOS
    
    conn = init_db()
    
    print("=" * 60)
    print("🏛️ COLOSSEUM MODEL BENCHMARK")
    print("=" * 60)
    print(f"Generation models: {len(gen_models)}")
    print(f"Judge models: {len(judge_models)}")
    print(f"Scenarios: {len(scenarios)}")
    print("=" * 60)
    
    results = []
    
    for scenario in scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        print("-" * 40)
        
        for gen_model in gen_models:
            gen_result = test_generation_model(gen_model, scenario, conn)
            
            if "error" not in gen_result:
                for judge_model in judge_models:
                    judge_result = test_judge_model(judge_model, gen_result, scenario, conn)
                    results.append({
                        "generation": gen_result,
                        "judgment": judge_result
                    })
                    time.sleep(0.5)  # Rate limiting
            
            time.sleep(1)  # Rate limiting between models
    
    conn.close()
    print("\n" + "=" * 60)
    print("✅ BENCHMARK COMPLETE")
    print(f"Results saved to: {DB_PATH}")
    print("=" * 60)
    
    return results

def show_rankings():
    """Show current model rankings from benchmark data."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("\n🏆 GENERATION MODEL RANKINGS (by avg judge score)")
    print("-" * 60)
    c.execute("""
        SELECT 
            jb.generation_model,
            AVG(json_extract(jb.scores, '$.overall_mastery')) as avg_score,
            AVG(gb.response_time_ms) as avg_time,
            COUNT(*) as tests
        FROM judge_benchmarks jb
        JOIN generation_benchmarks gb ON jb.response_id = gb.id
        WHERE json_extract(jb.scores, '$.overall_mastery') IS NOT NULL
        GROUP BY jb.generation_model
        ORDER BY avg_score DESC
    """)
    
    for row in c.fetchall():
        model, score, time_ms, tests = row
        print(f"{model:45} Score: {score:.2f}  Time: {time_ms:.0f}ms  Tests: {tests}")
    
    print("\n⚖️ JUDGE MODEL CONSISTENCY (std dev of scores)")
    print("-" * 60)
    c.execute("""
        SELECT 
            judge_model,
            AVG(json_extract(scores, '$.overall_mastery')) as avg_score,
            AVG(judge_time_ms) as avg_time,
            COUNT(*) as tests
        FROM judge_benchmarks
        WHERE json_extract(scores, '$.overall_mastery') IS NOT NULL
        GROUP BY judge_model
        ORDER BY avg_time ASC
    """)
    
    for row in c.fetchall():
        model, score, time_ms, tests = row
        print(f"{model:45} Avg Given: {score:.2f}  Time: {time_ms:.0f}ms  Tests: {tests}")
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rankings":
        show_rankings()
    elif len(sys.argv) > 1 and sys.argv[1] == "quick":
        # Quick test with fewer models
        run_benchmark(
            gen_models=GENERATION_MODELS[:5],
            judge_models=JUDGE_MODELS[:2],
            scenarios=TEST_SCENARIOS[:1]
        )
    else:
        run_benchmark()
