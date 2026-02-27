# 01. Overview

## What SIGIL/BOMBA SR Is
SIGIL (BOMBA SR runtime) is a local-first, multi-tenant agent runtime that bridges user interactions and LLM providers while enforcing memory, governance, tools, skills, projects/tasks, and approval workflows.

It is designed to operate as a general user assistant (not code-only), while still supporting strong coding capabilities as one domain of environment interaction.

## Core Responsibilities
- Route user messages through a deterministic runtime pipeline.
- Assemble context under model token constraints.
- Run an agentic loop (LLM -> tool calls -> LLM) with governance checks.
- Persist long-term memory and user identity/profile signals.
- Manage artifacts, projects, tasks, and sub-agent execution.
- Load and execute skills from local SKILL.md and registry.
- Support external skill ecosystems (ClawHub + Anthropic Skills) with trust + approval controls.

## Runtime Modes
- `chat`: conversational mode.
- `project`: project/task oriented mode when project/task context is active.
- `generic_info`: info retrieval mode for broad non-project questions.
- `command`: slash-command direct execution mode.
- `skill_nl`: chat-native deterministic skill operation mode.

## Multi-Tenant Model
- One runtime process may serve multiple tenants.
- Tenant is bound to a workspace root and dedicated runtime DB.
- No cross-tenant state sharing for runtime data.
- Skill catalog trust policy supports shared defaults + per-tenant override.

## Provider Model
Supported providers:
- Anthropic API
- OpenAI-compatible API
- OpenRouter via OpenAI-compatible protocol
- Static echo provider for deterministic local testing

## Why It Exists
- Make the execution environment smarter than a plain stateless chat completion.
- Provide safe tool use through governance and approvals.
- Provide durable memory and identity adaptation.
- Allow progressive capability growth via skills/plugins.
- Enable production-style introspection via telemetry/audit records.
