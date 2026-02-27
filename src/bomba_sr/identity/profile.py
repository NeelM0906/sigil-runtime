from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from bomba_sr.storage.db import RuntimeDB


@dataclass(frozen=True)
class ProfileSignal:
    signal_type: str
    signal_key: str
    signal_value: str
    confidence: float


class UserIdentityService:
    def __init__(self, db: RuntimeDB, auto_apply_confidence: float = 0.4):
        if not (0.0 <= auto_apply_confidence <= 1.0):
            raise ValueError("auto_apply_confidence must be in [0,1]")
        self.db = db
        self.auto_apply_confidence = auto_apply_confidence
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              display_name TEXT,
              preferences_json TEXT NOT NULL,
              constraints_json TEXT NOT NULL,
              goals_json TEXT NOT NULL,
              communication_style_json TEXT NOT NULL DEFAULT '{}',
              contact_info_json TEXT NOT NULL DEFAULT '{}',
              relationship_notes TEXT NOT NULL DEFAULT '',
              persona_summary TEXT NOT NULL,
              profile_version INTEGER NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(tenant_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS user_profile_signals (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              signal_type TEXT NOT NULL,
              signal_key TEXT NOT NULL,
              signal_value TEXT NOT NULL,
              confidence REAL NOT NULL,
              status TEXT NOT NULL,
              source_ref TEXT,
              created_at TEXT NOT NULL,
              decided_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_user_profile_signals
              ON user_profile_signals(tenant_id, user_id, created_at DESC);
            """
        )
        self._ensure_column("user_profiles", "communication_style_json", "TEXT NOT NULL DEFAULT '{}'")
        self._ensure_column("user_profiles", "contact_info_json", "TEXT NOT NULL DEFAULT '{}'")
        self._ensure_column("user_profiles", "relationship_notes", "TEXT NOT NULL DEFAULT ''")
        self.db.commit()

    def ensure_profile(self, tenant_id: str, user_id: str) -> dict:
        row = self.db.execute(
            "SELECT * FROM user_profiles WHERE tenant_id = ? AND user_id = ?",
            (tenant_id, user_id),
        ).fetchone()
        if row is not None:
            return self._profile_row(row)

        now = self._now()
        self.db.execute(
            """
            INSERT INTO user_profiles (
              id, tenant_id, user_id, display_name, preferences_json,
              constraints_json, goals_json, communication_style_json, contact_info_json,
              relationship_notes, persona_summary, profile_version, updated_at
            ) VALUES (?, ?, ?, NULL, '{}', '[]', '[]', '{}', '{}', '', '', 1, ?)
            """,
            (str(uuid.uuid4()), tenant_id, user_id, now),
        )
        self.db.commit()
        return self.get_profile(tenant_id, user_id)

    def get_profile(self, tenant_id: str, user_id: str) -> dict:
        row = self.db.execute(
            "SELECT * FROM user_profiles WHERE tenant_id = ? AND user_id = ?",
            (tenant_id, user_id),
        ).fetchone()
        if row is None:
            return self.ensure_profile(tenant_id, user_id)
        return self._profile_row(row)

    def ingest_turn(self, tenant_id: str, user_id: str, text: str, source_ref: str | None = None) -> dict:
        self.ensure_profile(tenant_id, user_id)
        signals = self.extract_signals(text)
        applied: list[dict] = []
        pending: list[dict] = []
        rejected: list[dict] = []

        for signal in signals:
            signal_id = self._record_signal(tenant_id, user_id, signal, source_ref)
            if signal.confidence >= self.auto_apply_confidence:
                self._apply_signal(tenant_id, user_id, signal)
                self._set_signal_status(signal_id, "applied")
                applied.append({"signal_id": signal_id, "type": signal.signal_type, "key": signal.signal_key})
            else:
                pending.append({"signal_id": signal_id, "type": signal.signal_type, "key": signal.signal_key})

        profile = self.get_profile(tenant_id, user_id)
        return {
            "applied": applied,
            "pending": pending,
            "rejected": rejected,
            "profile": profile,
        }

    def list_pending_signals(self, tenant_id: str, user_id: str) -> list[dict]:
        rows = self.db.execute(
            """
            SELECT * FROM user_profile_signals
            WHERE tenant_id = ? AND user_id = ? AND status = 'pending'
            ORDER BY created_at ASC
            """,
            (tenant_id, user_id),
        ).fetchall()
        return [self._signal_row(row) for row in rows]

    def decide_signal(self, tenant_id: str, user_id: str, signal_id: str, approved: bool) -> dict:
        row = self.db.execute(
            """
            SELECT * FROM user_profile_signals
            WHERE id = ? AND tenant_id = ? AND user_id = ?
            """,
            (signal_id, tenant_id, user_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"signal not found: {signal_id}")

        current = str(row["status"])
        if current != "pending":
            return self._signal_row(row)

        signal = ProfileSignal(
            signal_type=str(row["signal_type"]),
            signal_key=str(row["signal_key"]),
            signal_value=str(row["signal_value"]),
            confidence=float(row["confidence"]),
        )

        if approved:
            self._apply_signal(tenant_id, user_id, signal)
            self._set_signal_status(signal_id, "applied")
        else:
            self._set_signal_status(signal_id, "rejected")

        updated = self.db.execute("SELECT * FROM user_profile_signals WHERE id = ?", (signal_id,)).fetchone()
        if updated is None:
            raise ValueError("signal disappeared")
        return self._signal_row(updated)

    def extract_signals(self, text: str) -> list[ProfileSignal]:
        signals: list[ProfileSignal] = []

        name_match = re.search(r"\bmy name is\s+([A-Za-z][A-Za-z0-9_-]{1,50})", text, flags=re.IGNORECASE)
        if name_match:
            signals.append(
                ProfileSignal(
                    signal_type="display_name",
                    signal_key="display_name",
                    signal_value=name_match.group(1),
                    confidence=0.92,
                )
            )

        pref_matches = re.findall(r"\bi prefer\s+([a-zA-Z0-9 _./+-]{2,80})", text, flags=re.IGNORECASE)
        for pref in pref_matches[:3]:
            key = pref.strip().lower()
            signals.append(
                ProfileSignal(
                    signal_type="preference",
                    signal_key=key,
                    signal_value=pref.strip(),
                    confidence=0.72,
                )
            )

        goal_matches = re.findall(r"\bmy goal is to\s+([a-zA-Z0-9 ,._/-]{3,120})", text, flags=re.IGNORECASE)
        for goal in goal_matches[:3]:
            signals.append(
                ProfileSignal(
                    signal_type="goal",
                    signal_key=goal.strip().lower(),
                    signal_value=goal.strip(),
                    confidence=0.68,
                )
            )

        constraint_matches = re.findall(r"\bdon't\s+([a-zA-Z0-9 ,._/-]{3,120})", text, flags=re.IGNORECASE)
        for c in constraint_matches[:3]:
            signals.append(
                ProfileSignal(
                    signal_type="constraint",
                    signal_key=c.strip().lower(),
                    signal_value=c.strip(),
                    confidence=0.38,
                )
            )

        return signals

    def _record_signal(self, tenant_id: str, user_id: str, signal: ProfileSignal, source_ref: str | None) -> str:
        signal_id = str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO user_profile_signals (
              id, tenant_id, user_id, signal_type, signal_key, signal_value,
              confidence, status, source_ref, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                signal_id,
                tenant_id,
                user_id,
                signal.signal_type,
                signal.signal_key,
                signal.signal_value,
                signal.confidence,
                source_ref,
                self._now(),
            ),
        )
        self.db.commit()
        return signal_id

    def _set_signal_status(self, signal_id: str, status: str) -> None:
        self.db.execute(
            "UPDATE user_profile_signals SET status = ?, decided_at = ? WHERE id = ?",
            (status, self._now(), signal_id),
        )
        self.db.commit()

    def _apply_signal(self, tenant_id: str, user_id: str, signal: ProfileSignal) -> None:
        profile = self.get_profile(tenant_id, user_id)
        preferences = dict(profile["preferences"])
        constraints = list(profile["constraints"])
        goals = list(profile["goals"])
        display_name = profile.get("display_name")

        if signal.signal_type == "display_name":
            display_name = signal.signal_value
        elif signal.signal_type == "preference":
            preferences[signal.signal_key] = signal.signal_value
        elif signal.signal_type == "constraint":
            if signal.signal_value not in constraints:
                constraints.append(signal.signal_value)
        elif signal.signal_type == "goal":
            existing = {str(item.get("title", "")).lower() for item in goals if isinstance(item, dict)}
            if signal.signal_key not in existing:
                goals.append({"title": signal.signal_value, "active": True})

        summary_parts = []
        if display_name:
            summary_parts.append(f"name={display_name}")
        if preferences:
            summary_parts.append(f"preferences={len(preferences)}")
        if constraints:
            summary_parts.append(f"constraints={len(constraints)}")
        if goals:
            summary_parts.append(f"goals={len(goals)}")

        current_version = int(profile["profile_version"])
        self.db.execute(
            """
            UPDATE user_profiles
            SET display_name = ?, preferences_json = ?, constraints_json = ?, goals_json = ?,
                persona_summary = ?, profile_version = ?, updated_at = ?
            WHERE tenant_id = ? AND user_id = ?
            """,
            (
                display_name,
                json.dumps(preferences, separators=(",", ":")),
                json.dumps(constraints, separators=(",", ":")),
                json.dumps(goals, separators=(",", ":")),
                ", ".join(summary_parts),
                current_version + 1,
                self._now(),
                tenant_id,
                user_id,
            ),
        )
        self.db.commit()

    @staticmethod
    def _profile_row(row) -> dict:
        return {
            "tenant_id": str(row["tenant_id"]),
            "user_id": str(row["user_id"]),
            "display_name": str(row["display_name"]) if row["display_name"] is not None else None,
            "preferences": json.loads(str(row["preferences_json"])),
            "constraints": json.loads(str(row["constraints_json"])),
            "goals": json.loads(str(row["goals_json"])),
            "communication_style": json.loads(str(row["communication_style_json"])),
            "contact_info": json.loads(str(row["contact_info_json"])),
            "relationship_notes": str(row["relationship_notes"]) if row["relationship_notes"] is not None else "",
            "persona_summary": str(row["persona_summary"]),
            "profile_version": int(row["profile_version"]),
            "updated_at": str(row["updated_at"]),
        }

    @staticmethod
    def _signal_row(row) -> dict:
        return {
            "signal_id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "user_id": str(row["user_id"]),
            "signal_type": str(row["signal_type"]),
            "signal_key": str(row["signal_key"]),
            "signal_value": str(row["signal_value"]),
            "confidence": float(row["confidence"]),
            "status": str(row["status"]),
            "source_ref": str(row["source_ref"]) if row["source_ref"] is not None else None,
            "created_at": str(row["created_at"]),
            "decided_at": str(row["decided_at"]) if row["decided_at"] is not None else None,
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        rows = self.db.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row["name"]) for row in rows}
        if column in existing:
            return
        self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
