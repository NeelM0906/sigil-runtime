---
name: unblinded_translator
description: Transform long transcripts into structured Unblinded Formula knowledge records.
user-invocable: true
disable-model-invocation: false
risk-level: low
---
# Unblinded Translator Workflow

Use this skill to convert transcript content into structured, reusable formula knowledge.

## Inputs
- Transcript source path (local file) OR transcript text content.
- Optional output base name.
- Optional Pinecone upsert flag.

## Steps
1. **Read** the transcript from file or accept inline text.
2. **Parse** into logical segments (topics, teaching moments, Q&A).
3. **Extract** Formula mechanics, principles, and actionable insights.
4. **Structure** into a 7-column knowledge record format.
5. **Write** the structured output to workspace.
6. **Optionally upsert** to Pinecone for long-term retrieval.
