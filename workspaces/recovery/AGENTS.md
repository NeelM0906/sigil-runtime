# AGENTS.md — SAI Recovery

## Boot Sequence
1. Load SOUL.md → voice, personality, never-do list
2. Load IDENTITY.md → facts, creature level, domain
3. Load USER.md → who I serve, zone actions, done criteria
4. Scan `memory/*.md` → recent session state, working notes

## Memory Management

### Short-Term (Session)
- `memory/*.md` — working notes, case updates, session observations
- Conversation history — last 3-5 turns replayed, older turns summarized

### Long-Term (Persistent)
- **Pinecone `ublib2`** — 41K vectors, complete knowledge library
- **Pinecone `saimemory`** — core memory + cross-sister knowledge
- **Pinecone `ultimatestratabrain`** — 39K vectors, deep mastery patterns
- **Semantic memory** — memory_store entries with confidence scoring (Recovery owns case insights)
- **Workspace files** — memory/*.md working notes and case files

### Memory-First Protocol
Always query Pinecone before acting. Check if the answer already exists. Never rediscover.

## Context Offload Rules
- At 50% context usage: write working state to `memory/*.md`, summarize, continue lean
- Never hoard raw data in context — fetch, extract what's needed, discard the rest
- Case data stays in Pinecone/semantic memory, not in conversation context

## Single-Writer Protocol
Recovery owns case-related semantic memories. Other sisters read but do not write case data. All memory_store writes include: writer_id, timestamp, confidence, scope.
