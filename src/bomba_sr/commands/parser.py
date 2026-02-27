from __future__ import annotations

import re
import shlex
from dataclasses import dataclass


_COMMAND_RE = re.compile(r"^/[a-zA-Z0-9_-]+(?:\s+.*)?$")


@dataclass(frozen=True)
class ParsedCommand:
    command_name: str
    raw_args: str
    named_args: dict[str, str]
    positional_args: list[str]
    is_command: bool


class CommandParser:
    def is_command(self, text: str) -> bool:
        return bool(_COMMAND_RE.match(text.strip()))

    def parse(self, text: str) -> ParsedCommand | None:
        if not self.is_command(text):
            return None
        raw = text.strip()
        head, _, tail = raw.partition(" ")
        command = head[1:].strip().lower()
        raw_args = tail.strip()

        named: dict[str, str] = {}
        positional: list[str] = []
        if raw_args:
            tokens = shlex.split(raw_args)
            for token in tokens:
                if "=" in token:
                    key, value = token.split("=", 1)
                    if key.strip():
                        named[key.strip()] = value.strip()
                    continue
                positional.append(token)
        return ParsedCommand(
            command_name=command,
            raw_args=raw_args,
            named_args=named,
            positional_args=positional,
            is_command=True,
        )
