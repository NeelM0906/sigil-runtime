# Recovery Task System — Integration Guide

## Overview

This guide explains how the Recovery Task System configuration integrates with the existing Bomba SR (sigil-runtime) infrastructure. The system is designed as a **configuration overlay** — it does not modify the core platform. Instead, it uses conventions and metadata encoding to add Recovery-specific semantics on top of the existing project/task primitives.

---

## 1. Existing Infrastructure

The Bomba SR platform provides:

| Component | Technology | Location |
|-----------|-----------|----------|
| **Backend API** | Python / FastAPI | `sigil-runtime/api/` |
| **Database** | SQLite (WAL mode) | `RuntimeDB` wrapper |
| **Dashboard** | React (Mission Control) | `sigil-runtime/dashboard/` |
| **Agent Tools** | `project_create`, `task_create`, `task_update`, `task_list` | Built-in to all agents |

### Core Schema Fields

```
projects: project_id, name, description, status, workspace_root
tasks:    task_id, project_id, title, description, status, priority, owner_agent_id
```

The Recovery Task System uses these fields with the following conventions:

- **`project_id`** → Recovery project identifier (e.g., `recovery-pipeline`)
- **`title`** → Human-readable task title
- **`description`** → Contains Recovery metadata block + human description
- **`status`** → Maps from workflow stage (see `workflow_stages.json` → `status_mapping`)
- **`priority`** → Set from priority tier (`critical`, `high`, `medium`, `low`)
- **`owner_agent_id`** → Set from being routing (e.g., `the-agreement-maker`)

---

## 2. Metadata Encoding

Since the existing schema doesn't have custom fields for task type, workflow stage, or priority score, we encode Recovery metadata as a comment block at the top of the `description` field:

```
<!--RECOVERY_META:{"task_type":"agreement","stage":"negotiating","priority_score":82.5,"counterparty":"Acme Corp","agreement_type":"service_contract","estimated_value":75000,"deadline":"2026-04-30"}-->

Negotiating service contract with Acme Corp. Decision maker is Jane Smith (VP Partnerships).
Current terms: $75K annual retainer for full-stack AI consulting.
Key open items: payment terms (net-30 vs net-60), IP ownership clause.
```

### Parsing the Metadata

```python
import json
import re

def parse_recovery_meta(description: str) -> dict | None:
    """Extract Recovery metadata from a task description."""
    match = re.search(r'<!--RECOVERY_META:(.*?)-->', description, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return None

def inject_recovery_meta(meta: dict, human_description: str) -> str:
    """Create a description with embedded Recovery metadata."""
    meta_json = json.dumps(meta, separators=(',', ':'))
    return f"<!--RECOVERY_META:{meta_json}-->\n\n{human_description}"
```

---

## 3. Creating a Recovery Task

### Step 1: Set Up the Recovery Project (once)

```python
project_create(
    name="Recovery Pipeline",
    description="SAI Recovery relationship ecosystem management",
    project_id="recovery-pipeline"
)
```

### Step 2: Create a Typed Task

```python
# 1. Build metadata from task_types.json schema
meta = {
    "task_type": "agreement",
    "stage": "identified",
    "priority_score": 0,  # Will be calculated
    "counterparty": "Acme Corp",
    "agreement_type": "service_contract",
    "estimated_value": 75000,
    "deadline": "2026-04-30"
}

# 2. Calculate priority score using priority_scoring.json weights
priority_score = calculate_priority(meta)  # → 72.5
meta["priority_score"] = priority_score

# 3. Determine priority tier
tier = get_priority_tier(priority_score)  # → "high"

# 4. Route to being using being_routing.json
being = route_to_being(meta)  # → "the-connector" (identified stage)

# 5. Create the task
task_create(
    project_id="recovery-pipeline",
    title="Agreement: Acme Corp Service Contract",
    description=inject_recovery_meta(meta, "Potential $75K service contract with Acme Corp."),
    status="todo",
    priority=tier,
    owner_agent_id=being
)
```

### Step 3: Advance Through Workflow

```python
# When stage changes, update the task
meta["stage"] = "qualifying"
being = route_to_being(meta)  # Still "the-connector"

task_update(
    task_id="<task_id>",
    status="in_progress",  # From workflow_stages.json status_mapping
    owner_agent_id=being
)

# When advancing to proposal_sent, being changes
meta["stage"] = "proposal_sent"
being = route_to_being(meta)  # Now "the-agreement-maker"

task_update(
    task_id="<task_id>",
    owner_agent_id=being
)
```

---

## 4. Priority Recalculation

Priority scores should be recalculated:

1. **On creation** — initial scoring
2. **On stage transition** — time sensitivity may change
3. **On schedule** — daily recalc for time-sensitive dimensions
4. **On trigger** — when auto-escalation rules fire

```python
def calculate_priority(meta: dict) -> float:
    """Calculate priority score using weights from priority_scoring.json."""
    score = 0.0
    task_type = meta["task_type"]
    
    for dim_name, dim_config in PRIORITY_CONFIG["dimensions"].items():
        raw_score = assess_dimension(dim_name, meta)  # 0-100
        weight = dim_config["weight"]
        modifier = dim_config["task_type_modifiers"][task_type]["multiplier"]
        score += raw_score * weight * modifier
    
    return min(score, 100.0)
```

---

## 5. Being Routing Logic

```python
def route_to_being(meta: dict) -> str:
    """Evaluate routing rules to determine assigned being."""
    for rule in ROUTING_CONFIG["routing_rules"]["rules"]:
        if matches_condition(rule["condition"], meta):
            # Check for spawn_task rules
            if "spawn_task" in rule:
                handle_spawn(rule["spawn_task"], meta)
            return rule["assign_to"]
    
    # Fallback
    return ROUTING_CONFIG["fallback_routing"]["unmatched_task_type"]
```

---

## 6. Dashboard Integration

Tasks created through this system appear in the Mission Control Kanban board automatically since they use the standard task API. For Recovery-specific views:

- **Filter by project:** `project_id = "recovery-pipeline"`
- **Filter by being:** `owner_agent_id` matches one of the 4 Recovery beings
- **Sort by priority:** Use the `priority` field (critical > high > medium > low)
- **Stage visibility:** Parse `RECOVERY_META` from description for workflow stage detail

---

## 7. Cross-System Triggers

The workflow stages include `triggers_on_complete` that create follow-on tasks:

| Source Event | Generated Task |
|-------------|---------------|
| Agreement → closed_won | Retention task (onboarding) |
| Agreement → closed_won ($50K+) | PR task (case study) |
| Partnership → active | Retention task (health monitoring) |
| Retention → resolved (satisfaction ≥ 8) | PR task (testimonial) |
| Retention → churned | Retention task (win-back, 90-day delay) |
| Agreement → closed_lost | Retention task (re-engagement, 90-day delay) |

These triggers ensure the relationship lifecycle is continuous — no closed deal goes without a retention follow-up, and no happy client goes without a testimonial ask.
