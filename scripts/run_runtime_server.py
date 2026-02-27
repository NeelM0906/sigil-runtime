#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from bomba_sr.context.policy import TurnProfile
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest
from bomba_sr.subagents.protocol import SubAgentTask


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BOMBA runtime HTTP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    return parser.parse_args()


def _default_subagent_worker(run_id: str, task: SubAgentTask, protocol) -> dict:
    protocol.progress(run_id, 25, summary="Sub-agent booted")
    time.sleep(0.02)
    protocol.progress(run_id, 70, summary="Sub-agent processing")
    write_id = protocol.write_shared_memory(
        run_id=run_id,
        writer_agent_id=str(uuid.uuid4()),
        ticket_id=task.ticket_id,
        scope="proposal",
        confidence=0.82,
        content=f"Sub-agent summary for goal: {task.goal}",
        source_refs=[task.task_id],
    )
    protocol.promote_shared_write(write_id, merged_by_agent_id=str(uuid.uuid4()))
    return {
        "summary": "Sub-agent completed default worker",
        "artifacts": {"note": "default-subagent-worker"},
        "runtime_ms": 20,
        "token_usage": {"input": 64, "output": 22, "total": 86},
    }


def make_handler(bridge: RuntimeBridge):
    class Handler(BaseHTTPRequestHandler):
        def _read_json(self) -> dict:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length) if content_length else b"{}"
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._write(400, {"error": "invalid_json"})
                raise

        def _write(self, status: int, payload: dict | list) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/chat":
                self._chat()
                return
            if parsed.path == "/codeintel":
                self._codeintel()
                return
            if parsed.path == "/learning/approve":
                self._approve_learning()
                return
            if parsed.path == "/subagents/spawn":
                self._spawn_subagent()
                return
            if parsed.path == "/skills/register":
                self._register_skill()
                return
            if parsed.path == "/skills/execute":
                self._execute_skill()
                return
            if parsed.path == "/skills/install-request":
                self._create_install_request()
                return
            if parsed.path == "/skills/install":
                self._execute_install_request()
                return
            if parsed.path == "/skills/source-trust":
                self._set_source_trust()
                return
            if parsed.path == "/projects":
                self._create_project()
                return
            if parsed.path == "/tasks":
                self._create_task()
                return
            if parsed.path == "/tasks/update":
                self._update_task()
                return
            if parsed.path == "/approvals/decide":
                self._decide_approval()
                return
            if parsed.path == "/profile/signals/decide":
                self._decide_profile_signal()
                return
            if parsed.path == "/commands/execute":
                self._execute_command()
                return
            self._write(404, {"error": "not_found"})

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/artifacts":
                self._artifacts(parsed)
                return
            if parsed.path == "/subagents/events":
                self._subagent_events(parsed)
                return
            if parsed.path == "/skills":
                self._list_skills(parsed)
                return
            if parsed.path == "/skills/catalog":
                self._list_skill_catalog(parsed)
                return
            if parsed.path == "/skills/diagnostics":
                self._skills_diagnostics(parsed)
                return
            if parsed.path == "/skills/install-requests":
                self._list_install_requests(parsed)
                return
            if parsed.path == "/skills/source-trust":
                self._get_source_trust(parsed)
                return
            if parsed.path == "/skills/telemetry":
                self._list_skill_telemetry(parsed)
                return
            if parsed.path == "/skills/executions":
                self._list_skill_executions(parsed)
                return
            if parsed.path == "/projects":
                self._list_projects(parsed)
                return
            if parsed.path == "/tasks":
                self._list_tasks(parsed)
                return
            if parsed.path == "/approvals":
                self._list_approvals(parsed)
                return
            if parsed.path == "/learning/approvals":
                self._list_learning_approvals(parsed)
                return
            if parsed.path == "/profile":
                self._get_profile(parsed)
                return
            if parsed.path == "/profile/signals":
                self._list_profile_signals(parsed)
                return
            if parsed.path == "/health":
                self._write(200, {"ok": True})
                return
            if parsed.path == "/commands":
                self._list_commands(parsed)
                return
            self._write(404, {"error": "not_found"})

        def _chat(self) -> None:
            body = self._read_json()
            profile = TurnProfile(body.get("profile") or "chat")
            result = bridge.handle_turn(
                TurnRequest(
                    tenant_id=str(body["tenant_id"]),
                    session_id=str(body["session_id"]),
                    user_id=str(body["user_id"]),
                    user_message=str(body["message"]),
                    turn_id=str(body.get("turn_id") or uuid.uuid4()),
                    model_id=(str(body["model_id"]) if body.get("model_id") else None),
                    profile=profile,
                    workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
                    search_query=(str(body["search_query"]) if body.get("search_query") else None),
                    project_id=(str(body["project_id"]) if body.get("project_id") else None),
                    task_id=(str(body["task_id"]) if body.get("task_id") else None),
                )
            )
            self._write(200, result)

        def _codeintel(self) -> None:
            body = self._read_json()
            result = bridge.invoke_code_tool(
                tenant_id=str(body["tenant_id"]),
                tool_name=str(body["tool_name"]),
                arguments=dict(body.get("arguments") or {}),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
                session_id=(str(body["session_id"]) if body.get("session_id") else None),
                turn_id=(str(body["turn_id"]) if body.get("turn_id") else None),
                confidence=float(body.get("confidence") if body.get("confidence") is not None else 1.0),
            )
            self._write(200, result)

        def _approve_learning(self) -> None:
            body = self._read_json()
            result = bridge.approve_learning(
                tenant_id=str(body["tenant_id"]),
                user_id=str(body["user_id"]),
                update_id=str(body["update_id"]),
                approved=bool(body["approved"]),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
            )
            self._write(200, result)

        def _spawn_subagent(self) -> None:
            body = self._read_json()
            task = SubAgentTask(
                tenant_id=str(body["tenant_id"]),
                task_id=str(body.get("task_id") or uuid.uuid4()),
                ticket_id=str(body.get("ticket_id") or uuid.uuid4()),
                idempotency_key=str(body["idempotency_key"]),
                goal=str(body["goal"]),
                done_when=tuple(body.get("done_when") or ["Goal complete"]),
                input_context_refs=tuple(body.get("input_context_refs") or []),
                output_schema=dict(body.get("output_schema") or {"summary": "string"}),
                priority=str(body.get("priority") or "normal"),
                run_timeout_seconds=int(body.get("run_timeout_seconds") or 120),
                cleanup=str(body.get("cleanup") or "keep"),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
                model_id=(str(body["model_id"]) if body.get("model_id") else None),
            )
            handle = bridge.spawn_subagent(
                tenant_id=str(body["tenant_id"]),
                task=task,
                parent_session_id=str(body["parent_session_id"]),
                parent_turn_id=str(body["parent_turn_id"]),
                parent_agent_id=str(body["parent_agent_id"]),
                child_agent_id=str(body["child_agent_id"]),
                worker=_default_subagent_worker,
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
                parent_run_id=(str(body["parent_run_id"]) if body.get("parent_run_id") else None),
            )
            self._write(200, {"run_id": handle.run_id})

        def _register_skill(self) -> None:
            body = self._read_json()
            result = bridge.register_skill(
                tenant_id=str(body["tenant_id"]),
                manifest=dict(body["manifest"]),
                status=str(body.get("status") or "active"),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
            )
            self._write(200, result)

        def _execute_skill(self) -> None:
            body = self._read_json()
            result = bridge.execute_skill(
                tenant_id=str(body["tenant_id"]),
                skill_id=str(body["skill_id"]),
                inputs=dict(body.get("inputs") or {}),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
                session_id=(str(body["session_id"]) if body.get("session_id") else None),
                turn_id=(str(body["turn_id"]) if body.get("turn_id") else None),
                confidence=float(body.get("confidence") if body.get("confidence") is not None else 1.0),
            )
            self._write(200, result)

        def _create_install_request(self) -> None:
            body = self._read_json()
            result = bridge.create_skill_install_request(
                tenant_id=str(body["tenant_id"]),
                user_id=str(body["user_id"]),
                source=str(body["source"]),
                skill_id=str(body["skill_id"]),
                session_id=(str(body["session_id"]) if body.get("session_id") else None),
                turn_id=(str(body["turn_id"]) if body.get("turn_id") else None),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
                reason=(str(body["reason"]) if body.get("reason") else None),
            )
            self._write(200, result)

        def _execute_install_request(self) -> None:
            body = self._read_json()
            result = bridge.execute_skill_install(
                tenant_id=str(body["tenant_id"]),
                request_id=str(body["request_id"]),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
            )
            self._write(200, result)

        def _set_source_trust(self) -> None:
            body = self._read_json()
            result = bridge.set_skill_source_trust(
                tenant_id=str(body["tenant_id"]),
                source=str(body["source"]),
                trust_mode=str(body["trust_mode"]),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
            )
            self._write(200, {"source_trust": result})

        def _create_project(self) -> None:
            body = self._read_json()
            result = bridge.create_project(
                tenant_id=str(body["tenant_id"]),
                name=str(body["name"]),
                workspace_root=str(body["workspace_root"]),
                description=(str(body["description"]) if body.get("description") else None),
                project_id=(str(body["project_id"]) if body.get("project_id") else None),
                status=str(body.get("status") or "active"),
                runtime_workspace_root=(str(body["runtime_workspace_root"]) if body.get("runtime_workspace_root") else None),
            )
            self._write(200, result)

        def _create_task(self) -> None:
            body = self._read_json()
            result = bridge.create_task(
                tenant_id=str(body["tenant_id"]),
                project_id=str(body["project_id"]),
                title=str(body["title"]),
                description=(str(body["description"]) if body.get("description") else None),
                task_id=(str(body["task_id"]) if body.get("task_id") else None),
                status=str(body.get("status") or "todo"),
                priority=str(body.get("priority") or "normal"),
                owner_agent_id=(str(body["owner_agent_id"]) if body.get("owner_agent_id") else None),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
            )
            self._write(200, result)

        def _update_task(self) -> None:
            body = self._read_json()
            result = bridge.update_task(
                tenant_id=str(body["tenant_id"]),
                task_id=str(body["task_id"]),
                status=(str(body["status"]) if body.get("status") else None),
                priority=(str(body["priority"]) if body.get("priority") else None),
                owner_agent_id=(str(body["owner_agent_id"]) if body.get("owner_agent_id") else None),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
            )
            self._write(200, result)

        def _decide_approval(self) -> None:
            body = self._read_json()
            result = bridge.decide_approval(
                tenant_id=str(body["tenant_id"]),
                approval_id=str(body["approval_id"]),
                approved=bool(body["approved"]),
                decided_by=str(body.get("decided_by") or "user"),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
            )
            self._write(200, result)

        def _decide_profile_signal(self) -> None:
            body = self._read_json()
            result = bridge.decide_profile_signal(
                tenant_id=str(body["tenant_id"]),
                user_id=str(body["user_id"]),
                signal_id=str(body["signal_id"]),
                approved=bool(body["approved"]),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
            )
            self._write(200, result)

        def _execute_command(self) -> None:
            body = self._read_json()
            profile = TurnProfile(body.get("profile") or "chat")
            result = bridge.execute_command(
                tenant_id=str(body["tenant_id"]),
                session_id=str(body["session_id"]),
                user_id=str(body["user_id"]),
                command_text=str(body["command"]),
                workspace_root=(str(body["workspace_root"]) if body.get("workspace_root") else None),
                model_id=(str(body["model_id"]) if body.get("model_id") else None),
                profile=profile,
            )
            self._write(200, result)

        def _artifacts(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            session_id = query.get("session_id", [None])[0]
            if not tenant_id or not session_id:
                self._write(400, {"error": "tenant_id and session_id are required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            limit = int(query.get("limit", ["50"])[0])
            artifacts = bridge.list_artifacts(
                tenant_id=tenant_id,
                session_id=session_id,
                workspace_root=workspace_root,
                limit=limit,
            )
            self._write(200, {"artifacts": artifacts})

        def _subagent_events(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            run_id = query.get("run_id", [None])[0]
            if not tenant_id or not run_id:
                self._write(400, {"error": "tenant_id and run_id are required"})
                return
            after_seq = int(query.get("after_seq", ["0"])[0])
            workspace_root = query.get("workspace_root", [None])[0]
            events = bridge.poll_subagent_events(
                tenant_id=tenant_id,
                run_id=run_id,
                after_seq=after_seq,
                workspace_root=workspace_root,
            )
            self._write(200, {"events": events})

        def _list_skills(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            status = query.get("status", [None])[0]
            skills = bridge.list_skills(tenant_id=tenant_id, workspace_root=workspace_root, status=status)
            self._write(200, {"skills": skills})

        def _list_skill_catalog(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            source = query.get("source", [None])[0]
            limit = int(query.get("limit", ["200"])[0])
            skills = bridge.list_skill_catalog(
                tenant_id=tenant_id,
                workspace_root=workspace_root,
                source=source,
                limit=limit,
            )
            self._write(200, {"skills": skills})

        def _skills_diagnostics(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            self._write(200, {"diagnostics": bridge.skill_diagnostics(tenant_id, workspace_root=workspace_root)})

        def _list_install_requests(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            status = query.get("status", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            rows = bridge.list_skill_install_requests(
                tenant_id=tenant_id,
                workspace_root=workspace_root,
                status=status,
                limit=limit,
            )
            self._write(200, {"install_requests": rows})

        def _get_source_trust(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            self._write(200, {"source_trust": bridge.get_skill_source_trust(tenant_id, workspace_root=workspace_root)})

        def _list_skill_telemetry(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            rows = bridge.list_skill_telemetry(tenant_id=tenant_id, workspace_root=workspace_root, limit=limit)
            self._write(200, {"telemetry": rows})

        def _list_skill_executions(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            limit = int(query.get("limit", ["100"])[0])
            items = bridge.list_skill_executions(tenant_id=tenant_id, workspace_root=workspace_root, limit=limit)
            self._write(200, {"executions": items})

        def _list_projects(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            projects = bridge.list_projects(tenant_id=tenant_id, workspace_root=workspace_root)
            self._write(200, {"projects": projects})

        def _list_tasks(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            project_id = query.get("project_id", [None])[0]
            status = query.get("status", [None])[0]
            tasks = bridge.list_tasks(
                tenant_id=tenant_id,
                project_id=project_id,
                status=status,
                workspace_root=workspace_root,
            )
            self._write(200, {"tasks": tasks})

        def _list_approvals(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            items = bridge.list_pending_approvals(tenant_id=tenant_id, workspace_root=workspace_root)
            self._write(200, {"approvals": items})

        def _list_learning_approvals(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            user_id = query.get("user_id", [None])[0]
            if not tenant_id or not user_id:
                self._write(400, {"error": "tenant_id and user_id are required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            items = bridge.list_pending_learning_approvals(
                tenant_id=tenant_id,
                user_id=user_id,
                workspace_root=workspace_root,
            )
            self._write(200, {"approvals": items})

        def _get_profile(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            user_id = query.get("user_id", [None])[0]
            if not tenant_id or not user_id:
                self._write(400, {"error": "tenant_id and user_id are required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            profile = bridge.get_user_profile(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
            self._write(200, {"profile": profile})

        def _list_profile_signals(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            user_id = query.get("user_id", [None])[0]
            if not tenant_id or not user_id:
                self._write(400, {"error": "tenant_id and user_id are required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            items = bridge.list_pending_profile_signals(tenant_id=tenant_id, user_id=user_id, workspace_root=workspace_root)
            self._write(200, {"signals": items})

        def _list_commands(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", [None])[0]
            if not tenant_id:
                self._write(400, {"error": "tenant_id is required"})
                return
            workspace_root = query.get("workspace_root", [None])[0]
            commands = bridge.list_commands(tenant_id=tenant_id, workspace_root=workspace_root)
            self._write(200, {"commands": commands})

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return Handler


def main() -> int:
    args = parse_args()
    bridge = RuntimeBridge()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(bridge))
    print(f"runtime server listening on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
