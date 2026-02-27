# Research Notes: Agentic Memory, Search, and Runtime Patterns

Date: February 21, 2026

## OpenRouter Capability Reality Check

Observed from `/api/v1/models` on Feb 21, 2026:
- `anthropic/claude-opus-4.6`: context 1,000,000; max completion 128,000
- `anthropic/claude-sonnet-4.6`: context 1,000,000; max completion 128,000
- `openai/gpt-5.2-codex`: context 400,000; max completion 128,000
- `google/gemini-3.1-pro-preview`: context 1,048,576; max completion 65,536
- `x-ai/grok-4.1-fast`: context 2,000,000; max completion 30,000

Implication:
- fixed `128k` input assumptions are outdated; runtime capability discovery is required.

## OpenClaw / Clawdbot Patterns Worth Reusing

1. Memory as durable files + indexed retrieval
- Memory docs describe Markdown files as source of truth and retrieval via `memory_search`/`memory_get`.

2. Mandatory recall behavior
- `memory_search` tool description enforces recall before answering history-dependent questions.

3. Pre-compaction memory flush
- OpenClaw performs a silent turn near compaction threshold to persist durable memory.

4. Sub-agent semantics
- Sub-agents run asynchronously, return run IDs immediately, and announce back on completion.
- Depth and concurrency controls are explicit (`maxSpawnDepth`, `maxConcurrent`, `maxChildrenPerAgent`).

5. Loop safety
- Loop detection policy exists as configurable runtime guardrail.

## Community Plugin Ideas (use with validation)

From OpenClaw continuity/stability plugin READMEs:
- Temporal reranking for memory recall helps corrections outrank stale statements.
- Meta-memory noise filtering reduces retrieval pollution.
- Identity-level memory instructions in AGENTS.md can materially change recall behavior.
- Stability hooks can add entropy/drift/loop awareness signals.

Caution:
- These are promising patterns, but not core platform guarantees. Treat as optional features until validated in your stack.

## GitNexus Patterns Worth Reusing

1. Precompute architecture graph (not query-time rediscovery only)
2. Provide structured tools like impact/context/query instead of raw text retrieval alone
3. Keep index local and persistent
4. Feed citation-rich structural context back into agent loop

Caution:
- License is PolyForm Noncommercial; do not copy implementation directly into commercial paths.
- Use architectural ideas, not licensed code, unless licensing is acceptable.

## Agentic-First Search Recommendation

Default strategy:
1. `rg --files` inventory
2. `rg` scoped search (ignore-aware)
3. typed refinement (`-t`)
4. `rg -uuu` only on miss/low-confidence

Reason:
- best practical speed/relevance tradeoff and lower context noise.

