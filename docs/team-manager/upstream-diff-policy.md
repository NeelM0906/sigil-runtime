# Upstream Diff Policy: ATM to BOMBA SR

This document defines precisely what BOMBA SR takes from the ATM (Agent Team
Manager) v0.7.2 reference and what it replaces, rejects, or re-implements.

## What We Take from ATM

### Graph Data Model Concepts

- **Directed acyclic graph** for representing team structures and workflows.
- **Node-centric design** where each entity (person, agent, skill, etc.) is a
  graph node with position, dimensions, configuration, and optional parent
  for hierarchical nesting.
- **Edge semantics** for expressing relationships: dependency, delegation,
  data flow, reporting lines.

### Node Types

ATM defines a taxonomy of node kinds that we adopt wholesale:

| Kind       | Purpose                                          |
|------------|--------------------------------------------------|
| `human`    | A human team member or stakeholder                |
| `group`    | A container for grouping other nodes              |
| `agent`    | An AI agent with model config and instructions    |
| `skill`    | A reusable capability or tool                     |
| `pipeline` | An ordered sequence of execution steps            |
| `context`  | Shared context or knowledge attached to the graph |
| `note`     | Free-form annotation                              |

### Pipeline Concepts

- Pipelines as ordered step sequences attached to pipeline-type nodes.
- Steps reference other nodes (agents, skills) and define execution order.
- Variables scoped to graphs for parameterizing pipelines.

### Org Chart Visualization Patterns

- Hierarchical parent-child relationships via `parent_node_id`.
- Named layout snapshots for persisting spatial arrangements.
- Graph-level metadata for titles, descriptions, and tags.

## What We Do NOT Take from ATM

### Tauri Runtime

ATM is built on Tauri, which provides a Rust backend with native OS access and
a WebView shell for the React frontend. BOMBA SR has no use for any of this:

- No Rust compilation or Tauri CLI.
- No WebView or browser shell.
- No native windowing, menus, or system tray.

### Direct Anthropic API Calls from Browser

ATM routes LLM calls from the frontend through Tauri's IPC to the Rust backend,
which calls the Anthropic API directly. BOMBA SR replaces this entirely:

- All LLM calls go through `src/bomba_sr/llm/providers.py`.
- Provider selection: Anthropic > OpenAI > OpenRouter > StaticEcho.
- Model ID is configurable via `BOMBA_MODEL_ID`.

### Filesystem Access from Frontend

ATM persists graphs as JSON files on the local filesystem via Tauri's `fs` API.
BOMBA SR does not use filesystem persistence for structured data:

- All graph/node/edge data stored in SQLite tables.
- WAL mode for concurrent read access.
- Thread-safe via `RuntimeDB` with `threading.RLock()`.

### OS-Level Task Scheduler

ATM integrates with OS cron or task scheduler for periodic runs. BOMBA SR has
its own scheduler:

- `src/bomba_sr/autonomy/scheduler.py` provides `CronScheduler`.
- Uses `croniter` for cron expression parsing.
- Stores tasks in `scheduled_tasks` SQLite table.

## Replacement Mapping

| ATM Component              | BOMBA SR Replacement                                     |
|----------------------------|----------------------------------------------------------|
| Tauri IPC commands         | HTTP route handlers (`/team-graphs/*`, `/team-nodes/*`)  |
| Rust backend functions     | Python service layer (`src/bomba_sr/teams/`)             |
| Direct Claude API calls    | BOMBA provider routing (`llm/providers.py`)              |
| JSON file persistence      | SQLite tables (`team_graphs`, `team_nodes`, etc.)        |
| React + ReactFlow frontend | Headless API (dashboard is a separate deliverable)       |
| Tauri fs API               | `RuntimeDB` SQLite wrapper (`storage/db.py`)             |
| OS cron integration        | BOMBA `CronScheduler` (`autonomy/scheduler.py`)          |
| Desktop notifications      | Event streaming via sub-agent protocol                   |
| Single-user model          | Multi-tenant isolation (`tenant_id` on all tables)       |

## Design Principles for Divergence

1. **Multi-tenant first.** Every table and query includes `tenant_id`. ATM is
   single-user; BOMBA SR supports concurrent tenants.

2. **Governance-aware.** Team management operations flow through BOMBA's tool
   policy pipeline. High-risk actions (deploy, schedule) require governance
   approval.

3. **Provider-neutral LLM.** AI-assisted graph generation uses whatever LLM
   provider is configured, not a hardcoded Anthropic client.

4. **SQLite-native.** All persistence uses SQLite-compatible types and
   expressions. No PostgreSQL-isms in the team manager tables.

5. **Headless operation.** The API must be fully functional without any UI.
   Graph visualization is a rendering concern, not a persistence concern.
