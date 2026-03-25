from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from bomba_sr.governance.tool_profiles import resolve_alias
from bomba_sr.storage.db import RuntimeDB


RISK_LEVELS = {"low", "medium", "high", "critical"}

DEFAULT_MIN_CONFIDENCE = {
    "low": 0.2,
    "medium": 0.4,
    "high": 0.75,
    "critical": 0.99,
}

VALID_APPROVAL_STATUS = {"pending", "approved", "rejected", "expired", "cancelled"}


@dataclass(frozen=True)
class GovernanceDecision:
    policy_action: str
    allowed: bool
    requires_approval: bool
    reason: str
    approval_id: str | None = None


class ToolGovernanceService:
    def __init__(self, db: RuntimeDB):
        self.db = db
        self._tool_classifications: dict[str, tuple[str, str]] = {}
        self._ensure_schema()
        self._register_default_classifications()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS tool_governance_policies (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              policy_name TEXT NOT NULL,
              version INTEGER NOT NULL,
              policy_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(tenant_id, policy_name, version)
            );

            CREATE TABLE IF NOT EXISTS approval_queue (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              session_id TEXT,
              turn_id TEXT,
              action_type TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              risk_class TEXT NOT NULL,
              confidence REAL NOT NULL,
              status TEXT NOT NULL,
              reason TEXT,
              decided_by TEXT,
              requested_at TEXT NOT NULL,
              decided_at TEXT,
              expires_at TEXT
            );

            CREATE TABLE IF NOT EXISTS tool_audit_logs (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              session_id TEXT,
              turn_id TEXT,
              action_type TEXT NOT NULL,
              tool_name TEXT,
              backend TEXT,
              risk_class TEXT,
              confidence REAL,
              policy_action TEXT,
              payload_hash TEXT,
              outcome_json TEXT,
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_approval_tenant_status
              ON approval_queue(tenant_id, status, requested_at DESC);

            CREATE INDEX IF NOT EXISTS idx_tool_audit_tenant
              ON tool_audit_logs(tenant_id, created_at DESC);
            """
        )
        self.db.commit()

    def classify_tool(self, tool_name: str) -> tuple[str, str]:
        canonical = resolve_alias(tool_name)
        return self._tool_classifications.get(canonical, ("write", "medium"))

    def register_classification(self, tool_name: str, action_type: str, risk_class: str) -> None:
        if risk_class not in RISK_LEVELS:
            raise ValueError("invalid risk_class")
        self._tool_classifications[resolve_alias(tool_name)] = (str(action_type), str(risk_class))

    def evaluate(
        self,
        tenant_id: str,
        action_type: str,
        risk_class: str,
        confidence: float,
        payload: dict[str, Any],
        session_id: str | None,
        turn_id: str | None,
        reason: str | None = None,
    ) -> GovernanceDecision:
        if risk_class not in RISK_LEVELS:
            raise ValueError("invalid risk_class")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be in [0,1]")

        if action_type == "execute_shell_command" and confidence < 0.999:
            decision = GovernanceDecision(
                policy_action="deny",
                allowed=False,
                requires_approval=False,
                reason="critical_shell_command_denied_by_default",
            )
            self._audit(
                tenant_id=tenant_id,
                session_id=session_id,
                turn_id=turn_id,
                action_type=action_type,
                tool_name=payload.get("tool_name"),
                backend=str(payload.get("backend") or ""),
                risk_class=risk_class,
                confidence=confidence,
                policy_action=decision.policy_action,
                payload=payload,
                outcome={"decision": decision.reason},
            )
            return decision

        threshold = self._threshold_for(tenant_id, risk_class)
        if confidence >= threshold:
            decision = GovernanceDecision(
                policy_action="allow",
                allowed=True,
                requires_approval=False,
                reason=f"confidence_{confidence:.2f}_meets_{threshold:.2f}",
            )
            self._audit(
                tenant_id=tenant_id,
                session_id=session_id,
                turn_id=turn_id,
                action_type=action_type,
                tool_name=payload.get("tool_name"),
                backend=str(payload.get("backend") or ""),
                risk_class=risk_class,
                confidence=confidence,
                policy_action=decision.policy_action,
                payload=payload,
                outcome={"decision": decision.reason},
            )
            return decision

        approval_id = self._enqueue_approval(
            tenant_id=tenant_id,
            session_id=session_id,
            turn_id=turn_id,
            action_type=action_type,
            payload=payload,
            risk_class=risk_class,
            confidence=confidence,
            reason=reason or f"confidence_{confidence:.2f}_below_{threshold:.2f}",
        )
        decision = GovernanceDecision(
            policy_action="require_approval",
            allowed=False,
            requires_approval=True,
            reason=f"approval_required:{approval_id}",
            approval_id=approval_id,
        )
        self._audit(
            tenant_id=tenant_id,
            session_id=session_id,
            turn_id=turn_id,
            action_type=action_type,
            tool_name=payload.get("tool_name"),
            backend=str(payload.get("backend") or ""),
            risk_class=risk_class,
            confidence=confidence,
            policy_action=decision.policy_action,
            payload=payload,
            outcome={"approval_id": approval_id},
        )
        return decision

    def list_pending_approvals(self, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        self._expire_approvals()
        rows = self.db.execute(
            """
            SELECT * FROM approval_queue
            WHERE tenant_id = ? AND status = 'pending'
            ORDER BY requested_at ASC
            LIMIT ?
            """,
            (tenant_id, limit),
        ).fetchall()
        return [self._approval_row(row) for row in rows]

    def get_approval(self, tenant_id: str, approval_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT * FROM approval_queue WHERE tenant_id = ? AND id = ?",
            (tenant_id, approval_id),
        ).fetchone()
        if row is None:
            return None
        return self._approval_row(row)

    def decide_approval(self, tenant_id: str, approval_id: str, approved: bool, decided_by: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT * FROM approval_queue WHERE id = ? AND tenant_id = ?",
            (approval_id, tenant_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"approval not found: {approval_id}")

        current = str(row["status"])
        if current not in {"pending"}:
            return self._approval_row(row)

        status = "approved" if approved else "rejected"
        self.db.execute(
            "UPDATE approval_queue SET status = ?, decided_by = ?, decided_at = ? WHERE id = ?",
            (status, decided_by, self._now(), approval_id),
        )
        self.db.commit()

        updated = self.db.execute("SELECT * FROM approval_queue WHERE id = ?", (approval_id,)).fetchone()
        return self._approval_row(updated)

    def _threshold_for(self, tenant_id: str, risk_class: str) -> float:
        row = self.db.execute(
            """
            SELECT policy_json FROM tool_governance_policies
            WHERE tenant_id = ? AND policy_name = 'default'
            ORDER BY version DESC LIMIT 1
            """,
            (tenant_id,),
        ).fetchone()
        if row is None:
            return DEFAULT_MIN_CONFIDENCE[risk_class]

        try:
            payload = json.loads(str(row["policy_json"]))
        except json.JSONDecodeError:
            return DEFAULT_MIN_CONFIDENCE[risk_class]

        threshold = payload.get("thresholds", {}).get(risk_class)
        if isinstance(threshold, (int, float)) and 0 <= float(threshold) <= 1:
            return float(threshold)
        return DEFAULT_MIN_CONFIDENCE[risk_class]

    def upsert_default_policy(self, tenant_id: str, thresholds: dict[str, float] | None = None) -> dict[str, Any]:
        merged = dict(DEFAULT_MIN_CONFIDENCE)
        for key, value in (thresholds or {}).items():
            if key in merged and isinstance(value, (int, float)) and 0 <= float(value) <= 1:
                merged[key] = float(value)

        latest = self.db.execute(
            "SELECT MAX(version) AS v FROM tool_governance_policies WHERE tenant_id = ? AND policy_name = 'default'",
            (tenant_id,),
        ).fetchone()
        next_version = (int(latest["v"]) + 1) if latest and latest["v"] is not None else 1
        policy = {"thresholds": merged}

        self.db.execute(
            """
            INSERT INTO tool_governance_policies (id, tenant_id, policy_name, version, policy_json, created_at)
            VALUES (?, ?, 'default', ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                tenant_id,
                next_version,
                json.dumps(policy, separators=(",", ":")),
                self._now(),
            ),
        )
        self.db.commit()
        return {
            "tenant_id": tenant_id,
            "policy_name": "default",
            "version": next_version,
            "thresholds": merged,
        }

    def _enqueue_approval(
        self,
        tenant_id: str,
        session_id: str | None,
        turn_id: str | None,
        action_type: str,
        payload: dict[str, Any],
        risk_class: str,
        confidence: float,
        reason: str,
        ttl_minutes: int = 60,
    ) -> str:
        approval_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=ttl_minutes)
        self.db.execute(
            """
            INSERT INTO approval_queue (
              id, tenant_id, session_id, turn_id, action_type, payload_json,
              risk_class, confidence, status, reason, requested_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (
                approval_id,
                tenant_id,
                session_id,
                turn_id,
                action_type,
                json.dumps(payload, separators=(",", ":")),
                risk_class,
                confidence,
                reason,
                now.isoformat(),
                expires_at.isoformat(),
            ),
        )
        self.db.commit()
        return approval_id

    def _expire_approvals(self) -> None:
        now = self._now()
        self.db.execute(
            """
            UPDATE approval_queue
            SET status = 'expired', decided_at = ?
            WHERE status = 'pending' AND expires_at IS NOT NULL AND expires_at <= ?
            """,
            (now, now),
        )
        self.db.commit()

    def _audit(
        self,
        tenant_id: str,
        session_id: str | None,
        turn_id: str | None,
        action_type: str,
        tool_name: str | None,
        backend: str,
        risk_class: str,
        confidence: float,
        policy_action: str,
        payload: dict[str, Any],
        outcome: dict[str, Any],
    ) -> None:
        payload_blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(payload_blob.encode("utf-8")).hexdigest()
        self.db.execute(
            """
            INSERT INTO tool_audit_logs (
              id, tenant_id, session_id, turn_id, action_type, tool_name, backend,
              risk_class, confidence, policy_action, payload_hash, outcome_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                tenant_id,
                session_id,
                turn_id,
                action_type,
                tool_name,
                backend,
                risk_class,
                confidence,
                policy_action,
                payload_hash,
                json.dumps(outcome, separators=(",", ":")),
                self._now(),
            ),
        )
        self.db.commit()

    @staticmethod
    def _approval_row(row) -> dict[str, Any]:
        return {
            "approval_id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "session_id": str(row["session_id"]) if row["session_id"] is not None else None,
            "turn_id": str(row["turn_id"]) if row["turn_id"] is not None else None,
            "action_type": str(row["action_type"]),
            "payload": json.loads(str(row["payload_json"])),
            "risk_class": str(row["risk_class"]),
            "confidence": float(row["confidence"]),
            "status": str(row["status"]),
            "reason": str(row["reason"]) if row["reason"] is not None else None,
            "decided_by": str(row["decided_by"]) if row["decided_by"] is not None else None,
            "requested_at": str(row["requested_at"]),
            "decided_at": str(row["decided_at"]) if row["decided_at"] is not None else None,
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _register_default_classifications(self) -> None:
        self.register_classification("read", "read", "low")
        self.register_classification("glob", "read", "low")
        self.register_classification("grep", "read", "low")
        self.register_classification("memory_search", "read", "low")
        self.register_classification("list_approvals", "read", "low")
        self.register_classification("sessions_poll", "read", "low")
        self.register_classification("sessions_list", "read", "low")
        self.register_classification("session_status", "read", "low")
        self.register_classification("web_search", "read", "low")
        self.register_classification("web_fetch", "read", "low")
        self.register_classification("get_symbols_overview", "read", "low")
        self.register_classification("find_symbol", "read", "low")
        self.register_classification("find_referencing_symbols", "read", "low")

        self.register_classification("write", "write", "medium")
        self.register_classification("edit", "write", "medium")
        self.register_classification("apply_patch", "write", "medium")
        self.register_classification("memory_store", "write", "medium")
        self.register_classification("project_create", "write", "medium")
        self.register_classification("project_list", "read", "low")
        self.register_classification("task_create", "write", "medium")
        self.register_classification("task_list", "read", "low")
        self.register_classification("task_update", "write", "medium")
        self.register_classification("replace_symbol_body", "write", "medium")
        self.register_classification("insert_before_symbol", "write", "medium")
        self.register_classification("insert_after_symbol", "write", "medium")

        self.register_classification("rename_symbol", "write", "high")
        self.register_classification("decide_approval", "write", "high")
        self.register_classification("sessions_spawn", "execute", "high")
        self.register_classification("process", "execute", "high")

        # Keep action_type name for critical shell safeguard in evaluate().
        self.register_classification("exec", "execute_shell_command", "critical")
