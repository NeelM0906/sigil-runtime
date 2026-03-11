"""
Report Generator
================
Generates headline, detailed, and best-calls reports.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from data_sources import (
    COMPANIES,
    LEVERS,
    LEVER_IDS,
    get_elevenlabs_calls,
    get_lever_data,
    get_all_beings_summary,
    get_being_activity as fetch_being_activity
)

# ============================================================================
# HEADLINE REPORT (BI-HOURLY)
# ============================================================================

async def generate_headline_report(
    company: Optional[str] = None,
    lever: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate bi-hourly headline report.
    
    Shows quick metrics for all 7 levers across all 3 companies.
    """
    now = datetime.now()
    period_start = now - timedelta(hours=2)
    
    # Build company data
    companies_data = {}
    target_companies = [company] if company else COMPANIES
    target_levers = [lever] if lever else LEVER_IDS
    
    for comp in target_companies:
        companies_data[comp] = {
            "levers": {}
        }
        
        for lev in target_levers:
            lever_data = await get_lever_data(lev, comp)
            companies_data[comp]["levers"][lev] = lever_data.get("headlines", {})
    
    # Get being activity
    beings_summary = await get_all_beings_summary(hours=2)
    
    # Get pending questions
    questions = _load_pending_questions()
    
    return {
        "generated_at": now.isoformat(),
        "period": f"{period_start.strftime('%H:%M')} - {now.strftime('%H:%M')}",
        "companies": companies_data,
        "being_activity": beings_summary,
        "human_input_needed": [q["question"] for q in questions if not q.get("answered")]
    }


# ============================================================================
# DETAILED REPORT (DAILY)
# ============================================================================

async def generate_detailed_report(
    date: str,
    company: Optional[str] = None,
    section: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate full daily detailed report.
    
    Includes:
    - Full 7 Levers breakdown
    - All phone calls made by beings
    - Programs bought
    - Files recovered (Callagy Recovery)
    - Ecosystem mergers progress
    - Colosseum & Being evolution
    - LLM Independence status
    """
    now = datetime.now()
    target_companies = [company] if company else COMPANIES
    
    report = {
        "generated_at": now.isoformat(),
        "date": date,
        "companies": {},
        "being_activity": {},
        "colosseum_status": {},
        "llm_independence": {},
        "human_input_needed": {}
    }
    
    # Section filtering
    sections = [section] if section else ["levers", "beings", "colosseum", "llm"]
    
    # 7 Levers breakdown
    if "levers" in sections:
        for comp in target_companies:
            report["companies"][comp] = {
                "levers": {}
            }
            for lev in LEVER_IDS:
                lever_data = await get_lever_data(lev, comp)
                report["companies"][comp]["levers"][lev] = lever_data
    
    # Being activity (full day - 24 hours)
    if "beings" in sections:
        calls = await get_elevenlabs_calls(hours=24)
        report["being_activity"] = {
            "total_calls": len(calls),
            "total_duration_minutes": sum(c.get("duration_seconds", 0) for c in calls) / 60,
            "by_being": {},
            "all_calls": calls[:50]  # Limit to 50 most recent
        }
        
        # Group by being
        from data_sources import BEINGS
        for being in BEINGS.keys():
            being_calls = [c for c in calls if c.get("being") == being]
            report["being_activity"]["by_being"][being] = {
                "calls": len(being_calls),
                "duration_minutes": sum(c.get("duration_seconds", 0) for c in being_calls) / 60,
                "by_type": {
                    "ecosystem_merging": len([c for c in being_calls if c.get("lever") == "1"]),
                    "sales": len([c for c in being_calls if c.get("lever") == "3"]),
                    "actualizing": len([c for c in being_calls if "actualiz" in c.get("transcript", "").lower()]),
                    "other": len([c for c in being_calls if c.get("lever") not in ["1", "3"]])
                }
            }
    
    # Colosseum & Being Evolution
    if "colosseum" in sections:
        report["colosseum_status"] = await _get_colosseum_status()
    
    # LLM Independence
    if "llm" in sections:
        report["llm_independence"] = _get_llm_independence_status()
    
    # Human input needed
    questions = _load_pending_questions()
    report["human_input_needed"] = {
        "for_sean": [q for q in questions if q.get("for") == "Sean" and not q.get("answered")],
        "for_adam": [q for q in questions if q.get("for") == "Adam" and not q.get("answered")],
        "for_others": [q for q in questions if q.get("for") not in ["Sean", "Adam"] and not q.get("answered")]
    }
    
    return report


# ============================================================================
# BEST CALLS REPORT (FOR SEAN TO GRADE)
# ============================================================================

async def generate_best_calls_report(
    company: Optional[str] = None,
    lever: Optional[str] = None,
    limit: int = 3
) -> Dict[str, Any]:
    """
    Generate report of top calls for Sean to review.
    
    Returns top 3 calls per company per lever.
    These are the 9.99 calls for training other beings.
    """
    now = datetime.now()
    
    # Get all calls from last 24 hours
    all_calls = await get_elevenlabs_calls(hours=24)
    
    # Filter and organize
    target_companies = [company] if company else COMPANIES
    target_levers = [lever] if lever else LEVER_IDS
    
    calls_for_review = {}
    total_calls = 0
    
    for comp in target_companies:
        calls_for_review[comp] = {}
        company_calls = [c for c in all_calls if c.get("company") == comp]
        
        for lev in target_levers:
            lever_calls = [c for c in company_calls if c.get("lever") == lev]
            
            # Sort by score (highest first)
            lever_calls.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # Take top N
            top_calls = lever_calls[:limit]
            
            if top_calls:
                calls_for_review[comp][f"lever_{lev}"] = [
                    {
                        "call_id": c.get("call_id"),
                        "score": c.get("score"),
                        "being": c.get("being"),
                        "duration_seconds": c.get("duration_seconds"),
                        "summary": _summarize_transcript(c.get("transcript", "")),
                        "transcript_preview": c.get("transcript", "")[:500]
                    }
                    for c in top_calls
                ]
                total_calls += len(top_calls)
    
    return {
        "generated_at": now.isoformat(),
        "calls_for_review": calls_for_review,
        "total_calls_to_grade": total_calls
    }


# ============================================================================
# LEVER DRILLDOWN
# ============================================================================

async def get_lever_drilldown(lever_id: str, company: Optional[str] = None) -> Dict[str, Any]:
    """Get deep drill-down data for a specific lever."""
    data = await get_lever_data(lever_id, company)
    
    # Add additional context
    lever_names = {
        "0.25": "Sourcing Data",
        "0.5": "Shared Experiences (Process Mastery)",
        "1": "Ecosystem Mergers",
        "2": "Speaking Engagements & Marketing",
        "3": "Sales",
        "4": "Referrals",
        "5": "Direct Outreach",
        "6": "Advertising",
        "7": "Content/PR"
    }
    
    return {
        "lever_id": lever_id,
        "lever_name": lever_names.get(lever_id, "Unknown"),
        "company": company or "All",
        "generated_at": datetime.now().isoformat(),
        "headlines": data.get("headlines", {}),
        "drilldown": data.get("drilldown", {}),
        "data_points_available": _count_data_points(data.get("drilldown", {}))
    }


async def get_being_activity(being_name: str, hours: int = 2) -> Dict[str, Any]:
    """Get detailed activity for a specific being."""
    return await fetch_being_activity(being_name, hours)


# ============================================================================
# HELPERS
# ============================================================================

def _load_pending_questions() -> List[Dict]:
    """Load pending questions from file."""
    questions_file = "~/.openclaw/workspace/memory/pending-questions.json"
    if os.path.exists(questions_file):
        with open(questions_file, "r") as f:
            return json.load(f)
    return []


async def _get_colosseum_status() -> Dict[str, Any]:
    """Get Colosseum & Being evolution status."""
    # TODO: Connect to actual Colosseum monitoring
    return {
        "judge_architecture": {
            "structure_improvements": "Tracking judge accuracy metrics",
            "self_improvements": "Weekly judge retraining scheduled"
        },
        "being_performance": {
            "total_positions": 13,
            "performing_great": [],
            "needs_optimization": []
        },
        "expansion": {
            "should_create_more_sais": False,
            "expansion_recommendations": []
        }
    }


def _get_llm_independence_status() -> Dict[str, Any]:
    """Get LLM independence progress."""
    # TODO: Connect to actual LLM development tracking
    return {
        "current_status": "Planning phase",
        "progress_update": "Researching fine-tuning approaches",
        "next_steps": [
            "Evaluate open-source models",
            "Design training pipeline",
            "Identify data requirements"
        ]
    }


def _summarize_transcript(transcript: str, max_length: int = 100) -> str:
    """Generate a brief summary of a call transcript."""
    if not transcript:
        return "No transcript available"
    
    # Simple extraction of key points
    lines = transcript.strip().split("\n")
    if len(lines) <= 2:
        return transcript[:max_length]
    
    # Take first and last meaningful exchanges
    first = lines[0][:50] if lines else ""
    last = lines[-1][:50] if len(lines) > 1 else ""
    
    return f"{first}... {last}"


def _count_data_points(drilldown: Dict) -> int:
    """Count total data points in drilldown data."""
    count = 0
    for key, value in drilldown.items():
        if isinstance(value, dict):
            count += len(value)
        elif isinstance(value, list):
            count += len(value)
        else:
            count += 1
    return count
