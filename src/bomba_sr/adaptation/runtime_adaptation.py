from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from bomba_sr.storage.db import RuntimeDB


@dataclass(frozen=True)
class RuntimeMetrics:
    period_start: str
    period_end: str
    retrieval_precision_at_k: float
    search_escalation_rate: float
    subagent_success_rate: float
    subagent_p95_latency_ms: int
    loop_detector_incidents: int
    prediction_brier_score: float | None
    prediction_ece: float | None


class RuntimeAdaptationEngine:
    def __init__(self, db: RuntimeDB):
        self.db = db
        self._turn_counts: dict[str, int] = {}
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS raw_search_metrics (
              id TEXT PRIMARY KEY,
              escalated INTEGER NOT NULL,
              precision_at_k REAL,
              execution_ms INTEGER NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS raw_subagent_metrics (
              id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              runtime_ms INTEGER,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS raw_prediction_metrics (
              id TEXT PRIMARY KEY,
              brier_score REAL,
              ece REAL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS raw_loop_incidents (
              id TEXT PRIMARY KEY,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runtime_metrics_rollup (
              id TEXT PRIMARY KEY,
              period_start TEXT NOT NULL,
              period_end TEXT NOT NULL,
              retrieval_precision_at_k REAL,
              search_escalation_rate REAL,
              subagent_success_rate REAL,
              subagent_p95_latency_ms INTEGER,
              loop_detector_incidents INTEGER NOT NULL DEFAULT 0,
              prediction_brier_score REAL,
              prediction_ece REAL,
              created_at TEXT NOT NULL,
              UNIQUE(period_start, period_end)
            );

            CREATE TABLE IF NOT EXISTS policy_versions (
              id TEXT PRIMARY KEY,
              policy_name TEXT NOT NULL,
              version INTEGER NOT NULL,
              policy_json TEXT NOT NULL,
              diff_json TEXT NOT NULL,
              reason TEXT,
              rolled_back_from INTEGER,
              created_at TEXT NOT NULL,
              UNIQUE(policy_name, version)
            );

            CREATE INDEX IF NOT EXISTS idx_policy_versions_name_ver
              ON policy_versions(policy_name, version DESC);
            """
        )
        self.db.commit()

    def ingest_search_metric(self, escalated: bool, precision_at_k: float | None, execution_ms: int, created_at: str | None = None) -> None:
        self.db.execute(
            "INSERT INTO raw_search_metrics (id, escalated, precision_at_k, execution_ms, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), int(escalated), precision_at_k, execution_ms, created_at or self._now()),
        )
        self.db.commit()

    def ingest_subagent_metric(self, status: str, runtime_ms: int | None, created_at: str | None = None) -> None:
        self.db.execute(
            "INSERT INTO raw_subagent_metrics (id, status, runtime_ms, created_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), status, runtime_ms, created_at or self._now()),
        )
        self.db.commit()

    def ingest_prediction_metric(self, brier_score: float | None, ece: float | None, created_at: str | None = None) -> None:
        self.db.execute(
            "INSERT INTO raw_prediction_metrics (id, brier_score, ece, created_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), brier_score, ece, created_at or self._now()),
        )
        self.db.commit()

    def ingest_loop_incident(self, created_at: str | None = None) -> None:
        self.db.execute(
            "INSERT INTO raw_loop_incidents (id, created_at) VALUES (?, ?)",
            (str(uuid.uuid4()), created_at or self._now()),
        )
        self.db.commit()

    def aggregate_period(self, period_start: str, period_end: str) -> RuntimeMetrics:
        search_rows = self.db.execute(
            "SELECT escalated, precision_at_k FROM raw_search_metrics WHERE created_at >= ? AND created_at < ?",
            (period_start, period_end),
        ).fetchall()
        sub_rows = self.db.execute(
            "SELECT status, runtime_ms FROM raw_subagent_metrics WHERE created_at >= ? AND created_at < ?",
            (period_start, period_end),
        ).fetchall()
        pred_rows = self.db.execute(
            "SELECT brier_score, ece FROM raw_prediction_metrics WHERE created_at >= ? AND created_at < ?",
            (period_start, period_end),
        ).fetchall()
        loop_row = self.db.execute(
            "SELECT COUNT(*) AS c FROM raw_loop_incidents WHERE created_at >= ? AND created_at < ?",
            (period_start, period_end),
        ).fetchone()

        escalations = [int(r["escalated"]) for r in search_rows]
        precisions = [float(r["precision_at_k"]) for r in search_rows if r["precision_at_k"] is not None]
        escalation_rate = (sum(escalations) / len(escalations)) if escalations else 0.0
        retrieval_precision = (sum(precisions) / len(precisions)) if precisions else 0.0

        terminal = [r for r in sub_rows if str(r["status"]) in {"completed", "failed", "timed_out"}]
        completed = [r for r in terminal if str(r["status"]) == "completed"]
        success_rate = (len(completed) / len(terminal)) if terminal else 0.0

        runtimes = sorted(int(r["runtime_ms"]) for r in sub_rows if r["runtime_ms"] is not None)
        p95 = self._p95(runtimes)

        briers = [float(r["brier_score"]) for r in pred_rows if r["brier_score"] is not None]
        eces = [float(r["ece"]) for r in pred_rows if r["ece"] is not None]

        metrics = RuntimeMetrics(
            period_start=period_start,
            period_end=period_end,
            retrieval_precision_at_k=retrieval_precision,
            search_escalation_rate=escalation_rate,
            subagent_success_rate=success_rate,
            subagent_p95_latency_ms=p95,
            loop_detector_incidents=int(loop_row["c"]) if loop_row is not None else 0,
            prediction_brier_score=(sum(briers) / len(briers)) if briers else None,
            prediction_ece=(sum(eces) / len(eces)) if eces else None,
        )

        self.db.execute(
            """
            INSERT INTO runtime_metrics_rollup (
              id, period_start, period_end, retrieval_precision_at_k, search_escalation_rate,
              subagent_success_rate, subagent_p95_latency_ms, loop_detector_incidents,
              prediction_brier_score, prediction_ece, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(period_start, period_end) DO UPDATE SET
              retrieval_precision_at_k=excluded.retrieval_precision_at_k,
              search_escalation_rate=excluded.search_escalation_rate,
              subagent_success_rate=excluded.subagent_success_rate,
              subagent_p95_latency_ms=excluded.subagent_p95_latency_ms,
              loop_detector_incidents=excluded.loop_detector_incidents,
              prediction_brier_score=excluded.prediction_brier_score,
              prediction_ece=excluded.prediction_ece
            """,
            (
                str(uuid.uuid4()),
                metrics.period_start,
                metrics.period_end,
                metrics.retrieval_precision_at_k,
                metrics.search_escalation_rate,
                metrics.subagent_success_rate,
                metrics.subagent_p95_latency_ms,
                metrics.loop_detector_incidents,
                metrics.prediction_brier_score,
                metrics.prediction_ece,
                self._now(),
            ),
        )
        self.db.commit()
        return metrics

    def update_policy(self, policy_name: str, new_policy: dict[str, Any], reason: str | None = None) -> dict[str, Any]:
        latest = self._latest_policy(policy_name)
        if latest is None:
            version = 1
            prev_policy: dict[str, Any] = {}
        else:
            version = int(latest["version"]) + 1
            prev_policy = json.loads(str(latest["policy_json"]))

        diff = self._diff(prev_policy, new_policy)
        row_id = str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO policy_versions (
              id, policy_name, version, policy_json, diff_json, reason, rolled_back_from, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                row_id,
                policy_name,
                version,
                json.dumps(new_policy, sort_keys=True),
                json.dumps(diff, sort_keys=True),
                reason,
                self._now(),
            ),
        )
        self.db.commit()
        return {
            "id": row_id,
            "policy_name": policy_name,
            "version": version,
            "diff": diff,
            "policy": new_policy,
        }

    def rollback_policy(self, policy_name: str, target_version: int | None = None, reason: str | None = None) -> dict[str, Any]:
        latest = self._latest_policy(policy_name)
        if latest is None:
            raise ValueError(f"No policy versions found for {policy_name}")

        latest_version = int(latest["version"])
        if target_version is None:
            target_version = latest_version - 1
        if target_version < 1:
            raise ValueError("No earlier policy version available for rollback")

        target = self.db.execute(
            "SELECT * FROM policy_versions WHERE policy_name = ? AND version = ?",
            (policy_name, target_version),
        ).fetchone()
        if target is None:
            raise ValueError(f"Target version not found: {target_version}")

        target_policy = json.loads(str(target["policy_json"]))
        created = self.update_policy(policy_name, target_policy, reason=reason or f"rollback_to_{target_version}")
        self.db.execute(
            "UPDATE policy_versions SET rolled_back_from = ? WHERE id = ?",
            (latest_version, created["id"]),
        )
        self.db.commit()
        created["rolled_back_from"] = latest_version
        return created

    def detect_regression(self, policy_name: str, window: int = 2) -> dict[str, Any]:
        rows = self.db.execute(
            "SELECT * FROM runtime_metrics_rollup ORDER BY period_end DESC LIMIT ?",
            (window,),
        ).fetchall()
        if len(rows) < 2:
            return {"regression": False, "reasons": [], "policy_name": policy_name}

        latest = rows[0]
        prior = rows[1]
        reasons: list[str] = []

        if float(latest["retrieval_precision_at_k"] or 0) < float(prior["retrieval_precision_at_k"] or 0):
            reasons.append("retrieval_precision_declined")
        if float(latest["search_escalation_rate"] or 0) > float(prior["search_escalation_rate"] or 0):
            reasons.append("search_escalation_increased")
        if float(latest["subagent_success_rate"] or 0) < float(prior["subagent_success_rate"] or 0):
            reasons.append("subagent_success_declined")
        if int(latest["loop_detector_incidents"] or 0) > int(prior["loop_detector_incidents"] or 0):
            reasons.append("loop_incidents_increased")

        return {
            "regression": len(reasons) >= 2,
            "reasons": reasons,
            "policy_name": policy_name,
            "latest_period_end": latest["period_end"],
        }

    def get_policy(self, policy_name: str) -> dict[str, Any] | None:
        latest = self._latest_policy(policy_name)
        if latest is None:
            return None
        return {
            "policy_name": policy_name,
            "version": int(latest["version"]),
            "policy": json.loads(str(latest["policy_json"])),
            "diff": json.loads(str(latest["diff_json"])),
            "reason": latest["reason"],
            "rolled_back_from": latest["rolled_back_from"],
            "created_at": latest["created_at"],
        }

    def increment_turn(self, session_id: str) -> int:
        key = (session_id or "session-default").strip() or "session-default"
        next_turn = int(self._turn_counts.get(key, 0)) + 1
        self._turn_counts[key] = next_turn
        return next_turn

    def ingest_turn_metrics(self, session_id: str) -> int:
        return self.increment_turn(session_id)

    def check_and_correct(self, policy_name: str) -> dict[str, Any]:
        verdict = self.detect_regression(policy_name=policy_name, window=2)
        reasons = list(verdict.get("reasons") or [])
        latest = self.get_policy(policy_name) or {
            "version": 0,
            "policy": {},
        }
        current_policy = dict(latest.get("policy") or {})

        if bool(verdict.get("regression")):
            latest_version = int(latest.get("version") or 0)
            if latest_version >= 2:
                rollback = self.rollback_policy(
                    policy_name=policy_name,
                    reason="metrics_regression_autocorrect",
                )
                return {
                    "action": "rollback",
                    "reasons": reasons,
                    "target_version": int(rollback["version"]),
                    "rolled_back_from": int(rollback.get("rolled_back_from") or latest_version),
                    "policy": rollback["policy"],
                }

            adjustments = self._targeted_adjustments(current_policy, reasons)
            if adjustments:
                merged = dict(current_policy)
                merged.update(adjustments)
                created = self.update_policy(
                    policy_name=policy_name,
                    new_policy=merged,
                    reason="metrics_regression_adjust",
                )
                return {
                    "action": "adjust",
                    "reasons": reasons,
                    "adjustments": adjustments,
                    "target_version": int(created["version"]),
                    "policy": created["policy"],
                }

            return {
                "action": "none",
                "reasons": reasons,
                "target_version": int(latest.get("version") or 0),
                "policy": current_policy,
            }

        if len(reasons) == 1:
            adjustments = self._targeted_adjustments(current_policy, reasons)
            if adjustments:
                merged = dict(current_policy)
                merged.update(adjustments)
                created = self.update_policy(
                    policy_name=policy_name,
                    new_policy=merged,
                    reason="metrics_targeted_adjust",
                )
                return {
                    "action": "adjust",
                    "reasons": reasons,
                    "adjustments": adjustments,
                    "target_version": int(created["version"]),
                    "policy": created["policy"],
                }

        return {
            "action": "none",
            "reasons": reasons,
            "target_version": int(latest.get("version") or 0),
            "policy": current_policy,
        }

    def _latest_policy(self, policy_name: str):
        return self.db.execute(
            "SELECT * FROM policy_versions WHERE policy_name = ? ORDER BY version DESC LIMIT 1",
            (policy_name,),
        ).fetchone()

    @staticmethod
    def _targeted_adjustments(current_policy: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
        out: dict[str, Any] = {}

        if "loop_incidents_increased" in reasons:
            current_window = int(current_policy.get("loop_detection_window", 5))
            out["loop_detection_window"] = min(20, max(1, current_window + 1))

        if "search_escalation_increased" in reasons:
            current_budget = float(current_policy.get("budget_hard_stop_pct", 0.9))
            out["budget_hard_stop_pct"] = max(0.5, min(1.0, round(current_budget - 0.05, 2)))

        if "subagent_success_declined" in reasons:
            current_depth = int(current_policy.get("subagent_max_spawn_depth", 3))
            out["subagent_max_spawn_depth"] = max(1, current_depth - 1)

        if "retrieval_precision_declined" in reasons:
            current_iterations = int(current_policy.get("max_loop_iterations", 25))
            out["max_loop_iterations"] = max(5, current_iterations - 1)

        return out

    @staticmethod
    def _diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        diff: dict[str, Any] = {}
        keys = set(old.keys()) | set(new.keys())
        for key in sorted(keys):
            ov = old.get(key, "__missing__")
            nv = new.get(key, "__missing__")
            if ov == nv:
                continue
            if isinstance(ov, dict) and isinstance(nv, dict):
                nested = RuntimeAdaptationEngine._diff(ov, nv)
                if nested:
                    diff[key] = nested
            else:
                diff[key] = {"old": ov, "new": nv}
        return diff

    @staticmethod
    def _p95(values: list[int]) -> int:
        if not values:
            return 0
        idx = max(0, math.ceil(0.95 * len(values)) - 1)
        return values[idx]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
