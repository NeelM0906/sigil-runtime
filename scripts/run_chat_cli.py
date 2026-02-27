#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import uuid
from dataclasses import dataclass
from pathlib import Path

from bomba_sr.context.policy import TurnProfile
from bomba_sr.runtime.bridge import RuntimeBridge, TurnRequest


SIGIL_ASCII = r"""
   _____ _____ _____ _____ _
  / ____|_   _/ ____|_   _| |
 | (___   | || |  __  | | | |
  \___ \  | || | |_ | | | | |
  ____) |_| || |__| |_| |_| |____
 |_____/|_____\_____|_____|______|
"""


@dataclass
class SessionState:
    tenant_id: str
    session_id: str
    user_id: str
    workspace: str
    profile: str
    active_project_id: str | None = None
    active_task_id: str | None = None


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw.startswith("export "):
            raw = raw[len("export ") :].strip()
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and (key not in os.environ or not os.environ.get(key)):
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SIGIL interactive CLI")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--workspace", default=None)
    parser.add_argument(
        "--profile",
        default=None,
        choices=[x.value for x in TurnProfile],
    )
    parser.add_argument("--state-file", default=".runtime/sigil-cli-state.json")
    parser.add_argument("--new-session", action="store_true")
    return parser.parse_args()


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(path: Path, state: SessionState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tenant_id": state.tenant_id,
        "session_id": state.session_id,
        "user_id": state.user_id,
        "workspace": state.workspace,
        "profile": state.profile,
        "active_project_id": state.active_project_id,
        "active_task_id": state.active_task_id,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _print_welcome(state: SessionState) -> None:
    print(SIGIL_ASCII)
    print("SIGIL interactive runtime")
    print(f"tenant={state.tenant_id} session={state.session_id} user={state.user_id}")
    print(f"workspace={state.workspace}")
    print("Type /help for commands. Type /exit to quit.")
    print("Try: hi | who are you | what were we working on | help me with this")


def _print_help() -> None:
    print("Commands:")
    print("  /help                    Show this help")
    print("  /exit                    Exit SIGIL")
    print("  /session                 Show current session context")
    print("  /reset-session           Start a fresh session id")
    print("  /use-project <project>   Set active project context")
    print("  /use-task <task>         Set active task context")
    print("  /clear-context           Clear active project/task")
    print("  /approvals               Show pending approvals (tool + learning)")
    print("  /approve <id>            Approve by id (tool:<id> or learning:<id>)")
    print("  /reject <id>             Reject by id (tool:<id> or learning:<id>)")
    print("  /approve-learning <id>   Approve a pending learning update")
    print("  /reject-learning <id>    Reject a pending learning update")
    print("  /approve-learning-all    Approve all pending learning updates")
    print("  /reject-learning-all     Reject all pending learning updates")
    print("  /tool-approvals          Show pending governance tool approvals")
    print("  /profile                 Show learned user profile")
    print("  /signals                 Show pending profile signals")
    print("  /skills                  List skills")
    print("  /create-skill <name> <description>  Create a workspace skill without JSON")
    print("  /update-skill <skill_id> <description>  Update skill description")
    print("  /register-skill <file> [status]  Register a skill manifest JSON")
    print("  /catalog [source] [limit]  List shared catalog skills (clawhub|anthropic_skills)")
    print("  /skill-trust [source] [mode]  Get/set source trust override (read_only|allow_with_approval|blocked)")
    print("  /install-skill <source> <skill_id> [reason]  Create approval-gated install request")
    print("  /install-requests [status]  List skill install requests")
    print("  /apply-install <request_id>  Apply an approved install request")
    print("  /skills-diagnostics       Show permissive parser warnings")
    print("  /skills-telemetry [limit] Show skill ecosystem telemetry")
    print("  /run-skill <id> [json]   Execute skill with optional JSON input")
    print("  /projects                List projects")
    print("  /tasks [project_id]      List tasks")


def _handle_command(line: str, state: SessionState, bridge: RuntimeBridge, state_file: Path) -> bool:
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        print(f"invalid command: {exc}")
        return True

    if not parts:
        return True

    cmd = parts[0].lower()

    if cmd == "/help":
        _print_help()
        return True

    if cmd in {"/exit", "/quit"}:
        return False

    if cmd == "/session":
        print(json.dumps(state.__dict__, indent=2))
        return True

    if cmd == "/reset-session":
        state.session_id = str(uuid.uuid4())
        _save_state(state_file, state)
        print(f"new session: {state.session_id}")
        return True

    if cmd == "/use-project":
        if len(parts) < 2:
            print("usage: /use-project <project_id>")
            return True
        state.active_project_id = parts[1]
        _save_state(state_file, state)
        print(f"active project set: {state.active_project_id}")
        return True

    if cmd == "/use-task":
        if len(parts) < 2:
            print("usage: /use-task <task_id>")
            return True
        state.active_task_id = parts[1]
        _save_state(state_file, state)
        print(f"active task set: {state.active_task_id}")
        return True

    if cmd == "/clear-context":
        state.active_project_id = None
        state.active_task_id = None
        _save_state(state_file, state)
        print("cleared active project/task context")
        return True

    if cmd == "/approvals":
        learning = bridge.list_pending_learning_approvals(
            state.tenant_id,
            state.user_id,
            workspace_root=state.workspace,
        )
        tools = bridge.list_pending_approvals(state.tenant_id, workspace_root=state.workspace)
        combined = [
            {"id": f"learning:{item['update_id']}", "kind": "learning", **item}
            for item in learning
        ] + [
            {"id": f"tool:{item['approval_id']}", "kind": "tool", **item}
            for item in tools
        ]
        if not combined:
            print("no pending approvals")
        else:
            print(json.dumps(combined, indent=2))
        return True

    if cmd in {"/approve", "/reject"}:
        if len(parts) < 2:
            print(f"usage: {cmd} <approval_id>")
            return True
        approval_id = parts[1]
        approved = cmd == "/approve"
        if approval_id.startswith("tool:"):
            payload = bridge.decide_approval(
                tenant_id=state.tenant_id,
                approval_id=approval_id.split(":", 1)[1],
                approved=approved,
                decided_by="cli-user",
                workspace_root=state.workspace,
            )
            print(json.dumps(payload, indent=2))
            return True
        if approval_id.startswith("learning:"):
            payload = bridge.approve_learning(
                tenant_id=state.tenant_id,
                user_id=state.user_id,
                update_id=approval_id.split(":", 1)[1],
                approved=approved,
                workspace_root=state.workspace,
            )
            print(json.dumps(payload, indent=2))
            return True
        # Backward compatibility: assume learning approval id.
        payload = bridge.approve_learning(
            tenant_id=state.tenant_id,
            user_id=state.user_id,
            update_id=approval_id,
            approved=approved,
            workspace_root=state.workspace,
        )
        print(json.dumps(payload, indent=2))
        return True

    if cmd in {"/approve-learning", "/reject-learning"}:
        if len(parts) < 2:
            print(f"usage: {cmd} <update_id>")
            return True
        update_id = parts[1]
        approved = cmd == "/approve-learning"
        result = bridge.approve_learning(
            tenant_id=state.tenant_id,
            user_id=state.user_id,
            update_id=update_id,
            approved=approved,
            workspace_root=state.workspace,
        )
        print(json.dumps(result, indent=2))
        return True

    if cmd in {"/approve-learning-all", "/reject-learning-all"}:
        approved = cmd == "/approve-learning-all"
        approvals = bridge.list_pending_learning_approvals(
            state.tenant_id,
            state.user_id,
            workspace_root=state.workspace,
        )
        if not approvals:
            print("no pending approvals")
            return True
        outcomes = []
        for item in approvals:
            outcomes.append(
                bridge.approve_learning(
                    tenant_id=state.tenant_id,
                    user_id=state.user_id,
                    update_id=str(item["update_id"]),
                    approved=approved,
                    workspace_root=state.workspace,
                )
            )
        print(json.dumps({"count": len(outcomes), "results": outcomes}, indent=2))
        return True

    if cmd == "/tool-approvals":
        approvals = bridge.list_pending_approvals(state.tenant_id, workspace_root=state.workspace)
        if not approvals:
            print("no pending tool approvals")
        else:
            print(json.dumps(approvals, indent=2))
        return True

    if cmd == "/profile":
        profile = bridge.get_user_profile(state.tenant_id, state.user_id, workspace_root=state.workspace)
        print(json.dumps(profile, indent=2))
        return True

    if cmd == "/signals":
        signals = bridge.list_pending_profile_signals(state.tenant_id, state.user_id, workspace_root=state.workspace)
        if not signals:
            print("no pending profile signals")
        else:
            print(json.dumps(signals, indent=2))
        return True

    if cmd == "/skills":
        skills = bridge.list_skills(state.tenant_id, workspace_root=state.workspace)
        if not skills:
            print("no skills registered")
        else:
            print(json.dumps(skills, indent=2))
        return True

    if cmd == "/catalog":
        source = parts[1] if len(parts) > 1 else None
        limit = int(parts[2]) if len(parts) > 2 else 50
        skills = bridge.list_skill_catalog(
            tenant_id=state.tenant_id,
            workspace_root=state.workspace,
            source=source,
            limit=limit,
        )
        if not skills:
            print("no catalog skills found")
        else:
            print(json.dumps(skills, indent=2))
        return True

    if cmd == "/skill-trust":
        if len(parts) == 1:
            trust = bridge.get_skill_source_trust(state.tenant_id, workspace_root=state.workspace)
            print(json.dumps(trust, indent=2))
            return True
        if len(parts) < 3:
            print("usage: /skill-trust <source> <read_only|allow_with_approval|blocked>")
            return True
        policy = bridge.set_skill_source_trust(
            tenant_id=state.tenant_id,
            source=parts[1],
            trust_mode=parts[2],
            workspace_root=state.workspace,
        )
        print(json.dumps(policy, indent=2))
        return True

    if cmd == "/install-skill":
        if len(parts) < 3:
            print("usage: /install-skill <source> <skill_id> [reason]")
            return True
        reason = " ".join(parts[3:]).strip() if len(parts) > 3 else None
        payload = bridge.create_skill_install_request(
            tenant_id=state.tenant_id,
            user_id=state.user_id,
            source=parts[1],
            skill_id=parts[2],
            session_id=state.session_id,
            turn_id=str(uuid.uuid4()),
            workspace_root=state.workspace,
            reason=reason,
        )
        print(json.dumps(payload, indent=2))
        print("Next: use /approvals then /approve tool:<approval_id>, then /apply-install <request_id>")
        return True

    if cmd == "/install-requests":
        status = parts[1] if len(parts) > 1 else None
        rows = bridge.list_skill_install_requests(
            tenant_id=state.tenant_id,
            workspace_root=state.workspace,
            status=status,
            limit=100,
        )
        if not rows:
            print("no install requests")
        else:
            print(json.dumps(rows, indent=2))
        return True

    if cmd == "/apply-install":
        if len(parts) < 2:
            print("usage: /apply-install <request_id>")
            return True
        result = bridge.execute_skill_install(
            tenant_id=state.tenant_id,
            request_id=parts[1],
            workspace_root=state.workspace,
        )
        print(json.dumps(result, indent=2))
        return True

    if cmd == "/skills-diagnostics":
        print(json.dumps(bridge.skill_diagnostics(state.tenant_id, workspace_root=state.workspace), indent=2))
        return True

    if cmd == "/skills-telemetry":
        limit = int(parts[1]) if len(parts) > 1 else 50
        print(json.dumps(bridge.list_skill_telemetry(state.tenant_id, workspace_root=state.workspace, limit=limit), indent=2))
        return True

    if cmd == "/create-skill":
        if len(parts) < 3:
            print("usage: /create-skill <name> <description>")
            return True
        name = parts[1]
        description = " ".join(parts[2:])
        payload = bridge.invoke_code_tool(
            tenant_id=state.tenant_id,
            tool_name="skill_create",
            arguments={
                "name": name,
                "skill_id": name,
                "description": description,
                "body": f"You are the {name} skill. Execute requests related to: {description}.",
                "user_invocable": True,
            },
            workspace_root=state.workspace,
            session_id=state.session_id,
            turn_id=str(uuid.uuid4()),
            confidence=1.0,
        )
        print(json.dumps(payload, indent=2))
        return True

    if cmd == "/update-skill":
        if len(parts) < 3:
            print("usage: /update-skill <skill_id> <description>")
            return True
        skill_id = parts[1]
        description = " ".join(parts[2:])
        payload = bridge.invoke_code_tool(
            tenant_id=state.tenant_id,
            tool_name="skill_update",
            arguments={
                "skill_id": skill_id,
                "description": description,
            },
            workspace_root=state.workspace,
            session_id=state.session_id,
            turn_id=str(uuid.uuid4()),
            confidence=1.0,
        )
        print(json.dumps(payload, indent=2))
        return True

    if cmd == "/register-skill":
        if len(parts) < 2:
            print("usage: /register-skill <manifest.json> [status]")
            return True
        path = Path(parts[1]).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.exists():
            print(f"manifest file not found: {path}")
            return True
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"invalid JSON manifest: {exc}")
            return True
        status = parts[2] if len(parts) > 2 else "active"
        result = bridge.register_skill(
            tenant_id=state.tenant_id,
            manifest=manifest,
            status=status,
            workspace_root=state.workspace,
        )
        print(json.dumps(result, indent=2))
        return True

    if cmd == "/run-skill":
        if len(parts) < 2:
            print("usage: /run-skill <skill_id> [json_inputs]")
            return True
        skill_id = parts[1]
        payload = {}
        if len(parts) >= 3:
            try:
                payload = json.loads(parts[2])
            except json.JSONDecodeError as exc:
                print(f"invalid json input: {exc}")
                return True
        result = bridge.execute_skill(
            tenant_id=state.tenant_id,
            skill_id=skill_id,
            inputs=payload,
            workspace_root=state.workspace,
            session_id=state.session_id,
            turn_id=str(uuid.uuid4()),
            confidence=1.0,
        )
        print(json.dumps(result, indent=2))
        return True

    if cmd == "/projects":
        projects = bridge.list_projects(state.tenant_id, workspace_root=state.workspace)
        if not projects:
            print("no projects")
        else:
            print(json.dumps(projects, indent=2))
        return True

    if cmd == "/tasks":
        project_id = parts[1] if len(parts) > 1 else state.active_project_id
        tasks = bridge.list_tasks(state.tenant_id, project_id=project_id, workspace_root=state.workspace)
        if not tasks:
            print("no tasks")
        else:
            print(json.dumps(tasks, indent=2))
        return True

    print(f"unknown command: {cmd}. Use /help")
    return True


def main() -> int:
    _load_dotenv(Path(".env"))
    args = parse_args()
    state_file = Path(args.state_file).resolve()
    prev = _load_state(state_file)

    workspace = os.path.abspath(os.path.expanduser(args.workspace or prev.get("workspace") or os.getcwd()))
    if not os.path.exists(workspace):
        raise SystemExit(f"workspace does not exist: {workspace}")

    session_id = args.session_id or prev.get("session_id") or str(uuid.uuid4())
    if args.new_session:
        session_id = str(uuid.uuid4())

    state = SessionState(
        tenant_id=args.tenant_id or prev.get("tenant_id") or "tenant-local",
        session_id=session_id,
        user_id=args.user_id or prev.get("user_id") or "user-local",
        workspace=workspace,
        profile=args.profile or prev.get("profile") or "chat",
        active_project_id=prev.get("active_project_id"),
        active_task_id=prev.get("active_task_id"),
    )
    _save_state(state_file, state)

    bridge = RuntimeBridge()
    _print_welcome(state)

    while True:
        try:
            text = input("you> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nUse /exit to quit.")
            continue

        if not text:
            continue

        if text.startswith("/"):
            keep_running = _handle_command(text, state, bridge, state_file)
            if not keep_running:
                break
            continue

        try:
            result = bridge.handle_turn(
                TurnRequest(
                    tenant_id=state.tenant_id,
                    session_id=state.session_id,
                    user_id=state.user_id,
                    user_message=text,
                    profile=TurnProfile(state.profile),
                    workspace_root=state.workspace,
                    project_id=state.active_project_id,
                    task_id=state.active_task_id,
                )
            )
        except Exception as exc:
            print(f"sigil> error: {exc}")
            continue

        mode = result.get("turn", {}).get("mode")
        if mode:
            print(f"[mode: {mode}]")
        print("sigil>", result.get("assistant", {}).get("text", ""))

        approvals = result.get("approvals", {}) if isinstance(result.get("approvals"), dict) else {}
        pending_learning_approvals = approvals.get("pending_learning_approvals", [])
        pending_tool_approvals = approvals.get("pending_tool_approvals", [])
        if not approvals:
            pending_learning_approvals = result.get("memory", {}).get("pending_approvals", [])
            pending_tool_approvals = []
        pending_signals = result.get("identity", {}).get("pending_signals", [])
        pending_total = len(pending_learning_approvals) + len(pending_tool_approvals)
        if pending_total:
            print(
                f"pending approvals: {pending_total} "
                f"(learning={len(pending_learning_approvals)}, tool={len(pending_tool_approvals)}) "
                "(use /approvals)"
            )
        if pending_signals:
            print(f"pending profile signals: {len(pending_signals)} (use /signals)")

        artifacts = result.get("artifacts", [])
        if artifacts:
            print("artifacts:")
            for artifact in artifacts[:5]:
                print(f"- {artifact.get('type')} {artifact.get('path')}")
        skills_block = result.get("skills", {}) if isinstance(result.get("skills"), dict) else {}
        diagnostics = skills_block.get("parse_diagnostics", {})
        if isinstance(diagnostics, dict):
            warning_count = sum(len(v) for v in diagnostics.values() if isinstance(v, list))
            if warning_count:
                print(f"skill parser warnings: {warning_count} (use /skills-diagnostics)")

        _save_state(state_file, state)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
