#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import sys
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Windows: force UTF-8 on stdout/stderr so emoji and unicode don't crash
if sys.platform == "win32":
    for stream in ("stdout", "stderr"):
        s = getattr(sys, stream, None)
        if s and hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")

# Configure logging early so all modules can emit to stderr.
# Use DEBUG to enable [ORCH] orchestration diagnostics; WARNING for production.
logging.basicConfig(
    level=logging.DEBUG,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Load .env BEFORE importing bomba_sr so RuntimeConfig picks up all vars.
def _load_dotenv_early(path: Path, *, override: bool = True) -> None:
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
        if key and (override or key not in os.environ or not os.environ.get(key)):
            os.environ[key] = value

_load_dotenv_early(Path(__file__).resolve().parent.parent / ".env")

# ── Mission Control users ─────────────────────────────────────────────
# password_hash = sha256(password).hexdigest()
# To add users: python3 -c "import hashlib; print(hashlib.sha256(b'yourpassword').hexdigest())"
_MC_USERS: dict[str, dict] = {
    "admin@sigil.ai": {
        "id": "user-admin",
        "name": "Admin",
        "role": "admin",
        "password_hash": hashlib.sha256(b"sigil2026").hexdigest(),
    },
    "neel@acti.ai": {
        "id": "user-neel",
        "name": "Neel",
        "role": "admin",
        "password_hash": hashlib.sha256(b"neel2026").hexdigest(),
    },
    "nadav@acti.ai": {
        "id": "user-nadav",
        "name": "Nadav",
        "role": "operator",
        "password_hash": hashlib.sha256(b"nadav2026").hexdigest(),
    },
    "sean@acti.ai": {
        "id": "user-sean",
        "name": "Sean",
        "role": "admin",
        "password_hash": hashlib.sha256(b"sean2026").hexdigest(),
    },
}


def _load_openclaw_runtime_defaults(project_root: Path) -> None:
    config_path = project_root / "portable-openclaw" / "openclaw.json"
    if not config_path.is_file():
        return
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    agents = payload.get("agents") if isinstance(payload, dict) else {}
    agents = agents if isinstance(agents, dict) else {}
    defaults = agents.get("defaults") if isinstance(agents.get("defaults"), dict) else {}
    default_model = str(defaults.get("model") or "").strip()
    main_model = ""
    for item in agents.get("list") or []:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == "main":
            model = item.get("model")
            if isinstance(model, dict):
                main_model = str(model.get("primary") or "").strip()
            elif isinstance(model, str):
                main_model = model.strip()
            break
    selected_model = (main_model or default_model or "openrouter/anthropic/claude-opus-4.6").removeprefix("openrouter/")
    os.environ.setdefault("BOMBA_LLM_PROVIDER_PRIORITY", "openrouter")
    os.environ.setdefault("BOMBA_MODEL_ID", selected_model)
    os.environ.setdefault("BOMBA_CLASSIFY_MODEL", selected_model)
    os.environ.setdefault("BOMBA_COLOSSEUM_MODEL_ID", selected_model)
    os.environ.setdefault("BOMBA_TEAM_MANAGER_MODEL_ID", selected_model)

    memory_search = defaults.get("memorySearch") if isinstance(defaults.get("memorySearch"), dict) else {}
    embed_model = str(memory_search.get("model") or "").strip()
    remote = memory_search.get("remote") if isinstance(memory_search.get("remote"), dict) else {}
    remote_base = str(remote.get("baseUrl") or "").strip().rstrip("/")
    if embed_model:
        os.environ.setdefault("OPENAI_EMBEDDING_MODEL", embed_model)
        os.environ.setdefault("BOMBA_PINECONE_EMBED_MODEL", embed_model)
    if remote_base:
        os.environ.setdefault("OPENROUTER_BASE_URL", remote_base)

from bomba_sr.context.policy import TurnProfile
from bomba_sr.openclaw.integration import bundled_openclaw_root, ensure_portable_openclaw_layout, portable_home_root
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest
from bomba_sr.subagents.protocol import SubAgentTask
from bomba_sr.subagents.worker import SubAgentWorkerFactory

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"
MC_DIST_DIR = Path(__file__).resolve().parent.parent / "mission-control" / "dist"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_load_openclaw_runtime_defaults(PROJECT_ROOT)
PRIME_WORKSPACE = PROJECT_ROOT / "workspaces" / "prime"
ensure_portable_openclaw_layout(PROJECT_ROOT)
os.environ.setdefault("SIGIL_REPO_ROOT", str(PROJECT_ROOT))
os.environ.setdefault("SIGIL_WORKSPACES_ROOT", str(PROJECT_ROOT / "workspaces"))
os.environ.setdefault("SIGIL_PORTABLE_HOME", str(portable_home_root(PROJECT_ROOT)))
os.environ.setdefault("OPENCLAW_HOME", str(bundled_openclaw_root(PROJECT_ROOT)))
os.environ.setdefault("OPENCLAW_ROOT", str(bundled_openclaw_root(PROJECT_ROOT)))
os.environ.setdefault("OPENCLAW_ENV_FILE", str(PROJECT_ROOT / ".env"))


def _load_dotenv(path: Path, *, override: bool = True) -> None:
    """Read .env file into os.environ, preferring the repo-local bundle."""
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
        if key and (override or key not in os.environ or not os.environ.get(key)):
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
    for origin in os.getenv(
        "BOMBA_CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:8787,http://localhost:8787,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
)

MC_BEINGS_JSON = PROJECT_ROOT / "mission-control" / "data" / "beings.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BOMBA runtime HTTP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    return parser.parse_args()



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


def make_handler(bridge: RuntimeBridge, dashboard_svc=None, project_svc=None, pi_bridge=None):
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
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
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
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
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
            # ── Mission Control POST routes ──
            if parsed.path.startswith("/api/mc/"):
                self._mc_post(parsed)
                return
            # ── Dashboard control POST routes ──
            if parsed.path.startswith("/api/dashboard/"):
                self._dashboard_post(parsed)
                return
            self._write(404, {"error": "not_found"})

        def do_PATCH(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/mc/"):
                self._mc_patch(parsed)
                return
            self._write(404, {"error": "not_found"})

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/mc/"):
                self._mc_delete(parsed)
                return
            self._write(404, {"error": "not_found"})

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            # ── Dashboard: serve built frontend from mission-control/dist ──
            if parsed.path == "/" or parsed.path == "/dashboard" or parsed.path.startswith("/dashboard/"):
                if MC_DIST_DIR.is_dir():
                    rel = parsed.path.lstrip("/").removeprefix("dashboard").lstrip("/") or "index.html"
                    fpath = MC_DIST_DIR / rel
                    if not fpath.is_file():
                        fpath = MC_DIST_DIR / "index.html"  # SPA fallback
                    if fpath.is_file():
                        suffix = fpath.suffix.lower()
                        ctype = MIME_TYPES.get(suffix, "application/octet-stream")
                        data = fpath.read_bytes()
                        self.send_response(200)
                        self.send_header("Content-Type", ctype)
                        self.send_header("Content-Length", str(len(data)))
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(data)
                        return
                # Fallback to Vite dev server if dist not built
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:5173/")
                self.end_headers()
                return
            # ── Static assets (JS/CSS) from dist ──
            if parsed.path.startswith("/assets/") and MC_DIST_DIR.is_dir():
                fpath = MC_DIST_DIR / parsed.path.lstrip("/")
                if fpath.is_file():
                    suffix = fpath.suffix.lower()
                    ctype = MIME_TYPES.get(suffix, "application/octet-stream")
                    data = fpath.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=31536000, immutable")
                    self.end_headers()
                    self.wfile.write(data)
                    return
            # ── Deliverables static files ──
            if parsed.path.startswith("/deliverables/"):
                self._serve_deliverable(parsed.path)
                return
            # ── Mission Control GET routes ──
            if parsed.path.startswith("/api/mc/"):
                self._mc_get(parsed)
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
                elif path == "/api/team-manager/variables":
                    result = bridge.tm_set_variable(
                        tenant_id=tenant_id,
                        graph_id=str(body["graph_id"]),
                        key=str(body["key"]),
                        value=str(body.get("value", "")),
                        var_type=str(body.get("var_type", "string")),
                        workspace_root=workspace_root,
                    )
                    self._write_cors(200, result)
                elif path == "/api/team-manager/pipelines":
                    result = bridge.tm_save_pipeline(
                        tenant_id=tenant_id,
                        graph_id=str(body["graph_id"]),
                        node_id=str(body["node_id"]),
                        steps=body.get("steps", []),
                        workspace_root=workspace_root,
                    )
                    self._write_cors(200, result)
                elif path == "/api/team-manager/layouts":
                    result = bridge.tm_save_layout(
                        tenant_id=tenant_id,
                        graph_id=str(body["graph_id"]),
                        layout=body.get("layout", {}),
                        is_default=bool(body.get("is_default", False)),
                        workspace_root=workspace_root,
                    )
                    self._write_cors(200, result)
                elif path == "/api/team-manager/generate":
                    prompt = body.get("prompt", "")
                    if not prompt:
                        self._write_cors(400, {"error": "prompt is required"})
                        return
                    result = bridge.tm_generate_text(
                        tenant_id=tenant_id,
                        prompt=prompt,
                        system_prompt=body.get("system_prompt"),
                        max_tokens=int(body.get("max_tokens", 1024)),
                        workspace_root=workspace_root,
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
            # DELETE /api/team-manager/variables/{graph_id}/delete
            m = _re.match(r"/api/team-manager/variables/([^/]+)/delete$", path)
            if m:
                key = str(body.get("key", "")).strip()
                if not key:
                    self._write_cors(400, {"error": "key is required"})
                    return
                result = bridge.tm_delete_variable(
                    tenant_id=tenant_id, graph_id=m.group(1), key=key,
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
                if path == "/api/team-manager/variables":
                    graph_id = query.get("graph_id", [None])[0]
                    if not graph_id:
                        self._write_cors(400, {"error": "graph_id is required"})
                        return
                    items = bridge.tm_list_variables(
                        tenant_id=tenant_id, graph_id=graph_id, workspace_root=workspace_root,
                    )
                    self._write_cors(200, {"variables": items})
                    return
                if path == "/api/team-manager/pipelines":
                    node_id = query.get("node_id", [None])[0]
                    if not node_id:
                        self._write_cors(400, {"error": "node_id is required"})
                        return
                    result = bridge.tm_get_pipeline(
                        tenant_id=tenant_id, node_id=node_id, workspace_root=workspace_root,
                    )
                    if result is None:
                        self._write_cors(404, {"error": "pipeline_not_found"})
                    else:
                        self._write_cors(200, result)
                    return
                if path == "/api/team-manager/layouts":
                    graph_id = query.get("graph_id", [None])[0]
                    if not graph_id:
                        self._write_cors(400, {"error": "graph_id is required"})
                        return
                    items = bridge.tm_list_layouts(
                        tenant_id=tenant_id, graph_id=graph_id, workspace_root=workspace_root,
                    )
                    self._write_cors(200, {"layouts": items})
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
                worker=worker_factory.create_worker(),
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

        # ── Mission Control handlers ──

        def _mc_get(self, parsed) -> None:
            path = parsed.path
            query = parse_qs(parsed.query)

            if not dashboard_svc:
                self._write_cors(503, {"error": "dashboard service not initialized"})
                return

            try:
                # --- Beings ---
                if path == "/api/mc/beings":
                    type_f = query.get("type", [None])[0]
                    status_f = query.get("status", [None])[0]
                    beings = dashboard_svc.list_beings(type_filter=type_f, status_filter=status_f)
                    self._write_cors(200, {"beings": beings})
                    return
                if path.startswith("/api/mc/beings/"):
                    remainder = path.split("/api/mc/beings/", 1)[1]
                    parts = remainder.split("/")
                    bid = parts[0]
                    sub = parts[1] if len(parts) > 1 else None

                    # GET /api/mc/beings/:id/detail
                    if sub == "detail":
                        detail = dashboard_svc.get_being_detail(bid)
                        if not detail:
                            self._write_cors(404, {"error": "being not found"})
                            return
                        self._write_cors(200, detail)
                        return

                    # GET /api/mc/beings/:id/file?path=...
                    if sub == "file":
                        rel_path = query.get("path", [None])[0]
                        if not rel_path:
                            self._write_cors(400, {"error": "path query param required"})
                            return
                        content = dashboard_svc.get_being_file(bid, rel_path)
                        if content is None:
                            self._write_cors(404, {"error": "file not found"})
                            return
                        self._write_cors(200, {"content": content, "path": rel_path})
                        return

                    # GET /api/mc/beings/:id/skills
                    if sub == "skills":
                        skills = dashboard_svc.get_being_skill_list(bid)
                        self._write_cors(200, {"skills": skills})
                        return

                    # GET /api/mc/beings/:id  (basic being record)
                    being = dashboard_svc.get_being(bid)
                    if not being:
                        self._write_cors(404, {"error": "being not found"})
                        return
                    self._write_cors(200, {"being": being})
                    return

                # --- Projects Catalog ---
                if path == "/api/mc/projects":
                    projects = dashboard_svc.list_projects_catalog()
                    self._write_cors(200, {"projects": projects})
                    return

                # --- Dream Cycle ---
                if path == "/api/mc/dream-cycle/logs":
                    from bomba_sr.memory.dreaming import DreamCycle
                    limit = int(query.get("limit", ["20"])[0])
                    logs = DreamCycle.list_dream_logs(limit=limit)
                    self._write_cors(200, {"logs": logs})
                    return
                if path == "/api/mc/dream-cycle/status":
                    self._write_cors(200, {"dream_cycle": bridge.dream_cycle_status()})
                    return

                # --- Tasks ---
                if path == "/api/mc/tasks/history":
                    tid = query.get("taskId", [None])[0]
                    history = dashboard_svc.task_history(task_id=tid)
                    self._write_cors(200, {"history": history})
                    return
                if path == "/api/mc/tasks":
                    # Default: show top-level tasks only for a clean board view.
                    # Pass ?top_level_only=false to include child/sub-tasks.
                    top_level_only = query.get("top_level_only", ["true"])[0].lower() != "false"
                    tasks = dashboard_svc.list_tasks(
                        project_svc,
                        assignee=query.get("assignee", [None])[0],
                        priority=query.get("priority", [None])[0],
                        status=query.get("status", [None])[0],
                        from_date=query.get("from", [None])[0],
                        to_date=query.get("to", [None])[0],
                        top_level_only=top_level_only,
                    )
                    self._write_cors(200, {"tasks": tasks})
                    return
                if path.startswith("/api/mc/tasks/") and path.endswith("/steps"):
                    tid = path.split("/api/mc/tasks/", 1)[1].split("/")[0]
                    steps = dashboard_svc.get_task_steps(tid)
                    self._write_cors(200, {"steps": steps})
                    return
                if path.startswith("/api/mc/tasks/") and path.endswith("/artifacts"):
                    tid = path.split("/api/mc/tasks/", 1)[1].split("/")[0]
                    artifacts = dashboard_svc.list_task_artifacts(tid)
                    self._write_cors(200, {"artifacts": artifacts})
                    return
                if path == "/api/mc/tasks/cleanup":
                    deleted = dashboard_svc.clean_casual_tasks(project_svc)
                    self._write_cors(200, {"deleted": deleted})
                    return
                if path.startswith("/api/mc/tasks/") and path.endswith("/orchestration"):
                    tid = path.split("/api/mc/tasks/", 1)[1].split("/")[0]
                    task = dashboard_svc.get_task_with_orchestration(project_svc, tid)
                    self._write_cors(200, {"task": task})
                    return
                if path.startswith("/api/mc/tasks/") and path.endswith("/children"):
                    tid = path.split("/api/mc/tasks/", 1)[1].split("/")[0]
                    child_ids = dashboard_svc.get_task_children(tid)
                    children = []
                    for cid in child_ids:
                        try:
                            children.append(dashboard_svc.get_task(project_svc, cid))
                        except Exception:
                            children.append({"id": cid, "status": "unknown"})
                    self._write_cors(200, {"children": children, "parent_task_id": tid})
                    return
                if path.startswith("/api/mc/tasks/"):
                    tid = path.split("/api/mc/tasks/", 1)[1].split("/")[0]
                    task = dashboard_svc.get_task(project_svc, tid)
                    self._write_cors(200, {"task": task})
                    return

                # --- Orchestration ---
                if path.startswith("/api/mc/orchestration/") and path.endswith("/status"):
                    oid = path.split("/api/mc/orchestration/", 1)[1].split("/")[0]
                    status = dashboard_svc.get_orchestration_status(oid)
                    if status is None:
                        self._write_cors(404, {"error": "orchestration not found"})
                        return
                    self._write_cors(200, {"orchestration": status})
                    return
                if path.startswith("/api/mc/orchestration/") and path.endswith("/log"):
                    oid = path.split("/api/mc/orchestration/", 1)[1].split("/")[0]
                    log_entries = dashboard_svc.get_orchestration_log(oid)
                    self._write_cors(200, {"log": log_entries})
                    return

                # --- ACT-I Architecture ---
                if path == "/api/mc/acti/architecture":
                    from bomba_sr.acti.loader import get_full_architecture
                    self._write_cors(200, get_full_architecture())
                    return
                if path == "/api/mc/acti/beings":
                    from bomba_sr.acti.loader import load_beings
                    self._write_cors(200, {"beings": load_beings()})
                    return
                if path.startswith("/api/mc/acti/beings/"):
                    from bomba_sr.acti.loader import load_beings
                    acti_bid = path.split("/api/mc/acti/beings/", 1)[1].split("/")[0]
                    beings = load_beings()
                    match = next((b for b in beings if b["id"] == acti_bid), None)
                    if not match:
                        self._write_cors(404, {"error": "ACT-I being not found"})
                        return
                    self._write_cors(200, {"being": match})
                    return
                if path == "/api/mc/acti/clusters":
                    from bomba_sr.acti.loader import load_clusters
                    family = query.get("family", [None])[0]
                    being = query.get("being", [None])[0]
                    clusters = load_clusters()
                    if family:
                        clusters = [c for c in clusters if c["family"] == family]
                    if being:
                        clusters = [c for c in clusters if c["being"] == being]
                    self._write_cors(200, {"clusters": clusters})
                    return
                if path == "/api/mc/acti/skill-families":
                    from bomba_sr.acti.loader import load_skill_families
                    self._write_cors(200, {"skill_families": load_skill_families()})
                    return
                if path == "/api/mc/acti/levers":
                    from bomba_sr.acti.loader import LEVERS, load_lever_matrix
                    self._write_cors(200, {"levers": LEVERS, "matrix": load_lever_matrix()})
                    return
                if path.startswith("/api/mc/acti/sisters/"):
                    from bomba_sr.acti.loader import get_sister_profile
                    sid = path.split("/api/mc/acti/sisters/", 1)[1].split("/")[0]
                    profile = get_sister_profile(sid)
                    if not profile["beings"]:
                        self._write_cors(404, {"error": "no ACT-I beings mapped to this sister"})
                        return
                    self._write_cors(200, {"sister_id": sid, "profile": profile})
                    return

                # --- Chat Sessions ---
                if path == "/api/mc/chat/sessions":
                    _uid = query.get("user_id", [None])[0]
                    if not _uid:
                        self._write_cors(400, {"error": "user_id query parameter is required"})
                        return
                    sessions = dashboard_svc.list_sessions(user_id=_uid)
                    self._write_cors(200, {"sessions": sessions})
                    return

                # --- Chat ---
                if path == "/api/mc/chat/messages":
                    msgs = dashboard_svc.list_messages(
                        sender=query.get("sender", [None])[0],
                        target=query.get("target", [None])[0],
                        search=query.get("search", [None])[0],
                        session_id=query.get("session_id", [None])[0],
                        limit=int(query.get("limit", ["500"])[0]),
                        offset=int(query.get("offset", ["0"])[0]),
                    )
                    self._write_cors(200, {"messages": msgs})
                    return

                # --- Deliverables ---
                if path == "/api/mc/deliverables":
                    task_id = query.get("task_id", [None])[0]
                    if task_id:
                        deliverables = dashboard_svc.list_deliverables(task_id)
                    else:
                        deliverables = dashboard_svc.list_all_deliverables()
                    self._write_cors(200, {"deliverables": deliverables})
                    return

                # --- Sub-agents ---
                if path == "/api/mc/subagents":
                    runs = dashboard_svc.list_subagent_runs()
                    self._write_cors(200, {"runs": runs})
                    return

                # --- Artifacts ---
                if path.startswith("/api/mc/artifacts/") and path.endswith("/preview"):
                    aid = path.split("/api/mc/artifacts/", 1)[1].split("/")[0]
                    rec = dashboard_svc.get_artifact(aid)
                    if not rec:
                        self._write_cors(404, {"error": "artifact not found"})
                        return
                    fpath = Path(rec["path"])
                    if not fpath.is_file():
                        self._write_cors(404, {"error": "artifact file missing"})
                        return
                    from bomba_sr.artifacts.store import get_artifact_type_info
                    _, _, is_binary = get_artifact_type_info(rec.get("artifact_type", ""))
                    if is_binary:
                        self._write_cors(200, {
                            "type": "binary",
                            "download_url": f"/api/mc/artifacts/{aid}/download",
                            "mime_type": rec.get("mime_type", "application/octet-stream"),
                            "artifact": rec,
                        })
                    else:
                        try:
                            text = fpath.read_text(encoding="utf-8", errors="replace")[:50000]
                        except Exception:
                            text = ""
                        self._write_cors(200, {
                            "type": "text",
                            "content": text,
                            "mime_type": rec.get("mime_type", "text/plain"),
                            "artifact": rec,
                        })
                    return

                if path.startswith("/api/mc/artifacts/") and path.endswith("/download"):
                    aid = path.split("/api/mc/artifacts/", 1)[1].split("/")[0]
                    rec = dashboard_svc.get_artifact(aid)
                    if not rec:
                        self._write_cors(404, {"error": "artifact not found"})
                        return
                    import mimetypes
                    fpath = Path(rec["path"])
                    if not fpath.is_file():
                        self._write_cors(404, {"error": "artifact file missing"})
                        return
                    content_type = rec.get("mime_type", "application/octet-stream")
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Disposition", f'attachment; filename="{fpath.name}"')
                    self.send_header("Content-Length", str(fpath.stat().st_size))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(fpath.read_bytes())
                    return

                # --- Code (Pi Bridge) GET ---
                if path == "/api/mc/code/health":
                    if not pi_bridge:
                        self._write_cors(503, {"error": "code agent not configured"})
                        return
                    self._write_cors(200, pi_bridge.health())
                    return

                if path == "/api/mc/code/sessions":
                    if not pi_bridge:
                        self._write_cors(503, {"error": "code agent not configured"})
                        return
                    self._write_cors(200, {"sessions": pi_bridge.list_sessions()})
                    return

                if path.startswith("/api/mc/code/sessions/") and path.endswith("/messages"):
                    if not pi_bridge:
                        self._write_cors(503, {"error": "code agent not configured"})
                        return
                    sid = path.split("/api/mc/code/sessions/", 1)[1].split("/")[0]
                    result = pi_bridge.get_messages(sid)
                    self._write_cors(200, result)
                    return

                if path.startswith("/api/mc/code/sessions/") and path.endswith("/events"):
                    if not pi_bridge:
                        self._write_cors(503, {"error": "code agent not configured"})
                        return
                    sid = path.split("/api/mc/code/sessions/", 1)[1].split("/")[0]
                    self._mc_code_sse_stream(sid)
                    return

                if path == "/api/mc/code/state":
                    if not pi_bridge:
                        self._write_cors(503, {"error": "code agent not configured"})
                        return
                    result = pi_bridge.get_state()
                    self._write_cors(200, result)
                    return

                # --- SSE ---
                if path == "/api/mc/events":
                    self._mc_sse_stream()
                    return

                self._write_cors(404, {"error": "not_found"})
            except ValueError as exc:
                self._write_cors(404, {"error": str(exc)})
            except Exception as exc:
                self._write_cors(500, {"error": str(exc)})

        def _mc_post(self, parsed) -> None:
            path = parsed.path
            if not dashboard_svc:
                self._write_cors(503, {"error": "dashboard service not initialized"})
                return
            if not self._is_origin_allowed():
                self._write_cors(403, {"error": "origin_not_allowed"})
                return
            try:
                body = self._read_json()
            except Exception:
                return

            try:
                # --- Tasks ---
                if path == "/api/mc/tasks":
                    task = dashboard_svc.create_task(
                        project_svc,
                        title=body["title"],
                        description=body.get("description"),
                        status=body.get("status", "backlog"),
                        priority=body.get("priority", "medium"),
                        assignees=body.get("assignees"),
                        owner_agent_id=body.get("owner_agent_id"),
                        parent_task_id=body.get("parent_task_id"),
                    )
                    self._write_cors(201, {"task": task})
                    return

                # --- Orchestration ---
                if path == "/api/mc/orchestration":
                    if not dashboard_svc.orchestration_engine:
                        self._write_cors(503, {"error": "orchestration engine not initialized"})
                        return
                    result = dashboard_svc.orchestration_engine.start(
                        goal=body["goal"],
                        requester_session_id=body.get("session_id", "mc-chat-prime"),
                        sender=body.get("sender", "user"),
                    )
                    self._write_cors(201, {"orchestration": result})
                    return

                # --- Dream Cycle ---
                if path == "/api/mc/dream-cycle":
                    being_id = body.get("being_id")
                    result = bridge.dream_cycle_run_once(
                        being_id=being_id,
                        dashboard_svc=dashboard_svc,
                    )
                    self._write_cors(200, {"dream_cycle": result})
                    return

                # --- Auth: Login ---
                if path == "/api/mc/auth/login":
                    _email = (body.get("email") or "").strip().lower()
                    _password = body.get("password") or ""
                    if not _email or not _password:
                        self._write_cors(400, {"error": "Email and password required"})
                        return
                    _hash = hashlib.sha256(_password.encode()).hexdigest()
                    _row = dashboard_svc.db.execute(
                        "SELECT * FROM mc_users WHERE email = ?", (_email,)
                    ).fetchone()
                    if not _row or dict(_row).get("password_hash") != _hash:
                        self._write_cors(401, {"error": "Invalid credentials"})
                        return
                    _user = dict(_row)
                    _token = secrets.token_urlsafe(32)
                    self._write_cors(200, {
                        "user_id": _user["id"],
                        "email": _user["email"],
                        "name": _user["name"],
                        "role": _user.get("role", "operator"),
                        "token": _token,
                    })
                    return

                # --- Auth: Register ---
                if path == "/api/mc/auth/register":
                    _email = (body.get("email") or "").strip().lower()
                    _password = body.get("password") or ""
                    _name = (body.get("name") or "").strip()
                    if not _email or not _password or not _name:
                        self._write_cors(400, {"error": "Name, email, and password required"})
                        return
                    if len(_password) < 6:
                        self._write_cors(400, {"error": "Password must be at least 6 characters"})
                        return
                    _existing = dashboard_svc.db.execute(
                        "SELECT id FROM mc_users WHERE email = ?", (_email,)
                    ).fetchone()
                    if _existing:
                        self._write_cors(409, {"error": "Account already exists"})
                        return
                    _uid = f"user-{uuid.uuid4().hex[:8]}"
                    _hash = hashlib.sha256(_password.encode()).hexdigest()
                    _now = datetime.now(timezone.utc).isoformat()
                    dashboard_svc.db.execute_commit(
                        "INSERT INTO mc_users (id, email, name, password_hash, role, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                        (_uid, _email, _name, _hash, "operator", _now, _now),
                    )
                    _token = secrets.token_urlsafe(32)
                    self._write_cors(201, {
                        "user_id": _uid,
                        "email": _email,
                        "name": _name,
                        "role": "operator",
                        "token": _token,
                    })
                    return

                # --- Chat Sessions ---
                if path == "/api/mc/chat/sessions":
                    name = body.get("name", "New Chat")
                    _uid = body.get("user_id")
                    session = dashboard_svc.create_session(name, user_id=_uid)
                    self._write_cors(201, {"session": session})
                    return

                # --- Chat ---
                if path == "/api/mc/chat/messages":
                    content = body.get("content", "")
                    sender = body.get("sender", "user")
                    targets = body.get("targets", [])
                    mode = body.get("mode", "auto")
                    task_ref = body.get("taskRef")
                    session_id = body.get("session_id") or f"sess-{uuid.uuid4().hex}"
                    # Auto-route broadcast (no targets) to prime
                    if not targets:
                        targets = ["prime"]
                    msg_type = "broadcast"
                    if len(targets) == 1:
                        msg_type = "direct"
                    elif len(targets) > 1:
                        msg_type = "group"

                    msg = dashboard_svc.create_message(
                        sender=sender, content=content,
                        targets=targets, msg_type=msg_type,
                        mode=mode, task_ref=task_ref,
                        session_id=session_id,
                    )

                    # Route to each targeted being in background
                    for tid in targets:
                        dashboard_svc.route_to_being(tid, content, sender=sender, chat_session_id=session_id)

                    self._write_cors(201, {"message": msg})
                    return

                if path == "/api/mc/chat/system":
                    msg = dashboard_svc.create_system_message(
                        content=body.get("content", ""),
                        task_ref=body.get("taskRef"),
                    )
                    self._write_cors(201, {"message": msg})
                    return

                # --- Code (Pi Bridge) POST ---
                if path == "/api/mc/code/sessions":
                    if not pi_bridge:
                        self._write_cors(503, {"error": "code agent not configured"})
                        return
                    title = body.get("title", "New session")
                    session = pi_bridge.create_session(title=title)
                    self._write_cors(201, {
                        "session": {
                            "id": session.id,
                            "title": session.title,
                            "workspace_root": session.workspace_root,
                            "created_at": session.created_at,
                        },
                    })
                    return

                if path.startswith("/api/mc/code/sessions/") and path.endswith("/prompt"):
                    if not pi_bridge:
                        self._write_cors(503, {"error": "code agent not configured"})
                        return
                    sid = path.split("/api/mc/code/sessions/", 1)[1].split("/prompt")[0]
                    message = body.get("message", "")
                    if not message:
                        self._write_cors(400, {"error": "message is required"})
                        return
                    result = pi_bridge.send_prompt(sid, message)
                    self._write_cors(200, {"ok": True, "result": result})
                    return

                if path.startswith("/api/mc/code/sessions/") and path.endswith("/abort"):
                    if not pi_bridge:
                        self._write_cors(503, {"error": "code agent not configured"})
                        return
                    sid = path.split("/api/mc/code/sessions/", 1)[1].split("/abort")[0]
                    result = pi_bridge.abort(sid)
                    self._write_cors(200, {"ok": True, "result": result})
                    return

                if path.startswith("/api/mc/code/sessions/") and path.endswith("/respond-ui"):
                    if not pi_bridge:
                        self._write_cors(503, {"error": "code agent not configured"})
                        return
                    request_id = body.get("request_id", "")
                    if not request_id:
                        self._write_cors(400, {"error": "request_id is required"})
                        return
                    response = body.get("response", {})
                    pi_bridge.respond_ui(request_id, response)
                    self._write_cors(200, {"ok": True})
                    return

                self._write_cors(404, {"error": "not_found"})
            except KeyError as exc:
                self._write_cors(400, {"error": f"missing field: {exc}"})
            except ValueError as exc:
                self._write_cors(400, {"error": str(exc)})
            except Exception as exc:
                self._write_cors(500, {"error": str(exc)})

        def _mc_patch(self, parsed) -> None:
            path = parsed.path
            if not dashboard_svc:
                self._write_cors(503, {"error": "dashboard service not initialized"})
                return
            if not self._is_origin_allowed():
                self._write_cors(403, {"error": "origin_not_allowed"})
                return
            try:
                body = self._read_json()
            except Exception:
                return

            try:
                # PATCH /api/mc/beings/:id
                if path.startswith("/api/mc/beings/"):
                    bid = path.split("/api/mc/beings/", 1)[1].split("/")[0]
                    being = dashboard_svc.update_being(bid, body)
                    if not being:
                        self._write_cors(404, {"error": "being not found"})
                        return
                    self._write_cors(200, {"being": being})
                    return

                # PATCH /api/mc/chat/sessions/:id
                if path.startswith("/api/mc/chat/sessions/"):
                    sid = path.split("/api/mc/chat/sessions/", 1)[1].split("/")[0]
                    session = dashboard_svc.rename_session(sid, body.get("name", ""))
                    if not session:
                        self._write_cors(404, {"error": "session not found"})
                        return
                    self._write_cors(200, {"session": session})
                    return

                # PATCH /api/mc/tasks/:id
                if path.startswith("/api/mc/tasks/"):
                    tid = path.split("/api/mc/tasks/", 1)[1].split("/")[0]
                    task = dashboard_svc.update_task(
                        project_svc, tid,
                        status=body.get("status"),
                        priority=body.get("priority"),
                        owner_agent_id=body.get("owner_agent_id"),
                        assignees=body.get("assignees"),
                        title=body.get("title"),
                        description=body.get("description"),
                    )
                    self._write_cors(200, {"task": task})
                    return

                self._write_cors(404, {"error": "not_found"})
            except ValueError as exc:
                self._write_cors(400, {"error": str(exc)})
            except Exception as exc:
                self._write_cors(500, {"error": str(exc)})

        def _mc_delete(self, parsed) -> None:
            path = parsed.path
            if not dashboard_svc:
                self._write_cors(503, {"error": "dashboard service not initialized"})
                return
            if not self._is_origin_allowed():
                self._write_cors(403, {"error": "origin_not_allowed"})
                return

            try:
                # DELETE /api/mc/tasks/:id
                if path.startswith("/api/mc/tasks/"):
                    tid = path.split("/api/mc/tasks/", 1)[1].split("/")[0]
                    ok = dashboard_svc.delete_task(project_svc, tid)
                    if not ok:
                        self._write_cors(404, {"error": "task not found"})
                        return
                    self._write_cors(200, {"ok": True})
                    return

                # DELETE /api/mc/chat/sessions/:id
                if path.startswith("/api/mc/chat/sessions/"):
                    sid = path.split("/api/mc/chat/sessions/", 1)[1].split("/")[0]
                    ok = dashboard_svc.delete_session(sid)
                    if not ok:
                        self._write_cors(404, {"error": "session not found or is default"})
                        return
                    self._write_cors(200, {"ok": True})
                    return

                # DELETE /api/mc/chat/messages/:id
                if path.startswith("/api/mc/chat/messages/"):
                    mid = path.split("/api/mc/chat/messages/", 1)[1].split("/")[0]
                    ok = dashboard_svc.delete_message(mid)
                    if not ok:
                        self._write_cors(404, {"error": "message not found"})
                        return
                    self._write_cors(200, {"ok": True})
                    return

                # DELETE /api/mc/code/sessions/:id
                if path.startswith("/api/mc/code/sessions/"):
                    if not pi_bridge:
                        self._write_cors(503, {"error": "code agent not configured"})
                        return
                    sid = path.split("/api/mc/code/sessions/", 1)[1].split("/")[0]
                    ok = pi_bridge.delete_session(sid)
                    if not ok:
                        self._write_cors(404, {"error": "session not found"})
                        return
                    self._write_cors(200, {"ok": True})
                    return

                self._write_cors(404, {"error": "not_found"})
            except Exception as exc:
                self._write_cors(500, {"error": str(exc)})

        def _serve_deliverable(self, url_path: str) -> None:
            """Serve files from the deliverables/ directory."""
            # Sanitize: prevent path traversal
            clean = url_path.replace("\\", "/").lstrip("/")
            parts = clean.split("/")
            if len(parts) < 3 or ".." in parts:
                self._write_cors(404, {"error": "not found"})
                return
            fpath = PROJECT_ROOT / "projects" / clean
            if not fpath.is_file():
                self._write_cors(404, {"error": "file not found"})
                return
            content_type, _ = mimetypes.guess_type(str(fpath))
            content_type = content_type or "text/plain"
            try:
                data = fpath.read_bytes()
            except Exception:
                self._write_cors(500, {"error": "read error"})
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

        def _mc_code_sse_stream(self, session_id: str) -> None:
            """SSE endpoint for Code tab — streams Pi agent events for a session."""
            if not pi_bridge:
                self._write_cors(503, {"error": "code agent not configured"})
                return

            sub_id, event_queue = pi_bridge.subscribe(session_id)
            self.send_response(200)
            allowed_origin = self._cors_origin()
            if allowed_origin:
                self.send_header("Access-Control-Allow-Origin", allowed_origin)
                self.send_header("Vary", "Origin")
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            try:
                while True:
                    try:
                        evt = event_queue.get(timeout=20.0)
                    except Exception:
                        # keepalive
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        continue
                    # Filter to requested session
                    if evt.session_id != session_id:
                        continue
                    data = json.dumps({
                        "session_id": evt.session_id,
                        "event_type": evt.event_type,
                        "data": evt.data,
                        "timestamp": evt.timestamp,
                    }, default=str)
                    self.wfile.write(f"event: {evt.event_type}\n".encode())
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                pi_bridge.unsubscribe(sub_id)

        def _mc_sse_stream(self) -> None:
            """SSE endpoint — holds connection open, pushes events."""
            if not dashboard_svc:
                self._write_cors(503, {"error": "dashboard service not initialized"})
                return

            client_id = dashboard_svc.subscribe_sse()
            self.send_response(200)
            allowed_origin = self._cors_origin()
            if allowed_origin:
                self.send_header("Access-Control-Allow-Origin", allowed_origin)
                self.send_header("Vary", "Origin")
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            try:
                while True:
                    evt = dashboard_svc.poll_sse(client_id, timeout=20.0)
                    if evt is None:
                        # keepalive comment
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        continue
                    line = json.dumps(evt["data"], default=str)
                    self.wfile.write(f"event: {evt['event']}\n".encode())
                    self.wfile.write(f"data: {line}\n\n".encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                dashboard_svc.unsubscribe_sse(client_id)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return Handler


def main() -> int:
    args = parse_args()
    env_path = Path(__file__).resolve().parent.parent / ".env"
    env_example = Path(__file__).resolve().parent.parent / ".env.example"
    if not env_path.exists() and env_example.exists():
        import shutil
        shutil.copy2(env_example, env_path)
        print("INFO: Created .env from .env.example — fill in your API keys (especially OPENROUTER_API_KEY)")
    _load_dotenv(env_path)
    # Validate critical API key
    _or_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not _or_key or _or_key.startswith("<") or _or_key == "your-openrouter-key":
        print("WARNING: OPENROUTER_API_KEY is not set or still a placeholder.")
        print("         Edit .env and set a valid key, or LLM calls will return 401 errors.")
        print("         Get a key at https://openrouter.ai/keys")
    bridge = RuntimeBridge()
    worker_factory = SubAgentWorkerFactory(bridge=bridge)

    # Bootstrap Mission Control dashboard service
    dashboard_svc = None
    project_svc = None
    try:
        from bomba_sr.dashboard.service import DashboardService
        from bomba_sr.projects.service import ProjectService
        from bomba_sr.storage.db import RuntimeDB

        runtime_home = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime"))
        runtime_home.mkdir(parents=True, exist_ok=True)
        mc_db = RuntimeDB(runtime_home / "bomba_runtime.db")
        project_svc = ProjectService(mc_db)
        dashboard_svc = DashboardService(db=mc_db, bridge=bridge)
        dashboard_svc.ensure_mc_project(project_svc)
        # Wire artifact store for dashboard artifact tracking
        from bomba_sr.artifacts.store import ArtifactStore
        artifacts_root = runtime_home / "artifacts"
        artifact_store = ArtifactStore(mc_db, artifacts_root)
        dashboard_svc.set_artifact_store(artifact_store)
        artifact_store.set_on_created(dashboard_svc.notify_artifact_created)
        loaded = dashboard_svc.load_beings_from_configs()
        dashboard_svc.init_orchestration(project_svc)
        print(f"mission control: loaded {loaded} beings from configs")
        print("mission control: dashboard service ready (orchestration enabled)")
    except Exception as exc:
        print(f"mission control: init failed ({exc}), MC endpoints disabled")

    # Bootstrap Pi coding agent bridge (Code tab)
    pi_bridge = None
    try:
        from bomba_sr.dashboard.pi_bridge import PiBridge

        _pi_model = os.getenv("BOMBA_PI_MODEL", "openrouter/anthropic/claude-sonnet-4")
        _pi_tools = os.getenv("BOMBA_PI_TOOLS", "read,bash,edit,write,grep,find,ls")
        _pi_thinking = os.getenv("BOMBA_PI_THINKING", "off")
        _pi_enabled = os.getenv("BOMBA_PI_ENABLED", "true").lower() in ("1", "true", "yes")

        if _pi_enabled:
            _workspace = str(Path(__file__).resolve().parent.parent)
            _env_file = Path(_workspace) / ".env"

            def _pi_event_to_sse(evt):
                """Forward Pi events to dashboard SSE for global listeners."""
                if dashboard_svc:
                    dashboard_svc._emit_event(evt.event_type, {
                        "session_id": evt.session_id,
                        **evt.data,
                    })

            pi_bridge = PiBridge(
                workspace_root=_workspace,
                model=_pi_model,
                tools=_pi_tools,
                thinking=_pi_thinking,
                env_file=str(_env_file) if _env_file.exists() else None,
                on_event=_pi_event_to_sse,
            )
            print(f"mission control: code agent ready (model={_pi_model})")
        else:
            print("mission control: code agent disabled (BOMBA_PI_ENABLED=false)")
    except Exception as exc:
        print(f"mission control: code agent init failed ({exc}), Code tab disabled")

    server = ThreadingHTTPServer(
        (args.host, args.port),
        make_handler(bridge, dashboard_svc=dashboard_svc, project_svc=project_svc, pi_bridge=pi_bridge),
    )
    print(f"runtime server listening on http://{args.host}:{args.port}")
    print(f"mission control dashboard: http://127.0.0.1:5173  (start with: cd mission-control && npx vite)")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
