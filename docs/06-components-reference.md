# 06. Components Reference

This section documents each primary component and its role.

## Package: `runtime`

### `runtime/config.py`
- `RuntimeConfig`: immutable runtime settings loaded from env.
- `SerenaPolicy`: Serena integration toggles.

### `runtime/bridge.py`
- `RuntimeBridge`: main orchestrator and public service interface.
- `TurnRequest`: chat turn input model.
- Creates and caches per-tenant runtime containers.
- Exposes API methods used by CLI and HTTP server.

### `runtime/loop.py`
- `AgenticLoop`: iterative tool-call loop.
- `LoopConfig`, `LoopState`, `LoopResult`.
- Usage accounting, budget stop, tool scheduling, health injection, loop detection.

### `runtime/health.py`
- `HealthSnapshot`: loop health block rendered into system prompt.

### `runtime/rescue.py`
- `WorkspaceRescue`: pre-loop git rescue snapshot and cleanup helper.

### `runtime/tenancy.py`
- `TenantRegistry` / tenant workspace + db binding helpers.

## Package: `llm`

### `llm/providers.py`
- `ChatMessage`, `LLMResponse` models.
- `AnthropicProvider`, `OpenAICompatibleProvider`, `StaticEchoProvider`.
- `provider_from_env` selection.

## Package: `context`

### `context/policy.py`
- `ContextPolicyEngine`: context assembly and compression under model budgets.
- `TurnProfile` enum.

## Package: `tools`

### `tools/base.py`
- `ToolDefinition`, `ToolContext`, `ToolCallResult`.
- `ToolExecutor`: registration, policy filtering, governance evaluation, execution, truncation.

### Builtins
- `builtin_fs.py`: `read`, `write`, `edit`, `apply_patch`, `glob`, `grep`.
- `builtin_exec.py`: `exec`, `process`.
- `builtin_search.py`: search + code intelligence wrappers.
- `builtin_memory.py`: semantic/working memory operations.
- `builtin_approvals.py`: unified approvals listing/decision tools.
- `builtin_subagents.py`: spawn/poll/list sub-agent runs.
- `builtin_projects.py`: project/task CRUD tools.
- `builtin_skills.py`: skill create/update and install-request/apply tools.
- `builtin_compaction.py`: LLM-driven context compaction tool.
- `builtin_model_switch.py`: mid-loop model switching.
- `builtin_discovery.py`: dynamic tool enabling per loop.

## Package: `governance`

### `governance/tool_profiles.py`
- Tool groups, profiles (`minimal|coding|research|full`), alias resolution.

### `governance/policy_pipeline.py`
- `PolicyPipeline`: profile + allow/deny resolution into `ResolvedPolicy`.

### `governance/tool_policy.py`
- `ToolGovernanceService`: risk classification, decisioning, approvals queue, audit logs.
- `get_approval`, `list_pending_approvals`, `decide_approval`.

## Package: `skills`

### `skills/descriptor.py`
- `SkillDescriptor`, `SkillEligibility`, manifest conversion utility.

### `skills/skillmd_parser.py`
- YAML frontmatter parsing, metadata extraction, eligibility extraction.
- Permissive parsing + fallback + warning capture.

### `skills/loader.py`
- Skill filesystem scan with precedence.
- Snapshot cache, hot watcher, diagnostics map.

### `skills/registry.py`
- Skill persistence (SQLite), execution record persistence.

### `skills/engine.py`
- Skill execution orchestration over registered manifests.

### `skills/ecosystem.py`
- External skill catalog integration (ClawHub, Anthropic Skills).
- Source trust policy.
- Approval-gated install requests and installation.
- Telemetry events for ecosystem operations.

### `skills/eligibility.py`
- Runtime gating (os, binaries, env, config requirements).

## Package: `commands`

### `commands/parser.py`
- Slash command parsing.

### `commands/router.py`
- Slash command dispatch to built-ins/tool execution/skill loading.

### `commands/disclosure.py`
- Skill index formatting for model prompt injection.

### `commands/skill_nl_router.py`
- Deterministic natural language intent extraction for skill ecosystem operations.

## Package: `codeintel`

### `codeintel/router.py`
- Chooses Serena vs native codeintel implementation.

### `codeintel/serena.py`
- Serena transport-backed codeintel operations.

### `codeintel/native.py`
- Native fallback codeintel methods.

### `codeintel/base.py`
- Shared interfaces/models for codeintel operations.

## Package: `memory`

### `memory/hybrid.py`
- Hybrid memory store (DB + markdown + optional embeddings).
- Learning approvals, recall, semantic memory operations.

### `memory/embeddings.py`
- OpenAI embeddings provider wrapper.

### `memory/consolidation.py`
- Memory consolidation helpers.

## Package: `identity`

### `identity/profile.py`
- User profile extraction/updates with pending signal approvals.

## Package: `search`

### `search/agentic_search.py`
- Local-first code/document search execution and result packaging.

## Package: `subagents`

### `subagents/protocol.py`
- Run/event protocol, progress, completion, shared memory writes.

### `subagents/orchestrator.py`
- Async orchestration and crash storm circuit-breaker behavior.

## Package: `projects`

### `projects/service.py`
- Project/task persistence and retrieval.

## Package: `artifacts`

### `artifacts/store.py`
- Artifact creation and listing (markdown/code outputs, etc).

## Package: `adaptation`

### `adaptation/runtime_adaptation.py`
- Runtime metrics ingestion and rollup helpers.

## Package: `models`

### `models/capabilities.py`
- Model capabilities retrieval/caching (OpenRouter + fallback catalog).

## Package: `info`

### `info/retrieval.py`
- Generic information retrieval helpers used in non-project chat mode.

## Package: `plugins`

### `plugins/api.py`
- Plugin registration API (`register_tool`, `register_skill_dir`).

### `plugins/registry.py`
- Plugin discovery/load lifecycle from configured paths.

## Package: `storage`

### `storage/db.py`
- SQLite connection and helper wrapper.

## Entrypoint Scripts

### `scripts/run_chat_cli.py`
- User interactive CLI session.

### `scripts/run_runtime_server.py`
- HTTP server wrapper around `RuntimeBridge`.

### `scripts/run_user_e2e.py`
- Scripted user-level E2E utility.

## Contracts (`contracts/`)
- JSON schemas for approvals, context assembly, capabilities, plugins, projects/tasks, skills, tools, subagents, metrics, user profile.

## Test Suite (`tests/`)
- Unit + integration-like tests for all phases and Ouroboros enhancements.
- Current status target: full pass before merge.
