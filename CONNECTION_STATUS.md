# Connection Status Report

**Date:** 2026-03-03
**Total checks:** 37 — 30 PASS, 7 FAIL

## Summary

| Service | Status | Notes |
|---------|--------|-------|
| Pinecone Primary | PASS | 14 indexes, all 7 expected found, query + write working |
| Pinecone Strata | FAIL | Same key as Primary — Strata indexes on separate account need different key |
| Supabase | PASS | 4 tables readable, write + delete confirmed |
| ElevenLabs | PASS | 96 voices (Callie, Athena, Sean confirmed), 30 agents |
| Twilio | PASS | 50 numbers, +18322191931 active |
| Bland.ai | PASS | 129 pathways, 354K+ calls |
| OpenAI | PASS | text-embedding-3-small, 1536 dimensions |

## Action Required

- **Pinecone Strata**: The provided key (`pcsk_4Eksyx_...`) belongs to the primary account only. The Strata indexes (`ultimatestratabrain`, `oracleinfluencemastery`, `suritrial`, `2025selfmastery`, `nashmacropareto`, `rtioutcomes120`, `010526calliememory`) are on a separate Pinecone project (yvi7bh0) and need their own API key set as `PINECONE_API_KEY_STRATA` in `.env`.

## Detailed Results

| Service | Test | Status | Details |
|---------|------|--------|---------|
| Pinecone-Primary | list-indexes | PASS | Found 14 indexes: 012626bellavcalliememory, adamathenacontextualmemory, athenacontextualmemory, baslawyerathenacontextualmemory, kumar-pfd, kumar-requ |
| Pinecone-Primary | index-ublib2 | PASS |  |
| Pinecone-Primary | index-saimemory | PASS |  |
| Pinecone-Primary | index-athenacontextualmemory | PASS |  |
| Pinecone-Primary | index-uicontextualmemory | PASS |  |
| Pinecone-Primary | index-miracontextualmemory | PASS |  |
| Pinecone-Primary | index-seancallieupdates | PASS |  |
| Pinecone-Primary | index-seanmiracontextualmemory | PASS |  |
| Pinecone-Primary | query-ublib2 | PASS | 0 matches for 'zone action' |
| Pinecone-Strata | list-indexes | PASS | Found 14 indexes: 012626bellavcalliememory, adamathenacontextualmemory, athenacontextualmemory, baslawyerathenacontextualmemory, kumar-pfd, kumar-requ |
| Pinecone-Strata | index-ultimatestratabrain | FAIL | Not found in account |
| Pinecone-Strata | index-oracleinfluencemastery | FAIL | Not found in account |
| Pinecone-Strata | index-suritrial | FAIL | Not found in account |
| Pinecone-Strata | index-2025selfmastery | FAIL | Not found in account |
| Pinecone-Strata | index-nashmacropareto | FAIL | Not found in account |
| Pinecone-Strata | index-rtioutcomes120 | FAIL | Not found in account |
| Pinecone-Strata | index-010526calliememory | FAIL | Not found in account |
| Pinecone-Write | upsert | PASS | Upserted connectivity-test-0ecfae77, count=1 |
| Pinecone-Write | query-back | PASS | Retrieved connectivity-test-0ecfae77 with score=0.999916077 |
| Pinecone-Write | delete | PASS | Deleted connectivity-test-0ecfae77 |
| Supabase | read-sai_contacts | PASS | 487 rows |
| Supabase | read-sai_memory | PASS | 5 rows |
| Supabase | read-forge_operations | PASS | 1 rows |
| Supabase | read-acti_beings | PASS | 6 rows |
| Supabase | write-insert | PASS | Inserted test row 74014295-d26d-435e-a48b-5cab21265bd5 |
| Supabase | write-delete | PASS | Deleted test row 74014295-d26d-435e-a48b-5cab21265bd5 |
| ElevenLabs | list-voices | PASS | 96 voices |
| ElevenLabs | voice-Callie | PASS | ID=7YaUDeaStRuoYg3FKsmU |
| ElevenLabs | voice-Athena | PASS | ID=PoN4aHRTe7pgYxbAMHDN |
| ElevenLabs | voice-Sean | PASS | ID=SxDeVSYY9lOXTXQLlipi |
| ElevenLabs | list-agents | PASS | 30 agents |
| Twilio | list-numbers | PASS | 50 phone numbers |
| Twilio | configured-number | PASS | +18322191931 active, status=in-use |
| Bland.ai | list-pathways | PASS | 129 pathways |
| Bland.ai | list-calls | PASS | 354126 total calls |
| OpenAI | embeddings | PASS | text-embedding-3-small returned 1536 dimensions |
| OpenAI | dimension-check | PASS | 1536 dims as expected |
