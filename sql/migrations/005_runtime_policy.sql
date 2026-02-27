-- 005_runtime_policy.sql
-- Runtime capability cache, context assembly audit, and search execution telemetry.

CREATE TABLE IF NOT EXISTS model_capabilities_cache (
  model_id TEXT PRIMARY KEY,
  context_length INTEGER NOT NULL CHECK (context_length >= 8192),
  max_completion_tokens INTEGER NOT NULL CHECK (max_completion_tokens >= 256),
  supports_tools BOOLEAN NOT NULL,
  supports_json_mode BOOLEAN NOT NULL,
  provider_context_length INTEGER,
  raw_metadata JSONB DEFAULT '{}'::jsonb,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_model_capabilities_expires_at
  ON model_capabilities_cache(expires_at);

CREATE TABLE IF NOT EXISTS context_assembly_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  turn_id UUID NOT NULL,
  model_id TEXT NOT NULL,
  profile TEXT NOT NULL CHECK (
    profile IN ('chat', 'task_execution', 'planning', 'memory_recall', 'subagent_orchestration')
  ),
  model_context_length INTEGER NOT NULL CHECK (model_context_length >= 8192),
  reserved_output_tokens INTEGER NOT NULL CHECK (reserved_output_tokens >= 256),
  reserved_safety_tokens INTEGER NOT NULL CHECK (reserved_safety_tokens >= 256),
  input_budget_tokens INTEGER NOT NULL CHECK (input_budget_tokens >= 256),
  final_input_tokens INTEGER NOT NULL CHECK (final_input_tokens >= 0),
  compressed BOOLEAN NOT NULL DEFAULT false,
  compression_summary JSONB DEFAULT '{}'::jsonb,
  inclusion_summary JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_context_assembly_runs_session
  ON context_assembly_runs(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_context_assembly_runs_turn
  ON context_assembly_runs(turn_id);

CREATE TABLE IF NOT EXISTS search_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  turn_id UUID NOT NULL,
  plan_id UUID NOT NULL,
  query TEXT NOT NULL,
  intent TEXT NOT NULL CHECK (
    intent IN ('symbol_lookup', 'flow_trace', 'config_lookup', 'test_lookup', 'broad_discovery')
  ),
  pass INTEGER NOT NULL CHECK (pass IN (1, 2)),
  escalated BOOLEAN NOT NULL DEFAULT false,
  result_count INTEGER NOT NULL DEFAULT 0 CHECK (result_count >= 0),
  avg_confidence DOUBLE PRECISION,
  low_value_hit_ratio DOUBLE PRECISION CHECK (low_value_hit_ratio >= 0 AND low_value_hit_ratio <= 1),
  execution_ms INTEGER NOT NULL CHECK (execution_ms >= 0),
  command TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_search_executions_session
  ON search_executions(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_executions_plan
  ON search_executions(plan_id, pass);

CREATE TABLE IF NOT EXISTS runtime_metrics_rollup (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period_start TIMESTAMPTZ NOT NULL,
  period_end TIMESTAMPTZ NOT NULL,
  retrieval_precision_at_k DOUBLE PRECISION CHECK (
    retrieval_precision_at_k >= 0 AND retrieval_precision_at_k <= 1
  ),
  search_escalation_rate DOUBLE PRECISION CHECK (
    search_escalation_rate >= 0 AND search_escalation_rate <= 1
  ),
  subagent_success_rate DOUBLE PRECISION CHECK (
    subagent_success_rate >= 0 AND subagent_success_rate <= 1
  ),
  subagent_p95_latency_ms INTEGER CHECK (subagent_p95_latency_ms >= 0),
  loop_detector_incidents INTEGER NOT NULL DEFAULT 0 CHECK (loop_detector_incidents >= 0),
  prediction_brier_score DOUBLE PRECISION,
  prediction_ece DOUBLE PRECISION CHECK (prediction_ece >= 0 AND prediction_ece <= 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(period_start, period_end)
);

CREATE INDEX IF NOT EXISTS idx_runtime_metrics_period
  ON runtime_metrics_rollup(period_end DESC);
