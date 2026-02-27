-- 006_subagent_protocol.sql
-- Sub-agent task lifecycle, event stream, and shared working-memory write audit.

CREATE TABLE IF NOT EXISTS subagent_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID NOT NULL,
  ticket_id UUID NOT NULL,
  parent_session_id UUID NOT NULL,
  parent_turn_id UUID NOT NULL,
  parent_agent_id UUID NOT NULL,
  child_agent_id UUID NOT NULL,
  idempotency_key TEXT NOT NULL,
  goal TEXT NOT NULL,
  done_when JSONB NOT NULL,
  input_context_refs UUID[] NOT NULL DEFAULT '{}',
  output_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
  priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
  run_timeout_seconds INTEGER NOT NULL CHECK (run_timeout_seconds >= 5 AND run_timeout_seconds <= 86400),
  cleanup TEXT NOT NULL DEFAULT 'keep' CHECK (cleanup IN ('keep', 'archive')),
  status TEXT NOT NULL DEFAULT 'accepted' CHECK (
    status IN ('accepted', 'in_progress', 'blocked', 'failed', 'timed_out', 'completed')
  ),
  progress_pct INTEGER CHECK (progress_pct >= 0 AND progress_pct <= 100),
  accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  runtime_ms INTEGER CHECK (runtime_ms >= 0),
  token_usage JSONB,
  error_detail TEXT,
  artifacts JSONB,
  UNIQUE(parent_turn_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_subagent_runs_parent_session
  ON subagent_runs(parent_session_id, accepted_at DESC);

CREATE INDEX IF NOT EXISTS idx_subagent_runs_status
  ON subagent_runs(status, accepted_at DESC);

CREATE TABLE IF NOT EXISTS subagent_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES subagent_runs(id) ON DELETE CASCADE,
  ticket_id UUID NOT NULL,
  event_type TEXT NOT NULL CHECK (
    event_type IN ('accepted', 'started', 'progress', 'blocked', 'failed', 'timed_out', 'completed', 'announced')
  ),
  status TEXT NOT NULL CHECK (
    status IN ('accepted', 'in_progress', 'blocked', 'failed', 'timed_out', 'completed')
  ),
  progress_pct INTEGER CHECK (progress_pct >= 0 AND progress_pct <= 100),
  summary TEXT,
  artifacts JSONB,
  runtime_ms INTEGER CHECK (runtime_ms >= 0),
  token_usage JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subagent_events_run
  ON subagent_events(run_id, created_at ASC);

CREATE TABLE IF NOT EXISTS shared_working_memory_writes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID REFERENCES subagent_runs(id) ON DELETE SET NULL,
  writer_agent_id UUID NOT NULL,
  ticket_id UUID NOT NULL,
  scope TEXT NOT NULL CHECK (scope IN ('scratch', 'proposal', 'committed')),
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  content TEXT NOT NULL,
  source_refs UUID[] NOT NULL DEFAULT '{}',
  merged_by_agent_id UUID,
  merged_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_shared_working_memory_ticket
  ON shared_working_memory_writes(ticket_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_shared_working_memory_scope
  ON shared_working_memory_writes(scope, created_at DESC);
