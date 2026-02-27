# 02. Architecture

## High-Level Runtime Graph

User (CLI/Web/API)
-> RuntimeBridge (`src/bomba_sr/runtime/bridge.py`)
-> Tenant Runtime Container
- Context assembly
- Agentic loop
- Tool executor + governance
- Memory + identity
- Skills + ecosystem
- Subagents + projects/tasks
-> LLM provider + local tooling

## Request Lifecycle (`handle_turn`)
1. Resolve tenant runtime and workspace binding.
2. Parse slash command (if present).
3. Parse chat-native skill NL intents (if enabled).
4. Fetch model capability metadata.
5. Build search/generic retrieval inputs.
6. Assemble context (`ContextPolicyEngine`).
7. Prepare system prompt (includes available skills index).
8. Run agentic loop (if enabled):
- generate response
- parse tool calls
- execute tools via policy + governance
- append tool results
- apply stop conditions (iteration, loop detection, approvals, budget)
9. Persist:
- memory note + semantic learning
- identity profile signals
- adaptation metrics
- loop execution record
10. Return full response object with assistant text, approvals, identity, artifacts, diagnostics.

## Tenant Runtime Composition
Created in `_tenant_runtime` and cached per tenant:
- `RuntimeDB`
- `ModelCapabilityService`
- `SubAgentProtocol` + `SubAgentOrchestrator`
- `CodeIntelRouter`
- `ToolGovernanceService`
- `SkillRegistry` + `SkillEngine` + `SkillLoader`
- `SkillEcosystemService`
- `AgenticSearchExecutor`
- `HybridMemoryStore`
- `ProjectService`
- `PolicyPipeline`
- `ToolExecutor`
- `CommandParser` + `CommandRouter` + `SkillDisclosure`
- `UserIdentityService`
- `GenericInfoRetriever`

## Skills Architecture
Skill sources:
- Workspace skills: `<workspace>/skills/*/SKILL.md`
- User skills: `~/.sigil/skills/*/SKILL.md`
- Bundled skills: package bundled path
- Plugin skill dirs

Skill systems:
- `SkillMdParser`: parses frontmatter + body (permissive mode available).
- `SkillLoader`: scans roots, precedence, hot watcher, diagnostics.
- `SkillRegistry`: DB registry + execution history.
- `SkillEngine`: executes skill manifests.
- `SkillEcosystemService`: external catalogs, trust policy, install requests, telemetry.

## Governance and Policy
Two layers:
1. Policy Pipeline (`policy_pipeline.py`)
- Determines tool visibility/allowlist by profile and denies.

2. Tool Governance (`tool_policy.py`)
- Per call risk/confidence decision.
- Allow / deny / approval-required outcomes.
- Approval queue and audit logs.

## Agentic Loop (`runtime/loop.py`)
Features:
- Iterative tool-calling loop.
- Provider-specific tool call parsing (OpenAI-compatible + Anthropic blocks).
- Loop detection.
- Approval stop behavior.
- Estimated budget tracking and hard-stop.
- Parallel execution for read-only tool batches.
- Dynamic tool schema refresh with overrides.
- Health block injected into system prompt each iteration.
- Supports loop-state-mutation tools (`switch_model`, `compact_context`, `enable_tools`).

## Sub-Agents
- Asynchronous execution via `ThreadPoolExecutor`.
- Event protocol for progress/completion.
- Crash storm detector with cooldown to prevent failure cascades.

## State and Storage
- SQLite tables for skills, executions, approvals, audits, projects/tasks, memory, adaptation, loop runs.
- Filesystem artifacts under tenant runtime home.
- Workspace skills stored in project workspace.

## Safety Controls
- Tenant workspace guard path checks.
- Approval queue for low-confidence/high-risk actions.
- Rescue snapshot before loop (git-based rescue ref when enabled).
- Tool output truncation bounds for prompt safety.
