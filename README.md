# BOMBA SR Runtime (v1.1+)

Local-first, multi-tenant runtime for chat/coding agents with:
- Capability-aware context assembly (no fixed 128k assumptions)
- Agentic-first local search (`rg` two-pass)
- Hybrid memory (markdown + DB long-term + optional OpenAI embeddings)
- Confidence-gated learning (`>=0.4` auto-apply, `<0.4` approval queue)
- Async sub-agent protocol with event streaming + shared-memory writes
- Runtime adaptation metrics + policy versioning/rollback
- Serena-first code intelligence (enabled by default, edit tools enabled immediately)
- Skill runtime (register/list/execute skill manifests)
- Tool governance (risk + confidence policy, approval queue, audit trail)
- Project/task domain model with artifact linkage
- Generic information mode (optional citation snippets via Wikipedia retriever)
- User identity profile learning with pending signal approvals

## Documentation (Primary Entry)

Use the docs index first:

- `docs/README.md`

Key references:
- `docs/02-architecture.md`
- `docs/03-config-reference.md`
- `docs/04-cli-reference.md`
- `docs/05-http-api-reference.md`
- `docs/06-components-reference.md`
- `docs/07-ddd-workflow.md`

## Install / Run Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Chat CLI (user-style runtime test)

```bash
PYTHONPATH=src python3 scripts/run_chat_cli.py \
  --tenant-id tenant-local \
  --user-id user-local \
  --workspace /absolute/path/to/project
```

## HTTP Runtime Server (for web chat / integrations)

```bash
PYTHONPATH=src python3 scripts/run_runtime_server.py --host 127.0.0.1 --port 8787
```

Example chat request:

```bash
curl -s http://127.0.0.1:8787/chat \
  -H 'content-type: application/json' \
  -d '{
    "tenant_id":"tenant-local",
    "session_id":"sess-1",
    "user_id":"user-local",
    "workspace_root":"/absolute/path/to/project",
    "message":"I prefer Neovim. help me refactor parser"
  }' | jq
```

## Product APIs

- Chat/runtime:
  - `POST /chat`
  - `GET /artifacts`
- Code tools + governance:
  - `POST /codeintel`
  - `GET /approvals`
  - `POST /approvals/decide`
- Skills:
  - `POST /skills/register`
  - `GET /skills`
  - `POST /skills/execute`
  - `GET /skills/executions`
  - `GET /skills/catalog`
  - `GET /skills/diagnostics`
  - `GET /skills/install-requests`
  - `POST /skills/install-request`
  - `POST /skills/install`
  - `GET /skills/source-trust`
  - `POST /skills/source-trust`
  - `GET /skills/telemetry`
- Projects/tasks:
  - `POST /projects`
  - `GET /projects`
  - `POST /tasks`
  - `GET /tasks`
  - `POST /tasks/update`
- Identity/profile:
  - `GET /profile`
  - `GET /profile/signals`
  - `POST /profile/signals/decide`
- Sub-agents:
  - `POST /subagents/spawn`
  - `GET /subagents/events`

## Serena Defaults

Runtime defaults (from `RuntimeConfig`):
- `serena.enabled = true`
- `serena.edit_tools_enabled = true`
- `serena.fallback_to_native = true`

If Serena is reachable (`SERENA_BASE_URL`), tool calls use Serena first.
If not reachable, runtime falls back to native code-intel tools unless fallback is disabled.

## Environment

Use `.env.example` as the baseline. Key vars:
- Provider keys: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` or `OPENROUTER_API_KEY`
- Serena: `SERENA_BASE_URL`, `SERENA_API_KEY`, `SERENA_FALLBACK_TO_NATIVE`
- Runtime: `BOMBA_RUNTIME_HOME`, `BOMBA_MODEL_ID`, `BOMBA_LEARNING_AUTO_APPLY_CONFIDENCE`, `BOMBA_GENERIC_INFO_WEB_RETRIEVAL`
