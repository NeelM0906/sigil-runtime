---
name: colosseum
description: Run Colosseum tournament rounds, evaluate outcomes, and report leaderboard/evolution signals.
license: MIT
user-invocable: true
allowed-tools: exec_command file_read file_write memory_note
---
# Colosseum Runner (Forge)

Use this skill to operate the Forge Colosseum loop from the Forge workspace.

## Preconditions
1. Ensure working directory is `workspaces/forge/colosseum`.
2. Confirm Python runtime is available.
3. Confirm `v2/data/beings.json`, `v2/data/judges.json`, and `v2/data/scenarios.json` exist.

## Steps
1. Execute one tournament round:
   - run `python3 v2/tournament_v2.py`
2. Read generated artifacts in `v2/data/results/`:
   - latest leaderboard file
   - round/tournament result file
3. Extract and report:
   - top-ranked beings
   - biggest movers (up/down)
   - average and max score deltas
   - any anomalies or failed matchups
4. If configured round-count threshold is reached, trigger evolution path:
   - run evolution command/script for selected beings
   - note any post-evolution score shifts
5. Persist summary in memory notes with timestamp and file references.

## Output Contract
Return:
- `round_executed` (boolean)
- `leaderboard_path`
- `top_beings`
- `largest_movers`
- `evolution_triggered` (boolean)
- `errors`

## Failure Handling
- If execution fails, return stderr and halt further steps.
- If result files are missing, return partial status and diagnostics.
