Review the current staged and unstaged changes in this repository.

Steps:
1. Run `git diff` and `git diff --cached` to see all changes
2. Check changes against the conventions in CLAUDE.md:
   - No Flask/FastAPI/Django imports (stdlib http.server only)
   - No PostgreSQL/MongoDB usage (SQLite WAL only)
   - Thread safety: all DB access via RuntimeDB with RLock
   - No `rm` or `mv` without backup
   - PYTHONPATH=src for all imports
   - No files outside project root
3. Look for common issues:
   - Security: command injection, path traversal, unsanitized input
   - Missing thread safety in shared state
   - Hardcoded secrets or credentials
   - Broken imports (relative vs absolute)
   - Test files that won't be discovered by pytest (missing test_ prefix)
4. Summarize findings as: PASS (no issues), WARN (minor), or FAIL (blocking)
5. For each issue, cite the file and line number
