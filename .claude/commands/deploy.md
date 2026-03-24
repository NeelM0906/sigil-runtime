Run the pre-deploy checklist for this project.

Steps:
1. **Preflight**: Run `PYTHONPATH=src python3 scripts/preflight_check.py` if it exists, otherwise skip
2. **Tests**: Run `PYTHONPATH=src python3 -m pytest tests/ -q`. If any fail, STOP and report -- do not proceed
3. **Staged check**: Run `git status` to show what will be committed. Warn if `.env`, credentials, or binary files are staged
4. **Diff review**: Run `git diff --cached --stat` to summarize staged changes
5. **Commit**: Ask for a commit message or suggest one based on the diff. Commit with the message
6. **Push**: Push to the current branch with `git push -u origin <branch>`
7. Report final status: commit SHA, branch name, push result

STOP and ask for confirmation before step 5 (commit). Never force-push.
