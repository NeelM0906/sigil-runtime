#!/usr/bin/env python3
"""Scrub secrets and machine-local paths from the portable SAI bundle."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".py",
    ".sh",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
    ".toml",
    ".conf",
    ".ini",
    ".env",
    ".sql",
    ".csv",
    ".html",
}


REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'("apiKey"\s*:\s*")([^"]+)(")'), r'\1[REDACTED]\3'),
    (re.compile(r'("token"\s*:\s*")([^"]+)(")'), r'\1[REDACTED]\3'),
    (re.compile(r'("client_secret"\s*:\s*")([^"]+)(")'), r'\1[REDACTED]\3'),
    (re.compile(r'("clientSecret"\s*:\s*")([^"]+)(")'), r'\1[REDACTED]\3'),
    (re.compile(r"(Authorization:\s*Bearer\s+)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(SUPABASE_SERVICE_KEY=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(SUPABASE_ANON_KEY=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(SUPABASE_KEY=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(OPENAI_API_KEY=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(ANTHROPIC_API_KEY=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(OPENROUTER_API_KEY=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(PINECONE_API_KEY(?:_STRATA)?=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(ELEVENLABS_API_KEY=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(DEEPGRAM_API_KEY=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(BLAND_API_KEY=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(FAL_KEY(?:_NEW)?=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(FATHOM_API_KEY(?:_SAI)?=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(FATHOM_WEBHOOK_SECRET=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(VERCEL_TOKEN=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(NGROK_AUTHTOKEN=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(PERPLEXITY_API_KEY=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(ZOOM_CLIENT_SECRET=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(ZOOM_CLIENT_ID=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(ZOOM_ACCOUNT_ID=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(TWILIO_API_KEY_SID=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(TWILIO_API_KEY_SECRET=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(TWILIO_ACCOUNT_SID=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(DATABASE_URL=)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(SUPABASE_URL=)https://[^\s\"']+"), r"\1https://[REDACTED].supabase.co"),
    (re.compile(r"sb_secret_[A-Za-z0-9._-]+"), "[REDACTED]"),
    (re.compile(r"sb_publishable_[A-Za-z0-9._-]+"), "[REDACTED]"),
    (re.compile(r"sk-or-v1-[A-Za-z0-9]+"), "[REDACTED]"),
    (re.compile(r"sk-proj-[A-Za-z0-9_\-]+"), "[REDACTED]"),
    (re.compile(r"pcsk_[A-Za-z0-9._-]+"), "[REDACTED]"),
    (re.compile(r"pplx-[A-Za-z0-9._-]+"), "[REDACTED]"),
    (re.compile(r"sk-ant-[A-Za-z0-9._-]+"), "[REDACTED]"),
    (re.compile(r"\bvcp_[A-Za-z0-9]+\b"), "[REDACTED]"),
    (re.compile(r"\bwhsec_[A-Za-z0-9+/=]+\b"), "[REDACTED]"),
    (re.compile(r"\bMTQ[0-9A-Za-z._-]{20,}\b"), "[REDACTED]"),
    (re.compile(r"postgresql://[^ \n\"']+"), "postgresql://[REDACTED]"),
    (re.compile(r"/Users/samantha/\.openclaw"), "~/.openclaw"),
    (re.compile(r"/Users/samantha/Projects/colosseum"), "./workspaces/prime/Projects/colosseum"),
    (re.compile(r"/Users/samantha/Projects/prove-ahead"), "./workspaces/prime/Projects/prove-ahead"),
    (re.compile(r"/Users/samantha/Projects/webinar-machine"), "./workspaces/prime/Projects/webinar-machine"),
    (re.compile(r"/Users/samantha/Projects/youtube-transcripts"), "./workspaces/prime/Projects/youtube-transcripts"),
    (re.compile(r"/Users/samantha/recovery-colosseum"), "./workspaces/recovery/Projects/recovery-colosseum"),
    (re.compile(r"/Users/samantha"), "~"),
]


def should_process(path: Path) -> bool:
    if path.name == ".DS_Store":
        return False
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return ".jsonl." in path.name


def rewrite_file(path: Path) -> bool:
    try:
        original = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    updated = original
    for pattern, replacement in REPLACEMENTS:
        updated = pattern.sub(replacement, updated)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="+", help="Directories or files to sanitize")
    args = parser.parse_args()

    changed = 0
    for root_arg in args.roots:
        root = Path(root_arg)
        paths = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for path in paths:
            if not should_process(path):
                continue
            if rewrite_file(path):
                changed += 1
                print(path)
    print(f"sanitized_files={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
