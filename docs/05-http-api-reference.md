# 05. HTTP API Reference

Runtime server: `scripts/run_runtime_server.py`

## Start Server
```bash
PYTHONPATH=src python3 scripts/run_runtime_server.py --host 127.0.0.1 --port 8787
```

## POST Endpoints

### `/chat`
Primary chat turn execution.
Required fields:
- `tenant_id`, `session_id`, `user_id`, `message`
Optional:
- `turn_id`, `model_id`, `profile`, `workspace_root`, `search_query`, `project_id`, `task_id`

### `/codeintel`
Invoke a tool directly (`bridge.invoke_code_tool`).
Required:
- `tenant_id`, `tool_name`, `arguments`

### `/learning/approve`
Approve/reject memory learning update.
Required:
- `tenant_id`, `user_id`, `update_id`, `approved`

### `/subagents/spawn`
Spawn async sub-agent task.
Required:
- `tenant_id`, parent metadata, task payload fields

### `/skills/register`
Register JSON manifest skill.
Required:
- `tenant_id`, `manifest`

### `/skills/execute`
Execute registered skill.
Required:
- `tenant_id`, `skill_id`

### `/skills/install-request`
Create approval-gated catalog install request.
Required:
- `tenant_id`, `user_id`, `source`, `skill_id`

### `/skills/install`
Apply approved install request.
Required:
- `tenant_id`, `request_id`

### `/skills/source-trust`
Set per-tenant source trust override.
Required:
- `tenant_id`, `source`, `trust_mode`

### `/projects`
Create project.

### `/tasks`
Create task.

### `/tasks/update`
Update task fields.

### `/approvals/decide`
Decide governance approval.
Required:
- `tenant_id`, `approval_id`, `approved`

### `/profile/signals/decide`
Approve/reject identity signal.

### `/commands/execute`
Execute slash command through bridge.

## GET Endpoints

### `/health`
Returns `{ "ok": true }`

### `/commands`
List available commands.
Query: `tenant_id`, optional `workspace_root`

### `/artifacts`
List artifacts.
Query: `tenant_id`, `session_id`, optional `workspace_root`, `limit`

### `/subagents/events`
Poll sub-agent events.
Query: `tenant_id`, `run_id`, optional `after_seq`, `workspace_root`

### `/skills`
List registered skills.
Query: `tenant_id`, optional `status`, `workspace_root`

### `/skills/catalog`
List external catalog skills.
Query: `tenant_id`, optional `source`, `limit`, `workspace_root`

### `/skills/diagnostics`
List parser diagnostics warnings by skill id.
Query: `tenant_id`, optional `workspace_root`

### `/skills/install-requests`
List install requests.
Query: `tenant_id`, optional `status`, `limit`, `workspace_root`

### `/skills/source-trust`
Get source trust policy (shared defaults + tenant overrides).
Query: `tenant_id`, optional `workspace_root`

### `/skills/telemetry`
List skill ecosystem telemetry.
Query: `tenant_id`, optional `limit`, `workspace_root`

### `/skills/executions`
List skill execution records.

### `/projects`
List projects.

### `/tasks`
List tasks.

### `/approvals`
List pending tool approvals.

### `/learning/approvals`
List pending learning approvals.

### `/profile`
Get user profile.

### `/profile/signals`
Get pending identity signals.

## Response Shape Notes
`/chat` response includes:
- `tenant`, `turn`
- `assistant` (text, provider, usage, loop metadata)
- `approvals` (learning/tool/pending total)
- `skills` (parse diagnostics, telemetry status)
- `identity`, `memory`, `artifacts`, `search`, `context`, `adaptation`, `rescue`

## Schemas
Contract schemas are under `contracts/`.
Key files:
- `contracts/skill-descriptor.schema.json`
- `contracts/tool-definition.schema.json`
- `contracts/tool-governance-policy.schema.json`
- `contracts/subagent-task.schema.json`
