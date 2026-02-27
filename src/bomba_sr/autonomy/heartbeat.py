from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


HeartbeatRunner = Callable[[str], dict[str, Any] | None]


class HeartbeatEngine:
    def __init__(
        self,
        tenant_id: str,
        user_id: str,
        workspace_root: Path,
        runner: HeartbeatRunner,
        interval_seconds: int = 1800,
    ) -> None:
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.workspace_root = Path(workspace_root)
        self.runner = runner
        self.interval_seconds = max(1, int(interval_seconds))
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._runs = 0
        self._last_run_at: str | None = None
        self._last_result: dict[str, Any] | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        if self.is_running():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"bomba-heartbeat-{self.tenant_id}",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        self._thread = None

    def is_running(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    def run_once(self) -> dict[str, Any]:
        heartbeat_md = self._load_heartbeat_md()
        if not heartbeat_md:
            with self._lock:
                self._last_error = "heartbeat_file_missing"
            return {"ran": False, "reason": "heartbeat_file_missing"}

        try:
            result = self.runner(heartbeat_md) or {}
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
                self._last_run_at = datetime.now(timezone.utc).isoformat()
            return {"ran": False, "reason": "runner_error", "error": str(exc)}

        with self._lock:
            self._runs += 1
            self._last_result = result
            self._last_error = None
            self._last_run_at = datetime.now(timezone.utc).isoformat()
        return {"ran": True, "result": result}

    def status(self) -> dict[str, Any]:
        has_heartbeat_file = bool(self._load_heartbeat_md())
        with self._lock:
            return {
                "running": self.is_running(),
                "interval_seconds": self.interval_seconds,
                "runs": self._runs,
                "last_run_at": self._last_run_at,
                "last_error": self._last_error,
                "has_heartbeat_file": has_heartbeat_file,
                "last_result": self._last_result,
            }

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self.run_once()

    def _load_heartbeat_md(self) -> str | None:
        path = self.workspace_root / "HEARTBEAT.md"
        if not path.exists():
            return None
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return content or None
