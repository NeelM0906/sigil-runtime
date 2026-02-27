#!/usr/bin/env bash
# =============================================================================
# Query Enrichment Hook for Claude Code
# =============================================================================
#
# Receives user prompts via UserPromptSubmit, classifies intent, and injects
# minimal high-value context so Claude starts oriented instead of guessing.
#
# Design principles:
#   - Fast: < 2s execution, pure shell, no external API calls
#   - Minimal: ~300-500 tokens of injected context, never dumps everything
#   - Smart: classifies query intent and picks relevant context per category
#   - Non-destructive: exit 0 always, never blocks prompts
#
# Input (stdin): JSON with { prompt, cwd, session_id, ... }
# Output (stdout): JSON with hookSpecificOutput.additionalContext
#
# Install: registered as UserPromptSubmit hook in .claude/settings.json
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# PATH bootstrap (hooks run with minimal PATH)
# ---------------------------------------------------------------------------
for dir in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" /usr/bin /bin; do
  [ -d "$dir" ] && export PATH="$dir:$PATH"
done

# ---------------------------------------------------------------------------
# Find jq (required) and git (required)
# ---------------------------------------------------------------------------
JQ=$(command -v jq 2>/dev/null || echo "")
GIT=$(command -v git 2>/dev/null || echo "")

if [ -z "$JQ" ] || [ -z "$GIT" ]; then
  # Can't enrich without tools -- silently pass through
  exit 0
fi

# ---------------------------------------------------------------------------
# Read hook input
# ---------------------------------------------------------------------------
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | "$JQ" -r '.prompt // ""')
CWD=$(echo "$INPUT" | "$JQ" -r '.cwd // ""')

# Guard: empty prompt or not in our project
if [ -z "$PROMPT" ]; then
  exit 0
fi

# Resolve project root (find nearest .git ancestor from cwd)
PROJECT_ROOT="$CWD"
while [ "$PROJECT_ROOT" != "/" ] && [ ! -d "$PROJECT_ROOT/.git" ]; do
  PROJECT_ROOT=$(dirname "$PROJECT_ROOT")
done
if [ "$PROJECT_ROOT" = "/" ]; then
  # Not in a git repo -- can't provide useful context
  exit 0
fi

# ---------------------------------------------------------------------------
# QUERY CLASSIFICATION
# ---------------------------------------------------------------------------
# Uses keyword matching -- fast, no API call needed.
# Categories: debug, api, file, test, git, refactor, general

PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

classify_query() {
  local p="$1"

  # Test-related (check before debug -- "fix test failures" is a test task)
  if echo "$p" | grep -qE '(test|pytest|unittest|spec|coverage|assert|mock|fixture)'; then
    echo "test"
    return
  fi

  # Debug / error investigation (word-boundary -w to avoid "logic" matching "log")
  if echo "$p" | grep -qwE '(error|bug|fix|crash|fail|broken|trace|exception|debug|issue|wrong|stacktrace|log)' || echo "$p" | grep -qF 'not work'; then
    echo "debug"
    return
  fi

  # Git operations (check before general keywords)
  if echo "$p" | grep -qwE '(git|commit|branch|merge|rebase|diff|push|pull|stash|cherry)'; then
    echo "git"
    return
  fi

  # API / HTTP / messaging
  if echo "$p" | grep -qwE '(api|endpoint|curl|http|request|response|route|server|webhook|socket|rest|grpc)'; then
    echo "api"
    return
  fi

  # Refactoring (check before file -- "refactor module" is refactor, not file)
  if echo "$p" | grep -qwE '(refactor|extract|reorganize|decouple|simplify|abstract)'; then
    echo "refactor"
    return
  fi

  # File operations / structure
  if echo "$p" | grep -qwE '(file|directory|folder|tree|create|move|rename|path|import|module|package|structure)'; then
    echo "file"
    return
  fi

  echo "general"
}

CATEGORY=$(classify_query "$PROMPT_LOWER")

# ---------------------------------------------------------------------------
# CONTEXT GATHERING (category-aware)
# ---------------------------------------------------------------------------
# Each gatherer appends to CTX array. We join them at the end.

CTX=()

# --- Always included: baseline orientation (very compact) ---
BRANCH=$("$GIT" -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
SHORT_SHA=$("$GIT" -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo "?")

CTX+=("[project] bomba-sr-runtime | branch: $BRANCH ($SHORT_SHA) | root: $PROJECT_ROOT")

# --- Always: what changed recently (compact diff --stat) ---
DIFF_STAT=$("$GIT" -C "$PROJECT_ROOT" diff --stat --stat-width=60 2>/dev/null | tail -5)
if [ -n "$DIFF_STAT" ]; then
  CTX+=("[uncommitted changes]")
  CTX+=("$DIFF_STAT")
fi

# --- Always: staged files ---
STAGED=$("$GIT" -C "$PROJECT_ROOT" diff --cached --name-only 2>/dev/null | head -8)
if [ -n "$STAGED" ]; then
  CTX+=("[staged] $STAGED")
fi

# ---------------------------------------------------------------------------
# Category-specific context
# ---------------------------------------------------------------------------

case "$CATEGORY" in
  debug)
    # Recent git log (what happened lately that might have introduced the bug)
    RECENT_LOG=$("$GIT" -C "$PROJECT_ROOT" log --oneline -5 2>/dev/null || echo "")
    if [ -n "$RECENT_LOG" ]; then
      CTX+=("[recent commits]")
      CTX+=("$RECENT_LOG")
    fi

    # Check for recent error logs
    for logfile in "$PROJECT_ROOT"/*.log "$PROJECT_ROOT"/.runtime/*.log; do
      if [ -f "$logfile" ]; then
        TAIL=$(tail -8 "$logfile" 2>/dev/null | head -8)
        if [ -n "$TAIL" ]; then
          CTX+=("[log: $(basename "$logfile")]")
          CTX+=("$TAIL")
        fi
        break  # only first log file to keep context small
      fi
    done

    # Check pytest cache for last failure
    if [ -f "$PROJECT_ROOT/.pytest_cache/v/cache/lastfailed" ]; then
      LASTFAIL=$(cat "$PROJECT_ROOT/.pytest_cache/v/cache/lastfailed" 2>/dev/null | "$JQ" -r 'keys[:5][]' 2>/dev/null || echo "")
      if [ -n "$LASTFAIL" ]; then
        CTX+=("[last pytest failures] $LASTFAIL")
      fi
    fi
    ;;

  test)
    # Test structure overview
    TEST_COUNT=$(find "$PROJECT_ROOT/tests" -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')
    CTX+=("[tests] $TEST_COUNT test files in tests/")

    # Last test results from pytest cache
    if [ -f "$PROJECT_ROOT/.pytest_cache/v/cache/lastfailed" ]; then
      LASTFAIL=$(cat "$PROJECT_ROOT/.pytest_cache/v/cache/lastfailed" 2>/dev/null | "$JQ" -r 'keys[:5][]' 2>/dev/null || echo "")
      if [ -n "$LASTFAIL" ]; then
        CTX+=("[last failures] $LASTFAIL")
      fi
    fi

    # Run command hint
    CTX+=("[run tests] PYTHONPATH=src python3 -m pytest tests/ -v")
    ;;

  api)
    # API endpoints from README (extracted once, cached-ish via grep)
    CTX+=("[api server] PYTHONPATH=src python3 scripts/run_runtime_server.py --host 127.0.0.1 --port 8787")
    CTX+=("[curl template] curl -s http://127.0.0.1:8787/chat -H 'content-type: application/json' -d '{\"tenant_id\":\"tenant-local\",\"session_id\":\"sess-1\",\"user_id\":\"user-local\",\"workspace_root\":\"$PROJECT_ROOT\",\"message\":\"...\"}'")

    # Key API entry points
    CTX+=("[api entry] src/bomba_sr/runtime/bridge.py (RuntimeBridge.handle_turn)")
    CTX+=("[api routes] POST /chat, /codeintel, /skills/register, /skills/execute, /subagents/spawn, /projects, /tasks, /profile")
    ;;

  file)
    # Directory tree (depth-limited, no __pycache__)
    TREE=$(find "$PROJECT_ROOT/src/bomba_sr" -type d -maxdepth 2 -not -name '__pycache__' 2>/dev/null | sed "s|$PROJECT_ROOT/||" | sort | head -20)
    if [ -n "$TREE" ]; then
      CTX+=("[source modules]")
      CTX+=("$TREE")
    fi

    # Key config files
    CTX+=("[config] pyproject.toml, .env.example, .gitignore")
    CTX+=("[contracts] contracts/*.schema.json ($(ls "$PROJECT_ROOT/contracts/"*.schema.json 2>/dev/null | wc -l | tr -d ' ') schemas)")
    ;;

  git)
    # Richer git context
    RECENT_LOG=$("$GIT" -C "$PROJECT_ROOT" log --oneline -8 2>/dev/null || echo "")
    if [ -n "$RECENT_LOG" ]; then
      CTX+=("[recent commits]")
      CTX+=("$RECENT_LOG")
    fi

    # Branches
    BRANCHES=$("$GIT" -C "$PROJECT_ROOT" branch --list 2>/dev/null | head -5)
    if [ -n "$BRANCHES" ]; then
      CTX+=("[branches] $BRANCHES")
    fi

    # Stash count
    STASH_COUNT=$("$GIT" -C "$PROJECT_ROOT" stash list 2>/dev/null | wc -l | tr -d ' ')
    if [ "$STASH_COUNT" -gt 0 ]; then
      CTX+=("[stashes] $STASH_COUNT")
    fi
    ;;

  refactor)
    # Source module map for architecture awareness
    MODULES=$(find "$PROJECT_ROOT/src/bomba_sr" -type d -maxdepth 1 -not -name '__pycache__' 2>/dev/null | sed "s|$PROJECT_ROOT/src/bomba_sr||;s|^/||" | grep -v "^$" | sort)
    if [ -n "$MODULES" ]; then
      CTX+=("[bomba_sr modules] $MODULES")
    fi

    # File sizes for complexity hints
    LARGE_FILES=$(find "$PROJECT_ROOT/src" -name "*.py" -size +8k 2>/dev/null | sed "s|$PROJECT_ROOT/||" | head -5)
    if [ -n "$LARGE_FILES" ]; then
      CTX+=("[large source files] $LARGE_FILES")
    fi

    CTX+=("[architecture] docs/02-architecture.md")
    CTX+=("[key entry] src/bomba_sr/runtime/bridge.py -> handle_turn lifecycle")
    ;;

  general)
    # Light orientation -- module list + recent activity
    MODULES=$(find "$PROJECT_ROOT/src/bomba_sr" -type d -maxdepth 1 -not -name '__pycache__' 2>/dev/null | sed "s|$PROJECT_ROOT/src/bomba_sr||;s|^/||" | grep -v "^$" | sort | tr '\n' ', ')
    if [ -n "$MODULES" ]; then
      CTX+=("[modules] $MODULES")
    fi

    RECENT_LOG=$("$GIT" -C "$PROJECT_ROOT" log --oneline -3 2>/dev/null || echo "")
    if [ -n "$RECENT_LOG" ]; then
      CTX+=("[recent] $RECENT_LOG")
    fi

    CTX+=("[docs] docs/README.md -> docs/02-architecture.md")
    CTX+=("[run tests] PYTHONPATH=src python3 -m pytest tests/ -v")
    ;;
esac

# ---------------------------------------------------------------------------
# ASSEMBLE OUTPUT
# ---------------------------------------------------------------------------

# Join context lines with newlines
CONTEXT_BLOCK=""
for line in "${CTX[@]}"; do
  CONTEXT_BLOCK="${CONTEXT_BLOCK}${line}
"
done

# Trim trailing newline
CONTEXT_BLOCK=$(echo "$CONTEXT_BLOCK" | sed '/^$/d')

# Return as structured JSON with additionalContext (discrete injection)
"$JQ" -n \
  --arg ctx "$CONTEXT_BLOCK" \
  --arg cat "$CATEGORY" \
  '{
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: ("[query-enrichment intent=" + $cat + "]\n" + $ctx)
    }
  }'

exit 0
