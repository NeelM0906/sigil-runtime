#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ROOT="${1:-${BOMBA_OPENCLAW_SOURCE_ROOT:-}}"

if [[ -z "$SOURCE_ROOT" ]]; then
  echo "usage: scripts/import_portable_assets.sh /path/to/source-openclaw-root" >&2
  echo "or set BOMBA_OPENCLAW_SOURCE_ROOT before running it" >&2
  exit 1
fi

if [[ ! -d "$SOURCE_ROOT" ]]; then
  echo "source root not found: $SOURCE_ROOT" >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required" >&2
  exit 1
fi

EXCLUDES=(
  "--exclude=.git/"
  "--exclude=node_modules/"
  "--exclude=__pycache__/"
  "--exclude=.venv/"
  "--exclude=venv/"
  "--exclude=.DS_Store"
  "--exclude=*.pyc"
  "--exclude=*.sqlite"
  "--exclude=*.sqlite-*"
  "--exclude=*.db"
  "--exclude=*.db-*"
  "--exclude=*.tmp"
  "--exclude=.runtime/"
)

copy_dir() {
  local source="$1"
  local target="$2"
  if [[ ! -d "$source" ]]; then
    return
  fi
  mkdir -p "$target"
  rsync -a "${EXCLUDES[@]}" "$source"/ "$target"/
}

copy_file() {
  local source="$1"
  local target="$2"
  if [[ ! -f "$source" ]]; then
    return
  fi
  mkdir -p "$(dirname "$target")"
  rsync -a "${EXCLUDES[@]}" "$source" "$target"
}

copy_dir "$SOURCE_ROOT/workspace" "$REPO_ROOT/workspaces/prime"
copy_dir "$SOURCE_ROOT/workspace-forge" "$REPO_ROOT/workspaces/forge"
copy_dir "$SOURCE_ROOT/workspace-scholar" "$REPO_ROOT/workspaces/scholar"
copy_dir "$SOURCE_ROOT/workspace-memory" "$REPO_ROOT/workspaces/sai-memory"
copy_dir "$SOURCE_ROOT/workspace/sisters/sai-recovery" "$REPO_ROOT/workspaces/recovery"

copy_file "$SOURCE_ROOT/.env" "$REPO_ROOT/.env"
copy_file "$SOURCE_ROOT/openclaw.json" "$REPO_ROOT/portable-openclaw/openclaw.json"

for agent_id in main forge scholar memory recovery; do
  copy_dir "$SOURCE_ROOT/agents/$agent_id/sessions" "$REPO_ROOT/portable-openclaw/agents/$agent_id/sessions"
  copy_dir "$SOURCE_ROOT/agents/$agent_id/agent" "$REPO_ROOT/portable-openclaw/agents/$agent_id/agent"
done

PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" "$REPO_ROOT/scripts/bootstrap_portable_root.py"

echo "Portable asset import complete."
