---
name: memory_summarizer
description: Summarizes the latest memories (last 2 days) in 10 lines or less. Retrieves recent semantic and markdown memories, distills them into a concise summary capturing key events, learnings, and user interactions.
user-invocable: true
disable-model-invocation: false
risk-level: low
---
# memory_summarizer

## Purpose
Summarize BOMBA SR's latest memories (last 2 days) into a concise digest of **10 lines or less**.

## Steps

1. **Retrieve recent memories** — Use `memory_search` with a broad query (e.g. "recent interactions and learnings") with a limit of 20 to capture the last 2 days of activity.
2. **Filter by recency** — Only include memories whose `recency` timestamp falls within the last 2 days from the current date/time.
3. **Summarize** — Distill all qualifying memories into a summary of **10 lines or fewer**, covering:
   - Key user requests and outcomes
   - Important learnings or decisions stored
   - Any skills created or modified
   - Notable user preferences or goals discovered
4. **Format output** — Present the summary as a numbered list (max 10 items), each line being one key point. Use this format:

```
## 🧠 Memory Summary (Last 2 Days)

1. [point]
2. [point]
...
```

## Constraints
- **Max 10 lines** in the summary output.
- **Do not fabricate** — only summarize what is actually retrieved from memory.
- **Cite memory sources** where possible (e.g., `[source: memory://...]`).
- If no memories exist within the 2-day window, state: "No recent memories found in the last 2 days."

## Example Output

```
## 🧠 Memory Summary (Last 2 Days)

1. User (Zidane) introduced themselves and tested initial connectivity.
2. BOMBA SR architecture was analyzed — skills folder and workspace structure reviewed.
3. User's core goal recorded: make BOMBA SR "AGI-like" (general, autonomous, adaptive).
4. Learned not to create markdown artifacts for simple Q&A responses.
5. Pending approvals system was explored — no active approvals found at that time.
6. memory_summarizer skill created for quick memory digests.
```

## Invocation
User can trigger this skill by asking:
- "Summarize your recent memories"
- "What do you remember from the last 2 days?"
- "Memory summary"
- "Run memory_summarizer"
