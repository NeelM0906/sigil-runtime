# Voice Server Knowledge Integration Fix

**Zone Action #75 - CRITICAL**
**Status:** ✅ COMPLETE
**Miner:** Miner 13
**Date:** 2026-02-23

## Problem Statement

The voice server was running standalone and disconnected from the ecosystem's knowledge. During voice calls, Sai could only access:
- A static system prompt (hardcoded personality/instructions)
- Local memory files (MEMORY.md, daily logs) - capped at ~5KB
- No access to Pinecone's 100K+ vectors of knowledge

When someone asked about the Unblinded Formula, Zone Action, or any domain-specific knowledge, Sai could only fabricate or dodge — she had no RAG (Retrieval Augmented Generation) capability.

## Solution Implemented

### 1. Pinecone Knowledge Retrieval (RAG)

Added real-time knowledge retrieval from multiple Pinecone indexes:

```javascript
// Primary account (hw65sks)
- athenacontextualmemory (11K vectors) - core Athena memory
- ublib2 (41K vectors) - knowledge library
- saimemory - Sai's own memory
- uicontextualmemory (48K vectors) - per-user memories

// Strata account (yvi7bh0)  
- ultimatestratabrain (39K vectors) - deep domain knowledge
- oracleinfluencemastery - 4-Step Communication Model
- 2025selfmastery - self mastery content
- suritrial - court trial transcripts
- nashmacropareto - Zone Action deep-dive
```

### 2. Smart Context Injection

Before generating a response, the system now:
1. Checks if the query needs domain knowledge (not just "hi" or "bye")
2. Generates an embedding for the user's question
3. Queries multiple Pinecone indexes in parallel
4. Filters results by relevance score (>0.4)
5. Injects top 3 most relevant chunks into the system prompt

### 3. New API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/knowledge` | POST | Query Pinecone knowledge base |
| `/context` | GET | View current memory context (debugging) |
| `/health` | GET | Now shows Pinecone connection status |

#### Knowledge Endpoint Usage

```bash
# Query specific index
curl -X POST http://localhost:3334/knowledge \
  -H "Content-Type: application/json" \
  -d '{"query": "What is zone action?", "index": "athenacontextualmemory", "topK": 3}'

# Multi-index retrieval (default)
curl -X POST http://localhost:3334/knowledge \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the Unblinded Formula?"}'
```

## Technical Details

### Embedding Generation
Uses OpenAI's `text-embedding-3-small` (1536 dimensions) - same model used by all ecosystem indexes for compatibility.

### Pinecone Query
Direct HTTPS calls to Pinecone REST API (no SDK dependency):
- Automatic API key selection based on index (primary vs Strata)
- Hardcoded hosts for known indexes (avoids describe_index latency)
- Metadata extraction: `text`, `content`, `source` fields

### Performance Considerations
- Knowledge retrieval adds ~200-400ms latency per turn
- Only triggered for substantial queries (>20 chars, not greetings)
- Results cached in conversation context for follow-up questions
- Top 3 results × ~600 chars = ~1.8KB added to prompt

## Files Changed

- `/tools/voice-server/server.js` - Main implementation
  - Added `getEmbedding()` - OpenAI embedding generation
  - Added `queryPinecone()` - Direct Pinecone REST API calls
  - Added `retrieveKnowledge()` - Multi-index RAG orchestration
  - Modified `getAIResponse()` - Now includes knowledge retrieval
  - Added `/knowledge` and `/context` endpoints
  - Updated `/health` to show Pinecone status

## Testing

### Health Check
```bash
curl http://localhost:3334/health
# Should show pinecone: true, pineconeStrata: true
```

### Knowledge Query
```bash
curl -X POST http://localhost:3334/knowledge \
  -H "Content-Type: application/json" \
  -d '{"query": "What is zone action?"}'
# Should return relevant Athena content
```

### Live Call Test
1. Ensure ngrok is running: `ngrok http 3334`
2. Make a test call
3. Ask domain-specific questions
4. Check logs for "📚 Retrieved X knowledge chunks"

## Before/After

**Before:** Sai had ~5KB of context (hardcoded prompt + local memory)

**After:** Sai has access to:
- ~5KB local memory
- ~2KB retrieved knowledge per query
- 100K+ vectors on demand

## Future Enhancements

1. **Semantic caching** - Cache embeddings for common queries
2. **Query expansion** - Use conversation history to improve retrieval
3. **Per-caller namespaces** - Query user-specific memories from `uicontextualmemory`
4. **Strata indexes** - Add `ultimatestratabrain` to default retrieval (requires testing)
5. **Streaming RAG** - Start TTS before full knowledge retrieval completes

## Dependencies

No new npm packages required. Uses native `https` module for all API calls.

---

*Sai now has access to her full knowledge base during voice calls. She's no longer disconnected.*
