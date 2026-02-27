# 07. Documentation-Driven Development (DDD) Workflow

This repository now follows documentation-driven development as default.

## Rule
No implementation starts before behavior is documented and approved.

## Required Sequence for Every Feature
1. **Problem framing doc**
- user problem
- constraints
- non-goals
- success criteria

2. **Behavior contract doc**
- exact behavior in normal path
- error handling behavior
- approval/governance behavior
- persistence side effects
- telemetry emitted

3. **Interface doc updates**
- config/env vars
- CLI/API signatures
- schema changes (if any)

4. **Review and explicit sign-off**
- reviewer confirms behavior contract

5. **Implementation**
- code changes aligned to approved docs only

6. **Verification evidence**
- test additions/updates
- command outputs (summarized)
- migration notes

7. **Post-implementation doc sync**
- reflect any deviations discovered during coding

## PR/Merge Checklist
- [ ] Docs added/updated before code
- [ ] API docs updated
- [ ] Config docs updated
- [ ] Component docs updated
- [ ] Tests updated and passing
- [ ] Risk/approval impact documented
- [ ] Telemetry impact documented

## Documentation Granularity Standard
For each new component/functionality, docs must include:
- purpose
- input/output contract
- operational constraints
- failure modes
- approval requirements
- observability and telemetry points

## Change Types and Required Docs

### New Tool
Must update:
- `docs/06-components-reference.md`
- `docs/03-config-reference.md` (if env-configured)
- `docs/05-http-api-reference.md` or CLI docs if exposed
- governance note (risk/action type)

### New Skill/Ecosystem Behavior
Must update:
- `docs/02-architecture.md`
- `docs/04-cli-reference.md`
- `docs/05-http-api-reference.md`
- `docs/06-components-reference.md`

### Runtime Loop/Governance Change
Must update:
- `docs/02-architecture.md`
- `docs/03-config-reference.md`
- `docs/06-components-reference.md`

## Versioning and Changelog Discipline
- Keep docs in sync in same commit as behavior changes.
- Do not defer documentation to follow-up unless explicitly approved.
- If behavior diverges from prior docs, mark migration notes immediately.

## Review Template (use in design reviews)
1. What exact user-visible behavior changes?
2. What approvals/governance paths change?
3. What new data is persisted?
4. What telemetry is emitted?
5. What are rollback/disable controls?

## For This Repository Specifically
Before future implementation phases, submit:
- one short "Behavior Spec" markdown for that phase
- exact API/CLI/config diff in docs
- acceptance test matrix

Only then proceed with code.
