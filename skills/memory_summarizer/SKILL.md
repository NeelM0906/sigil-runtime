---
name: memory_summarizer
description: Summarizes the latest memories (last 2 days) in 10 lines or less. Retrieves recent semantic and markdown memories, distills them into a concise summary capturing key events, learnings, and user interactions.
user-invocable: true
disable-model-invocation: false
risk-level: low
---
# memory_summarizer

## Purpose
Summarize SAI's latest memories (last 2 days) into a concise digest of **10 lines or less**.

## Steps

1. **Retrieve recent memories** — Use `memory_search` with a broad query (e.g. "recent interactions and learnings") with a limit of 20 to capture the last 2 days of activity.
2. **Categorize** — Group memories by type: user interactions, task completions, learnings, system events.
3. **Prioritize** — Rank by significance (user-facing outcomes > internal maintenance).
4. **Synthesize** — Produce a 10-line-or-less summary capturing the most important events, decisions, and insights.
5. **Output** — Return the summary as plain text.
