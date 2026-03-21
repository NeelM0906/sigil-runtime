"""FastAPI application — coexists with the legacy ThreadingHTTPServer."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
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
        from bomba_sr.storage.db import RuntimeDB

        runtime_home = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime"))
        runtime_home.mkdir(parents=True, exist_ok=True)
        mc_db = RuntimeDB(runtime_home / "bomba_runtime.db")
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
    except Exception as exc:
        logger.warning("mission control init failed (%s), MC endpoints disabled", exc)

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
    from bomba_sr.api.routers import auth, chat, tasks
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(tasks.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
