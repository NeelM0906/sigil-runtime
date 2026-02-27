from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Iterable

from bomba_sr.skills.descriptor import SkillDescriptor
from bomba_sr.skills.eligibility import EligibilityEngine
from bomba_sr.skills.skillmd_parser import SkillMdParser


class SkillLoader:
    def __init__(
        self,
        skill_roots: Iterable[Path],
        eligibility: EligibilityEngine,
        parser: SkillMdParser,
    ) -> None:
        self.skill_roots = tuple(Path(root).expanduser().resolve() for root in skill_roots)
        self.eligibility = eligibility
        self.parser = parser
        self._snapshot: dict[str, SkillDescriptor] = {}
        self._path_index: dict[str, Path] = {}
        self._lock = threading.Lock()
        self._watcher: threading.Thread | None = None
        self._watch_stop = threading.Event()
        self._watch_signature: tuple[tuple[str, int], ...] = ()
        self._diagnostics: dict[str, list[str]] = {}

    def scan(self) -> dict[str, SkillDescriptor]:
        candidates: dict[str, SkillDescriptor] = {}
        source_paths: dict[str, Path] = {}
        diagnostics: dict[str, list[str]] = {}

        for root in self.skill_roots:
            if not root.exists() or not root.is_dir():
                continue
            for skill_md in self._discover_skill_md(root):
                try:
                    descriptor, warnings = self.parser.parse_file_with_diagnostics(skill_md, include_body=False)
                except Exception:
                    continue
                if descriptor is None:
                    continue
                if warnings:
                    diagnostics[descriptor.skill_id] = list(warnings)

                if not self.eligibility.check(descriptor):
                    continue
                # Roots are precedence ordered. First match wins.
                if descriptor.skill_id in candidates:
                    continue
                candidates[descriptor.skill_id] = descriptor
                source_paths[descriptor.skill_id] = skill_md

        with self._lock:
            self._snapshot = dict(candidates)
            self._path_index = dict(source_paths)
            self._diagnostics = diagnostics
            self._watch_signature = self._compute_signature()
            return dict(self._snapshot)

    def load_skill_body(self, skill_id: str) -> str:
        with self._lock:
            descriptor = self._snapshot.get(skill_id)
            source_path = self._path_index.get(skill_id)
        if descriptor is None or source_path is None:
            raise ValueError(f"skill not found: {skill_id}")

        if descriptor._body_loaded:
            return descriptor.body_text

        loaded = self.parser.parse_file(source_path, include_body=True)
        with self._lock:
            self._snapshot[skill_id] = loaded
        return loaded.body_text

    def start_watcher(self, debounce_ms: int = 250) -> None:
        if self._watcher is not None and self._watcher.is_alive():
            return

        self._watch_stop.clear()

        def run() -> None:
            interval = max(0.1, debounce_ms / 1000.0)
            while not self._watch_stop.wait(interval):
                current = self._compute_signature()
                with self._lock:
                    previous = self._watch_signature
                if current != previous:
                    self.scan()

        self._watcher = threading.Thread(target=run, name="skill-loader-watcher", daemon=True)
        self._watcher.start()

    def stop_watcher(self) -> None:
        self._watch_stop.set()
        if self._watcher is not None:
            self._watcher.join(timeout=2.0)

    def snapshot(self) -> dict[str, SkillDescriptor]:
        with self._lock:
            return dict(self._snapshot)

    def diagnostics(self) -> dict[str, list[str]]:
        with self._lock:
            return {k: list(v) for k, v in self._diagnostics.items()}

    def _compute_signature(self) -> tuple[tuple[str, int], ...]:
        rows: list[tuple[str, int]] = []
        for root in self.skill_roots:
            if not root.exists() or not root.is_dir():
                continue
            for skill_md in self._discover_skill_md(root):
                try:
                    stat = skill_md.stat()
                except OSError:
                    continue
                rows.append((str(skill_md), int(stat.st_mtime_ns)))
        rows.sort()
        return tuple(rows)

    @staticmethod
    def _discover_skill_md(root: Path) -> list[Path]:
        out: list[Path] = []
        root_skill = root / "SKILL.md"
        if root_skill.exists() and root_skill.is_file():
            out.append(root_skill)

        try:
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                skill_md = child / "SKILL.md"
                if skill_md.exists() and skill_md.is_file():
                    out.append(skill_md)
        except OSError:
            return out
        return out
