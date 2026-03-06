# TOOLS.md — SAI Memory

## Memory Tools

### memory_search
Search semantic + markdown memory across tenants.
- **When:** Finding past discoveries, checking if something was already learned
- **Not:** For Pinecone deep knowledge — use pinecone_query instead

### memory_get
Retrieve specific memory items by query.
- **When:** Pulling exact memory entries for fact-checking or cross-referencing
- **Not:** For broad discovery — use memory_search first

### memory_store
Store new semantic memories with confidence scoring.
- **When:** Persisting cross-sister insights, resolved contradictions, compound findings
- **Not:** For raw working notes — use write to memory/*.md instead

## Pinecone Tools

### pinecone_query
Query a specific Pinecone index.
- **When:** Deep retrieval from one index (ublib2, ultimatestratabrain, saimemory, seancallieupdates)
- **Not:** When you need breadth — use pinecone_multi_query

### pinecone_multi_query
Parallel query across multiple indexes simultaneously.
- **When:** Cross-referencing knowledge across 2+ indexes. This is Memory's signature move.
- **Not:** When you already know which single index has the answer

### pinecone_upsert
Embed and write to Pinecone for permanent storage.
- **When:** Uploading consolidated findings, deduplicated knowledge, compound insights
- **Not:** For temporary notes — use memory files instead

### pinecone_list_indexes
List available Pinecone indexes and their stats.
- **When:** Auditing index health, checking vector counts, discovering new indexes
- **Not:** For retrieval — use pinecone_query or pinecone_multi_query

## File Tools

### read
Read files from any sister workspace.
- **When:** Auditing sister workspaces, checking memory files, reading KNOWLEDGE.md
- **Not:** For Pinecone content — use pinecone_query

### write
Write files to workspace.
- **When:** Creating memory/*.md working notes, updating audit findings
- **Not:** For permanent knowledge — use memory_store or pinecone_upsert

## Knowledge Tools

### update_knowledge
Update KNOWLEDGE.md with significant findings.
- **When:** After discovering cross-sister patterns or resolving contradictions
- **Not:** For ephemeral session notes — use write to memory/*.md

### web_search
Search the web for current information.
- **When:** Grounding memory in current facts, verifying external claims
- **Not:** For internal knowledge — check Pinecone and memory first. Always.
