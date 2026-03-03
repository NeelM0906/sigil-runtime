"""
Beings Registry — register_being() utility.

Any script or agent can call register_being() to register themselves
on the Mission Control dashboard. Beings persist to the shared JSON
file that the dashboard reads.

Usage:
    from bomba_sr.tools.beings_registry import register_being, update_being, get_beings

    # Register a new being
    being = register_being(
        being_id="my-agent",
        name="My Agent",
        role="Specialist",
        tools=[{"name": "web_search", "description": "Search the web"}],
        skills=["Research", "Analysis"],
    )

    # Update status
    update_being("my-agent", status="busy")

    # Get all beings
    beings = get_beings()
"""

import json
import os
from pathlib import Path
from threading import Lock

_DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'mission-control', 'data', 'beings.json'
)
_DATA_PATH = os.environ.get('BOMBA_BEINGS_PATH', _DEFAULT_DATA_PATH)
_lock = Lock()


def _resolve_path():
    return Path(_DATA_PATH).resolve()


def _load():
    path = _resolve_path()
    if not path.exists():
        return {"beings": []}
    with open(path, 'r') as f:
        return json.load(f)


def _save(data):
    path = _resolve_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def register_being(
    being_id,
    name,
    role="",
    description="",
    being_type="custom",
    tools=None,
    skills=None,
    color="#6b7280",
    model_id="",
    workspace="",
    tenant_id="",
    status="offline",
    avatar=None,
):
    """
    Register a new being on the Mission Control dashboard.

    Args:
        being_id: Unique identifier (e.g. 'my-agent')
        name: Display name
        role: Short role description
        description: Full description
        being_type: One of 'runtime', 'sister', 'voice_agent', 'custom'
        tools: List of dicts with 'name' and 'description' keys
        skills: List of skill name strings
        color: Hex color for UI display
        model_id: LLM model identifier
        workspace: Workspace root path
        tenant_id: Tenant isolation key
        status: Initial status ('online', 'offline', 'busy', 'idle')
        avatar: 1-2 char avatar (defaults to first char of name)

    Returns:
        dict: The registered being object

    Raises:
        ValueError: If a being with the same ID already exists
    """
    if tools is None:
        tools = []
    if skills is None:
        skills = []

    being = {
        "id": being_id,
        "name": name,
        "role": role,
        "avatar": avatar or name[0].upper(),
        "status": status,
        "description": description,
        "type": being_type,
        "tools": tools,
        "skills": skills,
        "color": color,
        "model_id": model_id,
        "workspace": workspace,
        "tenant_id": tenant_id,
        "metrics": {"tasksCompleted": 0, "uptime": "0h", "successRate": 0},
    }

    with _lock:
        data = _load()
        if any(b["id"] == being_id for b in data["beings"]):
            raise ValueError(f"Being '{being_id}' already exists. Use update_being() instead.")
        data["beings"].append(being)
        _save(data)

    return being


def update_being(being_id, **changes):
    """
    Update an existing being's fields.

    Args:
        being_id: The being ID to update
        **changes: Fields to update (status, name, role, tools, skills, metrics, etc.)

    Returns:
        dict: The updated being, or None if not found
    """
    allowed = {'name', 'role', 'avatar', 'status', 'description', 'tools', 'skills',
               'color', 'model_id', 'metrics'}
    updates = {k: v for k, v in changes.items() if k in allowed}
    if not updates:
        return None

    with _lock:
        data = _load()
        for being in data["beings"]:
            if being["id"] == being_id:
                for key, val in updates.items():
                    being[key] = val
                _save(data)
                return being
    return None


def get_beings(status=None, being_type=None):
    """
    Get all beings with optional filters.

    Args:
        status: Filter by status
        being_type: Filter by type

    Returns:
        list: List of being dicts
    """
    data = _load()
    beings = data.get("beings", [])
    if status:
        beings = [b for b in beings if b.get("status") == status]
    if being_type:
        beings = [b for b in beings if b.get("type") == being_type]
    return beings


def get_being(being_id):
    """Get a single being by ID."""
    data = _load()
    for b in data.get("beings", []):
        if b["id"] == being_id:
            return b
    return None
