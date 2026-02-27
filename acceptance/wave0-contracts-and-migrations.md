# Wave 0 Acceptance: Contracts + Migrations

Date: February 21, 2026

## Scope

Validate the first implementation package for BOMBA SR v1.1:
- Contract schemas
- Database migrations
- No scaffolding-only deliverables

## Contract Files (must exist and parse)

- `/Users/zidane/Downloads/PROJEKT/contracts/model-capabilities.schema.json`
- `/Users/zidane/Downloads/PROJEKT/contracts/context-assembly-request.schema.json`
- `/Users/zidane/Downloads/PROJEKT/contracts/search-plan.schema.json`
- `/Users/zidane/Downloads/PROJEKT/contracts/search-result-pack.schema.json`
- `/Users/zidane/Downloads/PROJEKT/contracts/subagent-task.schema.json`
- `/Users/zidane/Downloads/PROJEKT/contracts/subagent-event.schema.json`
- `/Users/zidane/Downloads/PROJEKT/contracts/shared-memory-write.schema.json`
- `/Users/zidane/Downloads/PROJEKT/contracts/runtime-metrics.schema.json`

## Migration Files (must exist and apply)

- `/Users/zidane/Downloads/PROJEKT/sql/migrations/005_runtime_policy.sql`
- `/Users/zidane/Downloads/PROJEKT/sql/migrations/006_subagent_protocol.sql`

## Test Matrix

## T1 JSON Parse Check

Method:
- Run `jq empty` for each schema file.

Pass:
- All schema files parse with no syntax errors.

## T2 Schema Contract Completeness

Method:
- Verify required fields for each critical contract:
  - model capabilities: context and completion limits
  - context request: turn profile and inputs
  - search plan/result: pass/escalation semantics
  - sub-agent task/event: lifecycle semantics
  - shared write: metadata and scope

Pass:
- No missing required field from v1.1 locked decisions.

## T3 SQL Parse Check

Method:
- Run migration SQL through Postgres parser during migration run.

Pass:
- DDL compiles without syntax errors.

## T4 Constraint Check (Manual + Migration Test)

Method:
- Validate constraints exist for:
  - sub-agent status enum check
  - idempotency uniqueness `(parent_turn_id, idempotency_key)`
  - confidence range checks `[0,1]`
  - search pass check in `(1,2)`

Pass:
- Constraints are present in migration files and apply to DB.

## T5 No-Scaffolding Rule

Method:
- Inspect artifacts for placeholder-only files and TODO-only content.

Pass:
- Every artifact contains enforceable schema or executable DDL.

## Exit Criteria

Wave 0 is complete when:
1. T1-T5 pass.
2. Contracts and migrations are approved for implementation lanes A-F.
3. Gate to Wave 1 opened.

