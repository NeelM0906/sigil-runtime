# Upstream Baseline: Agent Team Manager (ATM)

## Reference Repository

| Field              | Value                                                  |
|--------------------|--------------------------------------------------------|
| **Project**        | Agent Team Manager (ATM)                               |
| **Repository**     | https://github.com/lspecian/agent-team-manager         |
| **Pinned Version** | v0.7.2                                                 |
| **License**        | See upstream repository                                |
| **Frozen At**      | 2026-03-02                                             |

## What ATM Is

ATM is a **Tauri desktop application** with a React frontend for visually managing
teams of AI agents. It provides a graph-based UI for composing agent organizations,
defining pipelines, and deploying configurations. Key characteristics:

- **Runtime:** Tauri (Rust backend + WebView frontend)
- **Frontend:** React + TypeScript + ReactFlow for graph editing
- **LLM calls:** Direct Anthropic API calls from the Tauri backend
- **Persistence:** Filesystem-based (JSON files via Tauri fs API)
- **Distribution:** Desktop binary (macOS, Windows, Linux)

## What BOMBA SR Is (contrast)

BOMBA SR is a **headless Python runtime** with no desktop dependencies:

- **Runtime:** Python 3.11+ stdlib `http.server.ThreadingHTTPServer`
- **Frontend:** None (HTML dashboard is a separate concern, not a desktop app)
- **LLM calls:** BOMBA provider routing (OpenRouter, Anthropic, OpenAI, StaticEcho)
- **Persistence:** SQLite (WAL mode) via `src/bomba_sr/storage/db.py`
- **Distribution:** Python package, runs on any server or CI environment

## Delta Policy

### What We Vendor (concepts and data models)

We adopt ATM's **conceptual architecture** for team/graph management:

1. **Graph data model** -- Directed graph with typed nodes and edges.
2. **Node type taxonomy** -- `human`, `group`, `agent`, `skill`, `pipeline`, `context`, `note`.
3. **Edge semantics** -- Typed relationships between nodes (dependency, delegation, data flow).
4. **Pipeline abstraction** -- Ordered step sequences attached to pipeline nodes.
5. **Layout persistence** -- Named layout snapshots for graph visualization.
6. **Variable scoping** -- Graph-scoped variables with typed values.
7. **Org chart patterns** -- Hierarchical team structures via `parent_node_id`.

### What We Fork (re-implement from scratch)

Everything below the conceptual layer is re-implemented for BOMBA's architecture:

1. **Storage layer** -- SQLite tables replace filesystem JSON (see `sql/migrations/009_team_manager.sql`).
2. **API surface** -- BOMBA HTTP route handlers replace Tauri IPC commands.
3. **LLM integration** -- BOMBA provider routing replaces direct Anthropic calls.
4. **Multi-tenancy** -- All tables include `tenant_id`; ATM is single-user.
5. **Governance** -- Tool policy pipeline applies to team management operations.
6. **Execution** -- Pipeline execution uses BOMBA's agentic loop, not ATM's runner.

### What We Do NOT Take

| ATM Component                | Reason for Exclusion                                      |
|------------------------------|-----------------------------------------------------------|
| Tauri runtime / Rust backend | BOMBA is pure Python; no native desktop bindings          |
| React frontend / ReactFlow   | BOMBA is headless; dashboard is a separate deliverable    |
| Direct Anthropic API calls   | BOMBA uses provider routing (OpenRouter primary)          |
| Filesystem persistence       | BOMBA uses SQLite with WAL mode                           |
| OS-level task scheduler      | BOMBA has its own CronScheduler                           |
| Desktop notifications        | No desktop runtime; BOMBA uses event streaming            |
| Tauri IPC protocol           | Replaced by BOMBA HTTP API                                |

## Version Tracking

When upstream ATM releases beyond v0.7.2, changes should be evaluated against
this delta policy. Only conceptual/data-model changes that align with the "What
We Vendor" list above should be considered for backport. Implementation changes
in Tauri, React, or filesystem layers are out of scope.
