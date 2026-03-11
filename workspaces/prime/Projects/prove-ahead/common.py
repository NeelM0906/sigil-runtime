from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

OPENCLAW_ENV_PATH = Path.home() / ".openclaw" / ".env"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_openclaw_env(env_path: Path = OPENCLAW_ENV_PATH) -> Dict[str, str]:
    """Load KEY=VALUE pairs from ~/.openclaw/.env into os.environ."""
    loaded: Dict[str, str] = {}
    if not env_path.exists():
        return loaded

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        os.environ.setdefault(key, value)
        loaded[key] = value

    return loaded


ACT_I_STATS = {
    "calls_made": "271K+",
    "pathways": 128,
    "users": "100+",
    "interactions": "thousands",
    "live_agents": 30,
    "formula_components": 39,
}

MATRIX_DIMENSIONS = [
    "emotional_intelligence",
    "formula_based_approach",
    "contextual_memory",
    "multi_agent_ecosystem",
    "voice_quality",
    "customization_depth",
    "integration_breadth",
    "pricing_model",
    "scale",
    "results_tracking",
]

DIMENSION_LABELS = {
    "emotional_intelligence": "Emotional Intelligence / Rapport",
    "formula_based_approach": "Formula-Based Approach",
    "contextual_memory": "Contextual Memory per User",
    "multi_agent_ecosystem": "Multi-Agent Ecosystem",
    "voice_quality": "Voice Quality / Naturalness",
    "customization_depth": "Customization Depth",
    "integration_breadth": "Integration Breadth",
    "pricing_model": "Pricing Model",
    "scale": "Scale",
    "results_tracking": "Results / Outcomes Tracking",
}
