#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bomba_sr.context.policy import TurnProfile
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest
from bomba_sr.subagents.protocol import SubAgentTask

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIME_WORKSPACE = PROJECT_ROOT / "workspaces" / "prime"


def _load_dotenv(path: Path) -> None:
    """Read .env file into os.environ (does not overwrite existing vars)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw.startswith("export "):
            raw = raw[len("export "):].strip()
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and (key not in os.environ or not os.environ.get(key)):
            os.environ[key] = value

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
}
CORS_ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv("BOMBA_CORS_ALLOWED_ORIGINS", "http://127.0.0.1:8787,http://localhost:8787").split(",")
    if origin.strip()
)


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


def _resolve_sisters_tenant(
    tenant_id: str,
    workspace_root: str | None,
) -> tuple[str, str | None]:
    """Return (tenant_id, workspace_root) that has sisters configured.

    If the caller's workspace already contains a sisters.json, use it as-is.
    Otherwise fall back to the prime workspace (workspaces/prime) where the
    canonical sisters.json lives.
    """
    if workspace_root and Path(workspace_root).expanduser().resolve().joinpath("sisters.json").exists():
        return tenant_id, workspace_root
    sisters_path = PRIME_WORKSPACE / "sisters.json"
    if sisters_path.is_file():
        return "tenant-prime", str(PRIME_WORKSPACE)
    return tenant_id, workspace_root


def make_handler(bridge: RuntimeBridge):
    class Handler(BaseHTTPRequestHandler):
        def _cors_origin(self) -> str | None:
            origin = str(self.headers.get("Origin") or "").strip()
            if not origin:
                return None
            if "*" in CORS_ALLOWED_ORIGINS:
                return "*"
            if origin in CORS_ALLOWED_ORIGINS:
                return origin
            return None

        def _is_origin_allowed(self) -> bool:
            origin = str(self.headers.get("Origin") or "").strip()
            if not origin:
                return True
            if "*" in CORS_ALLOWED_ORIGINS:
                return True
            return origin in CORS_ALLOWED_ORIGINS

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

        def _write_cors(self, status: int, payload: dict | list) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            allowed_origin = self._cors_origin()
            if allowed_origin:
                self.send_header("Access-Control-Allow-Origin", allowed_origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(encoded)

        def _serve_static(self, rel_path: str) -> None:
            if ".." in rel_path or "\\" in rel_path:
                self._write(403, {"error": "forbidden"})
                return
            file_path = DASHBOARD_DIR / rel_path
            if not file_path.is_file():
                self._write(404, {"error": "not_found"})
                return
            try:
                resolved = file_path.resolve()
                if not str(resolved).startswith(str(DASHBOARD_DIR.resolve())):
                    self._write(403, {"error": "forbidden"})
                    return
            except Exception:
                self._write(403, {"error": "forbidden"})
                return
            suffix = file_path.suffix.lower()
            content_type = MIME_TYPES.get(suffix, "application/octet-stream")
            try:
                data = file_path.read_bytes()
            except Exception:
                self._write(500, {"error": "read_error"})
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self) -> None:  # noqa: N802
            if not self._is_origin_allowed():
                self.send_response(403)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(204)
            allowed_origin = self._cors_origin()
            if allowed_origin:
                self.send_header("Access-Control-Allow-Origin", allowed_origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", "0")
            self.end_headers()

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
            # ── Team Manager POST routes ──
            if parsed.path.startswith("/api/team-manager/"):
                self._team_manager_post(parsed)
                return
            # ── Dashboard control POST routes ──
            if parsed.path.startswith("/api/dashboard/"):
                self._dashboard_post(parsed)
                return
            self._write(404, {"error": "not_found"})

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            # ── Dashboard static files ──
            if parsed.path == "/dashboard" or parsed.path == "/dashboard/":
                self._serve_static("index.html")
                return
            if parsed.path.startswith("/dashboard/"):
                rel = parsed.path[len("/dashboard/"):]
                self._serve_static(rel)
                return
            # ── Team Manager GET routes ──
            if parsed.path.startswith("/api/team-manager/"):
                self._team_manager_get(parsed)
                return
            # ── Dashboard API ──
            if parsed.path == "/api/dashboard":
                self._dashboard_overview(parsed)
                return
            if parsed.path == "/api/dashboard/activity":
                self._dashboard_activity(parsed)
                return
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

        # ── Dashboard API handlers ──

        def _dashboard_overview(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", ["tenant-local"])[0]
            user_id = query.get("user_id", ["user-local"])[0]
            workspace_root = query.get("workspace_root", [None])[0]
            try:
                data = bridge.dashboard_overview(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    workspace_root=workspace_root,
                )
                # If the current tenant has no sisters, fall back to the
                # prime workspace where sisters.json is expected to live.
                sisters = data.get("sisters") or {}
                if not sisters.get("items") and PRIME_WORKSPACE.is_dir():
                    try:
                        prime_items = bridge.list_sisters(
                            tenant_id="tenant-prime",
                            workspace_root=str(PRIME_WORKSPACE),
                        )
                        if prime_items:
                            data["sisters"] = {
                                "total": len(prime_items),
                                "running": sum(
                                    1 for s in prime_items if s.get("running")
                                ),
                                "items": prime_items,
                            }
                    except Exception:
                        pass  # prime tenant not available; keep empty sisters
                self._write_cors(200, data)
            except Exception as exc:
                self._write_cors(500, {"error": str(exc)})

        def _dashboard_activity(self, parsed) -> None:
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", ["tenant-local"])[0]
            user_id = query.get("user_id", ["user-local"])[0]
            workspace_root = query.get("workspace_root", [None])[0]
            limit = int(query.get("limit", ["50"])[0])
            try:
                data = bridge.dashboard_activity(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    workspace_root=workspace_root,
                    limit=limit,
                )
                self._write_cors(200, {"events": data})
            except Exception as exc:
                self._write_cors(500, {"error": str(exc)})

        def _dashboard_post(self, parsed) -> None:
            path = parsed.path
            if not self._is_origin_allowed():
                self._write_cors(403, {"error": "origin_not_allowed"})
                return
            try:
                body = self._read_json()
            except Exception:
                return
            tenant_id = str(body.get("tenant_id", "tenant-local"))
            user_id = str(body.get("user_id", "user-local"))
            workspace_root = str(body["workspace_root"]) if body.get("workspace_root") else None
            try:
                if path == "/api/dashboard/heartbeat/start":
                    result = bridge.heartbeat_start(tenant_id, user_id, workspace_root)
                elif path == "/api/dashboard/heartbeat/stop":
                    result = bridge.heartbeat_stop(tenant_id, user_id, workspace_root)
                elif path == "/api/dashboard/heartbeat/tick":
                    result = bridge.heartbeat_tick(tenant_id, user_id, workspace_root)
                elif path == "/api/dashboard/cron/start":
                    result = bridge.cron_start(tenant_id, user_id, workspace_root)
                elif path == "/api/dashboard/cron/stop":
                    result = bridge.cron_stop(tenant_id, user_id, workspace_root)
                elif path == "/api/dashboard/sisters/spawn":
                    sister_id = str(body.get("sister_id") or "").strip()
                    if not sister_id:
                        self._write_cors(400, {"error": "sister_id is required"})
                        return
                    # Sisters live under tenant-prime; resolve the correct
                    # tenant/workspace so spawn works from any dashboard tenant.
                    s_tenant, s_ws = _resolve_sisters_tenant(tenant_id, workspace_root)
                    result = bridge.spawn_sister(s_tenant, sister_id, s_ws)
                elif path == "/api/dashboard/sisters/stop":
                    sister_id = str(body.get("sister_id") or "").strip()
                    if not sister_id:
                        self._write_cors(400, {"error": "sister_id is required"})
                        return
                    s_tenant, s_ws = _resolve_sisters_tenant(tenant_id, workspace_root)
                    result = bridge.stop_sister(s_tenant, sister_id, s_ws)
                else:
                    self._write_cors(404, {"error": "not_found"})
                    return
                self._write_cors(200, result)
            except Exception as exc:
                self._write_cors(500, {"error": str(exc)})

        # ── Team Manager handlers ──

        def _team_manager_post(self, parsed) -> None:
            path = parsed.path
            if not self._is_origin_allowed():
                self._write_cors(403, {"error": "origin_not_allowed"})
                return
            try:
                body = self._read_json()
            except Exception:
                return
            tenant_id = str(body.get("tenant_id", "tenant-local"))
            workspace_root = str(body["workspace_root"]) if body.get("workspace_root") else None
            try:
                if path == "/api/team-manager/graphs":
                    result = bridge.tm_create_graph(
                        tenant_id=tenant_id,
                        workspace_root=workspace_root,
                        workspace_id=str(body.get("workspace_id", "")),
                        name=str(body["name"]),
                        description=str(body.get("description", "")),
                        metadata=body.get("metadata"),
                    )
                    self._write_cors(200, result)
                elif path == "/api/team-manager/nodes":
                    result = bridge.tm_add_node(
                        tenant_id=tenant_id,
                        workspace_root=workspace_root,
                        graph_id=str(body["graph_id"]),
                        kind=str(body["kind"]),
                        label=str(body.get("label", "")),
                        config=body.get("config"),
                        position_x=float(body.get("position_x", 0.0)),
                        position_y=float(body.get("position_y", 0.0)),
                    )
                    self._write_cors(200, result)
                elif path == "/api/team-manager/edges":
                    result = bridge.tm_add_edge(
                        tenant_id=tenant_id,
                        workspace_root=workspace_root,
                        graph_id=str(body["graph_id"]),
                        source_node_id=str(body["source_node_id"]),
                        target_node_id=str(body["target_node_id"]),
                        edge_type=str(body.get("edge_type", "feeds")),
                        metadata=body.get("metadata"),
                    )
                    self._write_cors(200, result)
                elif path == "/api/team-manager/validate":
                    result = bridge.tm_validate_graph(
                        tenant_id=tenant_id,
                        graph_id=str(body["graph_id"]),
                        workspace_root=workspace_root,
                    )
                    self._write_cors(200, result)
                elif path == "/api/team-manager/deploy":
                    result = bridge.tm_deploy_graph(
                        tenant_id=tenant_id,
                        graph_id=str(body["graph_id"]),
                        workspace_root=workspace_root,
                    )
                    self._write_cors(200, result)
                elif path == "/api/team-manager/deployments":
                    result = bridge.tm_deploy_graph(
                        tenant_id=tenant_id,
                        graph_id=str(body["graph_id"]),
                        workspace_root=workspace_root,
                    )
                    self._write_cors(200, result)
                elif path == "/api/team-manager/schedules":
                    result = bridge.tm_create_schedule(
                        tenant_id=tenant_id,
                        workspace_root=workspace_root,
                        graph_id=str(body["graph_id"]),
                        name=str(body["name"]),
                        cron_expression=str(body["cron_expression"]),
                        action=str(body.get("action", "deploy")),
                        action_params=body.get("action_params"),
                        requires_approval=bool(body.get("requires_approval", False)),
                    )
                    self._write_cors(200, result)
                else:
                    # PUT/DELETE via POST with _method or path-based routing
                    self._team_manager_mutation(path, body, tenant_id, workspace_root)
            except KeyError as exc:
                self._write_cors(400, {"error": f"missing field: {exc}"})
            except ValueError as exc:
                self._write_cors(400, {"error": str(exc), "error_type": "validation_failed"})
            except Exception as exc:
                self._write_cors(500, {"error": str(exc)})

        def _team_manager_mutation(self, path: str, body: dict, tenant_id: str, workspace_root: str | None) -> None:
            """Handle PUT/DELETE-style mutations routed as POST with action prefix."""
            import re as _re
            # PUT /api/team-manager/graphs/{id}
            m = _re.match(r"/api/team-manager/graphs/([^/]+)/update$", path)
            if m:
                result = bridge.tm_update_graph(
                    tenant_id=tenant_id, graph_id=m.group(1), workspace_root=workspace_root,
                    name=body.get("name"), description=body.get("description"), metadata=body.get("metadata"),
                )
                self._write_cors(200, result)
                return
            # DELETE /api/team-manager/graphs/{id}
            m = _re.match(r"/api/team-manager/graphs/([^/]+)/delete$", path)
            if m:
                result = bridge.tm_delete_graph(tenant_id=tenant_id, graph_id=m.group(1), workspace_root=workspace_root)
                self._write_cors(200, result)
                return
            # PUT /api/team-manager/nodes/{id}
            m = _re.match(r"/api/team-manager/nodes/([^/]+)/update$", path)
            if m:
                result = bridge.tm_update_node(
                    tenant_id=tenant_id, node_id=m.group(1), workspace_root=workspace_root,
                    label=body.get("label"), config=body.get("config"),
                    position_x=body.get("position_x"), position_y=body.get("position_y"),
                )
                self._write_cors(200, result)
                return
            # DELETE /api/team-manager/nodes/{id}
            m = _re.match(r"/api/team-manager/nodes/([^/]+)/delete$", path)
            if m:
                result = bridge.tm_delete_node(tenant_id=tenant_id, node_id=m.group(1), workspace_root=workspace_root)
                self._write_cors(200, result)
                return
            # DELETE /api/team-manager/edges/{id}
            m = _re.match(r"/api/team-manager/edges/([^/]+)/delete$", path)
            if m:
                result = bridge.tm_delete_edge(tenant_id=tenant_id, edge_id=m.group(1), workspace_root=workspace_root)
                self._write_cors(200, result)
                return
            # POST /api/team-manager/deployments/{id}/cancel
            m = _re.match(r"/api/team-manager/deployments/([^/]+)/cancel$", path)
            if m:
                result = bridge.tm_cancel_deployment(
                    tenant_id=tenant_id, deployment_id=m.group(1), workspace_root=workspace_root,
                )
                self._write_cors(200, result)
                return
            # POST /api/team-manager/deployments/{id}/primer
            m = _re.match(r"/api/team-manager/deployments/([^/]+)/primer$", path)
            if m:
                node_id = str(body.get("node_id") or "").strip()
                if not node_id:
                    self._write_cors(400, {"error": "node_id is required"})
                    return
                # Fetch the deployment to get graph_id
                deployment = bridge.tm_get_deployment(
                    tenant_id=tenant_id, deployment_id=m.group(1), workspace_root=workspace_root,
                )
                if deployment is None or deployment.get("error"):
                    self._write_cors(404, deployment or {"error": "deployment_not_found"})
                    return
                result = bridge.tm_generate_primer(
                    tenant_id=tenant_id, graph_id=deployment["graph_id"],
                    node_id=node_id, workspace_root=workspace_root,
                )
                self._write_cors(200, result)
                return
            # PUT /api/team-manager/schedules/{id}/update
            m = _re.match(r"/api/team-manager/schedules/([^/]+)/update$", path)
            if m:
                kwargs: dict = {}
                for field in ("name", "cron_expression", "action", "action_params", "enabled", "requires_approval"):
                    if field in body:
                        kwargs[field] = body[field]
                result = bridge.tm_update_schedule(
                    tenant_id=tenant_id, schedule_id=m.group(1), workspace_root=workspace_root,
                    **kwargs,
                )
                self._write_cors(200, result)
                return
            # DELETE /api/team-manager/schedules/{id}/delete
            m = _re.match(r"/api/team-manager/schedules/([^/]+)/delete$", path)
            if m:
                result = bridge.tm_delete_schedule(tenant_id=tenant_id, schedule_id=m.group(1), workspace_root=workspace_root)
                self._write_cors(200, result)
                return
            # POST /api/team-manager/schedules/{id}/toggle
            m = _re.match(r"/api/team-manager/schedules/([^/]+)/toggle$", path)
            if m:
                result = bridge.tm_toggle_schedule(
                    tenant_id=tenant_id, schedule_id=m.group(1),
                    enabled=bool(body.get("enabled", True)),
                    workspace_root=workspace_root,
                )
                self._write_cors(200, result)
                return
            self._write_cors(404, {"error": "not_found"})

        def _team_manager_get(self, parsed) -> None:
            path = parsed.path
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", ["tenant-local"])[0]
            workspace_root = query.get("workspace_root", [None])[0]
            try:
                if path == "/api/team-manager/graphs":
                    workspace_id = query.get("workspace_id", [None])[0]
                    items = bridge.tm_list_graphs(
                        tenant_id=tenant_id, workspace_root=workspace_root, workspace_id=workspace_id,
                    )
                    self._write_cors(200, {"graphs": items})
                    return
                import re as _re
                # GET /api/team-manager/graphs/{id}
                m = _re.match(r"/api/team-manager/graphs/([^/]+)$", path)
                if m:
                    graph_id = m.group(1)
                    result = bridge.tm_get_graph(tenant_id=tenant_id, graph_id=graph_id, workspace_root=workspace_root)
                    if result is None:
                        self._write_cors(404, {"error": "not_found"})
                    else:
                        nodes = bridge.tm_list_nodes(tenant_id=tenant_id, graph_id=graph_id, workspace_root=workspace_root)
                        edges = bridge.tm_list_edges(tenant_id=tenant_id, graph_id=graph_id, workspace_root=workspace_root)
                        self._write_cors(200, {"graph": result, "nodes": nodes, "edges": edges})
                    return
                if path == "/api/team-manager/nodes":
                    graph_id = query.get("graph_id", [None])[0]
                    if not graph_id:
                        self._write_cors(400, {"error": "graph_id is required"})
                        return
                    kind = query.get("kind", [None])[0]
                    items = bridge.tm_list_nodes(
                        tenant_id=tenant_id, graph_id=graph_id, workspace_root=workspace_root, kind=kind,
                    )
                    self._write_cors(200, {"nodes": items})
                    return
                if path == "/api/team-manager/edges":
                    graph_id = query.get("graph_id", [None])[0]
                    if not graph_id:
                        self._write_cors(400, {"error": "graph_id is required"})
                        return
                    edge_type = query.get("edge_type", [None])[0]
                    items = bridge.tm_list_edges(
                        tenant_id=tenant_id, graph_id=graph_id, workspace_root=workspace_root, edge_type=edge_type,
                    )
                    self._write_cors(200, {"edges": items})
                    return
                if path == "/api/team-manager/deployments":
                    graph_id = query.get("graph_id", [None])[0]
                    items = bridge.tm_list_deployments(
                        tenant_id=tenant_id, graph_id=graph_id, workspace_root=workspace_root,
                    )
                    self._write_cors(200, {"deployments": items})
                    return
                # GET /api/team-manager/deployments/{id}
                m = _re.match(r"/api/team-manager/deployments/([^/]+)$", path)
                if m:
                    result = bridge.tm_get_deployment(
                        tenant_id=tenant_id, deployment_id=m.group(1), workspace_root=workspace_root,
                    )
                    if result is None:
                        self._write_cors(404, {"error": "not_found"})
                    else:
                        self._write_cors(200, result)
                    return
                if path == "/api/team-manager/schedules":
                    graph_id = query.get("graph_id", [None])[0]
                    items = bridge.tm_list_schedules(
                        tenant_id=tenant_id, graph_id=graph_id, workspace_root=workspace_root,
                    )
                    self._write_cors(200, {"schedules": items})
                    return
                self._write_cors(404, {"error": "not_found"})
            except Exception as exc:
                self._write_cors(500, {"error": str(exc)})

        # ── Existing handlers ──

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
    _load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    bridge = RuntimeBridge()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(bridge))
    print(f"runtime server listening on http://{args.host}:{args.port}")
    print(f"dashboard available at http://{args.host}:{args.port}/dashboard")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
