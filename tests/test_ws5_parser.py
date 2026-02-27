from __future__ import annotations

import unittest

from bomba_sr.commands.parser import CommandParser


class CommandParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = CommandParser()

    def test_parse_command_with_named_and_positional_args(self) -> None:
        parsed = self.parser.parse("/summarize target=src level=high quick")
        assert parsed is not None
        self.assertTrue(parsed.is_command)
        self.assertEqual(parsed.command_name, "summarize")
        self.assertEqual(parsed.named_args["target"], "src")
        self.assertEqual(parsed.named_args["level"], "high")
        self.assertEqual(parsed.positional_args, ["quick"])

    def test_non_command_returns_none(self) -> None:
        self.assertFalse(self.parser.is_command("hello"))
        self.assertIsNone(self.parser.parse("hello"))


if __name__ == "__main__":
    unittest.main()
