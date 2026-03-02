# ATM / BOMBA SR Feature Parity Matrix

Reference: ATM v0.7.2 -- https://github.com/lspecian/agent-team-manager

## Status Key

| Status          | Meaning                                        |
|-----------------|------------------------------------------------|
| **Not Started** | No implementation work has begun               |
| **In Progress** | Partially implemented                          |
| **Done**        | Feature complete and tested                    |
| **N/A**         | Not applicable to BOMBA SR architecture        |
| **Deferred**    | Planned but not prioritized for current sprint |

## Must-Have Features

| ATM Feature                          | BOMBA Status   | Priority | Notes                                                                |
|--------------------------------------|----------------|----------|----------------------------------------------------------------------|
| Team graph CRUD                      | Not Started    | P0       | Create, read, update, delete top-level graph containers              |
| Node types: human                    | Not Started    | P0       | Human team member nodes with profile config                          |
| Node types: group                    | Not Started    | P0       | Container nodes for hierarchical grouping                            |
| Node types: agent                    | Not Started    | P0       | AI agent nodes with model/instruction config                         |
| Node types: skill                    | Not Started    | P0       | Skill reference nodes linked to BOMBA skill registry                 |
| Node types: pipeline                 | Not Started    | P0       | Pipeline nodes with attached step sequences                          |
| Node types: context                  | Not Started    | P0       | Shared context/knowledge nodes                                       |
| Node types: note                     | Not Started    | P0       | Free-form annotation nodes                                           |
| Node CRUD                            | Not Started    | P0       | Create, read, update, delete nodes within a graph                    |
| Edge management                      | Not Started    | P0       | Create, read, delete edges between nodes; typed relationships        |
| Graph-scoped variables               | Not Started    | P0       | Key-value variables scoped to a graph, typed (string/number/etc.)    |
| Pipeline step management             | Not Started    | P0       | Define and reorder steps within pipeline nodes                       |
| Layout persistence                   | Not Started    | P1       | Save and restore named layout snapshots                              |
| Deploy graph to agents               | Not Started    | P1       | Generate BOMBA sister configs from agent nodes                       |
| Schedule pipeline runs               | Not Started    | P1       | Integrate with BOMBA CronScheduler for recurring execution           |
| AI-assisted graph generation         | Not Started    | P1       | LLM generates graph structure from natural language description      |
| Multi-tenant isolation               | Not Started    | P0       | All queries filtered by tenant_id; enforced at DB schema level       |
| HTTP API endpoints                   | Not Started    | P0       | REST-style routes for all graph/node/edge operations                 |
| Governance integration               | Not Started    | P1       | High-risk ops (deploy, schedule) flow through tool policy pipeline   |
| Parent-child node nesting            | Not Started    | P0       | Hierarchical node relationships via parent_node_id                   |

## Later Features

| ATM Feature                          | BOMBA Status   | Priority | Notes                                                                |
|--------------------------------------|----------------|----------|----------------------------------------------------------------------|
| Advanced layout algorithms           | Deferred       | P2       | Auto-layout (force-directed, hierarchical, radial)                   |
| Template marketplace                 | Deferred       | P3       | Pre-built graph templates for common team structures                 |
| Graph versioning / history           | Deferred       | P2       | Track changes to graph structure over time                           |
| Graph diff / merge                   | Deferred       | P3       | Compare and merge graph versions                                     |
| Bulk import/export                   | Deferred       | P2       | JSON import/export for graph portability                             |
| Graph cloning                        | Deferred       | P2       | Deep-copy a graph with all nodes, edges, variables                   |
| Node search / filtering              | Deferred       | P2       | Search nodes by kind, label, config fields                           |
| Execution history dashboard          | Deferred       | P2       | Visual history of pipeline runs and outcomes                         |
| Collaborative editing                | Deferred       | P3       | Multiple users editing the same graph concurrently                   |

## Out of Scope

| ATM Feature                          | BOMBA Status   | Priority | Notes                                                                |
|--------------------------------------|----------------|----------|----------------------------------------------------------------------|
| Tauri native integrations            | N/A            | --       | BOMBA is headless Python; no native desktop bindings                 |
| Desktop notifications                | N/A            | --       | No desktop runtime; use event streaming instead                      |
| OS cron integration                  | N/A            | --       | BOMBA has its own CronScheduler; no OS-level cron needed             |
| Tauri IPC protocol                   | N/A            | --       | Replaced by BOMBA HTTP API                                           |
| React / ReactFlow frontend           | N/A            | --       | BOMBA is headless; dashboard is a separate deliverable               |
| WebView / browser shell              | N/A            | --       | No Tauri WebView; API-first architecture                             |
| Native file dialogs                  | N/A            | --       | No filesystem UI; graphs persisted in SQLite                         |
| System tray / menu bar               | N/A            | --       | No desktop presence                                                  |
| Auto-update mechanism                | N/A            | --       | BOMBA distributed as Python package, not desktop binary              |

## DB Schema Status

| Table              | Migration | Status      | Notes                                           |
|--------------------|-----------|-------------|-------------------------------------------------|
| `team_graphs`      | 009       | Done        | Top-level graph container                        |
| `team_nodes`       | 009       | Done        | Nodes within a graph, 7 kinds                    |
| `team_edges`       | 009       | Done        | Typed edges between nodes                        |
| `team_layouts`     | 009       | Done        | Named layout snapshots                           |
| `team_variables`   | 009       | Done        | Graph-scoped typed variables                     |
| `team_pipelines`   | 009       | Done        | Step sequences for pipeline nodes                |
