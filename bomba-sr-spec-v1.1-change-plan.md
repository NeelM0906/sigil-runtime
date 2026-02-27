# BOMBA SR Spec v1.1 Change Plan (Draft)

Date: February 21, 2026
Source spec: `/Users/zidane/Downloads/bomba-sr-spec.docx`

## Decisions Locked (from Neel)

1. Optimize for performance during development. Cost is not a gating factor.
2. Use a fixed primary model for now.
3. Parent agent should continue its own tasks while receiving sub-agent updates.
4. No hard budget constraints for now.
5. Sub-agents may write to shared working memory.
6. Need a recommended default for search strategy.
7. Contradictory memories are archived (not deleted).
8. No provider-specific routing constraints in phase 1.

## Core Critique of Current Spec

### 1) Fixed `128k` context cap is now structurally wrong

Current section `3.4` hardcodes:
- `MAX_CONTEXT = 128_000`

As of **February 21, 2026**, OpenRouter model metadata shows materially larger windows on common models. Examples:
- `anthropic/claude-opus-4.6`: 1,000,000 context
- `anthropic/claude-sonnet-4.6`: 1,000,000 context
- `openai/gpt-5.2-codex`: 400,000 context
- `google/gemini-3.1-pro-preview`: 1,048,576 context

Impact:
- You are under-utilizing available context on your fixed model.
- You also risk breakage if model-specific output limits differ from your static assumptions.

### 2) Context percentages are too rigid

Current assembly is fixed percentages by tier. This fails in at least 3 cases:
- Heavy tool-output turns
- Planning vs execution turns
- Memory-intensive recall turns

Needs a policy engine with per-turn profile selection, not fixed ratios.

### 3) Sub-agent model lacks production-grade run semantics

Current `10.2` spawn flow is clean but underspecified for runtime safety and observability:
- no idempotency key
- no explicit timeout/cancellation contract
- no progress event schema
- no merge protocol for shared working memory writes
- no announce retry/fallback chain

### 4) Agentic-first search is not specified enough

The spec mentions tools but does not define a deterministic local-code retrieval pipeline.
For a self-improving runtime, this must be explicit and measured.

## Recommended Policy for #6 (Search Strategy)

Use a **two-pass default**:

1. Pass A (default): ignore-aware `rg` search
- honors `.gitignore`
- scoped by file type and directories
- fastest path to high-signal results

2. Pass B (escalation): `rg -uuu` only when confidence is low
- include ignored + hidden + binary candidates
- only after explicit miss criteria are hit

Why this is optimal for your goals:
- best latency and relevance in normal coding workflows
- avoids noisy retrieval poisoning the context
- still guarantees broader recall when needed

## Drop-in Spec Replacements

## Replace Section 3.4 with: Dynamic Context Assembly

### 3.4 Context Assembly (Dynamic, Capability-Aware)

On every interaction, the Context Manager assembles an optimized context window using model capabilities discovered at runtime.

#### Runtime capability handshake

Before first turn per session (and every 6h cache refresh), fetch model metadata:
- `context_length`
- `top_provider.max_completion_tokens`
- supported response/tool parameters

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

#### Context budget calculation

```ts
const cap = capabilities.contextLength;
const reservedOutput = Math.min(32_000, Math.floor(cap * 0.20));
const reservedSafety = Math.max(2_000, Math.floor(cap * 0.03));
const availableInput = cap - reservedOutput - reservedSafety;
```

Notes:
- No fixed `128k` default.
- Output reserve scales with model capability.
- Safety reserve protects against tokenizer variance and tool-schema overhead.

#### Turn profiles (policy-driven)

```ts
type TurnProfile = 'chat' | 'task_execution' | 'planning' | 'memory_recall' | 'subagent_orchestration';
```

Each profile has its own tier weights and hard floors.

#### Inclusion order (must-keep first)

1. System prompt + ACTi contract (required)
2. User message + immediate tool state (required)
3. Active plan + task state (required for task/planning profiles)
4. Working memory (bounded, recency-first)
5. World state (field-level include, not full dump)
6. Semantic memory recall set (reranked)
7. Recent history (compressed summaries + last raw turns)
8. Procedural memory (only selected strategies)
9. Pending predictions (only actionable ones)

#### Compression invariants

Compression order remains `summarize > truncate > drop` with hard invariants:
- Never drop explicit user constraints from the current session.
- Never summarize tool outputs without preserving source references.
- Never keep contradictory memories without explicit recency labeling.

#### Pre-compaction memory flush

When token estimate crosses soft threshold, run silent memory flush:
- persist durable facts/decisions before compaction
- no user-visible reply by default

## Add New Section 3.5: Agentic-First Search (Local First)

### 3.5 Agentic-First Search (Local-First Retrieval Contract)

Local code retrieval is a first-class runtime primitive.

#### Search contract

```ts
interface SearchPlan {
  query: string;
  intent: 'symbol_lookup' | 'flow_trace' | 'config_lookup' | 'test_lookup' | 'broad_discovery';
  scope: string[];             // directories
  fileTypes: string[];         // ts, py, md, sql, etc.
  escalationAllowed: boolean;  // allow -uuu pass
}
```

#### Execution pipeline

1. File inventory
```bash
rg --files
```

2. Scoped search (default)
```bash
rg -n --hidden -g '!.git' -g '!node_modules' '<pattern>' <scopes>
```

3. Typed refinement
```bash
rg -n -t<type> '<pattern>' <scopes>
```

4. Escalation on miss (only if needed)
```bash
rg -uuu -n '<pattern>' <scopes>
```

5. Structured retrieval pack
- return file paths + line refs + confidence
- include why each result was selected

#### Miss criteria for escalation

Escalate from Pass A to Pass B when one of:
- zero matches on high-confidence query
- only matches from low-value files (generated/vendor)
- contradiction with known symbols from recent turns

#### Quality metrics

Track per session:
- retrieval precision@k
- escalation rate
- false-negative rate discovered during execution

## Replace Section 7 with: Fixed Model + Capability Handshake

### 7. Model Runtime Policy (Phase 1: Fixed Primary Model)

Phase 1 uses one fixed primary model for all turn types.

Recommended default (performance-first):
- `anthropic/claude-opus-4.6`

Fallbacks are only for hard failures (provider outage, malformed response, timeout).

#### Runtime policy

```ts
const PRIMARY_MODEL = 'anthropic/claude-opus-4.6';

interface ModelRunPolicy {
  mode: 'fixed_primary';
  primary: string;
  fallback: string[]; // used only on hard failure
  capabilityCacheTtlMinutes: number;
}
```

#### Why fixed now

- Simplifies debugging while architecture is evolving.
- Removes routing variance from quality analysis.
- Keeps memory/prediction behavior attributable to one model.

#### Capability discovery remains mandatory

Even with fixed model, fetch capabilities at runtime from model metadata:
- context window
- max completion tokens
- tool/json compatibility

## Replace Section 10.2 with: Async Sub-Agent Protocol

### 10.2 Sub-Agent Spawning (Asynchronous, Observable)

Sub-agents run asynchronously and do not block parent progress.
Parent receives progress updates via event stream and shared memory checkpoints.

#### Task contract

```ts
interface SubAgentTask {
  taskId: string;                // UUID
  idempotencyKey: string;        // parentTurnId + normalized task hash
  goal: string;
  doneWhen: string[];            // acceptance criteria
  inputContextRefs: string[];    // memory/interaction IDs
  outputSchema: object;
  priority: 'low' | 'normal' | 'high';
  runTimeoutSeconds: number;
  cleanup: 'keep' | 'archive';
}
```

#### Run lifecycle

`accepted -> in_progress -> blocked|failed|timed_out|completed`

#### Parent/sub-agent interaction

- Spawn returns immediately with `runId` + `ticketId`.
- Parent continues execution and can poll or subscribe to updates.
- Sub-agent emits progress checkpoints (`0-100%`, summary, artifacts).
- On completion, sub-agent sends announce event with status + result summary + runtime stats.

#### Shared working memory writes

Sub-agents may write shared working memory, but writes must include:
- `writer_agent_id`
- `ticket_id`
- `timestamp`
- `confidence`
- `scope` (`scratch` | `proposal` | `committed`)

Parent may promote `proposal -> committed` during merge.

#### Reliability requirements

- Stable idempotency key prevents duplicate spawns.
- Announce uses retry with exponential backoff.
- Cascade stop: stopping parent stops descendants.
- Max spawn depth configurable (default 1, optional 2 for orchestrator pattern).

## Add New Section 10.3: Spawn Admission + Loop Safety

### 10.3 Spawn Admission Control and Loop Safety

Even without cost budgets, runtime safety requires admission control.

#### Controls

- `maxConcurrentSubagents` (global)
- `maxChildrenPerParent`
- `maxSpawnDepth`
- `toolLoopDetection` (repeated call patterns)
- `cooldownMs` after loop detection

#### Default values (phase 1)

```json
{
  "maxConcurrentSubagents": 8,
  "maxChildrenPerParent": 5,
  "maxSpawnDepth": 1,
  "toolLoopDetection": {
    "enabled": true,
    "repeatThreshold": 3,
    "criticalThreshold": 6,
    "historySize": 20
  }
}
```

## Memory System Adjustments

Keep four-tier architecture, but add:

1. Contradiction archive contract
- contradictions are archived, not deleted
- new belief promoted with recency + evidence references

2. Retrieval anti-noise filter
- downrank meta-memory chatter ("do you remember", "I don't recall")
- up-rank substantive exchanges

3. Temporal rerank
- blend semantic relevance with recency half-life

## Self-Improving Runtime Layer (New framing)

Shift framing from "assistant with memory" to "runtime that learns execution policy":

- Tool outcomes become first-class learning events.
- Context assembly policy is updated from retrieval/quality metrics.
- Memory and orchestration policies are hook-driven and testable.
- Runtime state is explicit, inspectable, and versioned.

Suggested new subsection title:
- `2.3 Runtime Adaptation Layer (Policy + Hooks + Metrics)`

## What We Should Carry From OpenClaw/Clawdbot

1. Markdown memory as human-auditable source of truth plus indexed recall.
2. Mandatory memory recall step before answering history-dependent questions.
3. Pre-compaction silent memory flush to preserve durable context.
4. Non-blocking sub-agent runs with explicit announce-back semantics.
5. Sub-agent session isolation + depth-limited orchestration.
6. Tool-loop detection guardrails as runtime policy, not prompt text.
7. Hook-based runtime extension points (`before_prompt`, `before/after_tool_call`, `before_compaction`, `agent_end`).

## What We Should Carry From GitNexus

1. Precompute architecture context (dependency/call graph) instead of asking LLM to rediscover it every turn.
2. Expose structural retrieval primitives (impact/context/process) as tools.
3. Keep index local and persistent for low-latency retrieval.
4. Feed retrieval outputs as structured, citation-rich context blocks.

## Remaining Inputs Needed From You Before I Produce v1.1 Final Spec

1. Confirm fixed primary model id for phase 1:
- `anthropic/claude-opus-4.6` (recommended)
- `openai/gpt-5.2-codex`
- other

2. Confirm default sub-agent depth:
- `1` (recommended for now)
- `2` (orchestrator mode)

3. Confirm escalation threshold for `rg -uuu`:
- strict (only zero results)
- balanced (recommended: zero results or low-confidence hits)
- aggressive (escalate often)

4. Confirm whether we add graph indexing in phase 1 or phase 2:
- phase 1 optional plugin
- phase 2 core

