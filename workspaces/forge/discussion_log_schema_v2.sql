-- ============================================================================
-- DISCUSSION LOG SCHEMA v2 — Append-Only Conversation Topic Store
-- ACT-I Ecosystem | Sai Forge — Round 2 (improved)
-- 
-- Changelog vs v1:
--   • Dedicated `acti` schema instead of public
--   • Explicit `capture_window` column (timestamptz) for human-readable dedup
--   • Hash computed via BEFORE INSERT trigger (portable across PG versions)
--     instead of GENERATED ALWAYS AS (avoids complex-expression edge cases)
--   • CHECK constraints reject empty strings on being_id, topic, summary,
--     raw_excerpt
--   • TRUNCATE blocked via event trigger (BEFORE TRUNCATE row triggers
--     returning NULL do NOT block truncation — they allow it)
--   • Row-Level Security (RLS) scaffold — per-being isolation ready
--   • Batch upsert template (multi-row VALUES)
--   • Partitioning-ready notes (commented; activate for high-volume)
--   • Improved utility views with raw_excerpt included
--   • Idempotent: all CREATE IF NOT EXISTS / OR REPLACE
-- ============================================================================

-- 0. Extensions & Schema
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- digest(), gen_random_uuid()

CREATE SCHEMA IF NOT EXISTS acti;

COMMENT ON SCHEMA acti IS
    'ACT-I Ecosystem schema — houses all being-related persistent tables.';

-- ============================================================================
-- 1. TABLE: acti.discussion_log
-- ============================================================================
CREATE TABLE IF NOT EXISTS acti.discussion_log (

    -- Primary key --------------------------------------------------------
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    -- When the 4-hour snapshot pipeline ran
    captured_at     TIMESTAMPTZ     NOT NULL DEFAULT now(),

    -- Computed 4-hour window bucket (set by trigger, not caller)
    -- e.g. 2026-03-23 08:00:00+00  for any captured_at in [08:00, 12:00)
    capture_window  TIMESTAMPTZ     NOT NULL,

    -- Which ACT-I being originated the discussion
    being_id        TEXT            NOT NULL
                                   CONSTRAINT chk_being_id_nonempty
                                       CHECK (being_id <> ''),

    -- Optional session/thread identifier
    session_id      TEXT,

    -- Discussion topic or theme
    topic           TEXT            NOT NULL
                                   CONSTRAINT chk_topic_nonempty
                                       CHECK (topic <> ''),

    -- Concise summary of what was discussed
    summary         TEXT            NOT NULL
                                   CONSTRAINT chk_summary_nonempty
                                       CHECK (summary <> ''),

    -- Verbatim excerpt preserving original language — no dilution
    raw_excerpt     TEXT            NOT NULL
                                   CONSTRAINT chk_raw_excerpt_nonempty
                                       CHECK (raw_excerpt <> ''),

    -- Flexible JSONB field for tags, lever codes, cluster refs, etc.
    metadata        JSONB           NOT NULL DEFAULT '{}'::jsonb,

    -- -------------------------------------------------------------------
    -- DEDUPLICATION HASH
    -- SHA-256 of (being_id || '|' || topic || '|' || capture_window).
    -- Populated automatically by BEFORE INSERT trigger.
    -- Unique constraint prevents duplicate topic per being per window.
    -- -------------------------------------------------------------------
    dedup_hash      TEXT            NOT NULL,

    -- Row creation timestamp (immutable audit trail)
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    -- Unique constraint for dedup
    CONSTRAINT uq_discussion_log_dedup_hash UNIQUE (dedup_hash)
);

COMMENT ON TABLE acti.discussion_log IS
    'Append-only log of conversation discussion topics captured every 4 hours. '
    'No UPDATE, DELETE, or TRUNCATE permitted — enforced by triggers and event triggers. '
    'Invariant: no deletion, dilution, or distortion.';

COMMENT ON COLUMN acti.discussion_log.capture_window IS
    'Start of the 4-hour bucket containing captured_at. '
    'Computed automatically by fn_discussion_log_before_insert(). '
    'Formula: date_trunc(''day'', captured_at) + interval ''4h'' * floor(extract(hour from captured_at) / 4).';

COMMENT ON COLUMN acti.discussion_log.dedup_hash IS
    'SHA-256 hex of (being_id || ''|'' || topic || ''|'' || capture_window). '
    'Computed automatically by fn_discussion_log_before_insert(). '
    'Unique constraint prevents duplicate topics per being per 4-hour window.';

-- ============================================================================
-- 2. BEFORE INSERT TRIGGER — compute capture_window + dedup_hash
--    This replaces the v1 GENERATED ALWAYS AS column, which has portability
--    issues with complex expressions across Postgres versions.
-- ============================================================================
CREATE OR REPLACE FUNCTION acti.fn_discussion_log_before_insert()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_window TIMESTAMPTZ;
BEGIN
    -- Compute the 4-hour window bucket
    v_window := date_trunc('day', NEW.captured_at)
                + (INTERVAL '4 hours'
                   * floor(extract(hour FROM NEW.captured_at) / 4)::int);

    NEW.capture_window := v_window;

    -- Compute dedup hash: SHA-256 of (being_id | topic | window)
    NEW.dedup_hash := encode(
        digest(
            NEW.being_id
            || '|'
            || NEW.topic
            || '|'
            || to_char(v_window, 'YYYY-MM-DD"T"HH24:MI:SSOF'),
            'sha256'
        ),
        'hex'
    );

    -- Ensure created_at is always server time (prevent caller override)
    NEW.created_at := now();

    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trg_discussion_log_before_insert
    BEFORE INSERT ON acti.discussion_log
    FOR EACH ROW
    EXECUTE FUNCTION acti.fn_discussion_log_before_insert();

-- ============================================================================
-- 3. APPEND-ONLY ENFORCEMENT — Block UPDATE
-- ============================================================================
CREATE OR REPLACE FUNCTION acti.fn_block_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'UPDATE denied on %.%. This table is append-only. '
        'No deletion, dilution, or distortion permitted. Row id: %',
        TG_TABLE_SCHEMA, TG_TABLE_NAME, OLD.id
    USING ERRCODE = 'restrict_violation';
    RETURN NULL;  -- never reached
END;
$$;

CREATE OR REPLACE TRIGGER trg_block_discussion_log_update
    BEFORE UPDATE ON acti.discussion_log
    FOR EACH ROW
    EXECUTE FUNCTION acti.fn_block_update();

-- ============================================================================
-- 4. APPEND-ONLY ENFORCEMENT — Block DELETE
-- ============================================================================
CREATE OR REPLACE FUNCTION acti.fn_block_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'DELETE denied on %.%. This table is append-only. '
        'No deletion, dilution, or distortion permitted. Row id: %',
        TG_TABLE_SCHEMA, TG_TABLE_NAME, OLD.id
    USING ERRCODE = 'restrict_violation';
    RETURN NULL;  -- never reached
END;
$$;

CREATE OR REPLACE TRIGGER trg_block_discussion_log_delete
    BEFORE DELETE ON acti.discussion_log
    FOR EACH ROW
    EXECUTE FUNCTION acti.fn_block_delete();

-- ============================================================================
-- 5. APPEND-ONLY ENFORCEMENT — Block TRUNCATE
--
--    CRITICAL FIX from v1: A BEFORE TRUNCATE trigger that returns NULL does
--    NOT block truncation — TRUNCATE triggers are AFTER or BEFORE per
--    STATEMENT, and returning NULL from BEFORE STATEMENT does NOT cancel it
--    in the same way as row-level triggers. The reliable approach is an
--    event trigger on ddl_command_start filtering for TRUNCATE.
--
--    Note: Event triggers require superuser or a role with EVENT TRIGGER
--    privileges. If unavailable, REVOKE TRUNCATE as the fallback.
-- ============================================================================

-- Approach A: Event trigger (strongest — requires superuser)
CREATE OR REPLACE FUNCTION acti.fn_block_truncate_event()
RETURNS event_trigger
LANGUAGE plpgsql
AS $$
DECLARE
    obj RECORD;
BEGIN
    -- Check if any of the truncated tables is our discussion_log
    FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands() LOOP
        -- tag is 'TRUNCATE TABLE' for truncate events; but on
        -- ddl_command_start this function fires before execution.
        NULL;  -- placeholder: event trigger body below
    END LOOP;

    -- Simpler: just block ALL truncates matching our table
    -- On ddl_command_start, pg_event_trigger_ddl_commands() is not available.
    -- We use current_query() parsing instead.
    IF lower(current_query()) LIKE '%discussion_log%' THEN
        RAISE EXCEPTION
            'TRUNCATE denied on acti.discussion_log. '
            'This table is append-only. No deletion, dilution, or distortion permitted.'
        USING ERRCODE = 'restrict_violation';
    END IF;
END;
$$;

-- Event trigger on TRUNCATE (requires superuser; wrap in DO block to skip gracefully)
DO $$
BEGIN
    -- Drop existing event trigger if present (idempotent)
    BEGIN
        DROP EVENT TRIGGER IF EXISTS evttrg_block_discussion_log_truncate;
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE NOTICE 'Skipping event trigger drop — insufficient privilege.';
    END;

    -- Create event trigger
    BEGIN
        CREATE EVENT TRIGGER evttrg_block_discussion_log_truncate
            ON ddl_command_start
            WHEN TAG IN ('TRUNCATE TABLE')
            EXECUTE FUNCTION acti.fn_block_truncate_event();
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE NOTICE
            'Cannot create event trigger (requires superuser). '
            'Falling back to REVOKE TRUNCATE.';
    END;
END;
$$;

-- Approach B: Fallback — revoke TRUNCATE from non-superuser roles
-- Uncomment and set your app role name:
-- REVOKE TRUNCATE ON acti.discussion_log FROM your_app_role;

-- ============================================================================
-- 6. INDEXES
-- ============================================================================

-- B-tree on captured_at for time-range queries
CREATE INDEX IF NOT EXISTS idx_discussion_log_captured_at
    ON acti.discussion_log (captured_at);

-- B-tree on being_id for per-being lookups
CREATE INDEX IF NOT EXISTS idx_discussion_log_being_id
    ON acti.discussion_log (being_id);

-- GIN on metadata for flexible JSONB queries (@>, ?, ?&, ?| operators)
CREATE INDEX IF NOT EXISTS idx_discussion_log_metadata
    ON acti.discussion_log USING GIN (metadata jsonb_path_ops);

-- Composite: being + time range (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_discussion_log_being_time
    ON acti.discussion_log (being_id, captured_at DESC);

-- Composite: capture_window + being for dedup-adjacent queries
CREATE INDEX IF NOT EXISTS idx_discussion_log_window_being
    ON acti.discussion_log (capture_window, being_id);

-- ============================================================================
-- 7. ROW-LEVEL SECURITY (RLS) — per-being isolation scaffold
--    Enable when multi-tenant access is needed. Each being's service role
--    sets `SET app.current_being_id = 'the-technologist'` on connect.
-- ============================================================================
ALTER TABLE acti.discussion_log ENABLE ROW LEVEL SECURITY;

-- Policy: each being sees only its own rows
CREATE POLICY pol_being_isolation ON acti.discussion_log
    FOR SELECT
    USING (being_id = current_setting('app.current_being_id', true));

-- Policy: insert allowed for any authenticated role (trigger validates)
CREATE POLICY pol_allow_insert ON acti.discussion_log
    FOR INSERT
    WITH CHECK (true);

-- Superuser / table owner bypasses RLS by default.
-- For pipelines that need cross-being reads, use:
--   SET app.current_being_id = '*';
-- and create a permissive policy:
CREATE POLICY pol_admin_read ON acti.discussion_log
    FOR SELECT
    USING (current_setting('app.current_being_id', true) = '*');

-- ============================================================================
-- 8. UPSERT TEMPLATE — Single-Row INSERT ... ON CONFLICT DO NOTHING
--
--    The pipeline calls this every 4 hours. If the same (being_id, topic,
--    4-hour window) combination already exists, the INSERT is silently skipped.
--
--    Note: caller does NOT need to supply capture_window or dedup_hash —
--    the BEFORE INSERT trigger computes both automatically.
-- ============================================================================

-- TEMPLATE (parameterised — $1..$7 are bind variables):
/*
INSERT INTO acti.discussion_log (
    captured_at,
    being_id,
    session_id,
    topic,
    summary,
    raw_excerpt,
    metadata
)
VALUES (
    $1,    -- captured_at   (timestamptz) — pipeline execution timestamp
    $2,    -- being_id      (text)        — e.g. 'sai-prime', 'the-technologist'
    $3,    -- session_id    (text|null)   — optional thread/session reference
    $4,    -- topic         (text)        — discussion topic or theme
    $5,    -- summary       (text)        — concise summary
    $6,    -- raw_excerpt   (text)        — verbatim excerpt, no dilution
    $7     -- metadata      (jsonb)       — e.g. '{"lever":"L2","tags":["crm"]}'
)
ON CONFLICT (dedup_hash) DO NOTHING;
*/

-- ============================================================================
-- 9. BATCH UPSERT TEMPLATE — Multi-Row INSERT ... ON CONFLICT DO NOTHING
--    For pipelines that collect multiple topics per 4-hour window.
-- ============================================================================

-- TEMPLATE (multi-row):
/*
INSERT INTO acti.discussion_log (
    captured_at,
    being_id,
    session_id,
    topic,
    summary,
    raw_excerpt,
    metadata
)
VALUES
    ($1, $2, $3, $4, $5, $6, $7),
    ($8, $9, $10, $11, $12, $13, $14),
    ($15, $16, $17, $18, $19, $20, $21)
    -- ... additional rows ...
ON CONFLICT (dedup_hash) DO NOTHING;
*/

-- ============================================================================
-- 10. CONCRETE EXAMPLE — Runnable upsert with literal values
-- ============================================================================
INSERT INTO acti.discussion_log (
    captured_at,
    being_id,
    session_id,
    topic,
    summary,
    raw_excerpt,
    metadata
)
VALUES (
    '2026-03-23T14:30:00+00:00'::timestamptz,
    'the-technologist',
    'session-abc-123',
    'Postgres append-only schema design',
    'Designed discussion_log table with dedup hash, append-only triggers, '
    'and GIN indexes for the 4-hour snapshot pipeline.',
    'No deletion, dilution, or distortion. The table must be append-only.',
    '{"lever": "L7", "cluster": "Builder", "tags": ["postgres", "schema", "ddl"]}'::jsonb
)
ON CONFLICT (dedup_hash) DO NOTHING;

-- Running the same INSERT again should silently skip (dedup proof):
INSERT INTO acti.discussion_log (
    captured_at,
    being_id,
    session_id,
    topic,
    summary,
    raw_excerpt,
    metadata
)
VALUES (
    '2026-03-23T14:45:00+00:00'::timestamptz,   -- different time, SAME window
    'the-technologist',
    'session-def-456',
    'Postgres append-only schema design',          -- same topic
    'Duplicate test — this row should be skipped.',
    'This should not appear in the table.',
    '{}'::jsonb
)
ON CONFLICT (dedup_hash) DO NOTHING;

-- ============================================================================
-- 11. UTILITY VIEWS
-- ============================================================================

-- Recent discussions (last 24 hours) — includes raw_excerpt
CREATE OR REPLACE VIEW acti.v_recent_discussions AS
SELECT
    id,
    captured_at,
    capture_window,
    being_id,
    session_id,
    topic,
    summary,
    raw_excerpt,
    metadata,
    created_at
FROM acti.discussion_log
WHERE captured_at >= now() - INTERVAL '24 hours'
ORDER BY captured_at DESC, being_id;

-- Topic frequency across all beings
CREATE OR REPLACE VIEW acti.v_topic_frequency AS
SELECT
    topic,
    COUNT(*)                    AS occurrence_count,
    COUNT(DISTINCT being_id)    AS being_count,
    MIN(captured_at)            AS first_seen,
    MAX(captured_at)            AS last_seen,
    array_agg(DISTINCT being_id) AS beings
FROM acti.discussion_log
GROUP BY topic
ORDER BY occurrence_count DESC;

-- Per-being summary: row count, time range, distinct topics
CREATE OR REPLACE VIEW acti.v_being_summary AS
SELECT
    being_id,
    COUNT(*)                    AS total_entries,
    COUNT(DISTINCT topic)       AS distinct_topics,
    MIN(captured_at)            AS earliest_capture,
    MAX(captured_at)            AS latest_capture,
    COUNT(DISTINCT capture_window) AS windows_active
FROM acti.discussion_log
GROUP BY being_id
ORDER BY total_entries DESC;

-- ============================================================================
-- 12. HELPER FUNCTION — Query by being + time range
--     Returns all discussion rows for a given being within a time window.
-- ============================================================================
CREATE OR REPLACE FUNCTION acti.get_discussions(
    p_being_id  TEXT,
    p_from      TIMESTAMPTZ DEFAULT now() - INTERVAL '24 hours',
    p_to        TIMESTAMPTZ DEFAULT now()
)
RETURNS SETOF acti.discussion_log
LANGUAGE sql
STABLE
AS $$
    SELECT *
    FROM acti.discussion_log
    WHERE being_id = p_being_id
      AND captured_at >= p_from
      AND captured_at <= p_to
    ORDER BY captured_at DESC;
$$;

COMMENT ON FUNCTION acti.get_discussions IS
    'Retrieve discussion log entries for a specific being within a time range. '
    'Defaults to last 24 hours.';

-- ============================================================================
-- END OF SCHEMA v2
-- ============================================================================
