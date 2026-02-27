# 04. CLI Reference

Primary CLI: `scripts/run_chat_cli.py`

## Launch
```bash
PYTHONPATH=src python3 scripts/run_chat_cli.py \
  --tenant-id tenant-local \
  --user-id user-local \
  --workspace /absolute/path/to/workspace
```

Optional args:
- `--session-id`
- `--profile` (`chat|task_execution|retrieval` from `TurnProfile` enum)
- `--state-file`
- `--new-session`

The CLI loads `.env` automatically if present.

## Non-Command Chat
Any line not starting with `/` is treated as user chat and routed through `RuntimeBridge.handle_turn`.

## Built-In Slash Commands
Session/context:
- `/help`
- `/exit`
- `/session`
- `/reset-session`
- `/use-project <project_id>`
- `/use-task <task_id>`
- `/clear-context`

Approvals:
- `/approvals`
- `/approve <id>`
- `/reject <id>`
- `/approve-learning <id>`
- `/reject-learning <id>`
- `/approve-learning-all`
- `/reject-learning-all`
- `/tool-approvals`

Identity:
- `/profile`
- `/signals`

Skills:
- `/skills`
- `/create-skill <name> <description>`
- `/update-skill <skill_id> <description>`
- `/register-skill <manifest.json> [status]`
- `/run-skill <skill_id> [json_inputs]`

Skill ecosystem:
- `/catalog [source] [limit]`
- `/skill-trust [source] [mode]`
- `/install-skill <source> <skill_id> [reason]`
- `/install-requests [status]`
- `/apply-install <request_id>`
- `/skills-diagnostics`
- `/skills-telemetry [limit]`

Projects/tasks:
- `/projects`
- `/tasks [project_id]`

## Chat-Native Skill Wrappers (No Slash Needed)
When enabled (`BOMBA_SKILL_NL_ROUTER_ENABLED=true`), explicit natural language intent is routed deterministically:

Examples:
- "list skills from clawhub"
- "show trust settings"
- "set trust for clawhub to blocked"
- "install skill daily-brief from clawhub"
- "apply install request <uuid>"
- "show skills diagnostics"
- "show skills telemetry"

Behavior:
- Read-only actions execute directly.
- Mutating external installs create approval requests first.
- Install apply succeeds only after approval.

## Approval Flow for Catalog Installs
1. User requests install (slash or natural language).
2. Runtime creates install request + governance approval entry.
3. User approves via `/approve tool:<approval_id>`.
4. User executes `/apply-install <request_id>`.

## CLI Output Conventions
- `sigil> ...` response text
- mode line: `[mode: ...]`
- pending approval counters after each turn
- artifact file paths when generated
- parser warning hint when skill diagnostics exist
