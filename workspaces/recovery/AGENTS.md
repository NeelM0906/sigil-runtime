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
- **Supabase `sai_contacts`** — CRM records (single-writer: Recovery owns writes)
- **Supabase `sai_memory`** — persistent memory entries

### Memory-First Protocol
Always query Pinecone before acting. Check if the answer already exists. Never rediscover.

## Context Offload Rules
- At 50% context usage: write working state to `memory/*.md`, summarize, continue lean
- Never hoard raw data in context — fetch, extract what's needed, discard the rest
- Case data stays in Supabase/Pinecone, not in conversation context

## Single-Writer Protocol
Recovery owns `sai_contacts`. Other sisters read but do not write. All writes include: writer_id, timestamp, confidence, scope.
