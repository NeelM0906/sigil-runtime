# 08. User Flows (End-to-End)

## A. General Assistant Conversation
1. Start CLI.
2. Send normal message (e.g., "hi", "who are you", "what were we working on?").
3. Runtime processes via `handle_turn` with context assembly + loop.
4. Memory/identity updates are persisted; approvals may be queued when needed.

## B. Skill Creation by Conversation
1. User asks to create a skill in chat.
2. Agent can invoke `skill_create` tool.
3. Runtime writes `workspace/skills/<skill_id>/SKILL.md` and registers it.
4. Skill is available via `/skills` and slash invocation.

## C. External Skill Install (Approval-First)
1. User asks: "install skill <id> from clawhub".
2. NL router creates install request (no immediate write).
3. Governance creates approval item.
4. User approves via `/approve tool:<approval_id>`.
5. User applies via `/apply-install <request_id>`.
6. Runtime downloads SKILL.md, stores in workspace, registers skill, logs telemetry.

## D. Trust Policy Management
1. User asks: "show trust settings".
2. Runtime returns effective source trust policy.
3. User asks: "set trust for clawhub to blocked".
4. Tenant override is persisted and used for future requests.

## E. Diagnostics and Telemetry
1. User asks: "show skills diagnostics".
2. Runtime returns parser warnings keyed by skill id.
3. User asks: "show skills telemetry".
4. Runtime returns telemetry stream for skill ecosystem events.

## F. Project/Task Interaction
1. Create/list projects and tasks via CLI/API.
2. Set active project/task context in CLI.
3. Chat turns include project/task context in assembled prompt.

## G. Sub-Agent Invocation
1. Spawn task through API or tool.
2. Poll event stream for progress/completion.
3. Crash storm protection blocks new spawns during cooldown if repeated failures occur.

## H. Approval Operations
Unified `approvals` concept includes:
- governance tool approvals
- learning approvals

CLI supports both view and decision operations.
