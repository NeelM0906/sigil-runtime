# Runtime Roadmap (Coding Agent, Multi-Tenant, Local-First)

Date: February 21, 2026

## Locked Product/Architecture Decisions

- Multi-tenant from day one.
- Primary user interfaces: Web chat and CLI.
- Memory architecture: hybrid.
  - Markdown + index for working/human-auditable memory.
  - DB for long-term/user model/procedural and runtime state.
- Learning policy:
  - confidence >= 0.4: auto-apply.
  - confidence < 0.4: approval required.
- Projects/tasks/artifacts visible to user in real time.
- Must-win use case: coding agent.
- Sub-agents are core and enabled by default.
- Local-first deployment initially.
- Model adapters: OpenRouter + direct OpenAI + direct Anthropic.
- Embeddings preference: OpenAI embeddings.
- Tenant isolation: strict per-tenant filesystem and DB isolation.
- Artifact previews: code + markdown first.

## Serena Fit Assessment

Serena is useful as a code-intelligence backend for coding workflows.

Strong fit:
- Symbol-aware retrieval/editing tools (`find_symbol`, `find_referencing_symbols`, `replace_symbol_body`, etc.)
- LSP-backed semantic code operations over large codebases
- MCP and custom-agent integration paths

Not a fit as runtime core:
- Runtime lifecycle, tenant orchestration, memory learning policies, adaptation, approvals, and personality/user-state evolution remain your framework’s responsibility.

## Serena Integration Principle

Use Serena as the default backend under your `Code Intelligence Adapter` layer.

Do not delegate to Serena:
- tenant/session orchestration
- user model/personality/memory policy
- policy adaptation/rollback
- approval governance

Delegate to Serena:
- symbol lookup / reference navigation
- symbol-scoped edits and refactors
- IDE-like structural operations for complex repos

## Multi-Tenant Isolation Requirements for Serena

- One tenant = one isolated workspace root.
- One tenant = one dedicated Serena process (or sandboxed worker) when enabled.
- Enforce path root guards before and after tool calls.
- Disable or strictly gate dangerous tools by default (`execute_shell_command`).
- Require explicit runtime policy checks before enabling write/edit commands.

## Technical Plan

## Phase A: Core Runtime Gateway (Tenant-First)

- Build tenant-aware API and session routing.
- Build adapter interface for model providers and code-intelligence backends.
- Add strict tenant context propagation (`tenant_id` required everywhere).

## Phase B: Hybrid Memory + Learning

- Markdown memory store per tenant/session scope.
- OpenAI embedding index over markdown memory chunks.
- DB-backed long-term memory, user model, and procedural memory.
- Confidence gate for learning apply vs approval queue.

## Phase C: Coding Agent Runtime

- Toolchain includes:
  - local search (`rg` two-pass)
  - file edit/patch
  - command execution (guarded)
  - artifact generation
- Add `Code Intelligence Adapter` abstraction with two implementations:
  - Native runtime symbol/search ops
  - Serena-backed semantic ops

## Phase D: Serena Adapter (Default-Enabled)

- Implement adapter that proxies Serena tools by default.
- Enable read/navigation tools:
  - find_symbol
  - find_referencing_symbols
  - get_symbols_overview
- Enable edit tools immediately:
  - replace_symbol_body
  - insert_before_symbol
  - insert_after_symbol
  - rename_symbol
- Keep shell tool disabled initially.

## Phase E: Sub-Agent Orchestration

- Idempotent async spawn protocol.
- Parent non-blocking updates.
- Shared memory writes with merge metadata.
- Cascade stop and retryable announce path.

## Phase F: User-Visible Projects/Tasks/Artifacts

- Real-time artifacts panel (web) and command views (CLI).
- Code/markdown preview first.
- Task/project lifecycle surfaces.

## Phase G: Adaptation + Governance

- Metric rollups by tenant.
- Policy versioning/diff/rollback.
- Regression-triggered rollback.
- Approval queue UX for low-confidence updates.

## Serena Adoption Gate Criteria

Serena is enabled by default.

Fallback to native code-intel only when:
- Serena endpoint is unavailable, or
- Tenant policy explicitly disables Serena.

## Initial Safety Baseline

- `execute_shell_command`: disabled in Serena adapter by default.
- Edit tools enabled by default, with strict tenant path guards.
- Full audit logs on every Serena-backed operation.
