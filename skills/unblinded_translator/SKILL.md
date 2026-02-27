---
name: unblinded-translator
description: Transform long transcripts into structured Unblinded Formula knowledge records.
license: MIT
user-invocable: true
allowed-tools: read write memory_store pinecone_query
---
# Unblinded Translator Workflow

Use this skill to convert transcript content into structured, reusable formula knowledge.

## Inputs
- Transcript source path (local file) OR transcript text content.
- Optional output base name.
- Optional Pinecone upsert flag.

## Steps
1. Load transcript text from the provided source.
2. Normalize whitespace and preserve speaker boundaries where available.
3. Chunk transcript into 3000-character windows with 200-character overlap.
4. For each chunk, call the LLM with the translator prompt from `TRANSLATOR_PROMPT.md`.
5. Parse output into the schema:
   - `topic`
   - `context`
   - `formula_elements`
   - `main_lesson`
   - `seans_processing`
   - `seans_approach`
6. Merge chunk outputs into a single structured document with deduped themes and formula elements.
7. Save result JSON under workspace memory, for example:
   - `memory/translator/<name>-structured.json`
8. Save a markdown summary:
   - `memory/translator/<name>-summary.md`
9. If Pinecone tooling is available and explicitly requested, query index metadata and stage the structured output for upsert.

## Output Contract
Return:
- `chunks_processed`
- `output_json_path`
- `output_summary_path`
- `formula_elements_detected`
- `pinecone_staged` (boolean)
- `errors` (list)

## Notes
- Do not invent details not present in transcript content.
- Preserve uncertainty explicitly when confidence is low.
- Prefer concise, high-signal output over verbose narration.
