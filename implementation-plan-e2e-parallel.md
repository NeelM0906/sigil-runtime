# BOMBA SR v1.1 End-to-End Implementation Plan (Parallel)

Date: February 21, 2026
Spec baseline: `/Users/zidane/Downloads/PROJEKT/bomba-sr-spec-v1.1.md`
Execution mode: Parallel workstreams with strict integration gates
Rule: No scaffolding code. Every task must produce runnable behavior, schema, migration, or test.

## 1. Objectives

1. Ship v1.1 runtime behavior with measurable improvements over v1.0 assumptions.
2. Eliminate static context assumptions and move to capability-aware context packing.
3. Implement non-blocking sub-agent orchestration with auditable shared-memory writes.
4. Make local-first retrieval deterministic, testable, and quality-scored.
5. Install runtime adaptation hooks and policy versioning.

## 2. Execution Model

Work proceeds in parallel lanes. Integration happens only at gate checkpoints.

### Lanes

- Lane A: Substrate + Model Capability Handshake
- Lane B: Context Policy Engine + Compaction/Flush
- Lane C: Agentic-First Search (`rg` pipeline + escalation)
- Lane D: Memory Consolidation (contradictions, rerank, archival)
- Lane E: Sub-Agent Protocol + Event Stream + Admission Control
- Lane F: Observability + Evaluation + Runtime Adaptation

## 3. Dependency Graph

### Hard dependencies

- B depends on A capability metadata.
- C can start independently, integrates with B for context packing.
- D can start independently, integrates with B and F metrics.
- E can start independently, integrates with B (context refs) and F (telemetry).
- F starts immediately for metric schema, full dashboards after B/C/E.

### Integration gates

- Gate G1: A + B + C contract compatibility
- Gate G2: D + B memory packaging correctness
- Gate G3: E + F run/event telemetry correctness
- Gate G4: End-to-end regression and acceptance checks

## 4. Wave Plan

## Wave 0 (Day 0-1): Contract Freeze

Deliverables:
- JSON schemas for model capabilities, context requests, search plans, sub-agent tasks/events, shared-memory writes
- SQL migrations for runtime tables and sub-agent lifecycle tables
- Acceptance criteria document

Exit criteria:
- Contracts validated and reviewed
- Migrations apply cleanly
- No placeholder modules or TODO-only files

## Wave 1 (Day 1-4): Runtime Core

Lane A:
- Implement model capability fetch/cache path
- Add TTL refresh and fallback behavior

Lane B:
- Implement dynamic context budget calculator
- Implement turn-profile selection
- Implement compression invariants and pre-compaction flush trigger

Lane C:
- Implement two-pass search executor
- Implement miss/low-confidence escalation policy
- Return structured retrieval packs with citations

Exit criteria:
- Gate G1 passes with compatibility and basic e2e run

## Wave 2 (Day 4-8): Orchestration + Memory

Lane D:
- Implement contradiction archival and temporal rerank
- Apply anti-noise filters in recall path

Lane E:
- Implement sub-agent task contract enforcement
- Add idempotent spawn, lifecycle transitions, progress events
- Add shared-memory write metadata contract and parent merge policy
- Add cascade stop and retrying announce path

Exit criteria:
- Gate G2 and G3 pass

## Wave 3 (Day 8-12): Adaptation + Hardening

Lane F:
- Implement metric aggregation for prediction + retrieval + sub-agent reliability
- Implement policy versioning, diff logs, rollback mechanism

Cross-lane:
- Reliability hardening
- Failure-injection tests
- Latency and throughput tuning

Exit criteria:
- Gate G4 passes and v1.1 DoD is met

## 5. Parallel Task Breakdown (Immediate)

### A1 (Parallel)
- Create capability schema and persistence migration.

### B1 (Parallel)
- Create context assembly contract and compaction invariants contract.

### C1 (Parallel)
- Create search plan/result contract and escalation policy specification.

### D1 (Parallel)
- Create memory contradiction archival schema and retrieval ranking inputs.

### E1 (Parallel)
- Create sub-agent task/event/write contracts + SQL lifecycle tables.

### F1 (Parallel)
- Create metrics schema for retrieval/sub-agent/runtime adaptation signals.

## 6. Quality Gates

Each lane must provide:
- Schema or migration changes
- Runtime behavior definition
- Automated acceptance checks
- Observability fields

No lane can merge code that only stubs interfaces without behavior.

## 7. Acceptance Criteria (Top-Level)

1. Capability-aware context uses model metadata at runtime.
2. No static 128k context assumptions remain.
3. Search pipeline uses two-pass policy with explicit escalation criteria.
4. Sub-agent protocol is asynchronous, idempotent, and observable.
5. Shared-memory writes are metadata-rich and auditable.
6. Contradiction handling archives old beliefs and promotes latest evidence-backed beliefs.
7. Policy changes are versioned and rollbackable.

## 8. What Is Already Started

Completed now:
- v1.1 finalized spec document
- v1.1 parallel implementation plan document

In progress now:
- Wave 0 contract package (schemas + migrations + acceptance checks)

