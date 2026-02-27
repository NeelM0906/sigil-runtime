# BOMBA SR Product Runtime Spec (Sequences 1-5)

Date: February 21, 2026
Status: Implementation-aligned spec

## 0. Product Goal

Deliver a production-grade runtime that supports:
- general chat/information assistance,
- project-scoped coding/execution workflows,
- extensible skill/tool composition,
- asynchronous sub-agent orchestration,
- continuous user/persona learning under governed policy.

## 1. Sequence 1: Skill Runtime

### 1.1 Skill Manifest Contract

Each skill is a versioned manifest with deterministic execution metadata.

Required fields:
- `skill_id`: stable identifier (`snake_case`)
- `version`: semver
- `name`: human title
- `description`: concise purpose
- `entrypoint`: execution plan type (`template`, `python_callable`, `tool_chain`)
- `intent_tags`: list of routing tags
- `inputs`: typed inputs with required/default rules
- `outputs`: typed outputs
- `tools_required`: required tool names
- `risk_level`: `low|medium|high|critical`
- `default_enabled`: bool

### 1.2 Skill Lifecycle

- `draft` -> `validated` -> `active` -> `deprecated` -> `archived`
- only `active` skills can execute.
- execution records are immutable and auditable.

### 1.3 Execution Semantics

- skill execution is tenant-scoped.
- runtime validates schema and tool availability before run.
- result payloads include:
  - `status`, `output`, `tool_calls`, `duration_ms`, `error`.
- skill execution can be auto-approved or approval-gated via tool governance.

### 1.4 APIs

- `POST /skills/register`
- `GET /skills`
- `POST /skills/execute`
- `GET /skills/executions?tenant_id=...`

## 2. Sequence 2: Tool Governance

### 2.1 Policy Model

Governance evaluates each action with:
- `risk_class` (low/medium/high/critical)
- `confidence` (0..1)
- `approval_threshold` (default 0.4)
- `policy_action`: `allow|require_approval|deny`

### 2.2 Default Rules

- low-risk read actions: allow if confidence >= 0.2
- medium-risk writes: allow if confidence >= 0.4 else approval
- high-risk writes/commands: approval if confidence < 0.75
- critical/destructive actions: deny unless explicit override policy

### 2.3 Approval Queue

Approval item states:
- `pending` -> `approved|rejected|expired|cancelled`

Each item stores:
- actor/tenant/session/turn
- tool/action payload
- confidence/risk/policy reason
- expiry and decision metadata

### 2.4 Auditing

Every evaluated action emits audit log:
- request payload hash
- evaluator result
- executor backend
- timestamps

## 3. Sequence 3: Project + Task Domain Model

### 3.1 Project Entity

Required fields:
- `project_id`, `tenant_id`, `name`, `description`, `workspace_root`, `status`

Statuses:
- `active|paused|archived`

### 3.2 Task Entity

Required fields:
- `task_id`, `project_id`, `title`, `description`, `status`, `priority`, `owner_agent_id`

Statuses:
- `todo|in_progress|blocked|review|done|cancelled`

### 3.3 Artifact Linkage

All runtime artifacts can attach to:
- `project_id` (optional)
- `task_id` (optional)

### 3.4 APIs

- `POST /projects`
- `GET /projects`
- `POST /tasks`
- `GET /tasks?project_id=...`
- `PATCH /tasks/{task_id}`

## 4. Sequence 4: Generic Info Mode

### 4.1 Intent Routing

Classifier routes turns to:
- `project_mode` when project/task/workspace intent exists.
- `generic_info_mode` for broad informational questions.

### 4.2 Retrieval Strategy

For `generic_info_mode`:
- optional web summary retriever (Wikipedia API baseline)
- include source URLs and snippet citations
- never mix speculative/generated claims without citation marker

### 4.3 Safety and Fallback

- if web retrieval unavailable, respond with model-only answer and explicit uncertainty marker.
- no local codebase search required for purely generic questions.

## 5. Sequence 5: Identity + Learning

### 5.1 User Profile Model

Persistent per tenant+user:
- `display_name`
- `preferences` (tools/style/workflow)
- `goals` (active/inactive)
- `constraints`
- `persona_summary`
- `profile_version`

### 5.2 Signal Extraction

From each turn, extract candidate signals:
- `name`, `preference`, `constraint`, `goal`, `work_context`.

Signal confidence policy:
- >= 0.4 auto-apply
- < 0.4 approval queue

### 5.3 Profile Consolidation

Periodic (or on turn) consolidation:
- merge compatible signals
- archive contradictions
- increment profile version
- emit diff log

## 6. Cross-Sequence Integration

### 6.1 Turn Processing Order

1. Resolve tenant/session/project/task
2. Resolve user profile summary
3. Determine mode (`project` vs `generic_info`)
4. Run retrieval + context assembly
5. Execute tools/skills under governance
6. Produce response + artifacts
7. Persist learning/profile signals
8. Emit adaptation metrics

### 6.2 Non-Blocking Sub-Agents

- sub-agents can be attached to tasks.
- parent remains active and can continue turn work.
- sub-agent progress/events feed task timeline.

## 7. Product Acceptance Criteria

1. Skill manifests validated and executable.
2. Tool governance blocks/queues unsafe actions correctly.
3. Projects/tasks are first-class and visible via APIs.
4. Generic info mode returns citation-backed snippets when available.
5. Profile learning updates persist and are approval-gated per confidence rule.
6. Existing runtime behavior (search/context/memory/subagents) remains passing.

## 8. Rollout Plan

- Wave P1: contracts + tables + services (no API break)
- Wave P2: bridge integration + APIs + tests
- Wave P3: hardening, migration docs, rollout toggles

