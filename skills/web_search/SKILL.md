---
name: web_search
description: Search the web for current information. Use when user asks about recent events, documentation, or time-sensitive data.
user-invocable: true
disable-model-invocation: false
risk-level: low
---
# Web Search

When the request needs up-to-date information:
1. Call `web_search` with a precise query and limit 5.
2. Select the most relevant 1-3 results.
3. Call `web_fetch` on selected URLs.
4. Synthesize a concise answer with citations to fetched URLs.
5. If results are weak, refine query and search again.
