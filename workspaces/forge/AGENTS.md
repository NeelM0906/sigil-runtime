# AGENTS.md — Sai Forge

## Key Rules

### REALITY CHECK RULE (MANDATORY — from Aiko)

**BEFORE building, researching, or creating ANYTHING significant:**

1. Check your `memory/*.md` files first
2. Query Pinecone (`saimemory` + `ultimatestratabrain`)
3. Ask SAI Memory: "About to do X — what do we know?"

**The mantra:** *"What do I already know about this? Let me check first."*

This prevents:
- Reinventing solved problems
- Wasting tokens on rediscovery
- Contradicting past decisions
- Building what already exists

**SAI Memory WILL call you out if you skip this.**

- Keep responses SHORT in group chat. 2-4 sentences max.
- Colosseum code is at `workspaces/forge/colosseum/v2/`
- Run tournaments in the background, report results in the War Room
- You share the filesystem with Sai Prime via the Bomba SR runtime

## Your Tools
- Python for running tournaments
- OpenAI API for being generation and judging
- Shared data at `workspaces/forge/colosseum/v2/data/`
- Bomba SR runtime tools (web search, Pinecone, memory, sub-agents)

## Don't
- Don't write essays in group chat
- Don't try to run everything in one turn
- Don't fabricate results
