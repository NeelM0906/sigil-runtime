# Recovery Task Management System

> Customized task management configuration for SAI Recovery's relationship ecosystem operations.
> Designed to layer on top of the existing Bomba SR Mission Control infrastructure.

## Overview

Recovery's domain spans **agreements, partnerships, retention, and public relations** — all relationship-driven workflows that require specialized task handling beyond generic project management. This system provides:

1. **Typed Tasks** — Each task carries a `task_type` (agreement, partnership, retention, pr) with type-specific fields and validation
2. **Priority Scoring** — Weighted scoring model that accounts for revenue impact, relationship value, time sensitivity, and strategic alignment
3. **Workflow Stages** — Custom stage progressions per task type with transition rules and guard conditions
4. **Automation Triggers** — Escalation rules, routing logic, and scheduled actions that keep work flowing
5. **Being Routing** — Maps specific task types and stages to Recovery's specialist beings (agreement-maker, connector, keeper, multiplier)
6. **Dashboard Metrics** — Operational visibility into pipeline health, conversion rates, and being utilization

## Architecture

```
┌─────────────────────────────────────────────┐
│           Mission Control (React UI)         │
│         Kanban Board + Recovery Dashboard    │
├─────────────────────────────────────────────┤
│        Bomba SR FastAPI Backend              │
│   project_create / task_create / task_update │
├─────────────────────────────────────────────┤
│     Recovery Task System (this config)       │
│  schemas ─ config ─ templates ─ routing      │
├─────────────────────────────────────────────┤
│         RuntimeDB (SQLite + WAL)             │
│     projects / tasks / beings tables         │
└─────────────────────────────────────────────┘
```

## How It Connects to ACT-I Ecosystem

- **Task CRUD** uses the existing `task_create`, `task_update`, `task_list` tools available to all SAI sisters
- **Being routing** maps to real `owner_agent_id` values in the tasks table (e.g., `the-agreement-maker`, `the-connector`)
- **Project scoping** uses `project_id` to namespace Recovery's work separately from other sisters
- **Priority scoring** extends the existing `priority` field (low/medium/high/critical) with a numeric score for finer-grained ordering
- **Dashboard metrics** are computed from task state queries against the existing SQLite schema

## File Structure

```
recovery-task-system/
├── README.md                          ← You are here
├── schemas/
│   └── task_types.json                ← JSON schemas for each task type
├── config/
│   ├── priority_scoring.json          ← Scoring weights and rules
│   ├── workflow_stages.json           ← Stage definitions + transitions
│   ├── automation_triggers.json       ← Escalation, routing, scheduling rules
│   └── being_routing.json             ← Task-type-to-being mapping
└── templates/
    └── dashboard_metrics.md           ← Operational dashboard template
```

## Usage

### For the Technologist (Implementation)
1. Parse `schemas/task_types.json` to extend the task creation API with type-specific validation
2. Load `config/workflow_stages.json` to enforce valid stage transitions in `task_update`
3. Register `config/automation_triggers.json` as cron/event rules in the runtime scheduler
4. Use `config/being_routing.json` to auto-assign `owner_agent_id` when tasks are created or transition stages
5. Use `config/priority_scoring.json` to compute numeric priority scores from task metadata

### For Recovery (Operations)
1. Create tasks with `task_create` — the system auto-routes to the right being
2. Tasks move through type-specific stages (not generic "todo/in-progress/done")
3. Dashboard metrics refresh from `templates/dashboard_metrics.md` queries
4. Escalation triggers fire automatically when SLA thresholds are breached

### For Memory (Coordination)
1. All task state changes are logged for cross-sister context
2. Priority scoring history enables pattern analysis over time
3. Being utilization data feeds ecosystem health monitoring

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| JSON config over code | Allows non-technical updates; parseable by any being |
| Layered on existing CRUD | Zero infrastructure changes needed; works today |
| Type-specific stages | Generic stages lose domain meaning ("prospecting" ≠ "in-progress") |
| Numeric priority scores | The existing low/medium/high/critical is too coarse for 50+ active tasks |
| Being routing by stage | Different stages need different expertise (connector for outreach, agreement-maker for closing) |

## Version

- **v1.0** — Initial system design (March 2026)
- **Created by:** SAI Memory (configuration), The Technologist (architecture spec)
- **For:** SAI Recovery's relationship ecosystem operations
