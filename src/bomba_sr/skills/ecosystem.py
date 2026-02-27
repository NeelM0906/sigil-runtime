from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.skills.loader import SkillLoader
from bomba_sr.skills.registry import SkillRegistry
from bomba_sr.skills.skillmd_parser import SkillMdParser
from bomba_sr.storage.db import RuntimeDB


TRUST_READ_ONLY = "read_only"
TRUST_ALLOW_WITH_APPROVAL = "allow_with_approval"
TRUST_BLOCKED = "blocked"
VALID_TRUST_MODES = {TRUST_READ_ONLY, TRUST_ALLOW_WITH_APPROVAL, TRUST_BLOCKED}

SOURCE_ANTHROPIC = "anthropic_skills"
SOURCE_CLAWHUB = "clawhub"
KNOWN_SOURCES = {SOURCE_ANTHROPIC, SOURCE_CLAWHUB}

SHARED_TRUST_DEFAULTS = {
    SOURCE_ANTHROPIC: TRUST_ALLOW_WITH_APPROVAL,
    SOURCE_CLAWHUB: TRUST_ALLOW_WITH_APPROVAL,
}


@dataclass(frozen=True)
class CatalogSkill:
    source: str
    skill_id: str
    name: str
    description: str
    repo: str
    branch: str
    path: str
    download_url: str


@dataclass(frozen=True)
class InstallRequest:
    request_id: str
    tenant_id: str
    user_id: str
    source: str
    skill_id: str
    status: str
    approval_id: str | None
    reason: str | None
    installed_path: str | None


class SkillEcosystemService:
    def __init__(
        self,
        db: RuntimeDB,
        registry: SkillRegistry,
        loader: SkillLoader,
        parser: SkillMdParser,
        governance: ToolGovernanceService,
        *,
        enabled_sources: tuple[str, ...] = (SOURCE_CLAWHUB, SOURCE_ANTHROPIC),
        telemetry_enabled: bool = True,
        fetcher: Callable[[str], bytes] | None = None,
    ) -> None:
        self.db = db
        self.registry = registry
        self.loader = loader
        self.parser = parser
        self.governance = governance
        self.enabled_sources = tuple(s for s in enabled_sources if s in KNOWN_SOURCES)
        self.telemetry_enabled = telemetry_enabled
        self.fetcher = fetcher or self._default_fetch
        self._ensure_schema()

    def list_catalog_skills(self, source: str | None = None, limit: int = 200) -> list[CatalogSkill]:
        selected = source.strip() if isinstance(source, str) else None
        if selected and selected not in KNOWN_SOURCES:
            raise ValueError(f"unknown source: {selected}")

        out: list[CatalogSkill] = []
        sources = [selected] if selected else list(self.enabled_sources)
        for item in sources:
            if item == SOURCE_ANTHROPIC:
                out.extend(self._fetch_repo_catalog("anthropics/skills", source=item))
            elif item == SOURCE_CLAWHUB:
                out.extend(self._fetch_repo_catalog("openclaw/clawhub", source=item))
        out.sort(key=lambda x: (x.source, x.skill_id))
        return out[: max(1, int(limit))]

    def trust_policy(self, tenant_id: str) -> dict[str, str]:
        policy = dict(SHARED_TRUST_DEFAULTS)
        rows = self.db.execute(
            "SELECT source, trust_mode FROM skill_source_trust_overrides WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchall()
        for row in rows:
            src = str(row["source"])
            mode = str(row["trust_mode"])
            if src in KNOWN_SOURCES and mode in VALID_TRUST_MODES:
                policy[src] = mode
        return policy

    def set_trust_override(self, tenant_id: str, source: str, trust_mode: str) -> dict[str, str]:
        if source not in KNOWN_SOURCES:
            raise ValueError(f"unknown source: {source}")
        if trust_mode not in VALID_TRUST_MODES:
            raise ValueError(f"invalid trust_mode: {trust_mode}")
        now = self._now()
        self.db.execute(
            """
            INSERT INTO skill_source_trust_overrides (id, tenant_id, source, trust_mode, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id, source) DO UPDATE SET
              trust_mode = excluded.trust_mode,
              updated_at = excluded.updated_at
            """,
            (str(uuid.uuid4()), tenant_id, source, trust_mode, now),
        )
        self.db.commit()
        self._telemetry(tenant_id, None, "trust_override_set", {"source": source, "trust_mode": trust_mode})
        return self.trust_policy(tenant_id)

    def create_install_request(
        self,
        tenant_id: str,
        user_id: str,
        source: str,
        skill_id: str,
        workspace_root: str,
        session_id: str | None,
        turn_id: str | None,
        reason: str | None = None,
    ) -> InstallRequest:
        source = source.strip()
        skill_id = skill_id.strip()
        policy = self.trust_policy(tenant_id)
        mode = policy.get(source, TRUST_BLOCKED)
        if mode == TRUST_BLOCKED:
            raise ValueError(f"source blocked by trust policy: {source}")
        if mode == TRUST_READ_ONLY:
            raise ValueError(f"source is read-only: {source} (install disabled)")

        catalog_item = self._find_catalog_item(source, skill_id)
        decision = self.governance.evaluate(
            tenant_id=tenant_id,
            action_type="write",
            risk_class="high",
            confidence=0.0,
            payload={
                "tool_name": "skill_install_from_catalog",
                "source": source,
                "skill_id": skill_id,
                "download_url": catalog_item.download_url,
                "workspace_root": workspace_root,
            },
            session_id=session_id,
            turn_id=turn_id,
            reason=reason or "install_from_external_catalog_requires_approval",
        )
        if not decision.requires_approval or not decision.approval_id:
            raise RuntimeError("expected approval workflow for install request")

        req_id = str(uuid.uuid4())
        self.db.execute(
            """
            INSERT INTO skill_install_requests (
              id, tenant_id, user_id, source, skill_id, status, approval_id, reason, catalog_json, installed_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                req_id,
                tenant_id,
                user_id,
                source,
                skill_id,
                "pending_approval",
                decision.approval_id,
                reason,
                json.dumps(catalog_item.__dict__, separators=(",", ":")),
                self._now(),
                self._now(),
            ),
        )
        self.db.commit()
        self._telemetry(
            tenant_id,
            user_id,
            "install_request_created",
            {"request_id": req_id, "source": source, "skill_id": skill_id, "approval_id": decision.approval_id},
        )
        return self.get_install_request(tenant_id, req_id)

    def get_install_request(self, tenant_id: str, request_id: str) -> InstallRequest:
        row = self.db.execute(
            "SELECT * FROM skill_install_requests WHERE tenant_id = ? AND id = ?",
            (tenant_id, request_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"install request not found: {request_id}")
        return InstallRequest(
            request_id=str(row["id"]),
            tenant_id=str(row["tenant_id"]),
            user_id=str(row["user_id"]),
            source=str(row["source"]),
            skill_id=str(row["skill_id"]),
            status=str(row["status"]),
            approval_id=(str(row["approval_id"]) if row["approval_id"] is not None else None),
            reason=(str(row["reason"]) if row["reason"] is not None else None),
            installed_path=(str(row["installed_path"]) if row["installed_path"] is not None else None),
        )

    def list_install_requests(self, tenant_id: str, status: str | None = None, limit: int = 100) -> list[InstallRequest]:
        if status:
            rows = self.db.execute(
                """
                SELECT * FROM skill_install_requests
                WHERE tenant_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (tenant_id, status, limit),
            ).fetchall()
        else:
            rows = self.db.execute(
                """
                SELECT * FROM skill_install_requests
                WHERE tenant_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (tenant_id, limit),
            ).fetchall()
        return [
            InstallRequest(
                request_id=str(row["id"]),
                tenant_id=str(row["tenant_id"]),
                user_id=str(row["user_id"]),
                source=str(row["source"]),
                skill_id=str(row["skill_id"]),
                status=str(row["status"]),
                approval_id=(str(row["approval_id"]) if row["approval_id"] is not None else None),
                reason=(str(row["reason"]) if row["reason"] is not None else None),
                installed_path=(str(row["installed_path"]) if row["installed_path"] is not None else None),
            )
            for row in rows
        ]

    def execute_install(self, tenant_id: str, request_id: str, workspace_root: str) -> dict[str, Any]:
        request = self.get_install_request(tenant_id, request_id)
        if request.status == "installed":
            return {"installed": True, "request_id": request_id, "path": request.installed_path, "already_installed": True}

        if not request.approval_id:
            raise ValueError("install request missing approval id")
        approval = self.governance.get_approval(tenant_id, request.approval_id)
        if approval is None:
            raise ValueError("install approval not found")
        if approval["status"] != "approved":
            self._update_request_status(tenant_id, request_id, "pending_approval")
            raise ValueError(f"install request not approved yet: status={approval['status']}")

        row = self.db.execute(
            "SELECT catalog_json FROM skill_install_requests WHERE tenant_id = ? AND id = ?",
            (tenant_id, request_id),
        ).fetchone()
        if row is None:
            raise ValueError("install request not found")
        catalog_item = json.loads(str(row["catalog_json"]))
        raw = self.fetcher(str(catalog_item["download_url"])).decode("utf-8", errors="replace")

        skill_dir = Path(workspace_root).expanduser().resolve() / "skills" / request.skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(raw, encoding="utf-8")

        descriptor, warnings = self.parser.parse_file_with_diagnostics(skill_path, include_body=False, permissive=True)
        if descriptor is None:
            raise ValueError(f"unable to parse installed skill: {request.skill_id}")
        self.registry.register_from_descriptor(tenant_id=tenant_id, descriptor=descriptor, status="active")
        self.loader.scan()
        self._update_request_status(tenant_id, request_id, "installed", installed_path=str(skill_path))
        if warnings:
            self._telemetry(
                tenant_id,
                request.user_id,
                "install_parse_warnings",
                {"request_id": request_id, "skill_id": request.skill_id, "warnings": warnings},
            )
        self._telemetry(
            tenant_id,
            request.user_id,
            "install_completed",
            {"request_id": request_id, "source": request.source, "skill_id": request.skill_id, "path": str(skill_path)},
        )
        return {
            "installed": True,
            "request_id": request_id,
            "skill_id": request.skill_id,
            "path": str(skill_path),
            "warnings": warnings,
        }

    def list_telemetry(self, tenant_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.execute(
            """
            SELECT * FROM skill_telemetry_events
            WHERE tenant_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (tenant_id, limit),
        ).fetchall()
        return [
            {
                "event_id": str(row["id"]),
                "tenant_id": str(row["tenant_id"]),
                "user_id": (str(row["user_id"]) if row["user_id"] is not None else None),
                "event_type": str(row["event_type"]),
                "payload": json.loads(str(row["payload_json"])),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def _find_catalog_item(self, source: str, skill_id: str) -> CatalogSkill:
        for item in self.list_catalog_skills(source=source, limit=5000):
            if item.skill_id == skill_id:
                return item
        raise ValueError(f"skill not found in catalog: {source}/{skill_id}")

    def _update_request_status(
        self,
        tenant_id: str,
        request_id: str,
        status: str,
        *,
        installed_path: str | None = None,
    ) -> None:
        self.db.execute(
            """
            UPDATE skill_install_requests
            SET status = ?, installed_path = COALESCE(?, installed_path), updated_at = ?
            WHERE tenant_id = ? AND id = ?
            """,
            (status, installed_path, self._now(), tenant_id, request_id),
        )
        self.db.commit()

    def _fetch_repo_catalog(self, repo: str, source: str) -> list[CatalogSkill]:
        branch = "main"
        tree = self._get_git_tree(repo, branch)
        if tree is None:
            branch = "master"
            tree = self._get_git_tree(repo, branch) or []
        out: list[CatalogSkill] = []
        for row in tree:
            if not isinstance(row, dict):
                continue
            path = str(row.get("path") or "")
            if not path.endswith("SKILL.md"):
                continue
            skill_id = Path(path).parent.name.strip().lower()
            if not skill_id:
                continue
            raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
            title, description = self._extract_frontmatter_summary(raw_url, skill_id)
            out.append(
                CatalogSkill(
                    source=source,
                    skill_id=skill_id,
                    name=title,
                    description=description,
                    repo=repo,
                    branch=branch,
                    path=path,
                    download_url=raw_url,
                )
            )
        self._telemetry("shared", None, "catalog_listed", {"source": source, "count": len(out)})
        return out

    def _get_git_tree(self, repo: str, branch: str) -> list[dict[str, Any]] | None:
        url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
        try:
            payload = json.loads(self.fetcher(url).decode("utf-8"))
        except Exception:
            return None
        tree = payload.get("tree")
        if not isinstance(tree, list):
            return None
        return [dict(x) for x in tree if isinstance(x, dict)]

    def _extract_frontmatter_summary(self, raw_url: str, fallback_name: str) -> tuple[str, str]:
        try:
            raw = self.fetcher(raw_url).decode("utf-8", errors="replace")
        except Exception:
            return fallback_name, f"Skill imported from {raw_url}"
        match = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n?", raw, re.DOTALL)
        name = fallback_name
        description = f"Skill imported from {raw_url}"
        if match:
            block = match.group(1)
            n = re.search(r"^name:\s*(.+)$", block, re.MULTILINE)
            d = re.search(r"^description:\s*(.+)$", block, re.MULTILINE)
            if n:
                name = n.group(1).strip().strip("'\"")
            if d:
                description = d.group(1).strip().strip("'\"")
        return name, description

    def _telemetry(self, tenant_id: str, user_id: str | None, event_type: str, payload: dict[str, Any]) -> None:
        if not self.telemetry_enabled:
            return
        self.db.execute(
            """
            INSERT INTO skill_telemetry_events (id, tenant_id, user_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                tenant_id,
                user_id,
                event_type,
                json.dumps(payload, separators=(",", ":")),
                self._now(),
            ),
        )
        self.db.commit()

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS skill_source_trust_overrides (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              source TEXT NOT NULL,
              trust_mode TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(tenant_id, source)
            );

            CREATE TABLE IF NOT EXISTS skill_install_requests (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              source TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              status TEXT NOT NULL,
              approval_id TEXT,
              reason TEXT,
              catalog_json TEXT NOT NULL,
              installed_path TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS skill_telemetry_events (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              user_id TEXT,
              event_type TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_skill_install_requests_tenant
              ON skill_install_requests(tenant_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_skill_telemetry_tenant
              ON skill_telemetry_events(tenant_id, created_at DESC);
            """
        )
        self.db.commit()

    @staticmethod
    def _default_fetch(url: str) -> bytes:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "bomba-sr/1.0",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            raise ValueError(f"fetch failed {exc.code} for {url}") from exc

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
