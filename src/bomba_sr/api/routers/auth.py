"""Auth router — login, register, logout, me, change-password."""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from bomba_sr.api.deps import get_current_user, get_dashboard_svc

router = APIRouter(prefix="/api/mc/auth", tags=["auth"])

# ── Rate limiting (in-memory) ────────────────────────────────────────
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_RATE_WINDOW = 60.0
_LOGIN_RATE_MAX = 5


def _check_login_rate(email: str) -> bool:
    now = time.time()
    attempts = [t for t in _LOGIN_ATTEMPTS.get(email, []) if now - t < _LOGIN_RATE_WINDOW]
    _LOGIN_ATTEMPTS[email] = attempts
    return len(attempts) >= _LOGIN_RATE_MAX


def _record_login_failure(email: str) -> None:
    _LOGIN_ATTEMPTS.setdefault(email, []).append(time.time())


# ── Request / Response models ────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    email: str | None = None


# ── Public endpoints (no auth) ───────────────────────────────────────

@router.post("/login")
def login(body: LoginRequest, dashboard_svc=Depends(get_dashboard_svc)):
    email = body.email.strip().lower()
    password = body.password
    if not email or not password:
        raise HTTPException(400, "Email and password required")
    if _check_login_rate(email):
        raise HTTPException(429, "Too many login attempts. Try again later.")

    row = dashboard_svc.db.execute(
        "SELECT * FROM mc_users WHERE email = ?", (email,)
    ).fetchone()
    if not row:
        _record_login_failure(email)
        raise HTTPException(401, "Invalid credentials")

    user = dict(row)
    stored_hash = user.get("password_hash", "")
    if stored_hash.startswith("$2b$"):
        if not bcrypt.checkpw(password.encode(), stored_hash.encode()):
            _record_login_failure(email)
            raise HTTPException(401, "Invalid credentials")
    else:
        # Legacy SHA-256 — verify then upgrade to bcrypt
        if hashlib.sha256(password.encode()).hexdigest() != stored_hash:
            _record_login_failure(email)
            raise HTTPException(401, "Invalid credentials")
        new_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
        dashboard_svc.db.execute_commit(
            "UPDATE mc_users SET password_hash = ? WHERE id = ?",
            (new_hash, user["id"]),
        )

    # Single-session enforcement: invalidate existing tokens
    dashboard_svc.db.execute_commit(
        "DELETE FROM mc_sessions_auth WHERE user_id = ?", (user["id"],)
    )
    token = secrets.token_urlsafe(32)
    now_ts = datetime.now(timezone.utc).isoformat()
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    dashboard_svc.db.execute_commit(
        "INSERT INTO mc_sessions_auth (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
        (token, user["id"], now_ts, expires),
    )
    return {
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user.get("role", "operator"),
        "tenant_id": user.get("tenant_id", "tenant-local"),
        "token": token,
    }


@router.post("/register")
def register(body: RegisterRequest, dashboard_svc=Depends(get_dashboard_svc)):
    email = body.email.strip().lower()
    password = body.password
    name = body.name.strip()
    if not email or not password or not name:
        raise HTTPException(400, "Name, email, and password required")
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    existing = dashboard_svc.db.execute(
        "SELECT id FROM mc_users WHERE email = ?", (email,)
    ).fetchone()
    if existing:
        raise HTTPException(409, "Account already exists")

    uid = f"user-{uuid.uuid4().hex[:8]}"
    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    now = datetime.now(timezone.utc).isoformat()
    dashboard_svc.db.execute_commit(
        "INSERT INTO mc_users (id, email, name, password_hash, role, tenant_id, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (uid, email, name, pw_hash, "operator", tenant_id, now, now),
    )

    # Initialize tenant directory structure
    import os
    from pathlib import Path
    from bomba_sr.runtime.tenancy import TenantRegistry
    runtime_home = Path(os.getenv("BOMBA_RUNTIME_HOME", ".runtime"))
    registry = TenantRegistry(runtime_home)
    registry.ensure_tenant(tenant_id=tenant_id)

    # Issue token
    dashboard_svc.db.execute_commit(
        "DELETE FROM mc_sessions_auth WHERE user_id = ?", (uid,)
    )
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    dashboard_svc.db.execute_commit(
        "INSERT INTO mc_sessions_auth (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
        (token, uid, now, expires),
    )
    return {
        "user_id": uid,
        "email": email,
        "name": name,
        "role": "operator",
        "tenant_id": tenant_id,
        "token": token,
    }


# ── Protected endpoints (require auth) ──────────────────────────────

@router.get("/me")
def me(auth: dict = Depends(get_current_user), dashboard_svc=Depends(get_dashboard_svc)):
    row = dashboard_svc.db.execute(
        "SELECT id, email, name, role, tenant_id, created_at FROM mc_users WHERE id = ?",
        (auth["user_id"],),
    ).fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return {"user": dict(row)}


@router.patch("/me")
def update_me(
    body: UpdateProfileRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    updates: dict[str, str] = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.email is not None:
        updates["email"] = body.email.strip().lower()
    if not updates:
        raise HTTPException(400, "Nothing to update")

    set_clauses = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [datetime.now(timezone.utc).isoformat(), auth["user_id"]]
    dashboard_svc.db.execute_commit(
        f"UPDATE mc_users SET {set_clauses}, updated_at = ? WHERE id = ?",
        vals,
    )
    row = dashboard_svc.db.execute(
        "SELECT id, email, name, role, tenant_id, created_at FROM mc_users WHERE id = ?",
        (auth["user_id"],),
    ).fetchone()
    return {"user": dict(row)}


@router.post("/logout")
def logout(
    request: Request,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    # Delete the specific token (not all user sessions)
    raw_token = request.headers.get("Authorization", "")[7:]
    dashboard_svc.db.execute_commit(
        "DELETE FROM mc_sessions_auth WHERE token = ?", (raw_token,)
    )
    return {"ok": True}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    auth: dict = Depends(get_current_user),
    dashboard_svc=Depends(get_dashboard_svc),
):
    if not body.old_password or not body.new_password:
        raise HTTPException(400, "old_password and new_password required")
    if len(body.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters")

    row = dashboard_svc.db.execute(
        "SELECT password_hash FROM mc_users WHERE id = ?", (auth["user_id"],)
    ).fetchone()
    if not row:
        raise HTTPException(404, "User not found")

    stored = dict(row).get("password_hash", "")
    if stored.startswith("$2b$"):
        if not bcrypt.checkpw(body.old_password.encode(), stored.encode()):
            raise HTTPException(401, "Invalid current password")
    else:
        if hashlib.sha256(body.old_password.encode()).hexdigest() != stored:
            raise HTTPException(401, "Invalid current password")

    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
    dashboard_svc.db.execute_commit(
        "UPDATE mc_users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (new_hash, datetime.now(timezone.utc).isoformat(), auth["user_id"]),
    )
    # Invalidate all sessions
    dashboard_svc.db.execute_commit(
        "DELETE FROM mc_sessions_auth WHERE user_id = ?", (auth["user_id"],)
    )
    return {"ok": True}
