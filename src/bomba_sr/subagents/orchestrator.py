from __future__ import annotations

import logging
import threading
import time
import traceback
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

from bomba_sr.subagents.protocol import SubAgentProtocol, SubAgentTask


SubAgentWorker = Callable[[str, SubAgentTask, SubAgentProtocol], dict[str, Any]]
logger = logging.getLogger(__name__)


@dataclass
class CrashStormConfig:
    window_seconds: float = 60.0
    max_crashes: int = 3
    cooldown_seconds: float = 120.0


class CrashStormDetector:
    def __init__(self, config: CrashStormConfig | None = None):
        self.config = config or CrashStormConfig()
        self._crashes: deque[float] = deque()
        self._cooldown_until: float = 0.0
        self._lock = threading.Lock()

    def record_crash(self) -> bool:
        now = time.time()
        with self._lock:
            self._crashes.append(now)
            cutoff = now - self.config.window_seconds
            while self._crashes and self._crashes[0] < cutoff:
                self._crashes.popleft()
            if len(self._crashes) >= self.config.max_crashes:
                self._cooldown_until = now + self.config.cooldown_seconds
                return True
        return False

    def is_in_cooldown(self) -> bool:
        return time.time() < self._cooldown_until

    def reset(self) -> None:
        with self._lock:
            self._crashes.clear()
            self._cooldown_until = 0.0


@dataclass
class SubAgentHandle:
    run_id: str
    future: Future[dict[str, Any]]


class SubAgentOrchestrator:
    def __init__(
        self,
        protocol: SubAgentProtocol,
        max_workers: int = 8,
        crash_storm_config: CrashStormConfig | None = None,
    ):
        self.protocol = protocol
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="bomba-subagent")
        self.crash_detector = CrashStormDetector(crash_storm_config)
        self._futures: set[Future[dict[str, Any]]] = set()
        self._futures_lock = threading.Lock()

    def spawn_async(
        self,
        task: SubAgentTask,
        parent_session_id: str,
        parent_turn_id: str,
        parent_agent_id: str,
        child_agent_id: str,
        worker: SubAgentWorker,
        parent_run_id: str | None = None,
    ) -> SubAgentHandle:
        if self.crash_detector.is_in_cooldown():
            raise RuntimeError("Sub-agent spawn blocked: crash storm cooldown active")
        run = self.protocol.spawn(
            task=task,
            parent_session_id=parent_session_id,
            parent_turn_id=parent_turn_id,
            parent_agent_id=parent_agent_id,
            child_agent_id=child_agent_id,
            parent_run_id=parent_run_id,
        )
        run_id = str(run["run_id"])

        future = self.executor.submit(
            self._run_worker,
            run_id,
            task,
            worker,
        )
        with self._futures_lock:
            self._futures.add(future)
        future.add_done_callback(self._on_future_done)
        return SubAgentHandle(run_id=run_id, future=future)

    def _run_worker(self, run_id: str, task: SubAgentTask, worker: SubAgentWorker) -> dict[str, Any]:
        self.protocol.start(run_id)
        try:
            result = worker(run_id, task, self.protocol)
            summary = str(result.get("summary") or "completed")
            artifacts = result.get("artifacts") if isinstance(result.get("artifacts"), dict) else None
            runtime_ms = int(result.get("runtime_ms") or 0)
            token_usage = result.get("token_usage")
            if not isinstance(token_usage, dict):
                token_usage = None
            self.protocol.complete(
                run_id=run_id,
                summary=summary,
                artifacts=artifacts,
                runtime_ms=runtime_ms,
                token_usage=token_usage,
            )
            return result
        except Exception as exc:  # pragma: no cover - defensive path
            self.protocol.fail(run_id=run_id, reason=f"{exc}\n{traceback.format_exc()}")
            if self.crash_detector.record_crash():
                logger.warning("Sub-agent crash storm detected. Entering cooldown and cancelling pending futures.")
                self._cancel_pending_futures()
            raise

    def _on_future_done(self, future: Future[dict[str, Any]]) -> None:
        with self._futures_lock:
            self._futures.discard(future)

    def _cancel_pending_futures(self) -> None:
        with self._futures_lock:
            pending = list(self._futures)
        for future in pending:
            if not future.done():
                future.cancel()
