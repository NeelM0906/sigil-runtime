#!/usr/bin/env python3
"""
Ask Kai (Guide 2) — Send a message to Kai's webhook and wait for response.

Kai reads 100+ chunks before responding. He can take 1-5 minutes.
Default timeout is 5 minutes. Don't rush him.

Usage:
  python3 tools/ask_kai.py "Grade this opening on the creature scale"
  python3 tools/ask_kai.py --file reports/some-output.md "Grade this"
  python3 tools/ask_kai.py --timeout 600 "Deep analysis request"
"""

import argparse
import os
import sys
import requests
from pathlib import Path

# Kai's webhook (Guide 2 — the real one, use sparingly)
KAI_WEBHOOK = "https://n8n.unblindedteam.com/webhook/7496c229-e65c-440d-972f-2e16dae0816c"

# Kai's practice webhook (Guide 2 — for training/testing)
KAI_PRACTICE_WEBHOOK = "https://n8n.unblindedteam.com/webhook/dfffccb8-8b89-4e82-b355-8a972fd64b9f"


def ask_kai(message: str, timeout: int = 300, real: bool = False) -> str:
    """Send message to Kai webhook and return response."""
    webhook = KAI_WEBHOOK if real else KAI_PRACTICE_WEBHOOK
    
    print(f"📤 Sending to Kai ({'REAL' if real else 'practice'})...")
    print(f"⏳ Timeout: {timeout}s ({timeout//60}m {timeout%60}s)")
    print(f"   (Kai reads 100+ chunks — be patient)\n")
    
    try:
        resp = requests.post(
            webhook,
            json={"message": message},
            timeout=timeout,
        )
        
        if resp.status_code == 200:
            # Try to parse JSON response
            try:
                data = resp.json()
                if isinstance(data, dict):
                    return data.get("output", data.get("message", data.get("response", str(data))))
                return str(data)
            except Exception:
                return resp.text
        else:
            return f"ERROR: HTTP {resp.status_code} — {resp.text[:500]}"
    
    except requests.exceptions.ReadTimeout:
        return f"TIMEOUT after {timeout}s — Kai is still thinking. Try again with --timeout {timeout * 2}"
    except Exception as e:
        return f"ERROR: {e}"


def main():
    parser = argparse.ArgumentParser(description="Ask Kai (Guide 2) via n8n webhook")
    parser.add_argument("message", help="Message to send to Kai")
    parser.add_argument("--file", "-f", help="Attach a file's content to the message")
    parser.add_argument("--timeout", "-t", type=int, default=300, help="Timeout in seconds (default: 300 = 5 min)")
    parser.add_argument("--real", action="store_true", help="Use the REAL Kai webhook (use sparingly)")
    parser.add_argument("--output", "-o", help="Save response to file")
    args = parser.parse_args()

    message = args.message
    
    if args.file:
        filepath = Path(args.file)
        if filepath.exists():
            file_content = filepath.read_text()
            message = f"{message}\n\n--- ATTACHED FILE: {filepath.name} ---\n{file_content}"
        else:
            print(f"File not found: {args.file}")
            sys.exit(1)

    response = ask_kai(message, timeout=args.timeout, real=args.real)
    
    print("=" * 60)
    print("KAI'S RESPONSE:")
    print("=" * 60)
    print(response)
    
    if args.output:
        Path(args.output).write_text(response)
        print(f"\n💾 Saved to {args.output}")


if __name__ == "__main__":
    main()
