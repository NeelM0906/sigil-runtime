"""
MULTI-MODEL JUDGES — Each judge uses the LLM best suited for its evaluation type
"""

import os
import json
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

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

# Load judge model assignments
ASSIGNMENTS_PATH = Path(__file__).parent / "judge_model_assignments.json"
with open(ASSIGNMENTS_PATH) as f:
    JUDGE_ASSIGNMENTS = json.load(f)["judge_model_assignments"]

# Load judge definitions
JUDGES_PATH = Path(__file__).parent / "v2/data/judges_19.json"
with open(JUDGES_PATH) as f:
    JUDGES = json.load(f)

# Default fallback model
DEFAULT_MODEL = "anthropic/claude-sonnet-4.5"


def get_model_for_judge(judge_name: str) -> str:
    """Get the best model for a specific judge."""
    if judge_name in JUDGE_ASSIGNMENTS:
        return JUDGE_ASSIGNMENTS[judge_name]["model"]
    return DEFAULT_MODEL


def get_reason_for_assignment(judge_name: str) -> str:
    """Get the reason for a judge's model assignment."""
    if judge_name in JUDGE_ASSIGNMENTS:
        return JUDGE_ASSIGNMENTS[judge_name]["reason"]
    return "Default assignment"


def judge_response(
    judge_name: str,
    scenario: str,
    response: str,
    verbose: bool = False
) -> dict:
    """
    Have a specific judge evaluate a response using its assigned optimal model.
    
    Returns: {
        "judge_name": str,
        "model_used": str,
        "scores": dict,
        "feedback": str,
        "raw_output": str
    }
    """
    if judge_name not in JUDGES:
        return {"error": f"Unknown judge: {judge_name}"}
    
    judge = JUDGES[judge_name]
    model = get_model_for_judge(judge_name)
    
    if verbose:
        print(f"🔍 {judge['name']} using {model}")
        print(f"   Reason: {get_reason_for_assignment(judge_name)}")
    
    prompt = judge.get("prompt", "")
    
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"""
Scenario: {scenario}

Response to evaluate:
{response}

Provide your evaluation as JSON with scores and feedback.
"""}
    ]
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=800,
            temperature=0.3
        )
        
        raw_output = completion.choices[0].message.content
        
        # Try to parse JSON from response
        import re
        json_match = re.search(r'\{[^{}]*\}', raw_output, re.DOTALL)
        if json_match:
            try:
                scores = json.loads(json_match.group())
            except:
                scores = {"raw": raw_output, "parse_error": True}
        else:
            scores = {"raw": raw_output, "parse_error": True}
        
        return {
            "judge_name": judge_name,
            "judge_display_name": judge["name"],
            "model_used": model,
            "model_reason": get_reason_for_assignment(judge_name),
            "scores": scores,
            "feedback": scores.get("feedback", ""),
            "raw_output": raw_output
        }
        
    except Exception as e:
        return {
            "judge_name": judge_name,
            "model_used": model,
            "error": str(e)
        }


def run_all_judges(
    scenario: str,
    response: str,
    judges_to_run: list = None,
    verbose: bool = True
) -> dict:
    """
    Run all (or specified) judges on a response, each using their optimal model.
    
    Returns: {
        "scenario": str,
        "response_preview": str,
        "judgments": [list of judge results],
        "summary": {aggregate stats}
    }
    """
    judges_to_run = judges_to_run or list(JUDGES.keys())
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"🏛️ MULTI-MODEL JUDGMENT PANEL")
        print(f"{'='*60}")
        print(f"Judges: {len(judges_to_run)}")
        print(f"Models used: {len(set(get_model_for_judge(j) for j in judges_to_run))}")
        print(f"{'='*60}\n")
    
    results = []
    overall_scores = []
    
    for judge_name in judges_to_run:
        result = judge_response(judge_name, scenario, response, verbose=verbose)
        results.append(result)
        
        if "scores" in result and "overall" in result["scores"]:
            overall_scores.append(result["scores"]["overall"])
        
        if verbose:
            overall = result.get("scores", {}).get("overall", "N/A")
            print(f"   Score: {overall}\n")
    
    # Calculate summary
    summary = {
        "total_judges": len(results),
        "successful_judgments": len([r for r in results if "error" not in r]),
        "models_used": list(set(r.get("model_used", "unknown") for r in results)),
    }
    
    if overall_scores:
        summary["avg_overall_score"] = sum(overall_scores) / len(overall_scores)
        summary["min_score"] = min(overall_scores)
        summary["max_score"] = max(overall_scores)
    
    return {
        "scenario": scenario,
        "response_preview": response[:200] + "..." if len(response) > 200 else response,
        "judgments": results,
        "summary": summary
    }


def show_judge_assignments():
    """Display all judge-to-model assignments."""
    print("\n🏛️ JUDGE MODEL ASSIGNMENTS")
    print("="*70)
    
    # Group by model
    by_model = {}
    for judge_name in JUDGES:
        model = get_model_for_judge(judge_name)
        if model not in by_model:
            by_model[model] = []
        by_model[model].append({
            "name": judge_name,
            "display": JUDGES[judge_name]["name"],
            "reason": get_reason_for_assignment(judge_name)
        })
    
    for model, judges in sorted(by_model.items()):
        print(f"\n📦 {model} ({len(judges)} judges)")
        print("-"*50)
        for j in judges:
            print(f"  • {j['display']}")
            print(f"    Reason: {j['reason']}")
    
    print(f"\n{'='*70}")
    print(f"Total: {len(JUDGES)} judges across {len(by_model)} models")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "assignments":
        show_judge_assignments()
    else:
        # Demo run
        show_judge_assignments()
        
        print("\n\n🎯 DEMO JUDGMENT")
        print("="*70)
        
        demo_scenario = "A potential client says: 'I don't have the budget for this right now.'"
        demo_response = """I hear you on that. Budget is real - and honestly, I respect you being straight with me about where you're at.

Here's what I'm curious about though... when you say 'right now,' what would need to shift? Is it a timing thing, or is there something about the value that isn't landing yet?

Because if this genuinely isn't the right fit or time, I'm totally okay with that. But if there's a piece we haven't explored that could change the math... I'd love to dig into that with you."""
        
        # Run just 3 judges for demo
        result = run_all_judges(
            demo_scenario, 
            demo_response,
            judges_to_run=["sean_judge", "contamination_judge", "sales_closing_judge"],
            verbose=True
        )
        
        print("\n📊 SUMMARY")
        print(json.dumps(result["summary"], indent=2))
