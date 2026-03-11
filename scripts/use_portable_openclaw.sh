#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORTABLE_HOME="$REPO_ROOT/.portable-home"
PORTABLE_OPENCLAW="$REPO_ROOT/portable-openclaw"

python3 "$REPO_ROOT/scripts/bootstrap_portable_root.py" >/dev/null

export HOME="$PORTABLE_HOME"
export OPENCLAW_HOME="$PORTABLE_OPENCLAW"
export OPENCLAW_ROOT="$PORTABLE_OPENCLAW"
export OPENCLAW_ENV_FILE="$REPO_ROOT/.env"
export SIGIL_REPO_ROOT="$REPO_ROOT"
export SIGIL_WORKSPACES_ROOT="$REPO_ROOT/workspaces"

echo "Portable OpenClaw environment active:"
echo "  HOME=$HOME"
echo "  OPENCLAW_HOME=$OPENCLAW_HOME"
echo "  OPENCLAW_ENV_FILE=$OPENCLAW_ENV_FILE"
