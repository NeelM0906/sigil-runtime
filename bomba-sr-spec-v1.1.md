# BOMBA SR
## AI Assistant Platform - Technical Specification v1.1

Author: Neel | Unblinded / ACTi
Date: February 21, 2026
Status: Confirmed and Active

## 0. What Changed From v1.0

This version replaces static assumptions with runtime capability discovery and adds production-grade sub-agent protocol semantics.

### Confirmed Decisions

1. Development priority is performance; cost is not a gating factor.
2. Phase 1 uses a fixed primary model.
3. Parent agent remains active while sub-agents run and report updates.
4. No hard budget gating in phase 1.
5. Sub-agents can write shared working memory.
6. Local search policy is two-pass: ignore-aware first, broad escalation second.
7. Contradictory memories are archived, not deleted.
8. Provider-specific routing constraints are out of scope for phase 1.

### Locked Defaults

- Primary model: `anthropic/claude-opus-4.6`
- Search escalation mode: `balanced`
- Max spawn depth default: `1`
- Graph indexing: phase 2 core (phase 1 optional extension)

## 1. Architecture Overview

Bomba SR is an agent runtime platform, not a chat wrapper.

Core property:
- The runtime environment becomes progressively smarter through policy updates, structured memory, and verifiable feedback loops.

## 2. Viability Stack

### L0 Substrate
- OpenRouter client
- Runtime capability handshake
- Tool transport and usage telemetry

### L1 Cognition (ACTi)
- Perception -> Comprehension -> Intention -> Action -> Reflection
- Viability bounds enforced in orchestration, not only prompt text

### L2 Coordination
- Ticket-based multi-agent execution
- Shared-memory collaboration with write metadata

### L3 Evolution
- Runtime policy adaptation from prediction, retrieval, and execution metrics

## 3. Memory and Context

### 3.1 Memory Tiers

- Working: active execution state, scratchpad, in-flight plans
- Episodic: interaction outcomes and session summaries
- Semantic: durable facts/preferences/relationships
- Procedural: strategies and heuristics with evidence

Contradictions are resolved by promoting newer belief while preserving prior versions as archived records.

### 3.2 Context Assembly (Dynamic, Capability-Aware)

Context assembly is policy-driven and model-capability-aware.

#### Capability Handshake

Before first run in a session (and periodic refresh), fetch:
- `context_length`
- `top_provider.max_completion_tokens`
- model/tool compatibility metadata

```ts
interface ModelCapabilities {
  modelId: string;
  contextLength: number;
  maxCompletionTokens: number;
  supportsTools: boolean;
  supportsJsonMode: boolean;
  fetchedAt: string;
}
```

#### Budget Formula

```ts
const cap = capabilities.contextLength;
const reservedOutput = Math.min(32_000, Math.floor(cap * 0.20));
const reservedSafety = Math.max(2_000, Math.floor(cap * 0.03));
const availableInput = cap - reservedOutput - reservedSafety;
```

#### Turn Profiles

```ts
type TurnProfile =
  | 'chat'
  | 'task_execution'
  | 'planning'
  | 'memory_recall'
  | 'subagent_orchestration';
```

Each profile has profile-specific memory tier weights and hard floors.

#### Inclusion Order

1. System prompt + ACTi contract (required)
2. User message + current tool state (required)
3. Active task/plan state (required when relevant)
4. Working memory (bounded)
5. World state (field-level, not full dump)
6. Semantic recalls (reranked)
7. Recent history (compressed + recent raw turns)
8. Procedural memory (selected only)
9. Pending predictions (actionable only)

#### Compression Invariants

Compression order remains `summarize > truncate > drop` with hard rules:
- Never drop explicit user constraints in current session.
- Never summarize tool output without source references.
- Never present contradictory memories without recency/evidence labels.

#### Pre-Compaction Memory Flush

When token estimate approaches compaction threshold, run a silent memory flush turn to persist durable context before compression.

### 3.3 Agentic-First Search (Local-First Retrieval Contract)

Local retrieval is a first-class runtime primitive.

#### Search Plan Contract

```ts
interface SearchPlan {
  query: string;
  intent: 'symbol_lookup' | 'flow_trace' | 'config_lookup' | 'test_lookup' | 'broad_discovery';
  scope: string[];
  fileTypes: string[];
  escalationAllowed: boolean;
}
```

#### Execution Pipeline

1. Inventory:
```bash
rg --files
```

2. Scoped search (default):
```bash
rg -n --hidden -g '!.git' -g '!node_modules' '<pattern>' <scopes>
```

3. Typed refinement:
```bash
rg -n -t<type> '<pattern>' <scopes>
```

4. Escalation pass (only on miss/low-confidence):
```bash
rg -uuu -n '<pattern>' <scopes>
```

5. Retrieval pack output:
- file path
- line references
- confidence score
- retrieval rationale

#### Balanced Escalation Policy (Locked)

Escalate to pass 2 if:
- zero matches for high-confidence query, or
- matches are low-confidence/noisy (generated/vendor-heavy), or
- results conflict with known symbols from current execution state.

### 3.4 Code Intelligence Backend Policy (Serena Default)

Code-intelligence backend is Serena-first by default for coding-agent turns.

Locked defaults:
- `serena.enabled = true`
- `serena.editToolsEnabled = true`
- `serena.execute_shell_command = false`
- `serena.fallbackToNative = true`

Required guardrails:
- strict tenant path boundary checks on all code-intel inputs and outputs
- per-tenant workspace roots with no cross-tenant file access
- audit logging on each Serena-backed operation

If Serena endpoint is unavailable, runtime falls back to native code-intel tools for continuity.

## 4. Model Runtime Policy

Phase 1 policy is fixed primary model with fallback on hard failures.

```ts
const MODEL_POLICY = {
  mode: 'fixed_primary',
  primary: 'anthropic/claude-opus-4.6',
  fallback: ['anthropic/claude-sonnet-4.6', 'openai/gpt-5.2-codex'],
  capabilityCacheTtlMinutes: 360,
} as const;
```

Notes:
- Dynamic per-turn routing is intentionally deferred.
- Capability discovery remains mandatory despite fixed model policy.

## 5. Prediction-Convergence Loop

Prediction loop remains core learning signal, with one addition:
- Context/retrieval execution metrics now join prediction metrics as policy-update inputs.

Update inputs include:
- Brier/BSS/ECE trends
- retrieval precision@k
- escalation rate (`rg -uuu` fallback frequency)
- sub-agent completion reliability and latency

## 6. Sub-Agent Protocol (Asynchronous, Observable)

Sub-agents are asynchronous by default.
Parent does not block and can continue primary work while receiving progress updates.

### 6.1 Task Contract

```ts
interface SubAgentTask {
  taskId: string;
  idempotencyKey: string;
  goal: string;
  doneWhen: string[];
  inputContextRefs: string[];
  outputSchema: Record<string, unknown>;
  priority: 'low' | 'normal' | 'high';
  runTimeoutSeconds: number;
  cleanup: 'keep' | 'archive';
}
```

### 6.2 Lifecycle

`accepted -> in_progress -> blocked | failed | timed_out | completed`

### 6.3 Parent/Sub-Agent Interaction

- Spawn returns immediately with `runId` and `ticketId`.
- Parent receives event-stream updates and may poll status.
- Sub-agent emits checkpoints with progress and intermediate artifacts.
- Completion emits announce event with status, summary, runtime stats.

### 6.4 Shared Working Memory Writes

Sub-agents may write shared working memory, but every write must include:
- `writer_agent_id`
- `ticket_id`
- `timestamp`
- `confidence`
- `scope`: `scratch | proposal | committed`

Parent may promote `proposal -> committed` during merge/review.

### 6.5 Reliability Rules

- Idempotency key prevents duplicate runs.
- Announce uses retry + exponential backoff.
- Cascade stop: parent stop stops descendant runs.
- Max spawn depth default `1`; optional depth `2` orchestrator mode.

## 7. Admission Control and Loop Safety

No cost budget gate in phase 1, but runtime safety limits are mandatory.

```json
{
  "maxConcurrentSubagents": 8,
  "maxChildrenPerParent": 5,
  "maxSpawnDepth": 1,
  "toolLoopDetection": {
    "enabled": true,
    "historySize": 20,
    "repeatThreshold": 3,
    "criticalThreshold": 6,
    "detectorCooldownMs": 12000
  }
}
```

## 8. Runtime Adaptation Layer (New)

The runtime self-improves by updating execution policy, not by gradient training.

### 8.1 Adaptable Policies

- context packing policy
- retrieval ranking/threshold policy
- sub-agent spawn/admission policy
- procedural strategy weighting

### 8.2 Update Triggers

- sustained prediction calibration drift
- retrieval precision degradation
- repeated loop-detector incidents
- rising sub-agent failure clusters

### 8.3 Update Safeguards

- version every policy change
- rollback on regression detection
- diff summaries for every policy update

## 9. Implementation Milestones (Revised)

### Milestone 1
- Fixed model runtime
- Capability handshake
- Dynamic context assembly engine

### Milestone 2
- Agentic-first search pipeline (`rg` pass + escalation pass)
- Retrieval metrics and auditability

### Milestone 3
- Asynchronous sub-agent protocol
- Event stream and reliability semantics

### Milestone 4
- Memory contradiction archiving and temporal reranking
- Pre-compaction memory flush hardening

### Milestone 5
- Runtime adaptation layer
- Graph-context extension (core phase 2)

## 10. Guardrails and Security

- Autonomy boundaries enforced in orchestrator.
- Tool invocations validated against contract.
- Sub-agents inherit restricted capability envelopes.
- World/policy state versioned and rollbackable.
- External content and tool outputs are bounded and citation-traceable.

## 11. Final Definition of Done (v1.1)

System is considered v1.1-complete when:
- Context assembly is capability-aware and no static `128k` cap exists.
- Search uses two-pass local-first policy with measurable quality metrics.
- Sub-agent protocol supports non-blocking orchestration with progress updates.
- Shared memory writes are metadata-rich and auditable.
- Contradictory memory handling archives older beliefs with provenance.
- Runtime adaptation policies are versioned, measurable, and rollbackable.
