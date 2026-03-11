"""
Reporting Aggregator Proxy Server
=================================
Compiles bi-hourly reports from all data sources for Sean.
Tracks 7 levers across 3 companies, surfaces best calls for grading.

Port: 3344
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Data source imports
from data_sources import (
    get_elevenlabs_calls,
    get_pinecone_data,
    query_knowledge_base,
    COMPANIES,
    LEVERS
)
from report_generator import (
    generate_headline_report,
    generate_detailed_report,
    generate_best_calls_report
)

app = FastAPI(
    title="Reporting Aggregator Proxy",
    description="Bi-hourly reporting for Sean - 7 Levers across 3 Companies",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELS
# ============================================================================

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    companies: List[str]
    levers: List[str]

class HeadlineReport(BaseModel):
    generated_at: str
    period: str
    companies: Dict[str, Any]
    being_activity: Dict[str, Any]
    human_input_needed: List[str]

class DetailedReport(BaseModel):
    generated_at: str
    date: str
    companies: Dict[str, Any]
    being_activity: Dict[str, Any]
    colosseum_status: Dict[str, Any]
    llm_independence: Dict[str, Any]
    human_input_needed: Dict[str, Any]

class BestCallsReport(BaseModel):
    generated_at: str
    calls_for_review: Dict[str, Dict[str, List[Dict[str, Any]]]]
    total_calls_to_grade: int

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        companies=COMPANIES,
        levers=LEVERS
    )


@app.get("/report/headline", response_model=HeadlineReport)
async def get_headline_report(
    company: Optional[str] = Query(None, description="Filter by company"),
    lever: Optional[str] = Query(None, description="Filter by lever (0.25-7)")
):
    """
    Quick bi-hourly summary.
    
    Shows headlines for all 7 levers across all 3 companies.
    Use query params to filter by specific company or lever.
    """
    try:
        report = await generate_headline_report(company=company, lever=lever)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/report/detailed")
async def get_detailed_report(
    date: Optional[str] = Query(None, description="Date (YYYY-MM-DD), defaults to today"),
    company: Optional[str] = Query(None, description="Filter by company"),
    section: Optional[str] = Query(None, description="Section: levers, beings, colosseum, llm")
):
    """
    Full daily report with deep drill-downs.
    
    Includes:
    - Full 7 Levers breakdown for all companies
    - All phone calls made by beings
    - Programs bought that day
    - Files recovered (Callagy Recovery)
    - Ecosystem mergers progress
    - Colosseum & Being evolution status
    - LLM Independence progress
    """
    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        report = await generate_detailed_report(
            date=target_date,
            company=company,
            section=section
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/report/best-calls")
async def get_best_calls(
    company: Optional[str] = Query(None, description="Filter by company"),
    lever: Optional[str] = Query(None, description="Filter by lever"),
    limit: int = Query(3, description="Calls per company/lever (default 3)")
):
    """
    Top calls for Sean to review and grade.
    
    Returns top 3 calls per company per lever for:
    - ACT-I
    - Unblinded
    - Callagy Recovery
    
    These are the 9.99 calls for training other beings.
    This is how we get Sean's 10 calls to grade (#39).
    """
    try:
        report = await generate_best_calls_report(
            company=company,
            lever=lever,
            limit=limit
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/report/lever/{lever_id}")
async def get_lever_drilldown(
    lever_id: str,
    company: Optional[str] = Query(None, description="Filter by company")
):
    """
    Deep drill-down into a specific lever.
    
    Lever IDs:
    - 0.25: Sourcing Data
    - 0.5: Shared Experiences (Process Mastery)
    - 1: Ecosystem Mergers
    - 2: Speaking Engagements & Marketing
    - 3: Sales
    - 4: Referrals
    - 5: Direct Outreach
    - 6: Advertising
    - 7: Content/PR
    """
    from report_generator import get_lever_drilldown
    try:
        data = await get_lever_drilldown(lever_id, company)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/report/being/{being_name}")
async def get_being_activity(
    being_name: str,
    hours: int = Query(2, description="Hours to look back")
):
    """
    Get activity for a specific ACT-I being.
    
    Beings: Milo, Athena, Mira, Callie, etc.
    """
    from report_generator import get_being_activity
    try:
        data = await get_being_activity(being_name, hours)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report/question")
async def submit_question(
    question: str,
    for_person: str = Query("Sean", description="Who the question is for")
):
    """
    Submit a question that needs human input.
    
    Questions are surfaced in the bi-hourly report.
    """
    # Store in memory/questions file
    questions_file = "~/.openclaw/workspace/memory/pending-questions.json"
    try:
        if os.path.exists(questions_file):
            with open(questions_file, "r") as f:
                questions = json.load(f)
        else:
            questions = []
        
        questions.append({
            "question": question,
            "for": for_person,
            "submitted_at": datetime.now().isoformat(),
            "answered": False
        })
        
        with open(questions_file, "w") as f:
            json.dump(questions, f, indent=2)
        
        return {"status": "submitted", "question": question, "for": for_person}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3344)
