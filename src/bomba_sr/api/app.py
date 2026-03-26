"""FastAPI application — coexists with the legacy ThreadingHTTPServer."""
from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize bridge, dashboard_svc, project_svc on startup."""
    from bomba_sr.runtime.bridge import RuntimeBridge

    bridge = RuntimeBridge()
    app.state.bridge = bridge

    dashboard_svc = None
    project_svc = None
    try:
        from bomba_sr.artifacts.store import ArtifactStore
        from bomba_sr.dashboard.service import DashboardService
        from bomba_sr.projects.service import ProjectService
        from bomba_sr.storage.factory import create_shared_db

        mc_db = create_shared_db()
        runtime_home = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime"))
        runtime_home.mkdir(parents=True, exist_ok=True)
        project_svc = ProjectService(mc_db)
        dashboard_svc = DashboardService(db=mc_db, bridge=bridge)
        dashboard_svc.ensure_mc_project(project_svc)

        artifacts_root = runtime_home / "artifacts"
        artifact_store = ArtifactStore(mc_db, artifacts_root)
        dashboard_svc.set_artifact_store(artifact_store)
        artifact_store.set_on_created(dashboard_svc.notify_artifact_created)

        # Purge expired auth tokens
        purged = mc_db.execute_commit(
            "DELETE FROM mc_sessions_auth WHERE expires_at < ?",
            (datetime.now(timezone.utc).isoformat(),),
        ).rowcount
        if purged:
            logger.info("purged %d expired auth token(s)", purged)

        loaded = dashboard_svc.load_beings_from_configs()
        dashboard_svc.init_orchestration(project_svc)
        logger.info("mission control: loaded %d beings, orchestration ready", loaded)

        # Cleanup tasks stuck in_progress from a previous crash/restart
        stale = dashboard_svc.cleanup_stale_tasks(max_age_hours=2)
        if stale:
            logger.info("cleaned up %d stale in_progress tasks on startup", stale)

        # Periodic cleanup of stuck tasks (every hour)
        def _periodic_task_cleanup():
            import time as _time
            while True:
                _time.sleep(3600)
                try:
                    dashboard_svc.cleanup_stale_tasks(max_age_hours=2)
                except Exception:
                    pass

        threading.Thread(target=_periodic_task_cleanup, daemon=True, name="task-cleanup").start()
    except Exception as exc:
        import traceback
        logger.warning("mission control init failed (%s), MC endpoints disabled", exc)
        logger.warning("".join(traceback.format_exception(exc)))

    # Wire WebSocket manager into dashboard service
    from bomba_sr.api.ws import manager as ws_manager
    if dashboard_svc is not None:
        dashboard_svc._ws_manager = ws_manager
    app.state.ws_manager = ws_manager

    app.state.dashboard_svc = dashboard_svc
    app.state.project_svc = project_svc

    yield  # app is running


def create_app() -> FastAPI:
    app = FastAPI(title="Bomba SR", version="0.1.0", lifespan=lifespan)

    # CORS — same env var as the legacy server
    origins = [
        o.strip()
        for o in os.getenv(
            "BOMBA_CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    from bomba_sr.api.routers import (
        acti, admin, auth, beings, chat, cron, deliverables,
        events, orchestration, projects, skills, subagents, tasks, teams, upload,
    )
    app.include_router(acti.router)
    app.include_router(admin.router)
    app.include_router(auth.router)
    app.include_router(beings.router)
    app.include_router(chat.router)
    app.include_router(cron.router)
    app.include_router(deliverables.router)
    app.include_router(events.router)
    app.include_router(orchestration.router)
    app.include_router(projects.router)
    app.include_router(skills.router)
    app.include_router(subagents.router)
    app.include_router(tasks.router)
    app.include_router(teams.router)
    app.include_router(upload.router)

    # WebSocket endpoint for real-time events (replaces SSE as primary transport)
    from bomba_sr.api.ws import websocket_endpoint

    @app.websocket("/ws")
    async def ws_route(websocket: WebSocket, token: str = Query("")):
        await websocket_endpoint(websocket, token=token)

    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        body = await request.body()
        logger.error("422 on %s %s — body=%s errors=%s", request.method, request.url.path, body[:500], exc.errors())
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.get("/health")
    def health():
        import threading as _threading
        active = _threading.active_count()
        llm_threads = sum(1 for t in _threading.enumerate() if t.name.startswith("llm-"))
        route_threads = sum(1 for t in _threading.enumerate() if t.name.startswith("route-"))
        return {
            "status": "ok" if active < 100 else "degraded",
            "threads": active,
            "llm_active": llm_threads,
            "route_active": route_threads,
        }

    # ── Serve mission-control frontend (SPA with fallback) ───────────
    MC_DIST = Path(__file__).resolve().parent.parent.parent.parent / "mission-control" / "dist"
    if MC_DIST.is_dir():
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse

        # Serve /assets/* directly
        assets_dir = MC_DIST / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # SPA fallback: any non-API, non-asset path serves index.html
        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            from starlette.responses import Response
            file_path = MC_DIST / full_path
            if full_path and file_path.is_file() and ".." not in full_path:
                return FileResponse(str(file_path))
            # No-cache on index.html so deploys take effect immediately
            resp = FileResponse(str(MC_DIST / "index.html"))
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp

    return app


app = create_app()
