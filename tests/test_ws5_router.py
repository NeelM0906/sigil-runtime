from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bomba_sr.commands.parser import CommandParser
from bomba_sr.commands.router import CommandContext, CommandRouter
from bomba_sr.governance.policy_pipeline import PolicyPipeline, ToolPolicyContext
from bomba_sr.governance.tool_policy import ToolGovernanceService
from bomba_sr.skills.eligibility import EligibilityEngine
from bomba_sr.skills.loader import SkillLoader
from bomba_sr.skills.skillmd_parser import SkillMdParser
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.tools.base import ToolContext, ToolDefinition, ToolExecutor


def _guard(root: Path):
    def guard(path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        root_real = root.resolve()
        if candidate != root_real and root_real not in candidate.parents:
            raise ValueError("path escapes workspace")
        return candidate

    return guard


class CommandRouterTests(unittest.TestCase):
    def test_route_builtin_and_skill_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill_root = root / "skills"
            (skill_root / "summarize").mkdir(parents=True, exist_ok=True)
            (skill_root / "summarize" / "SKILL.md").write_text(
                "\n".join(
                    [
                        "---",
                        "name: summarize",
                        "description: Summarize workspace",
                        "user-invocable: true",
                        "---",
                        "Summarize the current project state.",
                    ]
                ),
                encoding="utf-8",
            )
            (skill_root / "ops-only").mkdir(parents=True, exist_ok=True)
            (skill_root / "ops-only" / "SKILL.md").write_text(
                "\n".join(
                    [
                        "---",
                        "name: ops-only",
                        "description: Hidden skill for explicit ops dispatch",
                        "user-invocable: true",
                        "disable-model-invocation: true",
                        "---",
                        "This skill should never invoke the model.",
                    ]
                ),
                encoding="utf-8",
            )

            loader = SkillLoader(
                skill_roots=[skill_root],
                eligibility=EligibilityEngine(),
                parser=SkillMdParser(),
            )
            loader.scan()

            db = RuntimeDB(root / "runtime.db")
            governance = ToolGovernanceService(db)
            governance.upsert_default_policy("tenant-router")
            pipeline = PolicyPipeline(governance)
            executor = ToolExecutor(governance=governance, pipeline=pipeline)
            executor.register(
                ToolDefinition(
                    name="list_approvals",
                    description="List approvals",
                    parameters={"type": "object", "properties": {}, "additionalProperties": True},
                    risk_level="low",
                    action_type="read",
                    execute=lambda _args, _ctx: {"approvals": []},
                )
            )
            router = CommandRouter(skill_loader=loader, tool_executor=executor)
            router.rebuild_command_map(loader.snapshot())
            parser = CommandParser()

            policy = pipeline.resolve(
                ToolPolicyContext(tenant_id="tenant-router"),
                available_tools=executor.known_tool_names(),
            )
            ctx = CommandContext(
                tool_context=ToolContext(
                    tenant_id="tenant-router",
                    session_id="s1",
                    turn_id="t1",
                    user_id="u1",
                    workspace_root=root,
                    db=db,
                    guard_path=_guard(root),
                ),
                policy=policy,
                profile_lookup=lambda: {"persona_summary": "test profile"},
            )

            help_result = router.route(parser.parse("/help"), ctx)  # type: ignore[arg-type]
            self.assertTrue(help_result.handled)
            self.assertTrue(help_result.bypass_llm)
            self.assertIn("commands", help_result.output or {})

            approvals_result = router.route(parser.parse("/approvals"), ctx)  # type: ignore[arg-type]
            self.assertTrue(approvals_result.handled)
            self.assertTrue(approvals_result.bypass_llm)
            self.assertEqual(approvals_result.output["status"], "executed")  # type: ignore[index]

            skill_result = router.route(parser.parse("/summarize"), ctx)  # type: ignore[arg-type]
            self.assertTrue(skill_result.handled)
            self.assertFalse(skill_result.bypass_llm)
            self.assertEqual(skill_result.skill_id, "summarize")
            self.assertIn("Summarize the current project state.", skill_result.skill_body or "")

            disabled_result = router.route(parser.parse("/ops-only"), ctx)  # type: ignore[arg-type]
            self.assertTrue(disabled_result.handled)
            self.assertTrue(disabled_result.bypass_llm)
            self.assertEqual((disabled_result.output or {}).get("error"), "model_invocation_disabled")

            unknown_result = router.route(parser.parse("/does-not-exist"), ctx)  # type: ignore[arg-type]
            self.assertFalse(unknown_result.handled)
            self.assertIn("unknown command", unknown_result.error or "")


if __name__ == "__main__":
    unittest.main()
