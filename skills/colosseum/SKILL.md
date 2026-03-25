---
name: colosseum
description: Run Colosseum tournament rounds, evaluate outcomes, and report leaderboard/evolution signals.
user-invocable: true
disable-model-invocation: false
risk-level: low
---
# Colosseum Runner (Forge)

Use this skill to operate the Forge Colosseum loop from the Forge workspace.

## Preconditions
1. Ensure working directory is `workspaces/forge/colosseum`.
2. Confirm Python runtime is available.
3. Confirm `v2/data/beings.json`, `v2/data/judges.json`, and `v2/data/scenarios.json` exist.

## Steps
1. **Load state** — Read current beings, judges, and scenarios from v2/data/.
2. **Run round** — Execute `python3 run_server.py` or invoke the round runner.
3. **Evaluate** — Parse round results, score beings, update leaderboard.
4. **Report** — Summarize round outcomes, top performers, evolution signals.
5. **Archive** — Save round results to history.
