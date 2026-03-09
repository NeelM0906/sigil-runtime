"""Dream Cycle — periodic background memory consolidation and cross-pollination.

SAI Memory runs dream cycles across all beings' memories to:
  1. Gather — collect working notes, semantic memories, procedural memories,
     KNOWLEDGE.md, REPRESENTATION.md, and task_results
  2. Consolidate — identify duplicates, contradictions, and stale entries
  3. Derive — infer new insights from accumulated data
  4. Prune — archive low-signal memories beyond a threshold
  5. Cross-pollinate — share high-relevance insights between beings

Dream cycles run independently of chat or orchestration — they are a
background maintenance process triggered on a timer or on demand.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bomba_sr.llm.providers import ChatMessage, provider_from_env

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DREAM_MODEL = os.environ.get("BOMBA_DREAM_MODEL", "minimax/minimax-m2.5")
MEMORY_PRUNE_THRESHOLD = 200  # max active semantic memories per being
CROSS_POLLINATE_CONFIDENCE = 0.5
DERIVED_INSIGHT_CONFIDENCE = 0.6
MAX_WORKING_NOTES = 50
MAX_SEMANTIC_MEMORIES = 20
MAX_PROCEDURAL_MEMORIES = 10
DREAM_LOGS_DIR = "workspaces/sai-memory/dream_logs"

CONSOLIDATE_SYSTEM_PROMPT = """\
You are SAI Memory running a dream cycle for {being_name} ({being_id}).
Review the following accumulated memories, notes, and knowledge.

Identify:
1. DUPLICATES: Memories or notes that say the same thing in different words. Pick the best version.
2. CONTRADICTIONS: Memories that contradict each other. Flag which is likely more current/accurate.
3. STALE: Information that is clearly outdated based on more recent entries.

Data:
{gathered_data}

Return ONLY a JSON object (no markdown fences):
{{
    "duplicates": [{{"keep": "memory_key_to_keep", "remove": ["keys_to_remove"]}}],
    "contradictions": [{{"memory_a": "key", "memory_b": "key", "resolution": "which to keep and why", "keep": "key_to_keep"}}],
    "stale": ["keys_of_stale_memories"]
}}
"""

DERIVE_SYSTEM_PROMPT = """\
You are SAI Memory running a dream cycle for {being_name} ({being_id}).
Given the consolidated memories below, derive new conclusions or patterns.

Look for:
1. Recurring themes across multiple tasks
2. Skills that have improved based on procedural memory success rates
3. Knowledge gaps — areas where the being has been asked about topics but had poor results
4. Relationships between pieces of information that the being may not have connected

Consolidated data:
{consolidated_data}

Return ONLY a JSON array of up to 5 derived insights (no markdown fences):
[
    {{"key": "derived::topic_name", "content": "The insight text", "relevance_to_others": ["being_id_1", "being_id_2"]}}
]

Rules:
- Each insight must be grounded in the provided data — do not invent.
- relevance_to_others should only list beings whose domain overlaps with the insight.
- Keep insights concise (1-3 sentences each).
"""


# ---------------------------------------------------------------------------
# DreamCycle
# ---------------------------------------------------------------------------

class DreamCycle:
    """Periodic memory consolidation engine for all beings."""

    def __init__(
        self,
        bridge: Any,
        dashboard_svc: Any,
        interval_seconds: int = 3600,
    ):
        self.bridge = bridge
        self.dashboard = dashboard_svc
        self.interval_seconds = max(60, int(interval_seconds))
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._runs = 0
        self._last_run_at: str | None = None
        self._last_error: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self.is_running():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="bomba-dream-cycle",
        )
        self._thread.start()
        log.info("Dream cycle started (interval=%ds)", self.interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._thread = None

    def is_running(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    def status(self) -> dict[str, Any]:
        return {
            "running": self.is_running(),
            "interval_seconds": self.interval_seconds,
            "total_runs": self._runs,
            "last_run_at": self._last_run_at,
            "last_error": self._last_error,
        }

    def _run_loop(self) -> None:
        """Background loop — run a full dream cycle, then sleep."""
        while not self._stop_event.is_set():
            try:
                self.run_cycle()
            except Exception as exc:
                with self._lock:
                    self._last_error = str(exc)
                log.exception("Dream cycle failed")
            self._stop_event.wait(self.interval_seconds)

    # ------------------------------------------------------------------
    # Public: run a cycle (can also be called on demand)
    # ------------------------------------------------------------------

    def run_cycle(self, being_id: str | None = None) -> dict[str, Any]:
        """Run a dream cycle for one being or all beings.

        Returns a summary of actions taken.
        """
        if being_id:
            beings = [being_id]
        else:
            all_beings = self.dashboard.list_beings() if self.dashboard else []
            beings = [b["id"] for b in all_beings if b.get("id") != "prime"]

        results: dict[str, Any] = {}
        for bid in beings:
            try:
                result = self._dream_for_being(bid)
                results[bid] = result
            except Exception as exc:
                log.warning("Dream cycle failed for %s: %s", bid, exc)
                results[bid] = {"error": str(exc)}

        with self._lock:
            self._runs += 1
            self._last_run_at = datetime.now(timezone.utc).isoformat()
            self._last_error = None

        log.info("Dream cycle completed for %d beings", len(beings))

        # Write dream log report
        try:
            self._write_dream_log(results)
        except Exception as exc:
            log.warning("Failed to write dream log: %s", exc)

        return results

    # ------------------------------------------------------------------
    # Per-being dream
    # ------------------------------------------------------------------

    def _dream_for_being(self, being_id: str) -> dict[str, Any]:
        """Run all 5 dream phases for a single being."""
        being = self.dashboard.get_being(being_id) if self.dashboard else None
        if not being:
            return {"skipped": True, "reason": "being_not_found"}

        being_name = being.get("name", being_id)
        tenant_id = being.get("tenant_id") or f"tenant-{being_id}"

        # Phase 1: Gather
        gathered = self._phase_gather(being_id, being, tenant_id)
        if not gathered.get("has_data"):
            return {"skipped": True, "reason": "no_data"}

        # Phase 2: Consolidate
        consolidation = self._phase_consolidate(being_id, being_name, gathered)

        # Phase 3: Derive
        derived = self._phase_derive(being_id, being_name, gathered)

        # Phase 4: Prune
        pruned = self._phase_prune(being_id, tenant_id)

        # Phase 5: Cross-pollinate
        cross_pollinated = self._phase_cross_pollinate(being_id, derived)

        return {
            "being_id": being_id,
            "gathered_counts": {
                "working_notes": len(gathered.get("working_notes", [])),
                "semantic_memories": len(gathered.get("semantic_memories", [])),
                "procedural_memories": len(gathered.get("procedural_memories", [])),
            },
            "consolidation": consolidation,
            "derived_count": len(derived),
            "pruned_count": pruned,
            "cross_pollinated_count": cross_pollinated,
        }

    # ------------------------------------------------------------------
    # Phase 1: Gather
    # ------------------------------------------------------------------

    def _phase_gather(
        self,
        being_id: str,
        being: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        """Collect all memory sources for a being."""
        result: dict[str, Any] = {"has_data": False}

        try:
            runtime = self.bridge._tenant_runtime(tenant_id)
        except Exception:
            return result

        # Working notes (from markdown_notes table) — query both user_id and being_id
        try:
            rows = runtime.db.execute(
                """
                SELECT note_id, relative_path, title, tags, confidence, created_at
                FROM markdown_notes
                WHERE user_id = ? OR being_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (being_id, being_id, MAX_WORKING_NOTES),
            ).fetchall()
            notes = []
            for r in rows:
                body = runtime.memory._read_note_body(str(r["relative_path"]))
                notes.append({
                    "note_id": str(r["note_id"]),
                    "title": str(r["title"]),
                    "content": body[:500] if body else "",
                    "created_at": str(r["created_at"]),
                })
            result["working_notes"] = notes
        except Exception as exc:
            log.debug("Could not gather working notes for %s: %s", being_id, exc)
            result["working_notes"] = []

        # Semantic memories — query both user_id and being_id
        try:
            rows = runtime.db.execute(
                """
                SELECT id, memory_key, content, recency_ts, version
                FROM memories
                WHERE (user_id = ? OR being_id = ?) AND active = 1 AND tier = 'semantic'
                ORDER BY updated_at DESC LIMIT ?
                """,
                (being_id, being_id, MAX_SEMANTIC_MEMORIES),
            ).fetchall()
            result["semantic_memories"] = [
                {
                    "memory_id": str(r["id"]),
                    "key": str(r["memory_key"]),
                    "content": str(r["content"])[:500],
                    "recency_ts": str(r["recency_ts"]),
                }
                for r in rows
            ]
        except Exception as exc:
            log.debug("Could not gather semantic memories for %s: %s", being_id, exc)
            result["semantic_memories"] = []

        # Procedural memories — query both user_id and being_id
        try:
            rows = runtime.db.execute(
                """
                SELECT id, strategy_key, content, success_count, failure_count
                FROM procedural_memories
                WHERE (user_id = ? OR being_id = ?) AND active = 1
                ORDER BY updated_at DESC LIMIT ?
                """,
                (being_id, being_id, MAX_PROCEDURAL_MEMORIES),
            ).fetchall()
            result["procedural_memories"] = [
                {
                    "strategy_key": str(r["strategy_key"]),
                    "content": str(r["content"])[:300],
                    "success_count": int(r["success_count"]),
                    "failure_count": int(r["failure_count"]),
                }
                for r in rows
            ]
        except Exception as exc:
            log.debug("Could not gather procedural memories for %s: %s", being_id, exc)
            result["procedural_memories"] = []

        # KNOWLEDGE.md and REPRESENTATION.md from workspace
        ws = being.get("workspace")
        if ws and ws != ".":
            ws_path = Path(ws) if Path(ws).is_absolute() else Path(os.environ.get("BOMBA_WORKSPACE", ".")) / ws
            for fname in ("KNOWLEDGE.md", "REPRESENTATION.md"):
                fpath = ws_path / fname
                if fpath.exists():
                    try:
                        result[fname.lower().replace(".", "_")] = fpath.read_text(encoding="utf-8")[:2000]
                    except OSError:
                        pass

        # Task results (recent participation)
        try:
            rows = runtime.db.execute(
                """
                SELECT task_id, goal, strategy, beings_used, synthesis, created_at
                FROM task_results
                WHERE beings_used LIKE ?
                ORDER BY created_at DESC LIMIT 5
                """,
                (f'%"{being_id}"%',),
            ).fetchall()
            result["task_results"] = [
                {
                    "task_id": str(r["task_id"]),
                    "goal": str(r["goal"])[:200],
                    "synthesis": str(r["synthesis"])[:300],
                    "created_at": str(r["created_at"]),
                }
                for r in rows
            ]
        except Exception:
            result["task_results"] = []

        # Mark as having data if any source has content
        has_any = (
            result.get("working_notes")
            or result.get("semantic_memories")
            or result.get("procedural_memories")
            or result.get("task_results")
        )
        result["has_data"] = bool(has_any)
        return result

    # ------------------------------------------------------------------
    # Phase 2: Consolidate
    # ------------------------------------------------------------------

    def _phase_consolidate(
        self,
        being_id: str,
        being_name: str,
        gathered: dict[str, Any],
    ) -> dict[str, Any]:
        """Identify duplicates, contradictions, and stale entries via LLM."""
        # Build a compact data summary for the LLM
        data_parts = []
        for mem in gathered.get("semantic_memories", []):
            data_parts.append(f"[semantic] key={mem['key']}: {mem['content']}")
        for note in gathered.get("working_notes", []):
            data_parts.append(f"[note] {note['title']}: {note['content'][:200]}")
        for proc in gathered.get("procedural_memories", []):
            total = proc["success_count"] + proc["failure_count"]
            ratio = proc["success_count"] / max(1, total)
            data_parts.append(f"[procedural] {proc['strategy_key']}: {proc['content'][:200]} (success_ratio={ratio:.2f})")

        if not data_parts:
            return {"duplicates": 0, "contradictions": 0, "stale": 0}

        gathered_text = "\n".join(data_parts[:60])  # cap to avoid context overflow

        try:
            provider = provider_from_env()
            prompt = CONSOLIDATE_SYSTEM_PROMPT.format(
                being_name=being_name,
                being_id=being_id,
                gathered_data=gathered_text,
            )
            resp = provider.generate(DREAM_MODEL, [ChatMessage(role="user", content=prompt)])
            reply = resp.text if hasattr(resp, "text") else str(resp)
            result = self._parse_json(reply)
        except Exception as exc:
            log.warning("Consolidation LLM call failed for %s: %s", being_id, exc)
            return {"duplicates": 0, "contradictions": 0, "stale": 0, "error": str(exc)}

        # Apply consolidation actions
        actions = {"duplicates": 0, "contradictions": 0, "stale": 0}
        try:
            tenant_id = f"tenant-{being_id}"
            runtime = self.bridge._tenant_runtime(tenant_id)

            # Remove duplicates
            for dup in result.get("duplicates", []):
                for key_to_remove in dup.get("remove", []):
                    self._archive_memory_by_key(runtime, being_id, key_to_remove, "duplicate")
                    actions["duplicates"] += 1

            # Resolve contradictions
            for contra in result.get("contradictions", []):
                keep_key = contra.get("keep")
                for key in [contra.get("memory_a"), contra.get("memory_b")]:
                    if key and key != keep_key:
                        self._archive_memory_by_key(runtime, being_id, key, "contradiction_resolved")
                        actions["contradictions"] += 1

            # Archive stale
            for stale_key in result.get("stale", []):
                self._archive_memory_by_key(runtime, being_id, stale_key, "stale")
                actions["stale"] += 1

        except Exception as exc:
            log.warning("Failed to apply consolidation for %s: %s", being_id, exc)
            actions["error"] = str(exc)

        return actions

    # ------------------------------------------------------------------
    # Phase 3: Derive
    # ------------------------------------------------------------------

    def _phase_derive(
        self,
        being_id: str,
        being_name: str,
        gathered: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Derive new insights from consolidated memories."""
        data_parts = []
        for mem in gathered.get("semantic_memories", []):
            data_parts.append(f"[semantic] {mem['key']}: {mem['content']}")
        for proc in gathered.get("procedural_memories", []):
            total = proc["success_count"] + proc["failure_count"]
            ratio = proc["success_count"] / max(1, total)
            data_parts.append(f"[procedural] {proc['strategy_key']}: success_ratio={ratio:.2f}")
        for tr in gathered.get("task_results", []):
            data_parts.append(f"[task] {tr['goal']}: {tr['synthesis'][:200]}")

        if not data_parts:
            return []

        try:
            provider = provider_from_env()
            prompt = DERIVE_SYSTEM_PROMPT.format(
                being_name=being_name,
                being_id=being_id,
                consolidated_data="\n".join(data_parts[:40]),
            )
            resp = provider.generate(DREAM_MODEL, [ChatMessage(role="user", content=prompt)])
            reply = resp.text if hasattr(resp, "text") else str(resp)
            insights = self._parse_json(reply)
        except Exception as exc:
            log.warning("Derive LLM call failed for %s: %s", being_id, exc)
            return []

        if not isinstance(insights, list):
            return []

        # Store derived insights as semantic memories
        stored: list[dict[str, Any]] = []
        try:
            tenant_id = f"tenant-{being_id}"
            runtime = self.bridge._tenant_runtime(tenant_id)
            for insight in insights[:5]:
                key = insight.get("key", f"derived::{uuid.uuid4().hex[:8]}")
                content = insight.get("content", "")
                if not content.strip():
                    continue
                runtime.memory.learn_semantic(
                    tenant_id=tenant_id,
                    user_id=being_id,
                    memory_key=key,
                    content=f"[Dream cycle insight] {content}",
                    confidence=DERIVED_INSIGHT_CONFIDENCE,
                    being_id=being_id,
                )
                stored.append(insight)
        except Exception as exc:
            log.warning("Failed to store derived insights for %s: %s", being_id, exc)

        return stored

    # ------------------------------------------------------------------
    # Phase 4: Prune
    # ------------------------------------------------------------------

    def _phase_prune(self, being_id: str, tenant_id: str) -> int:
        """Archive lowest-confidence, oldest memories if count exceeds threshold."""
        try:
            runtime = self.bridge._tenant_runtime(tenant_id)
        except Exception:
            return 0

        try:
            count_row = runtime.db.execute(
                "SELECT COUNT(*) AS c FROM memories WHERE (user_id = ? OR being_id = ?) AND active = 1 AND tier = 'semantic'",
                (being_id, being_id),
            ).fetchone()
            total = int(count_row["c"]) if count_row else 0

            if total <= MEMORY_PRUNE_THRESHOLD:
                return 0

            excess = total - MEMORY_PRUNE_THRESHOLD
            # Find the lowest-value memories: oldest, lowest implicit confidence
            # (memories with fewer versions and older recency_ts are lower value)
            rows = runtime.db.execute(
                """
                SELECT id, memory_key, content
                FROM memories
                WHERE (user_id = ? OR being_id = ?) AND active = 1 AND tier = 'semantic'
                ORDER BY recency_ts ASC, version ASC
                LIMIT ?
                """,
                (being_id, being_id, excess),
            ).fetchall()

            pruned = 0
            now = datetime.now(timezone.utc).isoformat()
            for row in rows:
                memory_id = str(row["id"])
                memory_key = str(row["memory_key"])
                old_content = str(row["content"])
                # Archive, don't delete
                runtime.db.execute(
                    """
                    INSERT INTO memory_archive (id, memory_id, user_id, memory_key, old_content, archived_at, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), memory_id, being_id, memory_key, old_content, now, "dream_prune"),
                )
                runtime.db.execute(
                    "UPDATE memories SET active = 0, updated_at = ? WHERE id = ?",
                    (now, memory_id),
                )
                pruned += 1

            if pruned:
                runtime.db.commit()
                log.info("Pruned %d memories for %s (was %d, threshold %d)", pruned, being_id, total, MEMORY_PRUNE_THRESHOLD)
            return pruned

        except Exception as exc:
            log.warning("Prune failed for %s: %s", being_id, exc)
            return 0

    # ------------------------------------------------------------------
    # Phase 5: Cross-pollinate
    # ------------------------------------------------------------------

    def _phase_cross_pollinate(
        self,
        source_being_id: str,
        derived_insights: list[dict[str, Any]],
    ) -> int:
        """Share high-relevance derived insights with other beings."""
        if not derived_insights:
            return 0

        pollinated = 0
        for insight in derived_insights:
            relevant_beings = insight.get("relevance_to_others", [])
            if not relevant_beings:
                continue

            content = insight.get("content", "")
            if not content.strip():
                continue

            source_being = self.dashboard.get_being(source_being_id) if self.dashboard else None
            source_name = source_being.get("name", source_being_id) if source_being else source_being_id

            for target_bid in relevant_beings:
                if target_bid == source_being_id or target_bid == "prime":
                    continue

                target = self.dashboard.get_being(target_bid) if self.dashboard else None
                if not target:
                    continue

                target_tenant = target.get("tenant_id") or f"tenant-{target_bid}"
                try:
                    target_runtime = self.bridge._tenant_runtime(target_tenant)
                    insight_key = f"cross_pollinate::{source_being_id}::{uuid.uuid4().hex[:8]}"
                    target_runtime.memory.learn_semantic(
                        tenant_id=target_tenant,
                        user_id=f"prime->{target_bid}",
                        memory_key=insight_key,
                        content=f"[From {source_name}'s dream cycle] {content}",
                        confidence=CROSS_POLLINATE_CONFIDENCE,
                        being_id=target_bid,
                    )
                    pollinated += 1
                    log.info(
                        "Cross-pollinated insight from %s to %s",
                        source_being_id, target_bid,
                    )
                except Exception as exc:
                    log.warning(
                        "Failed to cross-pollinate from %s to %s: %s",
                        source_being_id, target_bid, exc,
                    )

        return pollinated

    # ------------------------------------------------------------------
    # Dream log reporting
    # ------------------------------------------------------------------

    def _write_dream_log(self, results: dict[str, Any]) -> Path | None:
        """Write a markdown report of the dream cycle to dream_logs/."""
        project_root = Path(os.environ.get("BOMBA_PROJECT_ROOT", os.environ.get("BOMBA_WORKSPACE", ".")))
        log_dir = project_root / DREAM_LOGS_DIR
        log_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc)
        filename = now.strftime("%Y-%m-%d-%H-%M") + ".md"
        log_path = log_dir / filename

        lines = [f"# Dream Cycle Report — {now.strftime('%Y-%m-%d %H:%M UTC')}\n"]

        for being_id, result in results.items():
            lines.append(f"\n## Being: {being_id}")

            if result.get("skipped"):
                lines.append(f"- Skipped: {result.get('reason', 'unknown')}")
                continue

            if result.get("error"):
                lines.append(f"- Error: {result['error']}")
                continue

            consolidation = result.get("consolidation", {})
            lines.append(f"- Duplicates removed: {consolidation.get('duplicates', 0)}")
            lines.append(f"- Contradictions resolved: {consolidation.get('contradictions', 0)}")
            lines.append(f"- Stale entries archived: {consolidation.get('stale', 0)}")
            lines.append(f"- New insights derived: {result.get('derived_count', 0)}")
            lines.append(f"- Memories pruned: {result.get('pruned_count', 0)}")
            lines.append(f"- Cross-pollinated: {result.get('cross_pollinated_count', 0)}")

            counts = result.get("gathered_counts", {})
            lines.append(f"- Sources gathered: notes={counts.get('working_notes', 0)}, "
                         f"semantic={counts.get('semantic_memories', 0)}, "
                         f"procedural={counts.get('procedural_memories', 0)}")

        report_text = "\n".join(lines) + "\n"
        log_path.write_text(report_text, encoding="utf-8")
        log.info("Dream log written: %s", log_path)
        return log_path

    @staticmethod
    def list_dream_logs(limit: int = 20) -> list[dict[str, Any]]:
        """Return recent dream log entries (newest first)."""
        project_root = Path(os.environ.get("BOMBA_PROJECT_ROOT", os.environ.get("BOMBA_WORKSPACE", ".")))
        log_dir = project_root / DREAM_LOGS_DIR
        if not log_dir.is_dir():
            return []

        logs: list[dict[str, Any]] = []
        for fpath in sorted(log_dir.glob("*.md"), reverse=True):
            if len(logs) >= limit:
                break
            stat = fpath.stat()
            logs.append({
                "filename": fpath.name,
                "path": str(fpath.relative_to(project_root)),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
        return logs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _archive_memory_by_key(
        self,
        runtime: Any,
        user_id: str,
        memory_key: str,
        reason: str,
    ) -> bool:
        """Archive an active memory by its key."""
        now = datetime.now(timezone.utc).isoformat()
        row = runtime.db.execute(
            """
            SELECT id, content FROM memories
            WHERE (user_id = ? OR being_id = ?) AND memory_key = ? AND active = 1
            ORDER BY version DESC LIMIT 1
            """,
            (user_id, user_id, memory_key),
        ).fetchone()
        if row is None:
            return False

        memory_id = str(row["id"])
        old_content = str(row["content"])
        runtime.db.execute(
            """
            INSERT INTO memory_archive (id, memory_id, user_id, memory_key, old_content, archived_at, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), memory_id, user_id, memory_key, old_content, now, f"dream_{reason}"),
        )
        runtime.db.execute(
            "UPDATE memories SET active = 0, updated_at = ? WHERE id = ?",
            (now, memory_id),
        )
        runtime.db.commit()
        return True

    @staticmethod
    def _parse_json(text: str) -> Any:
        """Extract JSON from LLM response, handling markdown fences."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            start = 1
            end = len(lines)
            for i in range(1, len(lines)):
                if lines[i].strip() == "```":
                    end = i
                    break
            cleaned = "\n".join(lines[start:end])
        return json.loads(cleaned)
