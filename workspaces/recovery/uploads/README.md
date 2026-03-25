# Parameter Golf Autoresearch

Autoresearch-style autonomous experiment loop adapted for the [OpenAI parameter golf challenge](https://github.com/openai/parameter-golf).

**Metric**: FineWeb validation bits per byte (`val_bpb`). Lower is better.  
**Constraint**: compressed code + model + tokenizer ≤ **16,000,000 bytes**.  
**Eval limit**: reproducible in under 10 minutes on 8×H100s.

---

## Files

| File | Role | Editable? |
|------|------|-----------|
| `program.md` | Agent instructions — you iterate this | ✅ Human edits |
| `train.py` | Model, optimizer, training loop | ✅ Agent edits |
| `prepare.py` | Data prep, tokenizer, data loader | ❌ Fixed |
| `score.py` | Artifact legality checker | ❌ Fixed |
| `pyproject.toml` | Dependencies | ❌ (ask human to change) |

---

## Quickstart

```bash
# 1. Install dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# 2. One-time data + tokenizer prep (downloads FineWeb, trains BPE tokenizer)
uv run prepare.py

# 3. Verify everything is ready
uv run prepare.py --verify

# 4. Run one experiment manually to confirm it works
uv run train.py > run.log 2>&1
grep "^val_bpb:\|^artifact_bytes:" run.log

# 5. Run legality check
uv run score.py

# 6. Point Claude Code at program.md and let it run the loop
# Open Claude Code, navigate to this repo, and say:
#   "Read program.md and start the autoresearch loop"
```

---

## The Loop (what the agent does)

```
for each experiment:
  1. pick an idea from the Research Queue in program.md
  2. edit train.py
  3. uv run train.py > run.log 2>&1
  4. grep "^val_bpb:\|^artifact_bytes:" run.log
  5. uv run score.py
  6. if val_bpb improved AND legal: git commit  (advance)
     else:                           git checkout train.py  (revert)
  7. record in results.tsv
  8. repeat
```

---

## Key Numbers

| | Value |
|--|--|
| Artifact limit | 16,000,000 bytes |
| Baseline val_bpb | ~1.2244 |
| Baseline model | 9L 512d 8h 1024v tied |
| Baseline artifact | ~12-14 MB (estimated) |

---

## Research Strategy

See the Research Queue in `program.md` for the full prioritized list. The high-level bets (in priority order):

1. **Tokenizer engineering** — tokenizer-agnostic scoring is a massive clue. Bigger/smarter vocab may beat bigger model.
2. **Parameter tying / recurrence** — share one strong block applied N times instead of N separate blocks.
3. **Compression-aware training** — co-design with the compressor from day 1 (QAT, low-bit, codebooks).
4. **Test-time compute** — extra recurrent passes at eval cost compute, not bytes.
5. **Selective speedrun borrowings** — Muon optimizer, value skips, QK-norm, ReLU².

---

## Tips for Iterating program.md

The agent is only as good as its instructions. After each overnight run, update `program.md`:
- Cross off ideas that failed
- Add new hypotheses based on what the agent discovered
- Reprioritize if a new direction looks promising
- Tighten constraints if the agent kept trying illegal variants

This is your main job. The agent handles the rest.
