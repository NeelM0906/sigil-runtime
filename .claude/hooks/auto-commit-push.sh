#!/bin/bash
# Hook: TaskCompleted — auto-commit and push after every task completion
# This ensures each plan task gets its own commit+push, not one batch at the end.
#
# Safety: only stages tracked files + explicitly allowed paths.
# Never stages secrets, ad-hoc scripts, binaries, or submodules.
set -euo pipefail

INPUT=$(cat)

TASK_SUBJECT=$(echo "$INPUT" | jq -r '.task_subject // "completed task"')
TASK_ID=$(echo "$INPUT" | jq -r '.task_id // "unknown"')

cd "$CLAUDE_PROJECT_DIR" || exit 0

# Stage only tracked (modified/deleted) files — never sweeps in untracked files
git add -u

# Also stage new files ONLY in source and config directories (allowlist approach)
git add --ignore-errors \
  'src/**' \
  'tests/**' \
  'mission-control/src/**' \
  'docs/**' \
  'contracts/**' \
  'skills/**' \
  '.claude/commands/**' \
  '.claude/settings.json' \
  '.mcp.json' \
  'workspaces/*/SOUL.md' \
  'workspaces/*/IDENTITY.md' \
  'workspaces/*/MISSION.md' \
  'workspaces/*/VISION.md' \
  'workspaces/*/FORMULA.md' \
  'workspaces/*/DESCRIPTION.md' \
  'workspaces/*/TOOLS.md' \
  'workspaces/*/AGENTS.md' \
  'workspaces/*/USER.md' \
  'workspaces/*/KNOWLEDGE.md' \
  'workspaces/TEAM_CONTEXT.md' \
  'README.md' \
  'CLAUDE.md' \
  'pyproject.toml' \
  '.github/**' \
  2>/dev/null || true

# Safety: unstage anything that should never be committed
git reset HEAD -- \
  '.env' '*.key' '*.pem' 'credentials*' \
  '*.pdf' '*.pyc' '__pycache__' \
  '.external/**' '.sai-analysis' \
  2>/dev/null || true

# Only commit if there are staged changes
if git diff --cached --quiet 2>/dev/null; then
  echo '{"message":"No changes to commit for this task"}' >&2
  exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

# Use printf for safe message construction — no shell expansion of task subject
COMMIT_MSG=$(printf '%s\n\nTask-ID: %s\nAuto-committed by TaskCompleted hook.\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>' \
  "$TASK_SUBJECT" "$TASK_ID")

git commit -m "$COMMIT_MSG" 2>&1 | tail -1 >&2

git push origin "$BRANCH" 2>&1 | tail -2 >&2 || {
  echo '{"message":"Committed locally but push failed — will retry on next task"}' >&2
  exit 0
}

echo '{"message":"Committed and pushed task"}' >&2
exit 0
