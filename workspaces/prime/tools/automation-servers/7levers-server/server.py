#!/usr/bin/env python3
"""
7 Levers Metrics Proxy Server
Aggregates data from Bland.ai, ElevenLabs, and Zoom for ACT-I, Unblinded, Callagy Recovery
Provides REST endpoints for each lever (0.25, 0.5, 1-7) per company
Caches data for instant bi-hourly report generation

Port: 3340
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache
from collections import defaultdict

import httpx
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ============================================
# Configuration & Environment
# ============================================

def load_env():
    """Load environment variables from ~/.openclaw/.env"""
    env_path = Path.home() / '.openclaw' / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

load_env()

# API Keys
BLAND_API_KEY = os.environ.get('BLAND_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
ZOOM_ACCOUNT_ID = os.environ.get('ZOOM_ACCOUNT_ID')
ZOOM_CLIENT_ID = os.environ.get('ZOOM_CLIENT_ID')
ZOOM_CLIENT_SECRET = os.environ.get('ZOOM_CLIENT_SECRET')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_API_KEY_STRATA = os.environ.get('PINECONE_API_KEY_STRATA')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

PORT = int(os.environ.get('LEVERS_PORT', 3340))

# ============================================
# Company Configuration
# ============================================

# Mapping of companies to their Bland.ai pathway IDs
COMPANY_PATHWAYS = {
    'acti': {
        'name': 'ACT-I',
        'pathways': [],  # Will be auto-discovered
        'elevenlabs_agents': ['agent_8001kj7288ywf7vtdxn84amesb77'],  # Sisters shared agent
    },
    'unblinded': {
        'name': 'Unblinded',
        'pathways': [],  # Will be populated from Bland.ai
        'elevenlabs_agents': [],
    },
    'callagy_recovery': {
        'name': 'Callagy Recovery', 
        'pathways': [],
        'elevenlabs_agents': [],
    },
}

# 7 Levers + Sub-Levers Definition
LEVERS = {
    '0.25': {'name': 'Awareness', 'desc': 'Market awareness, brand recognition'},
    '0.5': {'name': 'Interest', 'desc': 'Lead generation, opt-ins'},
    '1': {'name': 'Traffic', 'desc': 'Inbound traffic, visitors'},
    '2': {'name': 'Opt-in Rate', 'desc': 'Conversion from visitor to lead'},
    '3': {'name': 'Buyer Rate', 'desc': 'Conversion from lead to buyer'},
    '4': {'name': 'Units per Buyer', 'desc': 'Average items purchased'},
    '5': {'name': 'Revenue per Unit', 'desc': 'Average revenue per sale'},
    '6': {'name': 'Profit Margin', 'desc': 'Profit percentage'},
    '7': {'name': 'Frequency', 'desc': 'Purchase frequency / retention'},
}

# ============================================
# Logging
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('7levers')

# ============================================
# Cache
# ============================================

class MetricsCache:
    """In-memory cache with TTL for metrics data"""
    
    def __init__(self, default_ttl: int = 7200):  # 2 hours default
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        if time.time() - self._timestamps.get(key, 0) > self._default_ttl:
            del self._cache[key]
            del self._timestamps[key]
            return None
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def clear(self):
        self._cache.clear()
        self._timestamps.clear()
    
    def stats(self) -> dict:
        return {
            'entries': len(self._cache),
            'keys': list(self._cache.keys()),
        }

cache = MetricsCache()

# ============================================
# API Clients
# ============================================

class BlandClient:
    """Bland.ai API client for call data"""
    
    BASE_URL = 'https://api.bland.ai/v1'
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_calls(self, limit: int = 1000, start_date: Optional[str] = None) -> List[dict]:
        """Fetch calls from Bland.ai"""
        # Bland.ai v1 API uses 'limit' but not 'start_date' in the same way
        # Fetch more calls and filter client-side if needed
        params = {'limit': min(limit, 1000)}  # API max is 1000 per request
        
        all_calls = []
        
        # Paginate if we need more than 1000
        while len(all_calls) < limit:
            resp = await self.client.get(
                f'{self.BASE_URL}/calls',
                headers={'authorization': self.api_key},
                params=params
            )
            resp.raise_for_status()
            data = resp.json()
            calls = data.get('calls', [])
            
            if not calls:
                break
            
            all_calls.extend(calls)
            
            # If we got fewer than requested, we've reached the end
            if len(calls) < params['limit']:
                break
            
            # For pagination, we'd need to track offset/cursor
            # Bland.ai uses different pagination - break for now
            break
        
        # Filter by date client-side if needed
        if start_date and all_calls:
            # Parse start_date as UTC-aware datetime
            start_dt = datetime.fromisoformat(start_date)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            
            filtered = []
            for call in all_calls:
                created = call.get('created_at', '')
                if created:
                    try:
                        # Normalize the timestamp
                        created_clean = created.replace('Z', '+00:00')
                        call_dt = datetime.fromisoformat(created_clean)
                        if call_dt.tzinfo is None:
                            call_dt = call_dt.replace(tzinfo=timezone.utc)
                        if call_dt >= start_dt:
                            filtered.append(call)
                    except (ValueError, TypeError):
                        filtered.append(call)  # Include if we can't parse date
                else:
                    filtered.append(call)
            return filtered
        
        return all_calls
    
    async def get_call_details(self, call_id: str) -> dict:
        """Get detailed info for a single call"""
        resp = await self.client.get(
            f'{self.BASE_URL}/calls/{call_id}',
            headers={'authorization': self.api_key}
        )
        resp.raise_for_status()
        return resp.json()
    
    async def get_pathways(self) -> List[dict]:
        """List all pathways"""
        resp = await self.client.get(
            f'{self.BASE_URL}/convo_pathway',
            headers={'authorization': self.api_key}
        )
        resp.raise_for_status()
        return resp.json().get('pathways', [])
    
    async def get_total_calls(self) -> int:
        """Get total call count"""
        resp = await self.client.get(
            f'{self.BASE_URL}/calls',
            headers={'authorization': self.api_key},
            params={'limit': 1}
        )
        resp.raise_for_status()
        return resp.json().get('total_count', 0)


class ElevenLabsClient:
    """ElevenLabs API client for conversation data"""
    
    BASE_URL = 'https://api.elevenlabs.io/v1'
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_conversations(self, agent_id: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Fetch conversations"""
        url = f'{self.BASE_URL}/convai/conversations'
        params = {'page_size': limit}
        if agent_id:
            params['agent_id'] = agent_id
        
        resp = await self.client.get(
            url,
            headers={'xi-api-key': self.api_key},
            params=params
        )
        resp.raise_for_status()
        return resp.json().get('conversations', [])
    
    async def get_conversation_details(self, conversation_id: str) -> dict:
        """Get full conversation with transcript"""
        resp = await self.client.get(
            f'{self.BASE_URL}/convai/conversations/{conversation_id}',
            headers={'xi-api-key': self.api_key}
        )
        resp.raise_for_status()
        return resp.json()
    
    async def get_agents(self) -> List[dict]:
        """List all conversational agents"""
        resp = await self.client.get(
            f'{self.BASE_URL}/convai/agents',
            headers={'xi-api-key': self.api_key}
        )
        resp.raise_for_status()
        return resp.json().get('agents', [])


class ZoomClient:
    """Zoom API client for meeting/recording data"""
    
    def __init__(self, account_id: str, client_id: str, client_secret: str):
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.client = httpx.AsyncClient(timeout=30.0)
        self._token = None
        self._token_expires = 0
    
    async def _get_token(self) -> str:
        """Get OAuth access token"""
        if self._token and time.time() < self._token_expires:
            return self._token
        
        resp = await self.client.post(
            'https://zoom.us/oauth/token',
            params={
                'grant_type': 'account_credentials',
                'account_id': self.account_id
            },
            auth=(self.client_id, self.client_secret)
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data['access_token']
        self._token_expires = time.time() + data.get('expires_in', 3600) - 60
        return self._token
    
    async def get_recordings(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[dict]:
        """Fetch cloud recordings using the user-level endpoint"""
        token = await self._get_token()
        
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        all_recordings = []
        next_page_token = None
        
        while True:
            params = {
                'from': from_date,
                'to': to_date,
                'page_size': 100,
            }
            if next_page_token:
                params['next_page_token'] = next_page_token
            
            # Use users/me/recordings for server-to-server OAuth
            resp = await self.client.get(
                'https://api.zoom.us/v2/users/me/recordings',
                headers={'Authorization': f'Bearer {token}'},
                params=params
            )
            
            if resp.status_code == 400:
                # Try alternate endpoint if first fails
                break
            
            resp.raise_for_status()
            data = resp.json()
            
            all_recordings.extend(data.get('meetings', []))
            next_page_token = data.get('next_page_token')
            
            if not next_page_token:
                break
        
        return all_recordings


# Initialize clients
bland_client = BlandClient(BLAND_API_KEY) if BLAND_API_KEY else None
elevenlabs_client = ElevenLabsClient(ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None
zoom_client = ZoomClient(ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET) if all([ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET]) else None

# ============================================
# Metrics Calculation
# ============================================

def score_call_quality(call: dict) -> float:
    """
    Score a call from 0-10 based on quality indicators.
    9.99+ calls are exceptional - surface these as "best calls"
    """
    score = 5.0  # Base score
    
    # Duration scoring (ideal: 5-15 minutes)
    duration = call.get('call_length', 0) or 0
    if 5 <= duration <= 15:
        score += 2.0
    elif 3 <= duration < 5 or 15 < duration <= 25:
        score += 1.0
    elif duration > 25:
        score += 0.5  # Long calls can be good but may indicate issues
    elif duration < 1:
        score -= 2.0  # Very short = likely failed
    
    # Status scoring
    status = (call.get('status') or '').lower()
    queue_status = (call.get('queue_status') or '').lower()
    if status == 'completed' and queue_status == 'complete':
        score += 1.5
    elif status == 'completed':
        score += 1.0
    elif status in ['error', 'failed', 'no-answer']:
        score -= 2.0
    
    # Transcript analysis (if available)
    transcript = call.get('concatenated_transcript', '') or ''
    word_count = len(transcript.split())
    
    if word_count > 500:
        score += 1.0  # Rich conversation
    elif word_count > 200:
        score += 0.5
    
    # Sentiment indicators in transcript
    positive_indicators = ['thank you', 'appreciate', 'helpful', 'great', 'amazing', 'perfect']
    negative_indicators = ['confused', 'frustrated', 'wrong', 'error', 'problem', 'issue']
    
    transcript_lower = transcript.lower()
    for indicator in positive_indicators:
        if indicator in transcript_lower:
            score += 0.2
    for indicator in negative_indicators:
        if indicator in transcript_lower:
            score -= 0.2
    
    # Clamp to 0-10 range
    return max(0.0, min(10.0, score))


def calculate_lever_metrics(calls: List[dict], lever: str) -> dict:
    """Calculate metrics for a specific lever based on call data"""
    
    if not calls:
        return {
            'lever': lever,
            'name': LEVERS.get(lever, {}).get('name', f'Lever {lever}'),
            'value': 0,
            'trend': 'neutral',
            'data_points': 0,
        }
    
    # Different calculations per lever
    if lever in ['0.25', '0.5']:
        # Awareness/Interest - count unique interactions
        unique_numbers = set(c.get('to', '') for c in calls if c.get('to'))
        value = len(unique_numbers)
        
    elif lever == '1':
        # Traffic - total calls
        value = len(calls)
        
    elif lever == '2':
        # Opt-in Rate - completed calls / total calls
        completed = sum(1 for c in calls if c.get('status') == 'completed')
        value = (completed / len(calls) * 100) if calls else 0
        
    elif lever == '3':
        # Buyer Rate - long calls (>3 min) / total (proxy for conversions)
        long_calls = sum(1 for c in calls if (c.get('call_length', 0) or 0) >= 3)
        value = (long_calls / len(calls) * 100) if calls else 0
        
    elif lever == '4':
        # Units per Buyer - average calls per unique number
        calls_by_number = defaultdict(int)
        for c in calls:
            num = c.get('to', '')
            if num:
                calls_by_number[num] += 1
        value = sum(calls_by_number.values()) / len(calls_by_number) if calls_by_number else 0
        
    elif lever == '5':
        # Revenue per Unit - average call duration (proxy)
        durations = [c.get('call_length', 0) or 0 for c in calls]
        value = sum(durations) / len(durations) if durations else 0
        
    elif lever == '6':
        # Profit Margin - efficiency score (completed / total adjusted)
        completed = sum(1 for c in calls if c.get('status') == 'completed')
        errored = sum(1 for c in calls if c.get('status') in ['error', 'failed'])
        value = ((completed - errored) / len(calls) * 100) if calls else 0
        
    elif lever == '7':
        # Frequency - returning callers ratio
        calls_by_number = defaultdict(int)
        for c in calls:
            num = c.get('to', '')
            if num:
                calls_by_number[num] += 1
        returning = sum(1 for count in calls_by_number.values() if count > 1)
        value = (returning / len(calls_by_number) * 100) if calls_by_number else 0
    else:
        value = 0
    
    return {
        'lever': lever,
        'name': LEVERS.get(lever, {}).get('name', f'Lever {lever}'),
        'description': LEVERS.get(lever, {}).get('desc', ''),
        'value': round(value, 2),
        'trend': 'neutral',  # TODO: Calculate from historical data
        'data_points': len(calls),
    }


async def get_drill_down_data(calls: List[dict], lever: str, limit: int = 100) -> List[dict]:
    """Get detailed data points for a lever drill-down"""
    
    data_points = []
    
    for call in calls[:limit]:
        call_id = call.get('c_id') or call.get('call_id', 'unknown')
        score = score_call_quality(call)
        
        data_points.append({
            'call_id': call_id,
            'created_at': call.get('created_at', ''),
            'to': call.get('to', ''),
            'from': call.get('from', ''),
            'duration_min': round(call.get('call_length', 0) or 0, 2),
            'status': call.get('status', ''),
            'queue_status': call.get('queue_status', ''),
            'pathway_id': call.get('pathway_id', ''),
            'quality_score': round(score, 2),
            'transcript_preview': (call.get('concatenated_transcript', '') or '')[:200],
        })
    
    return sorted(data_points, key=lambda x: x['quality_score'], reverse=True)


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title='7 Levers Metrics Proxy',
    description='Aggregates data from Bland.ai, ElevenLabs, Zoom for lever-based business metrics',
    version='1.0.0',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ============================================
# Models
# ============================================

class LeverMetric(BaseModel):
    lever: str
    name: str
    description: Optional[str] = None
    value: float
    trend: str
    data_points: int

class CompanyMetrics(BaseModel):
    company: str
    company_name: str
    timestamp: str
    levers: List[LeverMetric]
    total_calls: int
    period_days: int

class BestCall(BaseModel):
    call_id: str
    company: str
    quality_score: float
    duration_min: float
    created_at: str
    to: str
    status: str
    transcript_preview: str

# ============================================
# Endpoints
# ============================================

@app.get('/health')
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'ok',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'services': {
            'bland': bland_client is not None,
            'elevenlabs': elevenlabs_client is not None,
            'zoom': zoom_client is not None,
        },
        'cache': cache.stats(),
    }


@app.get('/companies')
async def list_companies():
    """List all tracked companies"""
    return {
        'companies': [
            {'id': k, 'name': v['name']} 
            for k, v in COMPANY_PATHWAYS.items()
        ]
    }


@app.get('/levers')
async def list_levers():
    """List all lever definitions"""
    return {'levers': LEVERS}


@app.get('/metrics/{company}')
async def get_company_metrics(
    company: str,
    days: int = Query(default=30, ge=1, le=365),
    refresh: bool = Query(default=False),
) -> CompanyMetrics:
    """Get all lever metrics for a company"""
    
    if company not in COMPANY_PATHWAYS:
        raise HTTPException(status_code=404, detail=f'Company {company} not found')
    
    cache_key = f'metrics:{company}:{days}'
    
    if not refresh:
        cached = cache.get(cache_key)
        if cached:
            return CompanyMetrics(**cached)
    
    # Fetch data from APIs
    calls = []
    if bland_client:
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            all_calls = await bland_client.get_calls(limit=5000, start_date=start_date)
            
            # Filter by company pathways (if configured)
            pathways = COMPANY_PATHWAYS[company].get('pathways', [])
            if pathways:
                calls = [c for c in all_calls if c.get('pathway_id') in pathways]
            else:
                # No pathway filter - use all calls for now
                calls = all_calls
        except Exception as e:
            logger.error(f'Bland.ai fetch error: {e}')
    
    # Calculate metrics for each lever
    levers = []
    for lever_id in LEVERS.keys():
        metric = calculate_lever_metrics(calls, lever_id)
        levers.append(metric)
    
    result = {
        'company': company,
        'company_name': COMPANY_PATHWAYS[company]['name'],
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'levers': levers,
        'total_calls': len(calls),
        'period_days': days,
    }
    
    cache.set(cache_key, result)
    return CompanyMetrics(**result)


@app.get('/metrics/{company}/lever/{lever_id}')
async def get_lever_metric(
    company: str,
    lever_id: str,
    days: int = Query(default=30, ge=1, le=365),
) -> LeverMetric:
    """Get specific lever metric for a company"""
    
    if company not in COMPANY_PATHWAYS:
        raise HTTPException(status_code=404, detail=f'Company {company} not found')
    
    if lever_id not in LEVERS:
        raise HTTPException(status_code=404, detail=f'Lever {lever_id} not found')
    
    # Get full metrics and extract the specific lever
    metrics = await get_company_metrics(company, days=days)
    
    for lever in metrics.levers:
        if lever.lever == lever_id:
            return lever
    
    raise HTTPException(status_code=404, detail=f'Lever {lever_id} not found')


@app.get('/drill-down/{company}/lever/{lever_id}')
async def get_lever_drill_down(
    company: str,
    lever_id: str,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=100, ge=10, le=500),
):
    """Get detailed drill-down data for a lever (50-100 data points)"""
    
    if company not in COMPANY_PATHWAYS:
        raise HTTPException(status_code=404, detail=f'Company {company} not found')
    
    if lever_id not in LEVERS:
        raise HTTPException(status_code=404, detail=f'Lever {lever_id} not found')
    
    # Fetch calls
    calls = []
    if bland_client:
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            calls = await bland_client.get_calls(limit=limit * 2, start_date=start_date)
        except Exception as e:
            logger.error(f'Bland.ai fetch error: {e}')
    
    data_points = await get_drill_down_data(calls, lever_id, limit)
    
    return {
        'company': company,
        'company_name': COMPANY_PATHWAYS[company]['name'],
        'lever': lever_id,
        'lever_name': LEVERS[lever_id]['name'],
        'data_points': data_points,
        'count': len(data_points),
    }


@app.get('/best-calls')
async def get_best_calls(
    company: Optional[str] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    min_score: float = Query(default=9.0, ge=0, le=10),
    limit: int = Query(default=20, ge=1, le=100),
) -> List[BestCall]:
    """
    Surface the best calls (9.99 quality score target).
    These are exceptional calls worth studying and replicating.
    """
    
    cache_key = f'best_calls:{company or "all"}:{days}:{min_score}'
    cached = cache.get(cache_key)
    if cached:
        return [BestCall(**c) for c in cached]
    
    # Fetch calls
    calls = []
    if bland_client:
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            calls = await bland_client.get_calls(limit=1000, start_date=start_date)
        except Exception as e:
            logger.error(f'Bland.ai fetch error: {e}')
    
    # Score all calls
    scored_calls = []
    for call in calls:
        score = score_call_quality(call)
        if score >= min_score:
            scored_calls.append({
                'call_id': call.get('c_id') or call.get('call_id', 'unknown'),
                'company': company or 'all',
                'quality_score': round(score, 2),
                'duration_min': round(call.get('call_length', 0) or 0, 2),
                'created_at': call.get('created_at', ''),
                'to': call.get('to', ''),
                'status': call.get('status', ''),
                'transcript_preview': (call.get('concatenated_transcript', '') or '')[:300],
            })
    
    # Sort by score descending
    scored_calls.sort(key=lambda x: x['quality_score'], reverse=True)
    best = scored_calls[:limit]
    
    cache.set(cache_key, best)
    return [BestCall(**c) for c in best]


@app.get('/call/{call_id}')
async def get_call_details(call_id: str):
    """Get full details for a specific call"""
    
    if not bland_client:
        raise HTTPException(status_code=503, detail='Bland.ai client not configured')
    
    try:
        call = await bland_client.get_call_details(call_id)
        call['quality_score'] = score_call_quality(call)
        return call
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get('/stats')
async def get_aggregate_stats():
    """Get aggregate statistics across all sources"""
    
    stats = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'bland': {},
        'elevenlabs': {},
        'zoom': {},
    }
    
    if bland_client:
        try:
            total = await bland_client.get_total_calls()
            stats['bland'] = {
                'total_calls': total,
                'status': 'connected',
            }
        except Exception as e:
            stats['bland'] = {'status': 'error', 'error': str(e)}
    
    if elevenlabs_client:
        try:
            agents = await elevenlabs_client.get_agents()
            conversations = await elevenlabs_client.get_conversations(limit=10)
            stats['elevenlabs'] = {
                'agents': len(agents),
                'recent_conversations': len(conversations),
                'status': 'connected',
            }
        except Exception as e:
            stats['elevenlabs'] = {'status': 'error', 'error': str(e)}
    
    if zoom_client:
        try:
            recordings = await zoom_client.get_recordings()
            stats['zoom'] = {
                'recordings_30d': len(recordings),
                'status': 'connected',
            }
        except Exception as e:
            stats['zoom'] = {'status': 'error', 'error': str(e)}
    
    return stats


@app.post('/cache/clear')
async def clear_cache():
    """Clear the metrics cache"""
    cache.clear()
    return {'status': 'ok', 'message': 'Cache cleared'}


@app.get('/report/{company}')
async def generate_report(
    company: str,
    days: int = Query(default=30, ge=1, le=365),
):
    """Generate a comprehensive bi-hourly report for a company"""
    
    if company not in COMPANY_PATHWAYS:
        raise HTTPException(status_code=404, detail=f'Company {company} not found')
    
    # Get metrics
    metrics = await get_company_metrics(company, days=days)
    
    # Get best calls
    best_calls = await get_best_calls(company=company, days=days, min_score=8.0, limit=5)
    
    # Build report
    report = {
        'company': metrics.company_name,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'period_days': days,
        'summary': {
            'total_calls': metrics.total_calls,
            'levers': {l.lever: {'name': l.name, 'value': l.value, 'trend': l.trend} for l in metrics.levers},
        },
        'highlights': {
            'best_calls': [c.dict() for c in best_calls],
            'top_lever': max(metrics.levers, key=lambda x: x.value).dict() if metrics.levers else None,
        },
        'raw_metrics': metrics.dict(),
    }
    
    return report


# ============================================
# Background Tasks
# ============================================

async def refresh_all_caches():
    """Background task to refresh all company caches"""
    logger.info('🔄 Starting cache refresh...')
    for company in COMPANY_PATHWAYS.keys():
        try:
            await get_company_metrics(company, days=30, refresh=True)
            logger.info(f'✅ Refreshed cache for {company}')
        except Exception as e:
            logger.error(f'❌ Failed to refresh {company}: {e}')
    logger.info('🔄 Cache refresh complete')


@app.on_event('startup')
async def startup_event():
    """Initialize on startup"""
    logger.info('🚀 7 Levers Metrics Proxy starting...')
    logger.info(f'   Bland.ai: {"✅" if bland_client else "❌"}')
    logger.info(f'   ElevenLabs: {"✅" if elevenlabs_client else "❌"}')
    logger.info(f'   Zoom: {"✅" if zoom_client else "❌"}')
    
    # Initial cache warm-up
    asyncio.create_task(refresh_all_caches())


# ============================================
# Main
# ============================================

if __name__ == '__main__':
    uvicorn.run(
        'server:app',
        host='0.0.0.0',
        port=PORT,
        reload=False,
        log_level='info',
    )
