from __future__ import annotations

import fnmatch
import os
import shlex
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LOW_VALUE_SEGMENTS = (
    "/node_modules/",
    "/dist/",
    "/build/",
    "/vendor/",
    "/.git/",
    "/coverage/",
)


@dataclass(frozen=True)
class SearchPlan:
    query: str
    intent: str
    scope: list[str]
    file_types: list[str]
    escalation_allowed: bool = True
    escalation_mode: str = "balanced"
    known_symbols: list[str] | None = None


@dataclass(frozen=True)
class SearchHit:
    path: str
    line_start: int
    line_end: int
    confidence: float
    snippet: str
    rationale: str


@dataclass(frozen=True)
class SearchResultPack:
    plan_id: str
    executed_at: float
    pass_number: int
    escalated: bool
    results: list[SearchHit]
    commands: list[str]
    execution_ms: int
    low_value_hit_ratio: float
    avg_confidence: float


class AgenticSearchExecutor:
    def __init__(self, cwd: str | Path):
        self.cwd = Path(cwd).resolve()
        self._rg_available = shutil.which("rg") is not None

    def execute(self, plan: SearchPlan) -> SearchResultPack:
        if not plan.query.strip():
            raise ValueError("Search query is required")
        if not plan.scope:
            raise ValueError("At least one search scope is required")

        start = time.time()
        plan_id = str(uuid.uuid4())

        pass1_hits, pass1_cmds = self._run_pass(plan, unrestricted=False)
        escalated = self._should_escalate(plan, pass1_hits)

        if escalated and plan.escalation_allowed:
            pass2_hits, pass2_cmds = self._run_pass(plan, unrestricted=True)
            hits = self._dedupe_hits(pass1_hits + pass2_hits)
            commands = pass1_cmds + pass2_cmds
            pass_number = 2
        else:
            hits = pass1_hits
            commands = pass1_cmds
            pass_number = 1

        elapsed_ms = int((time.time() - start) * 1000)
        low_value_ratio = self._low_value_ratio(hits)
        avg_conf = (sum(h.confidence for h in hits) / len(hits)) if hits else 0.0

        return SearchResultPack(
            plan_id=plan_id,
            executed_at=time.time(),
            pass_number=pass_number,
            escalated=(pass_number == 2),
            results=hits,
            commands=commands,
            execution_ms=elapsed_ms,
            low_value_hit_ratio=low_value_ratio,
            avg_confidence=avg_conf,
        )

    def _run_pass(self, plan: SearchPlan, unrestricted: bool) -> tuple[list[SearchHit], list[str]]:
        if not self._rg_available:
            hits = self._exec_python_fallback(plan, pass_label=(2 if unrestricted else 1), unrestricted=unrestricted)
            cmd_desc = f"python-fallback-search pass={2 if unrestricted else 1} unrestricted={str(unrestricted).lower()}"
            return self._dedupe_hits(hits), [cmd_desc]

        commands: list[list[str]] = []

        base = ["rg", "-n"]
        if unrestricted:
            base.append("-uuu")
        else:
            base.extend(["--hidden", "-g", "!.git", "-g", "!node_modules"])

        if plan.file_types:
            typed_cmd = base + [f"-t{ft}" for ft in plan.file_types] + [plan.query] + plan.scope
            commands.append(typed_cmd)
            # Keep an untyped scoped pass as backup for uncommon extensions.
            scoped_cmd = base + [plan.query] + plan.scope
            commands.append(scoped_cmd)
        else:
            scoped_cmd = base + [plan.query] + plan.scope
            commands.append(scoped_cmd)

        all_hits: list[SearchHit] = []
        for cmd in commands:
            all_hits.extend(self._exec_rg(cmd, pass_label=(2 if unrestricted else 1)))

        return self._dedupe_hits(all_hits), [" ".join(shlex.quote(x) for x in c) for c in commands]

    def _exec_rg(self, cmd: list[str], pass_label: int) -> list[SearchHit]:
        proc = subprocess.run(
            cmd,
            cwd=str(self.cwd),
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode not in (0, 1):
            raise RuntimeError(f"rg failed ({proc.returncode}): {proc.stderr.strip()}")

        hits: list[SearchHit] = []
        for line in proc.stdout.splitlines():
            parsed = self._parse_rg_line(line)
            if parsed is None:
                continue
            path, line_no, snippet = parsed
            confidence = self._confidence(path, snippet)
            rationale = self._rationale(path, snippet, pass_label)
            hits.append(
                SearchHit(
                    path=path,
                    line_start=line_no,
                    line_end=line_no,
                    confidence=confidence,
                    snippet=snippet,
                    rationale=rationale,
                )
            )
        return hits

    def _exec_python_fallback(self, plan: SearchPlan, pass_label: int, unrestricted: bool) -> list[SearchHit]:
        hits: list[SearchHit] = []
        query = plan.query
        cwd_real = Path(os.path.realpath(str(self.cwd)))
        scope_paths = [self.cwd / s for s in plan.scope]

        for scope in scope_paths:
            root = scope.resolve()
            if not root.exists():
                continue

            for current_root, dirs, files in os.walk(root):
                rel_root = os.path.relpath(current_root, self.cwd)
                normalized_root = "/" + rel_root.replace("\\", "/").strip("./") + "/"
                if not unrestricted:
                    dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "dist", "build", "vendor", "coverage"}]
                    if any(segment in normalized_root for segment in LOW_VALUE_SEGMENTS):
                        continue

                for filename in files:
                    path_obj = Path(current_root) / filename
                    rel_path = os.path.relpath(os.path.realpath(str(path_obj)), str(cwd_real)).replace("\\", "/")

                    if plan.file_types and not self._matches_types(filename, plan.file_types):
                        continue
                    if not unrestricted and self._is_low_value_path(rel_path):
                        continue

                    for line_no, line in self._iter_file_lines(path_obj):
                        if query in line:
                            snippet = line.strip()
                            hits.append(
                                SearchHit(
                                    path=rel_path,
                                    line_start=line_no,
                                    line_end=line_no,
                                    confidence=self._confidence(rel_path, snippet),
                                    snippet=snippet,
                                    rationale=self._rationale(rel_path, snippet, pass_label),
                                )
                            )
        return hits

    @staticmethod
    def _matches_types(filename: str, file_types: list[str]) -> bool:
        ext = filename.rsplit(".", 1)
        if len(ext) != 2:
            return False
        suffix = ext[1].lower()
        for ft in file_types:
            normalized = ft.lower().lstrip(".")
            if suffix == normalized:
                return True
            # Handle ripgrep aliases that map to many file patterns.
            if normalized == "py" and fnmatch.fnmatch(filename.lower(), "*.py"):
                return True
            if normalized in {"ts", "tsx"} and filename.lower().endswith((".ts", ".tsx")):
                return True
            if normalized in {"js", "jsx"} and filename.lower().endswith((".js", ".jsx")):
                return True
            if normalized == "md" and filename.lower().endswith(".md"):
                return True
        return False

    @staticmethod
    def _iter_file_lines(path_obj: Path):
        try:
            with path_obj.open("r", encoding="utf-8", errors="ignore") as handle:
                for idx, line in enumerate(handle, start=1):
                    yield idx, line
        except OSError:
            return

    @staticmethod
    def _parse_rg_line(line: str) -> tuple[str, int, str] | None:
        # rg -n output: path:line:match
        first = line.find(":")
        if first <= 0:
            return None
        second = line.find(":", first + 1)
        if second <= first:
            return None

        path = line[:first]
        line_s = line[first + 1 : second]
        snippet = line[second + 1 :]

        try:
            line_no = int(line_s)
        except ValueError:
            return None

        return path, line_no, snippet.strip()

    @staticmethod
    def _is_low_value_path(path: str) -> bool:
        norm = "/" + path.replace("\\", "/").strip("/") + "/"
        return any(segment in norm for segment in LOW_VALUE_SEGMENTS)

    def _confidence(self, path: str, snippet: str) -> float:
        score = 0.55
        if not self._is_low_value_path(path):
            score += 0.15
        if 0 < len(snippet) < 220:
            score += 0.10
        if "TODO" not in snippet and "generated" not in snippet.lower():
            score += 0.10
        if any(ch.isalpha() for ch in snippet):
            score += 0.10
        return max(0.0, min(1.0, score))

    def _rationale(self, path: str, snippet: str, pass_label: int) -> str:
        low_value = self._is_low_value_path(path)
        quality = "high-signal path" if not low_value else "low-value path"
        snippet_hint = "short exact line" if len(snippet) < 220 else "longer line"
        return f"pass{pass_label}: {quality}; {snippet_hint}; lexical match"

    def _should_escalate(self, plan: SearchPlan, pass1_hits: list[SearchHit]) -> bool:
        if not plan.escalation_allowed:
            return False
        mode = plan.escalation_mode

        if mode == "strict":
            return len(pass1_hits) == 0

        if mode == "aggressive":
            if len(pass1_hits) == 0:
                return True
            avg_conf = sum(h.confidence for h in pass1_hits) / len(pass1_hits)
            return avg_conf < 0.65

        # balanced mode
        if len(pass1_hits) == 0 and self._is_high_confidence_query(plan.query):
            return True

        if pass1_hits:
            avg_conf = sum(h.confidence for h in pass1_hits) / len(pass1_hits)
            low_value_ratio = self._low_value_ratio(pass1_hits)
            if avg_conf < 0.45 or low_value_ratio > 0.70:
                return True

        if plan.known_symbols:
            joined = "\n".join(f"{h.path} {h.snippet}" for h in pass1_hits).lower()
            if not any(sym.lower() in joined for sym in plan.known_symbols):
                return True

        return False

    @staticmethod
    def _is_high_confidence_query(query: str) -> bool:
        q = query.strip()
        if len(q) < 4:
            return False
        regex_meta = set(".*+?[]{}()|\\")
        return not any(ch in regex_meta for ch in q)

    @staticmethod
    def _low_value_ratio(hits: list[SearchHit]) -> float:
        if not hits:
            return 0.0
        low = sum(1 for h in hits if AgenticSearchExecutor._is_low_value_path(h.path))
        return low / len(hits)

    @staticmethod
    def _dedupe_hits(hits: list[SearchHit]) -> list[SearchHit]:
        seen: set[tuple[str, int]] = set()
        out: list[SearchHit] = []
        for hit in sorted(hits, key=lambda h: (-h.confidence, h.path, h.line_start)):
            key = (hit.path, hit.line_start)
            if key in seen:
                continue
            seen.add(key)
            out.append(hit)
        return out


def result_pack_to_dict(pack: SearchResultPack) -> dict[str, Any]:
    return {
        "planId": pack.plan_id,
        "executedAt": pack.executed_at,
        "pass": pack.pass_number,
        "escalated": pack.escalated,
        "executionMs": pack.execution_ms,
        "lowValueHitRatio": pack.low_value_hit_ratio,
        "avgConfidence": pack.avg_confidence,
        "commands": pack.commands,
        "results": [
            {
                "path": h.path,
                "lineStart": h.line_start,
                "lineEnd": h.line_end,
                "confidence": h.confidence,
                "snippet": h.snippet,
                "rationale": h.rationale,
            }
            for h in pack.results
        ],
    }
