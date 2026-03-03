# Lessons Learned

## 2026-02-27: Echo Chamber Warning

### What Happened
SAI Forge and SAI Scholar iterated on theoretical "execution protocol" frameworks for ~2 hours (v1.0 → v16.2) without producing executable code:
- Elaborate Python pseudocode with religious/quantum metaphors
- Class names like `HolyGrailLoader()`, `SeraphimSanctifier()`, `QuantumFieldCommander()`
- Version numbers escalating without implementation
- Repeated summaries of identical conceptual architecture

### The Pattern
1. One sister proposes a framework
2. Another sister summarizes it
3. First sister iterates (v+1)
4. Repeat without human validation or actual execution

### The Lesson
**When sisters start iterating abstract frameworks without human validation, flag it and return to practical execution.**

### What Should Have Happened
- Data was acquired (126K contacts) ✅
- Next practical step: Run 500-contact validation batch
- NOT: Continue iterating theoretical framework documentation

### Prevention
- After completing a milestone, ask "What's the next executable step?"
- If the answer is more documentation/framework design, pause and check with humans
- Prefer small working implementations over elaborate theoretical designs

---

## 2026-02-27: Attribution Matters

### What Happened
Wrestling metaphor and "never good enough" philosophy were incorrectly attributed to Adam. Aiko corrected this directly.

### The Lesson
When capturing quotes or philosophy, verify attribution carefully. Memory persistence means errors propagate across sessions.

### Prevention
- When uncertain about attribution, ask
- Lock important quotes with explicit source attribution
- Correct immediately when notified of errors

---

## 2026-02-27: Public Sheets Don't Need Auth

### What Happened
Spent time troubleshooting GOG authentication (`aes.KeyUnwrap(): integrity check failed`) when the sheet was public.

### The Lesson
For public Google Sheets, direct curl export works without any authentication:
```bash
curl -L "https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid={GID}" -o output.csv
```

### Prevention
- Check if sheet is public before attempting authenticated access
- Try the simple approach first
