# 03. Configuration Reference

Configuration is defined in `src/bomba_sr/runtime/config.py` with supplemental provider envs in `src/bomba_sr/llm/providers.py` and embeddings in `src/bomba_sr/memory/embeddings.py`.

## Provider Credentials
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (default: `https://api.openai.com/v1`)
- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL` (default: `https://openrouter.ai/api/v1`)

Provider selection order:
1. Anthropic key
2. OpenAI key
3. OpenRouter key
4. StaticEchoProvider fallback

## Core Runtime
- `BOMBA_RUNTIME_HOME` (default: `.runtime`)
- `BOMBA_MODEL_ID` (default: `anthropic/claude-opus-4.6`)
- `BOMBA_LEARNING_AUTO_APPLY_CONFIDENCE` (default: `0.4`)
- `BOMBA_CAPABILITY_CACHE_TTL_SECONDS` (default: `21600`)
- `BOMBA_GENERIC_INFO_WEB_RETRIEVAL` (default: `true`)

## Skills and Plugins
- `BOMBA_SKILL_ROOTS` (delimited by `:`, `;`, or `,`)
- `BOMBA_SKILL_WATCHER` (default: `true`)
- `BOMBA_SKILL_WATCHER_DEBOUNCE_MS` (default: `250`)
- `BOMBA_PLUGIN_PATHS`
- `BOMBA_PLUGIN_ALLOW`
- `BOMBA_PLUGIN_DENY`

## Tool Policy
- `BOMBA_TOOL_PROFILE` (`minimal|coding|research|full`, default: `full`)
- `BOMBA_TOOL_ALLOW`
- `BOMBA_TOOL_DENY`

## Agentic Loop
- `BOMBA_AGENTIC_LOOP_ENABLED` (default: `true`)
- `BOMBA_MAX_LOOP_ITERATIONS` (default: `25`)
- `BOMBA_LOOP_DETECTION_WINDOW` (default: `5`)

## Budget and Output Bounds
- `BOMBA_BUDGET_LIMIT_USD` (default: `2.0`)
- `BOMBA_BUDGET_HARD_STOP_PCT` (default: `0.9`)
- `BOMBA_TOOL_RESULT_MAX_CHARS` (default: `15000`)
- `BOMBA_SHELL_OUTPUT_MAX_CHARS` (default: `50000`)
- `BOMBA_PARALLEL_READ_TOOLS` (default: `true`)

## Recovery and Sub-Agent Stability
- `BOMBA_RESCUE_ENABLED` (default: `true`)
- `BOMBA_SUBAGENT_CRASH_WINDOW` (default: `60`)
- `BOMBA_SUBAGENT_CRASH_MAX` (default: `3`)
- `BOMBA_SUBAGENT_CRASH_COOLDOWN` (default: `120`)

## Skill Ecosystem and NL Routing
- `BOMBA_SKILL_PARSING_PERMISSIVE` (default: `true`)
- `BOMBA_SKILLS_TELEMETRY_ENABLED` (default: `true`)
- `BOMBA_SKILL_NL_ROUTER_ENABLED` (default: `true`)
- `BOMBA_SKILL_CATALOG_SOURCES` (default: `clawhub,anthropic_skills`)
- `BOMBA_COMPACTION_MODEL_ID` (optional model override for context compaction tool)

## Serena / Code Intel
- `SERENA_BASE_URL` (default: `http://127.0.0.1:9121`)
- `SERENA_API_KEY` (optional)
- `SERENA_FALLBACK_TO_NATIVE` (default: `true`)

## Memory Embeddings
- `OPENAI_EMBEDDING_MODEL` (default: `text-embedding-3-large`)
- `OPENAI_BASE_URL` used by embeddings client

## Validation Rules (enforced in `RuntimeConfig.__post_init__`)
- confidence in `[0,1]`
- positive TTLs and limits
- iteration windows >= 1
- budget > 0, hard-stop pct in `(0,1]`
- sub-agent crash thresholds valid
- non-empty skill catalog sources
