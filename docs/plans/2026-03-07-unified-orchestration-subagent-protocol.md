# Unified Orchestration onto SubAgentProtocol - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace thread-based subtask execution in OrchestrationEngine with SubAgentProtocol spawns, unifying orchestration onto the existing protocol for DB-backed state, crash detection, idempotency, depth enforcement, and cascade stop.

**Architecture:** OrchestrationEngine gets a reference to SubAgentOrchestrator (which wraps SubAgentProtocol). _execute_subtask uses spawn_async() instead of direct bridge.handle_turn() calls. _await_run_completion polls the protocol DB. Outputs flow through shared_working_memory_writes (the worker already writes there). _phase_review keeps reading state["subtask_outputs"] (populated post-completion); _phase_synthesize reads from shared memory.

**Tech Stack:** Python 3.11+, SQLite (WAL), pytest, existing SubAgentProtocol/Orchestrator/WorkerFactory

---

### Task 1: Add SubAgentOrchestrator to OrchestrationEngine.__init__

**Files:**
- Modify: `src/bomba_sr/orchestration/engine.py:13-283`

**Step 1: Add imports**

Add `import time` and subagent imports to engine.py.

**Step 2: Modify __init__ signature**

Add optional `subagent_orchestrator` parameter. After schema setup, resolve from bridge if not provided. Store as `self.subagent_orch` and `self.protocol`.

**Step 3: Run existing tests to verify no breakage**

Run: `PYTHONPATH=src python3 -m pytest tests/test_orchestration_engine.py -v`
Expected: All existing tests pass (they pass None for subagent_orchestrator)

**Step 4: Commit**

```bash
git add src/bomba_sr/orchestration/engine.py
git commit -m "feat(orch): accept SubAgentOrchestrator in OrchestrationEngine.__init__"
```

---

### Task 2: Extract _build_delegation_message

**Files:**
- Modify: `src/bomba_sr/orchestration/engine.py` (lines 631-687)

**Step 1: Create _build_delegation_message method**

Extract the delegation message construction (ACT-I identity prefix, context section, task title, instructions, acceptance criteria) from _execute_subtask into a standalone method. Keep exact same message format.

**Step 2: Run tests**

Run: `PYTHONPATH=src python3 -m pytest tests/test_orchestration_engine.py -v`
Expected: PASS

---

### Task 3: Replace _execute_subtask with SubAgentProtocol spawn

**Files:**
- Modify: `src/bomba_sr/orchestration/engine.py`

**Step 1: Rewrite _execute_subtask**

New flow: resolve being info, build delegation message via _build_delegation_message, create SubAgentTask, call self.subagent_orch.spawn_async(), store run_id in subtask_ids, return run_id.

**Step 2: Add _on_subtask_completed helper**

Reads output from shared_working_memory_writes, restores being status, populates state["subtask_outputs"] (for _phase_review compat), writes semantic memory, logs events.

---

### Task 4: Replace _phase_delegate thread management

**Files:**
- Modify: `src/bomba_sr/orchestration/engine.py`

**Step 1: Rewrite _phase_delegate**

Sequential: spawn -> await -> _on_subtask_completed -> next.
Parallel: spawn all -> await all -> _on_subtask_completed for each.

**Step 2: Add _await_run_completion**

Poll protocol.get_run() until status is terminal or timeout. On timeout, call protocol.cascade_stop().

---

### Task 5: Replace _collect_prior_outputs with shared memory reads

**Files:**
- Modify: `src/bomba_sr/orchestration/engine.py`

**Step 1: Add _collect_prior_outputs_from_shared_memory**

Read from shared_working_memory_writes filtered by ticket_id and scope="committed".

**Step 2: Delete old _collect_prior_outputs**

Remove the method that reads from state["subtask_outputs"].

---

### Task 6: Update _phase_synthesize to read from shared memory

**Files:**
- Modify: `src/bomba_sr/orchestration/engine.py` (lines 870-882)

**Step 1: Replace output reading**

Change `raw_outputs = dict(state["subtask_outputs"])` to read from `self.protocol.read_shared_memory(ticket_id=task_id, scope="committed")`.

---

### Task 7: Write new tests

**Files:**
- Create: `tests/test_orchestration_subagent.py`

8 tests covering: spawn via protocol, idempotency, parallel spawns, sequential await ordering, prior outputs from shared memory, synthesis from shared memory, timeout cascade stop, failed subtask handling.

---

### Task 8: Update existing tests

**Files:**
- Modify: `tests/test_orchestration_engine.py`
- Modify: `tests/test_hardening_verification.py`
- Modify: `tests/test_orchestration_persistence.py`
- Modify: `tests/test_e2e_memory_architecture.py`

Update all OrchestrationEngine() constructor calls to work with the new optional parameter.

---

### Task 9: Run full test suite and commit

Run: `PYTHONPATH=src python3 -m pytest tests/ -v`
Commit: `feat: unify orchestration execution onto SubAgentProtocol`
