# TOOLS.md — SAI Recovery

## Pinecone Tools

### pinecone_query
Query one Pinecone index (ublib2, saimemory, ultimatestratabrain).
- **When:** Deep retrieval from one knowledge base
- **Not:** Need breadth — use pinecone_multi_query

### pinecone_multi_query
Parallel query across multiple indexes.
- **When:** Cross-referencing across 2+ indexes
- **Not:** When you know which single index has the answer

## Memory Tools

### memory_search
Search semantic + markdown memory.
- **When:** Finding past discoveries, checking if already learned
- **Not:** For Pinecone deep knowledge — use pinecone_query

### memory_store
Store new semantic memories with confidence scoring.
- **When:** Persisting cross-sister insights, resolved findings
- **Not:** For raw working notes — use write to memory/*.md

## CRM Tools

### supabase_read
Read from sai_contacts or sai_memory tables.
- **When:** Looking up contact records, case data, memory entries
- **Not:** For knowledge retrieval — use Pinecone

### supabase_write
Write to sai_contacts or sai_memory (single-writer: Recovery owns).
- **When:** Updating contact records, logging case outcomes
- **Not:** Without verifying single-writer protocol

## Voice Tools

### voice_make_call
Outbound Bland.ai voice call.
- **When:** Provider follow-up, intake confirmation, status updates
- **Not:** Without a clear script and next-action plan

### voice_list_calls / voice_get_transcript
Review past calls and transcripts.
- **When:** Auditing call outcomes, extracting action items
- **Not:** For general search — use memory_search

## File Tools

### read / write
Read and write workspace files.
- **When:** Session notes in memory/*.md, updating KNOWLEDGE.md
- **Not:** For permanent knowledge — use memory_store or pinecone

## Web

### web_search
Search the web for current information.
- **When:** Verifying external claims, checking regulatory updates
- **Not:** For internal knowledge — check Pinecone first. Always.
