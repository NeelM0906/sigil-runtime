from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from bomba_sr.commands.parser import ParsedCommand
from bomba_sr.governance.policy_pipeline import ResolvedPolicy
from bomba_sr.skills.loader import SkillLoader
from bomba_sr.tools.base import ToolContext, ToolExecutor


@dataclass(frozen=True)
class CommandResult:
    handled: bool
    bypass_llm: bool
    output: dict[str, Any] | None
    skill_id: str | None
    skill_body: str | None
    error: str | None


@dataclass(frozen=True)
class CommandContext:
    tool_context: ToolContext
    policy: ResolvedPolicy
    profile_lookup: Callable[[], dict[str, Any]] | None = None


class CommandRouter:
    def __init__(self, skill_loader: SkillLoader, tool_executor: ToolExecutor):
        self.skill_loader = skill_loader
        self.tool_executor = tool_executor
        self._command_map: dict[str, str] = {}
        self.rebuild_command_map(self.skill_loader.snapshot())

    def rebuild_command_map(self, skills: dict[str, Any]) -> None:
        mapping: dict[str, str] = {}
        for descriptor in skills.values():
            if not descriptor.user_invocable:
                continue
            mapping[descriptor.name.lower()] = descriptor.skill_id
        self._command_map = mapping

    def route(self, parsed: ParsedCommand, context: CommandContext) -> CommandResult:
        command = parsed.command_name.lower()
        if command == "help":
            return CommandResult(
                handled=True,
                bypass_llm=True,
                output={"commands": self.available_commands()},
                skill_id=None,
                skill_body=None,
                error=None,
            )
        if command == "skills":
            skills = self.skill_loader.snapshot()
            return CommandResult(
                handled=True,
                bypass_llm=True,
                output={
                    "skills": [
                        {
                            "skill_id": s.skill_id,
                            "name": s.name,
                            "description": s.description,
                            "source": s.source,
                            "source_path": s.source_path,
                            "user_invocable": s.user_invocable,
                            "disable_model_invocation": s.disable_model_invocation,
                        }
                        for s in sorted(skills.values(), key=lambda x: x.skill_id)
                    ]
                },
                skill_id=None,
                skill_body=None,
                error=None,
            )
        if command == "approvals":
            result = self.tool_executor.execute(
                tool_name="list_approvals",
                arguments={"type": "all"},
                context=context.tool_context,
                policy=context.policy,
            )
            return CommandResult(
                handled=True,
                bypass_llm=True,
                output=result.as_dict(),
                skill_id=None,
                skill_body=None,
                error=None,
            )
        if command == "profile" and context.profile_lookup is not None:
            return CommandResult(
                handled=True,
                bypass_llm=True,
                output={"profile": context.profile_lookup()},
                skill_id=None,
                skill_body=None,
                error=None,
            )

        skill_id = self._command_map.get(command)
        if skill_id is None:
            return CommandResult(
                handled=False,
                bypass_llm=False,
                output=None,
                skill_id=None,
                skill_body=None,
                error=f"unknown command: /{command}",
            )

        skills = self.skill_loader.snapshot()
        descriptor = skills.get(skill_id)
        if descriptor is None:
            return CommandResult(
                handled=True,
                bypass_llm=True,
                output={"error": f"skill_not_found:{skill_id}"},
                skill_id=skill_id,
                skill_body=None,
                error=None,
            )

        if descriptor.command_dispatch == "tool" and descriptor.command_tool:
            result = self.tool_executor.execute(
                tool_name=descriptor.command_tool,
                arguments={
                    "command": parsed.raw_args,
                    "command_name": parsed.command_name,
                    "skill_name": descriptor.name,
                },
                context=context.tool_context,
                policy=context.policy,
            )
            return CommandResult(
                handled=True,
                bypass_llm=True,
                output=result.as_dict(),
                skill_id=skill_id,
                skill_body=None,
                error=None,
            )

        body = self.skill_loader.load_skill_body(skill_id)
        return CommandResult(
            handled=True,
            bypass_llm=False,
            output={"skill_id": skill_id},
            skill_id=skill_id,
            skill_body=body,
            error=None,
        )

    def available_commands(self) -> list[dict[str, str]]:
        builtins = [
            {"command": "/help", "description": "Show available commands"},
            {"command": "/skills", "description": "List loaded skills"},
            {"command": "/approvals", "description": "List pending approvals"},
            {"command": "/profile", "description": "Show user profile"},
        ]
        skill_commands = [
            {"command": f"/{name}", "description": f"Invoke skill {name}"}
            for name in sorted(self._command_map.keys())
        ]
        return builtins + skill_commands
