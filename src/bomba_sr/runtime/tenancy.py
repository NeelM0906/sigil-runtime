from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


_TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


class TenantIsolationError(ValueError):
    pass


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    tenant_home: Path
    workspace_root: Path
    runtime_root: Path
    db_path: Path
    memory_root: Path
    artifacts_root: Path


class TenantRegistry:
    def __init__(self, runtime_home: str | Path) -> None:
        self.runtime_home = Path(runtime_home).resolve()
        self.tenants_root = self.runtime_home / "tenants"
        self.tenants_root.mkdir(parents=True, exist_ok=True)

    def ensure_tenant(self, tenant_id: str, workspace_root: str | Path | None = None) -> TenantContext:
        self._validate_tenant_id(tenant_id)

        tenant_home = self.tenants_root / tenant_id
        tenant_home.mkdir(parents=True, exist_ok=True)

        metadata_path = tenant_home / "tenant.json"
        resolved_workspace = self._resolve_workspace(tenant_home, metadata_path, workspace_root)
        resolved_workspace.mkdir(parents=True, exist_ok=True)

        runtime_root = tenant_home / "runtime"
        runtime_root.mkdir(parents=True, exist_ok=True)

        memory_root = tenant_home / "memory"
        memory_root.mkdir(parents=True, exist_ok=True)

        artifacts_root = tenant_home / "artifacts"
        artifacts_root.mkdir(parents=True, exist_ok=True)

        db_path = runtime_root / "runtime.db"

        self._write_metadata(metadata_path, tenant_id, resolved_workspace)
        return TenantContext(
            tenant_id=tenant_id,
            tenant_home=tenant_home,
            workspace_root=resolved_workspace,
            runtime_root=runtime_root,
            db_path=db_path,
            memory_root=memory_root,
            artifacts_root=artifacts_root,
        )

    def guard_path(self, tenant: TenantContext, path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = (tenant.workspace_root / candidate).resolve()
        else:
            candidate = candidate.resolve()

        root = tenant.workspace_root.resolve()
        if candidate == root or root in candidate.parents:
            return candidate

        raise TenantIsolationError(
            f"Path escapes tenant workspace boundary: {candidate} not under {root}"
        )

    @staticmethod
    def _validate_tenant_id(tenant_id: str) -> None:
        if not _TENANT_ID_PATTERN.match(tenant_id):
            raise TenantIsolationError(
                "Invalid tenant_id. Use letters, numbers, underscore, hyphen, dot (max 128)."
            )

    def _resolve_workspace(
        self,
        tenant_home: Path,
        metadata_path: Path,
        workspace_root: str | Path | None,
    ) -> Path:
        if workspace_root is not None:
            chosen = Path(workspace_root).expanduser().resolve()
            return chosen

        if metadata_path.exists():
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            existing = payload.get("workspace_root")
            if isinstance(existing, str) and existing:
                return Path(existing).expanduser().resolve()

        return (tenant_home / "workspace").resolve()

    @staticmethod
    def _write_metadata(metadata_path: Path, tenant_id: str, workspace_root: Path) -> None:
        payload = {
            "tenant_id": tenant_id,
            "workspace_root": str(workspace_root),
        }
        metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
