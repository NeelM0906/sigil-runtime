# Connection Status Report

**Date:** 2026-03-03
**Total checks:** 29 — 28 PASS, 1 FAIL

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
| Pinecone-Write | upsert | PASS | Upserted connectivity-test-76297fff, count=1 |
| Pinecone-Write | query-back | FAIL | Expected connectivity-test-76297fff, got [] |
| Pinecone-Write | delete | PASS | Deleted connectivity-test-76297fff |
| Supabase | read-sai_contacts | PASS | 487 rows |
| Supabase | read-sai_memory | PASS | 5 rows |
| Supabase | read-forge_operations | PASS | 1 rows |
| Supabase | read-acti_beings | PASS | 6 rows |
| Supabase | write-insert | PASS | Inserted test row f43d45d9-5f40-4085-b232-69980ea09f93 |
| Supabase | write-delete | PASS | Deleted test row f43d45d9-5f40-4085-b232-69980ea09f93 |
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
