"""Tests for the Mission Control DashboardService."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bomba_sr.dashboard.service import (
    DashboardService, MC_TENANT, MC_PROJECT_ID,
    TYPE_SISTER, TYPE_RUNTIME, TYPE_VOICE_AGENT, TYPE_SUBAGENT,
    _extract_json, _NOT_TASK_PATTERNS, _REPRESENTATION_KEYWORDS,
)
from bomba_sr.artifacts.store import ArtifactStore
from bomba_sr.openclaw.integration import ensure_portable_openclaw_layout, list_agent_workspaces, load_openclaw_config
from bomba_sr.projects.service import ProjectService
from bomba_sr.storage.db import RuntimeDB


@pytest.fixture()
def db():
    _db = RuntimeDB(":memory:")
    yield _db
    _db.close()


@pytest.fixture(autouse=True)
def isolate_openclaw_env(monkeypatch, tmp_path):
    monkeypatch.setenv("BOMBA_OPENCLAW_SOURCE_ROOT", str(tmp_path / "missing-openclaw"))
    monkeypatch.setenv("BOMBA_OPENCLAW_SYNC_POLL_SECONDS", "0")
    monkeypatch.setenv("BOMBA_ENABLE_BUNDLED_SYNC", "false")


@pytest.fixture()
def project_svc(db):
    return ProjectService(db)


@pytest.fixture()
def svc(db):
    return DashboardService(db=db, bridge=None, sisters=None)


@pytest.fixture()
def svc_with_bridge(db):
    mock_bridge = MagicMock()
    mock_bridge.handle_turn.return_value = {"reply": "Hello from mock LLM"}
    return DashboardService(db=db, bridge=mock_bridge, sisters=None)


SEED_DATA_DIR = Path(__file__).resolve().parent.parent / "mission-control" / "data"


# ── Schema ────────────────────────────────────────────────────

class TestSchema:
    def test_tables_created(self, db, svc):
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "mc_beings" in tables
        assert "mc_messages" in tables
        assert "mc_task_history" in tables
        assert "mc_task_assignments" in tables
        assert "mc_events" in tables

    def test_idempotent_schema(self, db):
        """Creating the service twice should not fail."""
        DashboardService(db=db)
        DashboardService(db=db)


# ── Beings ────────────────────────────────────────────────────

class TestBeings:
    def test_seed_beings(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        count = svc.seed_beings(path)
        assert count == 7  # 7 beings in seed data
        beings = svc.list_beings()
        assert len(beings) == 7

    def test_seed_idempotent(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        second = svc.seed_beings(path)
        assert second == 0  # no-op

    def test_seed_missing_file(self, svc):
        count = svc.seed_beings("/nonexistent/beings.json")
        assert count == 0

    def test_list_beings_filter_type(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        sisters = svc.list_beings(type_filter="sister")
        assert all(b["type"] == "sister" for b in sisters)
        assert len(sisters) == 3  # forge, scholar, recovery

    def test_list_beings_filter_status(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        online = svc.list_beings(status_filter="online")
        assert all(b["status"] == "online" for b in online)

    def test_get_being(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        b = svc.get_being("prime")
        assert b is not None
        assert b["name"] == "Prime"
        assert b["type"] == "runtime"

    def test_sanitizes_stored_paths_in_messages_and_beings(self, svc, db):
        now = svc._now()
        db.execute(
            "INSERT INTO mc_messages (id, type, sender, targets, content, timestamp, mode, task_ref, session_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "msg-path",
                "direct",
                "user",
                json.dumps(["prime"]),
                '[tool] read {"path": "/Users/tester/.openclaw/workspace-scholar/HEARTBEAT.md"}',
                now,
                "auto",
                None,
                "general",
            ),
        )
        db.execute(
            "INSERT INTO mc_beings (id,name,status,created_at,updated_at,workspace) VALUES (?,?,?,?,?,?)",
            (
                "portable-being",
                "Portable Being",
                "online",
                now,
                now,
                "/Users/tester/.openclaw/sigil-runtime-chat-sessions-deliverables/workspaces/forge",
            ),
        )
        db.commit()

        svc._sanitize_stored_paths()

        msg = next(m for m in svc.list_messages(session_id="general", limit=10) if m["id"] == "msg-path")
        assert "/Users/tester/" not in msg["content"]
        assert "~/.openclaw" in msg["content"]

        being = svc.get_being("portable-being")
        assert being is not None
        assert being["workspace"] == "workspaces/forge"

    def test_get_being_not_found(self, svc):
        assert svc.get_being("nonexistent") is None

    def test_update_being(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        updated = svc.update_being("prime", {"status": "busy"})
        assert updated["status"] == "busy"

    def test_update_being_not_found(self, svc):
        result = svc.update_being("nonexistent", {"status": "online"})
        assert result is None

    def test_being_tools_deserialized(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        b = svc.get_being("prime")
        assert isinstance(b["tools"], list)
        assert len(b["tools"]) > 0

    def test_sync_being_statuses_no_sisters(self, svc):
        """Should not crash when no sisters registry is available."""
        svc.sync_being_statuses_from_sisters()  # no-op


# ── Config-driven beings loader ──────────────────────────────

class TestConfigLoader:
    def test_load_beings_from_configs(self, svc):
        """Should load beings from real workspace config files."""
        count = svc.load_beings_from_configs()
        assert count > 0
        beings = svc.list_beings()
        assert len(beings) == count

    def test_prime_loaded_as_runtime(self, svc):
        svc.load_beings_from_configs()
        prime = svc.get_being("prime")
        assert prime is not None
        assert prime["type"] == TYPE_RUNTIME
        assert prime["status"] == "online"
        assert prime["workspace"] == "workspaces/prime"

    def test_sisters_loaded_from_json(self, svc):
        svc.load_beings_from_configs()
        forge = svc.get_being("forge")
        assert forge is not None
        assert forge["type"] == TYPE_SISTER
        assert forge["tenant_id"] == "tenant-forge"
        assert forge["workspace"] == "workspaces/forge"

    def test_soul_name_loaded(self, svc):
        """Sisters should get their name from SoulConfig."""
        svc.load_beings_from_configs()
        forge = svc.get_being("forge")
        # SoulConfig parses "Sai Forge" from workspaces/forge/SOUL.md
        assert forge is not None
        assert "Forge" in forge["name"]

    def test_voice_agents_loaded(self, svc):
        svc.load_beings_from_configs()
        callie = svc.get_being("callie")
        assert callie is not None
        assert callie["type"] == TYPE_VOICE_AGENT
        assert callie["agent_id"]  # Should have a Bland agent_id

    def test_voice_agents_no_tenant(self, svc):
        """Voice agents should have no tenant — they live on Bland.ai."""
        svc.load_beings_from_configs()
        callie = svc.get_being("callie")
        assert callie["tenant_id"] == ""

    def test_upsert_idempotent(self, svc):
        """Running load twice should update, not duplicate."""
        count1 = svc.load_beings_from_configs()
        count2 = svc.load_beings_from_configs()
        assert count1 == count2
        beings = svc.list_beings()
        assert len(beings) == count1

    def test_filter_by_type_sister(self, svc):
        svc.load_beings_from_configs()
        sisters = svc.list_beings(type_filter=TYPE_SISTER)
        assert all(b["type"] == TYPE_SISTER for b in sisters)
        assert len(sisters) >= 3  # forge, scholar, recovery at minimum

    def test_filter_by_type_voice(self, svc):
        svc.load_beings_from_configs()
        voice = svc.list_beings(type_filter=TYPE_VOICE_AGENT)
        assert all(b["type"] == TYPE_VOICE_AGENT for b in voice)
        assert len(voice) >= 1

    def test_recovery_sister_tenant(self, svc):
        svc.load_beings_from_configs()
        recovery = svc.get_being("recovery")
        assert recovery is not None
        assert recovery["tenant_id"] == "tenant-recovery"


# ── Chat Messages ─────────────────────────────────────────────

class TestChat:
    def test_create_and_list_messages(self, svc):
        msg = svc.create_message(sender="user", content="Hello world")
        assert msg["sender"] == "user"
        assert msg["content"] == "Hello world"
        assert msg["id"].startswith("msg-")

        msgs = svc.list_messages()
        assert len(msgs) == 1
        assert msgs[0]["id"] == msg["id"]

    def test_message_targets(self, svc):
        msg = svc.create_message(
            sender="user",
            content="@athena check metrics",
            targets=["athena"],
            msg_type="direct",
        )
        assert msg["targets"] == ["athena"]

    def test_filter_by_sender(self, svc):
        svc.create_message(sender="user", content="msg 1")
        svc.create_message(sender="athena", content="msg 2")
        user_msgs = svc.list_messages(sender="user")
        assert len(user_msgs) == 1
        assert user_msgs[0]["sender"] == "user"

    def test_filter_by_search(self, svc):
        svc.create_message(sender="user", content="check metrics please")
        svc.create_message(sender="user", content="hello world")
        results = svc.list_messages(search="metrics")
        assert len(results) == 1

    def test_system_message(self, svc):
        msg = svc.create_system_message("Task created", task_ref="task-001")
        assert msg["type"] == "system"
        assert msg["sender"] == "system"
        assert msg["task_ref"] == "task-001"

    def test_delete_message(self, svc):
        msg = svc.create_message(sender="user", content="to delete")
        assert svc.delete_message(msg["id"]) is True
        assert svc.list_messages() == []

    def test_delete_nonexistent_message(self, svc):
        assert svc.delete_message("msg-nonexistent") is False

    def test_pagination(self, svc):
        for i in range(10):
            svc.create_message(sender="user", content=f"msg {i}")
        page = svc.list_messages(limit=3, offset=0)
        assert len(page) == 3
        page2 = svc.list_messages(limit=3, offset=3)
        assert len(page2) == 3
        assert page[0]["id"] != page2[0]["id"]

    def test_list_messages_does_not_force_openclaw_sync(self, svc):
        sync = MagicMock()
        svc.openclaw_sync = sync
        svc.create_message(sender="user", content="no sync please")

        msgs = svc.list_messages()

        assert len(msgs) == 1
        sync.sync_once.assert_not_called()

    def test_route_to_being_no_bridge(self, svc):
        """Without a bridge, should create an offline placeholder message."""
        svc.route_to_being("athena", "Hello")
        # Wait for the background thread
        time.sleep(0.2)
        msgs = svc.list_messages(sender="athena")
        assert len(msgs) == 1
        assert "offline" in msgs[0]["content"].lower() or "no LLM" in msgs[0]["content"]

    def test_route_to_being_with_bridge(self, svc_with_bridge):
        path = SEED_DATA_DIR / "beings.json"
        if path.exists():
            svc_with_bridge.seed_beings(path)
        svc_with_bridge.route_to_being("athena", "What's our status?")
        time.sleep(0.3)
        msgs = svc_with_bridge.list_messages(sender="athena")
        assert len(msgs) == 1
        assert msgs[0]["content"] == "Hello from mock LLM"

    def test_short_confirmation_anchors_latest_offer(self, db):
        captured: dict[str, str] = {}
        mock_bridge = MagicMock()

        def _handle(req):
            captured["user_message"] = req.user_message
            return {"reply": "Queued"}

        mock_bridge.handle_turn.side_effect = _handle
        svc = DashboardService(db=db, bridge=mock_bridge, sisters=None)
        svc.load_beings_from_configs()
        svc.create_message(
            sender="prime",
            content="I can generate the mountain cycling sunrise video now. Say 'yes generate it' and I'll run that exact video prompt.",
            targets=["user"],
            msg_type="direct",
            session_id="general",
        )

        svc._route_to_being_sync("prime", "yes generate it", "user", "general")

        assert "confirmed_offer" in captured["user_message"]
        assert "mountain cycling sunrise video" in captured["user_message"]
        assert captured["user_message"].rstrip().endswith("User follow-up: yes generate it")

    def test_route_to_voice_agent_rejected(self, svc):
        """Voice agents should not be chat-routable."""
        svc.load_beings_from_configs()
        svc.route_to_being("callie", "Hello")
        time.sleep(0.2)
        msgs = svc.list_messages(sender="callie")
        assert len(msgs) == 1
        assert "voice agent" in msgs[0]["content"].lower()


class TestOpenClawSync:
    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    def test_imports_live_openclaw_session_into_dashboard(self, db, project_svc, monkeypatch, tmp_path):
        openclaw_root = tmp_path / "openclaw"
        workspace = openclaw_root / "workspace"
        (workspace / "memory").mkdir(parents=True)
        (workspace / "memory" / "2026-03-11.md").write_text("memory", encoding="utf-8")
        (workspace / "AGENTS.md").write_text("# Prime", encoding="utf-8")

        (openclaw_root / "openclaw.json").write_text(json.dumps({
            "agents": {
                "list": [
                    {
                        "id": "main",
                        "workspace": str(workspace),
                        "model": {"primary": "openrouter/anthropic/claude-opus-4.6"},
                        "tools": {"alsoAllow": ["read", "exec"]},
                    }
                ]
            }
        }), encoding="utf-8")

        session_id = "11111111-2222-3333-4444-555555555555"
        updated_at_ms = int(time.time() * 1000)
        sessions_dir = openclaw_root / "agents" / "main" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "sessions.json").write_text(json.dumps({
            "agent:main:discord:channel:1477568016697790486": {
                "sessionId": session_id,
                "updatedAt": updated_at_ms,
            }
        }), encoding="utf-8")
        self._write_jsonl(
            sessions_dir / f"{session_id}.jsonl",
            [
                {
                    "type": "session",
                    "version": 3,
                    "id": session_id,
                    "timestamp": "2026-03-11T17:00:00Z",
                    "cwd": str(workspace),
                },
                {
                    "type": "message",
                    "timestamp": "2026-03-11T17:00:01Z",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": "Query Pinecone for Sean positioning notes"}],
                    },
                },
                {
                    "type": "message",
                    "timestamp": "2026-03-11T17:00:02Z",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "toolCall",
                                "name": "pinecone_query",
                                "arguments": {"index": "ublib2", "query": "Sean positioning notes"},
                            }
                        ],
                    },
                },
                {
                    "type": "message",
                    "timestamp": "2026-03-11T17:00:03Z",
                    "message": {
                        "role": "toolResult",
                        "content": [{"type": "text", "text": "Found 3 relevant Pinecone matches"}],
                    },
                },
                {
                    "type": "message",
                    "timestamp": "2026-03-11T17:00:04Z",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "I found 3 notes and summarized the overlap."}],
                    },
                },
            ],
        )

        monkeypatch.setenv("BOMBA_OPENCLAW_SOURCE_ROOT", str(openclaw_root))
        monkeypatch.setenv("BOMBA_OPENCLAW_SYNC_POLL_SECONDS", "0")

        svc = DashboardService(db=db, bridge=None, sisters=None)
        svc.ensure_mc_project(project_svc)
        svc.sync_openclaw_once()

        imported = svc.get_session(session_id)
        assert imported is not None
        assert imported["name"].startswith("Discord 1477568016697790486")

        messages = svc.list_messages(session_id=session_id)
        assert [m["sender"] for m in messages] == ["user", "prime", "prime", "prime"]
        assert any("pinecone_query" in m["content"] for m in messages)
        assert any("Found 3 relevant Pinecone matches" in m["content"] for m in messages)

        tasks = svc.list_tasks(project_svc)
        imported_task = next((t for t in tasks if t["id"].startswith("ocl-task-")), None)
        assert imported_task is not None
        assert imported_task["status"] == "in_progress"
        assert imported_task["assignees"] == ["prime"]

        prime = svc.get_being("prime")
        assert prime is not None
        assert prime["workspace"] == str(openclaw_root)
        assert prime["status"] == "busy"
        assert "read" in prime["tools"]

        svc.sync_openclaw_once()
        session_again = svc.get_session(session_id)
        assert session_again is not None

    def test_being_detail_supports_external_workspace_paths(self, db, project_svc, monkeypatch, tmp_path):
        openclaw_root = tmp_path / "openclaw"
        workspace = openclaw_root / "workspace"
        (workspace / "memory").mkdir(parents=True)
        (workspace / "memory" / "today.md").write_text("hello", encoding="utf-8")
        (openclaw_root / "AGENTS.md").write_text("# Prime Root", encoding="utf-8")
        (openclaw_root / "openclaw.json").write_text(json.dumps({
            "agents": {"list": [{"id": "main", "workspace": str(workspace), "model": {"primary": "x"}}]}
        }), encoding="utf-8")
        sessions_dir = openclaw_root / "agents" / "main" / "sessions"
        session_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        (sessions_dir / "sessions.json").parent.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "sessions.json").write_text(json.dumps({
            "agent:main:main": {"sessionId": session_id, "updatedAt": int(time.time() * 1000)}
        }), encoding="utf-8")
        self._write_jsonl(sessions_dir / f"{session_id}.jsonl", [
            {"type": "session", "id": session_id, "timestamp": "2026-03-11T17:00:00Z", "cwd": str(workspace)},
            {"type": "message", "timestamp": "2026-03-11T17:00:01Z", "message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}},
        ])

        monkeypatch.setenv("BOMBA_OPENCLAW_SOURCE_ROOT", str(openclaw_root))
        monkeypatch.setenv("BOMBA_OPENCLAW_SYNC_POLL_SECONDS", "0")

        svc = DashboardService(db=db, bridge=None, sisters=None)
        svc.ensure_mc_project(project_svc)
        svc.sync_openclaw_once()

        detail = svc.get_being_detail("prime")
        assert detail is not None
        assert detail["identity"]["workspace_abs"] == str(openclaw_root.resolve())
        assert any(file["name"] == "AGENTS.md" for file in detail["identity"]["files"])

    def test_projects_catalog_lists_openclaw_projects(self, db, project_svc, monkeypatch, tmp_path):
        openclaw_root = tmp_path / "openclaw"
        main_workspace = openclaw_root / "workspace"
        forge_workspace = openclaw_root / "workspace-forge"
        (main_workspace / "Projects" / "colosseum" / "v2" / "data").mkdir(parents=True)
        (main_workspace / "Projects" / "client-alpha").mkdir(parents=True)
        (forge_workspace / "colosseum-dashboard").mkdir(parents=True)
        for rel in (
            "beings.json",
            "judges.json",
            "scenarios.json",
        ):
            (main_workspace / "Projects" / "colosseum" / "v2" / "data" / rel).write_text("{}", encoding="utf-8")
        (main_workspace / "Projects" / "colosseum" / "README.md").write_text("Main tournament", encoding="utf-8")
        (forge_workspace / "colosseum-dashboard" / "README.md").write_text("Forge arena", encoding="utf-8")
        (openclaw_root / "openclaw.json").write_text(json.dumps({
            "agents": {
                "defaults": {"workspace": str(main_workspace)},
                "list": [
                    {"id": "main", "workspace": str(main_workspace)},
                    {"id": "forge", "workspace": str(forge_workspace)},
                ],
            }
        }), encoding="utf-8")

        monkeypatch.setenv("BOMBA_OPENCLAW_SOURCE_ROOT", str(openclaw_root))
        monkeypatch.setenv("BOMBA_OPENCLAW_SYNC_POLL_SECONDS", "0")

        svc = DashboardService(db=db, bridge=None, sisters=None)
        svc.ensure_mc_project(project_svc)

        projects = svc.list_projects_catalog()
        ids = {project["id"] for project in projects}
        assert "workspace-main" in ids
        assert "main-project-colosseum" in ids
        assert "forge-colosseum-dashboard" in ids

    def test_runtime_chat_session_id_isolated_per_dashboard_session(self, svc):
        assert svc._runtime_chat_session_id("prime", "general") == "mc-chat-general-prime"
        assert svc._runtime_chat_session_id("prime", "session 42 / alpha") == "mc-chat-session-42-alpha-prime"


class TestPortableOpenClawBundle:
    def test_load_openclaw_config_with_explicit_root_without_external_sync(self, tmp_path, monkeypatch):
        monkeypatch.delenv("BOMBA_OPENCLAW_SOURCE_ROOT", raising=False)
        bundle_root = tmp_path / "portable-openclaw"
        (bundle_root / "agents").mkdir(parents=True)
        config_path = bundle_root / "openclaw.json"
        config_path.write_text(json.dumps({
            "agents": {
                "defaults": {"workspace": "/tmp/old-workspace"},
                "list": [{"id": "forge", "workspace": "/tmp/old-forge"}],
            }
        }), encoding="utf-8")

        payload = load_openclaw_config(bundle_root)

        assert payload["agents"]["defaults"]["workspace"] == "/tmp/old-workspace"

    def test_ensure_portable_openclaw_layout_rewrites_workspace_paths(self, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir(parents=True)
        (repo_root / "pyproject.toml").write_text("[project]\nname='portable-test'\nversion='0.0.0'\n", encoding="utf-8")
        (repo_root / "workspaces" / "prime" / "tools").mkdir(parents=True)
        (repo_root / "workspaces" / "forge" / "tools").mkdir(parents=True)
        (repo_root / "workspaces" / "scholar" / "tools").mkdir(parents=True)
        (repo_root / "workspaces" / "sai-memory" / "tools").mkdir(parents=True)
        (repo_root / "workspaces" / "recovery" / "tools").mkdir(parents=True)
        (repo_root / ".venv" / "bin").mkdir(parents=True)
        (repo_root / ".env").write_text("SUPABASE_URL=https://example.supabase.co\n", encoding="utf-8")
        bundle_root = repo_root / "portable-openclaw"
        bundle_root.mkdir(parents=True)
        (bundle_root / "openclaw.json").write_text(json.dumps({
            "agents": {
                "defaults": {"workspace": "./workspace"},
                "list": [
                    {"id": "main", "workspace": "./workspace"},
                    {"id": "forge", "workspace": "./workspace-forge"},
                ],
            }
        }), encoding="utf-8")

        portable_root = ensure_portable_openclaw_layout(repo_root)
        workspaces = list_agent_workspaces(portable_root)
        rewritten = json.loads((portable_root / "openclaw.json").read_text(encoding="utf-8"))

        assert portable_root == bundle_root
        assert (repo_root / ".portable-home" / ".openclaw").is_symlink()
        assert (bundle_root / "workspace").is_symlink()
        assert rewritten["agents"]["defaults"]["workspace"] == "./workspace"
        assert rewritten["agents"]["list"][0]["workspace"] == "./workspace"
        assert rewritten["agents"]["list"][1]["workspace"] == "./workspace-forge"
        assert workspaces["main"] == (repo_root / "workspaces" / "prime").resolve()
        assert workspaces["forge"] == (repo_root / "workspaces" / "forge").resolve()


# ── Tasks ─────────────────────────────────────────────────────

class TestTasks:
    def test_ensure_mc_project(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        proj = project_svc.get_project(MC_TENANT, MC_PROJECT_ID)
        assert proj["name"] == "Mission Control"

    def test_ensure_mc_project_idempotent(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        svc.ensure_mc_project(project_svc)  # should not fail

    def test_create_task(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Test task", priority="high")
        assert task["title"] == "Test task"
        assert task["priority"] == "high"
        assert task["status"] == "backlog"
        assert "assignees" in task

    def test_create_task_with_assignees(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(
            project_svc, title="Assigned task",
            assignees=["athena", "callie"],
        )
        assert set(task["assignees"]) == {"athena", "callie"}

    def test_list_tasks(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        svc.create_task(project_svc, title="Task A")
        svc.create_task(project_svc, title="Task B", priority="high")
        tasks = svc.list_tasks(project_svc)
        assert len(tasks) == 2

    def test_list_tasks_filter_priority(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        svc.create_task(project_svc, title="Normal", priority="normal")
        svc.create_task(project_svc, title="High", priority="high")
        high = svc.list_tasks(project_svc, priority="high")
        assert len(high) == 1
        assert high[0]["priority"] == "high"

    def test_list_tasks_filter_assignee(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        svc.create_task(project_svc, title="For Athena", assignees=["athena"])
        svc.create_task(project_svc, title="For Callie", assignees=["callie"])
        athena_tasks = svc.list_tasks(project_svc, assignee="athena")
        assert len(athena_tasks) == 1

    def test_get_task_with_history(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Task with history")
        result = svc.get_task(project_svc, task["task_id"])
        assert "history" in result
        assert len(result["history"]) >= 1
        assert result["history"][0]["action"] == "created"

    def test_update_task_status(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="To update")
        updated = svc.update_task(project_svc, task["task_id"], status="in_progress")
        assert updated["status"] == "in_progress"

    def test_update_task_assignees(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Reassign", assignees=["athena"])
        updated = svc.update_task(
            project_svc, task["task_id"],
            assignees=["callie", "mylo"],
        )
        assert set(updated["assignees"]) == {"callie", "mylo"}

    def test_delete_task(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="To delete")
        assert svc.delete_task(project_svc, task["task_id"]) is True
        assert svc.list_tasks(project_svc) == []

    def test_delete_task_not_found(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        assert svc.delete_task(project_svc, "nonexistent") is False

    def test_task_history_global(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        svc.create_task(project_svc, title="A")
        svc.create_task(project_svc, title="B")
        history = svc.task_history()
        assert len(history) == 2

    def test_task_history_per_task(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Tracked")
        svc.update_task(project_svc, task["task_id"], status="in_progress")
        history = svc.task_history(task_id=task["task_id"])
        assert len(history) == 2  # created + updated

    @patch.object(DashboardService, "_classify_message", return_value="light_task")
    def test_route_auto_creates_task(self, _mock_cls, db, project_svc):
        """Messaging a being should auto-create a task that transitions through statuses."""
        mock_bridge = MagicMock()
        mock_bridge.handle_turn.return_value = {"reply": "Done!"}
        svc = DashboardService(db=db, bridge=mock_bridge, sisters=None)
        svc.ensure_mc_project(project_svc)
        svc.load_beings_from_configs()

        # Subscribe to SSE to capture events
        cid = svc.subscribe_sse()

        svc.route_to_being("sai-memory", "Summarize the weekly report", sender="user")
        time.sleep(0.5)

        # Task should have been auto-created and finished
        tasks = svc.list_tasks(project_svc)
        chat_tasks = [t for t in tasks if "Summarize the weekly report" in t.get("title", "")]
        assert len(chat_tasks) >= 1, f"Expected auto-created task, got: {[t['title'] for t in tasks]}"

        task = chat_tasks[0]
        assert task["status"] == "done", f"Expected done, got {task['status']}"
        assert "sai-memory" in task.get("assignees", [])

        # SSE events should have been emitted for task creation and status changes
        events = []
        while True:
            evt = svc.poll_sse(cid, timeout=0.1)
            if evt is None:
                break
            events.append(evt)
        svc.unsubscribe_sse(cid)

        task_events = [e for e in events if e["event"] == "task_update"]
        assert len(task_events) >= 2, f"Expected >=2 task events, got {len(task_events)}"

    @patch.object(DashboardService, "_classify_message", return_value="light_task")
    def test_route_error_reverts_task(self, _mock_cls, db, project_svc):
        """If bridge.handle_turn raises, task should revert to backlog."""
        mock_bridge = MagicMock()
        mock_bridge.handle_turn.side_effect = RuntimeError("LLM failed")
        svc = DashboardService(db=db, bridge=mock_bridge, sisters=None)
        svc.ensure_mc_project(project_svc)
        svc.load_beings_from_configs()

        svc.route_to_being("sai-memory", "Fail this task", sender="user")
        time.sleep(0.5)

        tasks = svc.list_tasks(project_svc)
        chat_tasks = [t for t in tasks if "Fail this task" in t.get("title", "")]
        assert len(chat_tasks) >= 1
        assert chat_tasks[0]["status"] == "backlog"


# ── SSE ───────────────────────────────────────────────────────

class TestSSE:
    def test_subscribe_unsubscribe(self, svc):
        cid = svc.subscribe_sse()
        assert cid in svc._sse_clients
        svc.unsubscribe_sse(cid)
        assert cid not in svc._sse_clients

    def test_emit_event_delivered(self, svc):
        cid = svc.subscribe_sse()
        svc._emit_event("test_event", {"key": "value"})
        evt = svc.poll_sse(cid, timeout=1.0)
        assert evt is not None
        assert evt["event"] == "test_event"
        assert evt["data"]["key"] == "value"
        svc.unsubscribe_sse(cid)

    def test_emit_event_persisted(self, svc):
        svc._emit_event("test_event", {"key": "value"})
        rows = svc.db.execute("SELECT * FROM mc_events").fetchall()
        assert len(rows) == 1
        assert rows[0]["event_type"] == "test_event"

    def test_poll_timeout(self, svc):
        cid = svc.subscribe_sse()
        evt = svc.poll_sse(cid, timeout=0.1)
        assert evt is None
        svc.unsubscribe_sse(cid)

    def test_chat_message_emits_sse(self, svc):
        cid = svc.subscribe_sse()
        svc.create_message(sender="user", content="SSE test")
        evt = svc.poll_sse(cid, timeout=1.0)
        assert evt is not None
        assert evt["event"] == "chat_message"
        assert evt["data"]["content"] == "SSE test"
        svc.unsubscribe_sse(cid)

    def test_artifact_event_also_emits_output_payload(self, svc, tmp_path):
        store = ArtifactStore(svc.db, tmp_path / "artifacts")
        svc.set_artifact_store(store)
        record = store.create_binary_artifact(
            tenant_id=MC_TENANT,
            session_id="general",
            turn_id="turn-1",
            project_id=None,
            task_id=None,
            artifact_type="video",
            title="Fal video",
            data=b"video",
            filename="fal-video-1.mp4",
            created_by="fal:test",
        )
        cid = svc.subscribe_sse()

        svc.notify_artifact_created(record)

        evt = svc.poll_sse(cid, timeout=1.0)
        assert evt is not None
        assert evt["event"] == "deliverable_created"
        assert evt["data"]["filename"] == "fal-video-1.mp4"
        svc.unsubscribe_sse(cid)

    def test_being_status_emits_sse(self, svc):
        path = SEED_DATA_DIR / "beings.json"
        if not path.exists():
            pytest.skip("beings.json not found")
        svc.seed_beings(path)
        cid = svc.subscribe_sse()
        svc.update_being("prime", {"status": "busy"})
        evt = svc.poll_sse(cid, timeout=1.0)
        assert evt is not None
        assert evt["event"] == "being_status"
        assert evt["data"]["being_id"] == "prime"
        svc.unsubscribe_sse(cid)

    def test_task_update_emits_sse(self, svc, project_svc):
        svc.ensure_mc_project(project_svc)
        cid = svc.subscribe_sse()
        svc.create_task(project_svc, title="SSE task")
        evt = svc.poll_sse(cid, timeout=1.0)
        assert evt is not None
        assert evt["event"] == "task_update"
        assert evt["data"]["action"] == "created"
        svc.unsubscribe_sse(cid)

    def test_multiple_subscribers(self, svc):
        cid1 = svc.subscribe_sse()
        cid2 = svc.subscribe_sse()
        svc._emit_event("broadcast", {"msg": "hello"})
        e1 = svc.poll_sse(cid1, timeout=1.0)
        e2 = svc.poll_sse(cid2, timeout=1.0)
        assert e1 is not None
        assert e2 is not None
        assert e1["data"]["msg"] == "hello"
        assert e2["data"]["msg"] == "hello"
        svc.unsubscribe_sse(cid1)
        svc.unsubscribe_sse(cid2)


# ── Sub-agents ────────────────────────────────────────────────

class TestSubAgents:
    def test_list_subagent_runs_empty(self, svc):
        runs = svc.list_subagent_runs()
        assert runs == []

    def test_list_subagent_runs_no_table(self, db):
        """Should not crash if subagent_runs table does not exist."""
        svc = DashboardService(db=db)
        runs = svc.list_subagent_runs()
        assert runs == []


# ── Task Classification ──────────────────────────────────────

class TestTaskClassification:
    """Test the message classification layer that gates task creation."""

    def test_extract_json_plain(self):
        assert _extract_json('{"classification": "not_task"}') == {"classification": "not_task"}

    def test_extract_json_fenced(self):
        text = '```json\n{"classification": "full_task"}\n```'
        assert _extract_json(text) == {"classification": "full_task"}

    def test_extract_json_empty(self):
        assert _extract_json("") is None
        assert _extract_json("no json here") is None

    def test_not_task_patterns(self):
        """Common greetings/casual messages should match the fast-path regex."""
        not_tasks = [
            "Hi", "hey", "Hello", "howdy", "yo", "gm", "gn", "sup",
            "How are you?", "how's it going?", "thanks", "thank you",
            "ok", "okay", "bye", "see ya",
            "tell me about yourself", "who are you", "what can you do",
            "what tools do you have", "what tools are available",
            "what are your capabilities", "what do you know",
            "Good morning!", "HELLO", "Hi!",
        ]
        for msg in not_tasks:
            assert _NOT_TASK_PATTERNS.match(msg.strip()), f"Expected '{msg}' to match not_task pattern"

    def test_not_task_pattern_rejects_tasks(self):
        """Real task messages should NOT match the fast-path regex."""
        tasks = [
            "Search Pinecone for zone action content",
            "Audit all contacts in Supabase",
            "Research influence mastery and write a report",
            "What's the status of the Pinecone integration",
            "Summarize the weekly report",
        ]
        for msg in tasks:
            assert not _NOT_TASK_PATTERNS.match(msg.strip()), f"'{msg}' should NOT match not_task"

    def test_classify_message_fast_path_greeting(self, svc):
        """Greetings should be classified via regex fast-path (no LLM call)."""
        assert svc._classify_message("Hi") == "not_task"
        assert svc._classify_message("hey!") == "not_task"
        assert svc._classify_message("Hello") == "not_task"
        assert svc._classify_message("How are you?") == "not_task"

    def test_classify_message_short(self, svc):
        """Very short messages (< 4 chars) are not_task."""
        assert svc._classify_message("ok") == "not_task"
        assert svc._classify_message("hi") == "not_task"

    @patch("bomba_sr.llm.providers.provider_from_env")
    def test_classify_message_llm_light_task(self, mock_pfe, svc):
        """LLM returns light_task for single-action requests."""
        mock_provider = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = '{"classification": "light_task"}'
        mock_provider.generate.return_value = mock_resp
        mock_pfe.return_value = mock_provider

        result = svc._classify_message("Search Pinecone for zone action content")
        assert result == "light_task"

    @patch("bomba_sr.llm.providers.provider_from_env")
    def test_classify_message_llm_full_task(self, mock_pfe, svc):
        """LLM returns full_task for multi-step requests."""
        mock_provider = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = '{"classification": "full_task"}'
        mock_provider.generate.return_value = mock_resp
        mock_pfe.return_value = mock_provider

        result = svc._classify_message("Audit all memory files and flag inconsistencies")
        assert result == "full_task"

    @patch("bomba_sr.llm.providers.provider_from_env")
    def test_classify_message_llm_failure_defaults_not_task(self, mock_pfe, svc):
        """If LLM fails, default to not_task (safe fallback)."""
        mock_pfe.side_effect = RuntimeError("No API key")
        result = svc._classify_message("Do something complex with the data")
        assert result == "not_task"

    def test_auto_create_task_rejects_not_task(self, svc):
        """_auto_create_task must raise ValueError if classification is not_task."""
        with pytest.raises(ValueError, match="not a task-creating classification"):
            svc._auto_create_task(
                "prime", {"name": "Prime"}, "hey how are you",
                classification="not_task",
            )

    def test_auto_create_task_rejects_unknown_classification(self, svc):
        """_auto_create_task must reject any unknown classification value."""
        with pytest.raises(ValueError, match="not a task-creating classification"):
            svc._auto_create_task(
                "prime", {"name": "Prime"}, "something",
                classification="maybe_task",
            )

    def test_auto_create_task_requires_classification_kwarg(self, svc):
        """_auto_create_task cannot be called without the classification parameter."""
        with pytest.raises(TypeError):
            svc._auto_create_task("prime", {"name": "Prime"}, "do stuff")

    def test_route_not_task_creates_no_task(self, db, project_svc):
        """'not_task' messages should NOT create a task on the board."""
        mock_bridge = MagicMock()
        mock_bridge.handle_turn.return_value = {"reply": "Hey there!"}
        svc = DashboardService(db=db, bridge=mock_bridge, sisters=None)
        svc.ensure_mc_project(project_svc)
        svc.load_beings_from_configs()

        svc.route_to_being("sai-memory", "Hi", sender="user")
        time.sleep(0.5)

        tasks = svc.list_tasks(project_svc)
        greeting_tasks = [t for t in tasks if "Hi" in t.get("title", "")]
        assert len(greeting_tasks) == 0, f"Greeting should not create task, got: {[t['title'] for t in tasks]}"

    @patch("bomba_sr.llm.providers.provider_from_env")
    def test_route_light_task_creates_task(self, mock_pfe, db, project_svc):
        """'light_task' messages should create a task that auto-completes."""
        mock_provider = MagicMock()
        mock_classify_resp = MagicMock()
        mock_classify_resp.text = '{"classification": "light_task"}'
        mock_provider.generate.return_value = mock_classify_resp
        mock_pfe.return_value = mock_provider

        mock_bridge = MagicMock()
        mock_bridge.handle_turn.return_value = {"reply": "Found 3 results"}
        svc = DashboardService(db=db, bridge=mock_bridge, sisters=None)
        svc.ensure_mc_project(project_svc)
        svc.load_beings_from_configs()

        svc.route_to_being("sai-memory", "Search Pinecone for zone action content", sender="user")
        time.sleep(0.5)

        tasks = svc.list_tasks(project_svc)
        search_tasks = [t for t in tasks if "Search Pinecone" in t.get("title", "")]
        assert len(search_tasks) == 1
        assert search_tasks[0]["status"] == "done"
        # light_task should have no steps
        assert len(search_tasks[0].get("steps", [])) == 0

    @patch("bomba_sr.llm.providers.provider_from_env")
    def test_route_full_task_creates_task_with_steps(self, mock_pfe, db, project_svc):
        """'full_task' messages should create a task with sub-steps."""
        mock_provider = MagicMock()
        # First call: classification
        # Second call: step generation
        classify_resp = MagicMock()
        classify_resp.text = '{"classification": "full_task"}'
        steps_resp = MagicMock()
        steps_resp.text = '{"steps": ["Scan all contacts", "Check phone fields", "Flag missing entries"]}'
        mock_provider.generate.side_effect = [classify_resp, steps_resp]
        mock_pfe.return_value = mock_provider

        mock_bridge = MagicMock()
        mock_bridge.handle_turn.return_value = {"reply": "Audit complete. Found 5 missing."}
        svc = DashboardService(db=db, bridge=mock_bridge, sisters=None)
        svc.ensure_mc_project(project_svc)
        svc.load_beings_from_configs()

        svc.route_to_being("sai-memory", "Audit all contacts and flag missing phone numbers", sender="user")
        time.sleep(0.5)

        tasks = svc.list_tasks(project_svc)
        audit_tasks = [t for t in tasks if "Audit all contacts" in t.get("title", "")]
        assert len(audit_tasks) == 1
        task = audit_tasks[0]
        assert task["status"] == "done"
        # Should have steps, all completed
        steps = task.get("steps", [])
        assert len(steps) == 3
        assert all(s["status"] == "done" for s in steps)

    @patch.object(DashboardService, "_classify_message", return_value="light_task")
    def test_route_auto_creates_task(self, _mock_cls, db, project_svc):
        """Messaging a being should auto-create a task that transitions through statuses."""
        mock_bridge = MagicMock()
        mock_bridge.handle_turn.return_value = {"reply": "Done!"}
        svc = DashboardService(db=db, bridge=mock_bridge, sisters=None)
        svc.ensure_mc_project(project_svc)
        svc.load_beings_from_configs()

        # Subscribe to SSE to capture events
        cid = svc.subscribe_sse()

        svc.route_to_being("sai-memory", "Summarize the weekly report", sender="user")
        time.sleep(0.5)

        # Task should have been auto-created and finished
        tasks = svc.list_tasks(project_svc)
        chat_tasks = [t for t in tasks if "Summarize the weekly report" in t.get("title", "")]
        assert len(chat_tasks) >= 1, f"Expected auto-created task, got: {[t['title'] for t in tasks]}"

        task = chat_tasks[0]
        assert task["status"] == "done", f"Expected done, got {task['status']}"
        assert "sai-memory" in task.get("assignees", [])

        # SSE events should have been emitted for task creation and status changes
        events = []
        while True:
            evt = svc.poll_sse(cid, timeout=0.1)
            if evt is None:
                break
            events.append(evt)
        svc.unsubscribe_sse(cid)

        task_events = [e for e in events if e["event"] == "task_update"]
        assert len(task_events) >= 2, f"Expected >=2 task events, got {len(task_events)}"

    @patch.object(DashboardService, "_classify_message", return_value="light_task")
    def test_route_error_reverts_task(self, _mock_cls, db, project_svc):
        """If bridge.handle_turn raises, task should revert to backlog."""
        mock_bridge = MagicMock()
        mock_bridge.handle_turn.side_effect = RuntimeError("LLM failed")
        svc = DashboardService(db=db, bridge=mock_bridge, sisters=None)
        svc.ensure_mc_project(project_svc)
        svc.load_beings_from_configs()

        svc.route_to_being("sai-memory", "Fail this task", sender="user")
        time.sleep(0.5)

        tasks = svc.list_tasks(project_svc)
        chat_tasks = [t for t in tasks if "Fail this task" in t.get("title", "")]
        assert len(chat_tasks) >= 1
        assert chat_tasks[0]["status"] == "backlog"


# ── Task Steps ───────────────────────────────────────────────

class TestTaskSteps:
    """Test sub-step CRUD on the task board."""

    def test_create_steps(self, db, project_svc):
        svc = DashboardService(db=db, bridge=None, sisters=None)
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Test task", status="backlog")
        tid = task["id"]

        steps = svc.create_task_steps(tid, ["Step 1", "Step 2", "Step 3"])
        assert len(steps) == 3
        assert steps[0]["label"] == "Step 1"
        assert steps[0]["status"] == "pending"
        assert steps[1]["step_number"] == 1

    def test_get_steps(self, db, project_svc):
        svc = DashboardService(db=db, bridge=None, sisters=None)
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Test", status="backlog")
        svc.create_task_steps(task["id"], ["A", "B"])

        fetched = svc.get_task_steps(task["id"])
        assert len(fetched) == 2
        assert fetched[0]["label"] == "A"
        assert fetched[1]["label"] == "B"

    def test_update_step_status(self, db, project_svc):
        svc = DashboardService(db=db, bridge=None, sisters=None)
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Test", status="backlog")
        steps = svc.create_task_steps(task["id"], ["Do thing"])

        updated = svc.update_task_step(steps[0]["id"], "done")
        assert updated["status"] == "done"

    def test_advance_task_step(self, db, project_svc):
        svc = DashboardService(db=db, bridge=None, sisters=None)
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="Multi", status="in_progress")
        steps = svc.create_task_steps(task["id"], ["One", "Two", "Three"])

        # Start first step
        svc.update_task_step(steps[0]["id"], "in_progress")

        # Advance: should complete step 0, start step 1
        completed = svc.advance_task_step(task["id"])
        assert completed is not None
        assert completed["label"] == "One"

        refreshed = svc.get_task_steps(task["id"])
        assert refreshed[0]["status"] == "done"
        assert refreshed[1]["status"] == "in_progress"
        assert refreshed[2]["status"] == "pending"

    def test_steps_in_normalized_task(self, db, project_svc):
        svc = DashboardService(db=db, bridge=None, sisters=None)
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="With steps", status="backlog")
        svc.create_task_steps(task["id"], ["X", "Y"])

        full = svc.get_task(project_svc, task["id"])
        assert "steps" in full
        assert len(full["steps"]) == 2

    def test_steps_sse_events(self, db, project_svc):
        svc = DashboardService(db=db, bridge=None, sisters=None)
        svc.ensure_mc_project(project_svc)
        task = svc.create_task(project_svc, title="SSE steps", status="backlog")

        cid = svc.subscribe_sse()
        svc.create_task_steps(task["id"], ["Alpha", "Beta"])

        events = []
        while True:
            evt = svc.poll_sse(cid, timeout=0.2)
            if evt is None:
                break
            events.append(evt)
        svc.unsubscribe_sse(cid)

        step_events = [e for e in events if e["event"] == "task_steps_update"]
        assert len(step_events) >= 1

    def test_clean_casual_tasks(self, db, project_svc):
        """clean_casual_tasks should remove auto-created greeting tasks."""
        svc = DashboardService(db=db, bridge=None, sisters=None)
        svc.ensure_mc_project(project_svc)
        svc.load_beings_from_configs()

        # Create a casual task and a real task
        svc.create_task(
            project_svc, title="Hi", description="Auto-created from chat message to SAI Memory",
            status="done", assignees=["sai-memory"],
        )
        svc.create_task(
            project_svc, title="Audit contacts", description="Auto-created from chat message to SAI Recovery",
            status="done", assignees=["sai-recovery"],
        )
        svc.create_task(
            project_svc, title="Manual task", description="User-created",
            status="backlog",
        )

        deleted = svc.clean_casual_tasks(project_svc)
        assert deleted == 1  # Only "Hi" should be deleted

        remaining = svc.list_tasks(project_svc)
        titles = [t["title"] for t in remaining]
        assert "Hi" not in titles
        assert "Audit contacts" in titles
        assert "Manual task" in titles
