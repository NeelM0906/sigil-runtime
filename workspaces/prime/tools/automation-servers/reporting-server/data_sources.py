"""
Data Sources for Reporting Server
==================================
Connects to ElevenLabs, Pinecone, and other data sources.
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
env_path = "~/.openclaw/.env"
if os.path.exists(env_path):
    load_dotenv(env_path)

# Also load from workspace-forge for Pinecone
forge_env = "~/.openclaw/workspace-forge/.env"
if os.path.exists(forge_env):
    load_dotenv(forge_env)

# ============================================================================
# CONSTANTS
# ============================================================================

COMPANIES = ["ACT-I", "Unblinded", "Callagy Recovery"]

LEVERS = [
    "0.25 - Sourcing Data",
    "0.5 - Shared Experiences",
    "1 - Ecosystem Mergers",
    "2 - Speaking & Marketing",
    "3 - Sales",
    "4 - Referrals",
    "5 - Direct Outreach",
    "6 - Advertising",
    "7 - Content/PR"
]

LEVER_IDS = ["0.25", "0.5", "1", "2", "3", "4", "5", "6", "7"]

# Company to Pinecone namespace mapping
COMPANY_NAMESPACES = {
    "ACT-I": "acti",
    "Unblinded": "unblinded",
    "Callagy Recovery": "callagy"
}

# ACT-I Being agents
BEINGS = {
    "Milo": "agent_id_milo",  # Aiko's being
    "Athena": "agent_id_athena",  # Ecosystem merging, sales, actualizing
    "Mira": "agent_id_mira",
    "Callie": "agent_id_callie"
}

# ============================================================================
# ELEVENLABS DATA
# ============================================================================

async def get_elevenlabs_calls(
    hours: int = 2,
    agent_id: Optional[str] = None,
    company: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch recent calls from ElevenLabs API.
    
    Returns list of calls with:
    - call_id
    - agent_name
    - duration
    - transcript
    - score (if available)
    - company (inferred from agent)
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        return _mock_elevenlabs_calls(hours, company)
    
    calls = []
    cutoff = datetime.now() - timedelta(hours=hours)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get conversations from ElevenLabs
            response = await client.get(
                "https://api.elevenlabs.io/v1/convai/conversations",
                headers={"xi-api-key": api_key},
                params={"page_size": 50}
            )
            
            if response.status_code == 200:
                data = response.json()
                conversations = data.get("conversations", [])
                
                # Process up to 10 recent conversations to avoid timeout
                for conv in conversations[:10]:
                    # Parse timestamp
                    created = conv.get("start_time_unix_secs", 0)
                    if created:
                        conv_time = datetime.fromtimestamp(created)
                        if conv_time >= cutoff:
                            calls.append({
                                "call_id": conv.get("conversation_id"),
                                "agent_id": conv.get("agent_id", ""),
                                "being": _agent_to_being(conv.get("agent_id", "")),
                                "company": _agent_to_company(conv.get("agent_id", "")),
                                "duration_seconds": conv.get("call_duration_secs", 0),
                                "start_time": conv_time.isoformat(),
                                "transcript": "",  # Skip full transcript fetch for speed
                                "score": 0.5,
                                "status": conv.get("status", "unknown"),
                                "lever": "3"  # Default to sales
                            })
            else:
                return _mock_elevenlabs_calls(hours, company)
    except Exception as e:
        print(f"ElevenLabs API error: {e}")
        return _mock_elevenlabs_calls(hours, company)
    
    # If no calls found, return mock data
    if not calls:
        return _mock_elevenlabs_calls(hours, company)
    
    # Filter by company if specified
    if company:
        calls = [c for c in calls if c.get("company") == company]
    
    return calls


def _agent_to_being(agent_id: str) -> str:
    """Map agent ID to being name."""
    for name, aid in BEINGS.items():
        if agent_id == aid:
            return name
    return "Athena"  # Default


def _agent_to_company(agent_id: str) -> str:
    """Map agent ID to company."""
    # For now, return ACT-I as default
    return "ACT-I"


def _parse_elevenlabs_call(conv: Dict) -> Dict[str, Any]:
    """Parse ElevenLabs conversation into standardized format."""
    agent_id = conv.get("agent_id", "")
    
    # Determine company and being from agent
    company = "ACT-I"  # Default
    being = "Unknown"
    for name, aid in BEINGS.items():
        if agent_id == aid:
            being = name
            break
    
    # Extract transcript
    transcript = ""
    messages = conv.get("transcript", [])
    if isinstance(messages, list):
        for msg in messages:
            role = msg.get("role", "")
            text = msg.get("message", "")
            transcript += f"{role}: {text}\n"
    
    # Calculate score if analysis available
    analysis = conv.get("analysis", {})
    score = analysis.get("call_successful", None)
    
    return {
        "call_id": conv.get("conversation_id"),
        "agent_id": agent_id,
        "being": being,
        "company": company,
        "duration_seconds": conv.get("call_duration_secs", 0),
        "start_time": datetime.fromtimestamp(
            conv.get("start_time_unix_secs", 0)
        ).isoformat(),
        "transcript": transcript,
        "score": 1.0 if score else 0.5 if score is None else 0.0,
        "analysis": analysis,
        "status": conv.get("status", "unknown")
    }


def _mock_elevenlabs_calls(hours: int, company: Optional[str] = None) -> List[Dict]:
    """Return mock data when API not available."""
    mock_calls = [
        {
            "call_id": "mock_001",
            "being": "Athena",
            "company": "ACT-I",
            "duration_seconds": 320,
            "start_time": datetime.now().isoformat(),
            "transcript": "Mock call transcript for testing...",
            "score": 0.92,
            "lever": "1"
        },
        {
            "call_id": "mock_002",
            "being": "Milo",
            "company": "Unblinded",
            "duration_seconds": 180,
            "start_time": datetime.now().isoformat(),
            "transcript": "Mock Milo call...",
            "score": 0.88,
            "lever": "3"
        },
        {
            "call_id": "mock_003",
            "being": "Athena",
            "company": "Callagy Recovery",
            "duration_seconds": 420,
            "start_time": datetime.now().isoformat(),
            "transcript": "Mock recovery call...",
            "score": 0.95,
            "lever": "3"
        }
    ]
    
    if company:
        return [c for c in mock_calls if c["company"] == company]
    return mock_calls


# ============================================================================
# PINECONE DATA
# ============================================================================

async def get_pinecone_data(
    index_name: str = "athenacontextualmemory",
    namespace: Optional[str] = None,
    query: str = "",
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Query Pinecone for relevant data.
    
    Available indexes:
    - athenacontextualmemory (11K vectors)
    - uicontextualmemory (48K vectors, namespaced by user email)
    - ublib2 (41K vectors)
    - ultimatestratabrain (39K vectors - use PINECONE_API_KEY_STRATA)
    """
    try:
        from pinecone import Pinecone
        from openai import OpenAI
        
        # Determine which API key to use
        if index_name in ["ultimatestratabrain", "suritrial", "2025selfmastery"]:
            api_key = os.environ.get("PINECONE_API_KEY_STRATA")
        else:
            api_key = os.environ.get("PINECONE_API_KEY")
        
        if not api_key:
            return []
        
        pc = Pinecone(api_key=api_key)
        openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Get embedding for query
        embedding = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        ).data[0].embedding
        
        # Query Pinecone
        index = pc.Index(index_name)
        results = index.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=namespace or ""
        )
        
        return [
            {
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata,
                "text": match.metadata.get("text", "")[:500]
            }
            for match in results.matches
        ]
    except Exception as e:
        print(f"Pinecone error: {e}")
        return []


async def query_knowledge_base(query: str, top_k: int = 5) -> List[Dict]:
    """Query the main knowledge base for relevant info."""
    results = []
    
    # Query multiple indexes
    indexes = ["athenacontextualmemory", "ublib2"]
    for index in indexes:
        data = await get_pinecone_data(
            index_name=index,
            query=query,
            top_k=top_k
        )
        results.extend(data)
    
    # Sort by score and return top results
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:top_k]


# ============================================================================
# LEVER-SPECIFIC DATA FETCHERS
# ============================================================================

async def get_lever_data(lever_id: str, company: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch data for a specific lever.
    
    Returns both headline metrics and drill-down data.
    """
    lever_fetchers = {
        "0.25": _fetch_sourcing_data,
        "0.5": _fetch_shared_experiences,
        "1": _fetch_ecosystem_mergers,
        "2": _fetch_marketing_data,
        "3": _fetch_sales_data,
        "4": _fetch_referral_data,
        "5": _fetch_outreach_data,
        "6": _fetch_advertising_data,
        "7": _fetch_content_data
    }
    
    fetcher = lever_fetchers.get(lever_id)
    if fetcher:
        return await fetcher(company)
    return {}


async def _fetch_sourcing_data(company: Optional[str]) -> Dict:
    """Lever 0.25 - Sourcing Data"""
    # TODO: Connect to actual data sources (CRM, spreadsheets, etc.)
    return {
        "headlines": {
            "total_new_contacts": 0,
            "new_lawyers": 0,
            "new_accountants": 0,
            "new_financial_providers": 0,
            "new_other_professionals": 0
        },
        "drilldown": {
            "by_city_state": {},
            "by_source_channel": {},
            "ideal_avatar_match_pct": 0,
            "contact_quality_scores": {}
        }
    }


async def _fetch_shared_experiences(company: Optional[str]) -> Dict:
    """Lever 0.5 - Shared Experiences (Process Mastery)"""
    return {
        "headlines": {
            "heart_of_influence_shows": 0,
            "show_runners": [],
            "people_on_shows": 0,
            "conversations_with_beings": 0,
            "acceleration_sessions_booked": 0,
            "ecosystem_merging_from_shows": 0
        },
        "drilldown": {
            "individual_show_metrics": [],
            "conversion_rates": {},
            "being_performance_per_show": {}
        }
    }


async def _fetch_ecosystem_mergers(company: Optional[str]) -> Dict:
    """Lever 1 - Ecosystem Mergers"""
    return {
        "headlines": {
            "total_active_mergers": 0,
            "new_merger_conversations_today": 0,
            "stages": {
                "stage_1": 0,
                "stage_2": 0,
                "stage_3": 0,
                "stage_4": 0,
                "stage_5": 0,
                "stage_6": 0
            }
        },
        "drilldown": {
            "partner_names_status": [],
            "conversation_transcripts": [],
            "projected_value": 0
        }
    }


async def _fetch_marketing_data(company: Optional[str]) -> Dict:
    """Lever 2 - Speaking Engagements & Marketing"""
    return {
        "headlines": {
            "speaking_engagements_today": 0,
            "webinar_registrations": 0,
            "opt_ins_from_events": 0,
            "digital_marketing_opt_ins": 0,
            "social_media_conversions": 0
        },
        "drilldown": {
            "by_platform": {},
            "by_campaign": {},
            "conversion_funnels": {},
            "cost_per_acquisition": 0
        }
    }


async def _fetch_sales_data(company: Optional[str]) -> Dict:
    """Lever 3 - Sales"""
    calls = await get_elevenlabs_calls(hours=2, company=company)
    sales_calls = [c for c in calls if c.get("lever") == "3"]
    
    return {
        "headlines": {
            "sales_meetings_held": len(sales_calls),
            "revenue_closed": 0,
            "disposable_income_generated": 0,
            "pipeline_value": 0
        },
        "drilldown": {
            "by_rep_being": {},
            "by_product_service": {},
            "close_rates": {},
            "average_deal_size": 0
        }
    }


async def _fetch_referral_data(company: Optional[str]) -> Dict:
    """Lever 4 - Referrals"""
    return {
        "headlines": {
            "referrals_received": 0,
            "referral_conversations": 0,
            "referral_conversions": 0
        },
        "drilldown": {}
    }


async def _fetch_outreach_data(company: Optional[str]) -> Dict:
    """Lever 5 - Direct Outreach"""
    calls = await get_elevenlabs_calls(hours=2, company=company)
    outreach_calls = [c for c in calls if c.get("lever") == "5"]
    
    return {
        "headlines": {
            "outbound_calls_made": len(outreach_calls),
            "conversations_held": len([c for c in outreach_calls if c.get("duration_seconds", 0) > 60]),
            "appointments_set": 0
        },
        "drilldown": {}
    }


async def _fetch_advertising_data(company: Optional[str]) -> Dict:
    """Lever 6 - Advertising"""
    return {
        "headlines": {
            "ad_spend": 0,
            "leads_generated": 0,
            "cost_per_lead": 0
        },
        "drilldown": {}
    }


async def _fetch_content_data(company: Optional[str]) -> Dict:
    """Lever 7 - Content/PR"""
    return {
        "headlines": {
            "content_pieces_published": 0,
            "reach_impressions": 0,
            "engagement_metrics": {}
        },
        "drilldown": {}
    }


# ============================================================================
# BEING ACTIVITY
# ============================================================================

async def get_being_activity(being_name: str, hours: int = 2) -> Dict[str, Any]:
    """Get activity summary for a specific ACT-I being."""
    calls = await get_elevenlabs_calls(hours=hours)
    being_calls = [c for c in calls if c.get("being") == being_name]
    
    return {
        "being": being_name,
        "period_hours": hours,
        "total_calls": len(being_calls),
        "total_duration_minutes": sum(c.get("duration_seconds", 0) for c in being_calls) / 60,
        "by_company": {},
        "by_lever": {},
        "calls": being_calls
    }


async def get_all_beings_summary(hours: int = 2) -> Dict[str, Any]:
    """Get summary of all ACT-I being activity."""
    calls = await get_elevenlabs_calls(hours=hours)
    
    summary = {
        "total_calls": len(calls),
        "by_being": {}
    }
    
    for being in BEINGS.keys():
        being_calls = [c for c in calls if c.get("being") == being]
        summary["by_being"][being] = {
            "calls": len(being_calls),
            "duration_minutes": sum(c.get("duration_seconds", 0) for c in being_calls) / 60
        }
    
    return summary
