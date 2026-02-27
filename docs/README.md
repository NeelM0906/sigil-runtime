# SIGIL / BOMBA SR Documentation

This documentation set is the source of truth for the current runtime behavior and is intended to support documentation-driven development.

## Audience
- Runtime developers
- Plugin/skill authors
- Infrastructure and operations engineers
- Product engineers integrating CLI/web chat

## Documentation Map
1. [`docs/01-overview.md`](./01-overview.md)
- What SIGIL is, what problems it solves, core capabilities, and design goals.

2. [`docs/02-architecture.md`](./02-architecture.md)
- End-to-end architecture, runtime flow, multi-tenant model, and subsystem interactions.

3. [`docs/03-config-reference.md`](./03-config-reference.md)
- Complete environment variable and runtime config reference.

4. [`docs/04-cli-reference.md`](./04-cli-reference.md)
- Full interactive CLI usage, commands, and user-test flows.

5. [`docs/05-http-api-reference.md`](./05-http-api-reference.md)
- HTTP runtime server endpoints, request/response semantics.

6. [`docs/06-components-reference.md`](./06-components-reference.md)
- Component-by-component technical reference across `src/bomba_sr` and scripts.

7. [`docs/07-ddd-workflow.md`](./07-ddd-workflow.md)
- Documentation-driven development process to be followed going forward.

## Current Version Scope
This reflects the repository state as of the latest passing test run (`100 passed`).

## Change Management Rule (DDD)
For any new feature/change:
1. Update/add docs first (behavior contract, API, config, failure modes).
2. Review docs and approve behavior.
3. Implement code.
4. Update docs with final implementation notes.
