#!/bin/bash
# Hook: TaskCompleted — auto-commit and push after every task completion
# This ensures each plan task gets its own commit+push, not one batch at the end.
set -euo pipefail

INPUT=$(cat)

TASK_SUBJECT=$(echo "$INPUT" | jq -r '.task_subject // "completed task"')
TASK_ID=$(echo "$INPUT" | jq -r '.task_id // "unknown"')

cd "$CLAUDE_PROJECT_DIR" || exit 0

# Stage all tracked changes + new files (but skip .env, credentials, large binaries)
git add -A -- . ':!.env' ':!*.key' ':!*.pem' ':!credentials*'

# Only commit if there are staged changes
if git diff --cached --quiet 2>/dev/null; then
  echo '{"message":"No changes to commit for this task"}' >&2
  exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

COMMIT_MSG=$(cat <<EOF
${TASK_SUBJECT}

Task-ID: ${TASK_ID}
Auto-committed by TaskCompleted hook.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)

git commit -m "$COMMIT_MSG" 2>&1 | tail -1 >&2

git push origin "$BRANCH" 2>&1 | tail -2 >&2 || {
  echo '{"message":"Committed locally but push failed — will retry on next task"}' >&2
  exit 0
}

echo '{"message":"Committed and pushed: '"${TASK_SUBJECT}"'"}' >&2
exit 0
