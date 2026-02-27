-- 007_product_runtime.sql
-- Product runtime entities for skills, governance, projects/tasks, and user identity.

CREATE TABLE IF NOT EXISTS skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL,
  skill_id TEXT NOT NULL,
  version TEXT NOT NULL,
  manifest JSONB NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('draft', 'validated', 'active', 'deprecated', 'archived')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, skill_id, version)
);

CREATE TABLE IF NOT EXISTS skill_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL,
  skill_id TEXT NOT NULL,
  skill_version TEXT NOT NULL,
  session_id TEXT,
  turn_id TEXT,
  status TEXT NOT NULL CHECK (status IN ('accepted', 'in_progress', 'completed', 'failed', 'blocked')),
  input_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  output_json JSONB,
  tool_calls JSONB,
  error_detail TEXT,
  duration_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS tool_governance_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL,
  policy_name TEXT NOT NULL,
  version INTEGER NOT NULL,
  policy_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, policy_name, version)
);

CREATE TABLE IF NOT EXISTS approval_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL,
  session_id TEXT,
  turn_id TEXT,
  action_type TEXT NOT NULL,
  payload_json JSONB NOT NULL,
  risk_class TEXT NOT NULL CHECK (risk_class IN ('low', 'medium', 'high', 'critical')),
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled')),
  reason TEXT,
  decided_by TEXT,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  decided_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS tool_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL,
  session_id TEXT,
  turn_id TEXT,
  action_type TEXT NOT NULL,
  tool_name TEXT,
  backend TEXT,
  risk_class TEXT,
  confidence DOUBLE PRECISION,
  policy_action TEXT,
  payload_hash TEXT,
  outcome_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  workspace_root TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'paused', 'archived')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, project_id)
);

CREATE TABLE IF NOT EXISTS project_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL CHECK (status IN ('todo', 'in_progress', 'blocked', 'review', 'done', 'cancelled')),
  priority TEXT NOT NULL CHECK (priority IN ('low', 'normal', 'high')),
  owner_agent_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, task_id)
);

CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  display_name TEXT,
  preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
  constraints_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  goals_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  persona_summary TEXT NOT NULL DEFAULT '',
  profile_version INTEGER NOT NULL DEFAULT 1,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS user_profile_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  signal_key TEXT NOT NULL,
  signal_value TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  status TEXT NOT NULL CHECK (status IN ('pending', 'applied', 'rejected')),
  source_ref TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  decided_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_skills_tenant_skill ON skills(tenant_id, skill_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_exec_tenant ON skill_executions(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_approval_tenant_status ON approval_queue(tenant_id, status, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_tenant ON projects(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON project_tasks(project_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_tenant_user ON user_profiles(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_profile_signals_tenant_user ON user_profile_signals(tenant_id, user_id, created_at DESC);
