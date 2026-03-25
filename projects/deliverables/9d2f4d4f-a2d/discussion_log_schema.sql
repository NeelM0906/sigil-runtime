-- ============================================================================
-- DISCUSSION LOG SCHEMA — Append-Only Conversation Topic Store
-- ACT-I Ecosystem | Designed by The Technologist (Sai Forge)
-- 
-- Purpose: Stores conversation discussion topics captured every 4 hours.
-- Invariant: NO deletion, dilution, or distortion. Append-only enforced
--            at the database level via triggers.
-- ============================================================================

-- 0. Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()

-- ============================================================================
-- 1. TABLE: discussion_log
-- ============================================================================
CREATE TABLE IF NOT EXISTS discussion_log (
    -- Primary key
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),

    -- When the 4-hour snapshot pipeline ran
    captured_at     TIMESTAMPTZ     NOT NULL DEFAULT now(),

    -- Which ACT-I being originated the discussion
    being_id        TEXT            NOT NULL,

    -- Optional session/thread identifier
    session_id      TEXT,

    -- Discussion topic or theme
    topic           TEXT            NOT NULL,

    -- Concise summary of what was discussed
    summary         TEXT            NOT NULL,

    -- Verbatim excerpt preserving original language — no dilution
    raw_excerpt     TEXT            NOT NULL,

    -- Flexible JSONB field for tags, lever codes, cluster refs, etc.
    metadata        JSONB           NOT NULL DEFAULT '{}'::jsonb,

    -- -----------------------------------------------------------------------
    -- DEDUPLICATION HASH
    -- Deterministic hash of (being_id, topic, 4-hour window).
    -- The 4-hour window is captured_at truncated to the nearest 4-hour block.
    -- This prevents the same topic from the same being in the same capture
    -- window from being inserted twice.
    -- -----------------------------------------------------------------------
    dedup_hash      TEXT            GENERATED ALWAYS AS (
                        encode(
                            digest(
                                being_id
                                || '|'
                                || topic
                                || '|'
                                || to_char(
                                       date_trunc('day', captured_at)
                                       + (INTERVAL '4 hours' * floor(extract(hour FROM captured_at) / 4)),
                                       'YYYY-MM-DD"T"HH24'
                                   ),
                                'sha256'
                            ),
                            'hex'
                        )
                    ) STORED,

    -- Row creation timestamp (immutable audit trail)
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

-- Add table comment
COMMENT ON TABLE discussion_log IS
    'Append-only log of conversation discussion topics captured every 4 hours. '
    'No UPDATE or DELETE permitted — enforced by triggers.';

-- ============================================================================
-- 2. UNIQUE CONSTRAINT on dedup_hash (deduplication)
-- ============================================================================
ALTER TABLE discussion_log
    ADD CONSTRAINT uq_discussion_log_dedup_hash UNIQUE (dedup_hash);

-- ============================================================================
-- 3. INDEXES for fast querying
-- ============================================================================

-- B-tree on captured_at for time-range queries
CREATE INDEX IF NOT EXISTS idx_discussion_log_captured_at
    ON discussion_log (captured_at);

-- B-tree on being_id for per-being lookups
CREATE INDEX IF NOT EXISTS idx_discussion_log_being_id
    ON discussion_log (being_id);

-- GIN on metadata for flexible JSONB queries (@>, ?, ?&, ?| operators)
CREATE INDEX IF NOT EXISTS idx_discussion_log_metadata
    ON discussion_log USING GIN (metadata);

-- Composite index for common query pattern: being + time range
CREATE INDEX IF NOT EXISTS idx_discussion_log_being_time
    ON discussion_log (being_id, captured_at DESC);

-- ============================================================================
-- 4. APPEND-ONLY ENFORCEMENT — Block UPDATE
-- ============================================================================
CREATE OR REPLACE FUNCTION fn_block_discussion_log_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'UPDATE denied on discussion_log. This table is append-only. '
        'No deletion, dilution, or distortion permitted. Row id: %',
        OLD.id;
    RETURN NULL;  -- never reached
END;
$$;

CREATE TRIGGER trg_block_discussion_log_update
    BEFORE UPDATE ON discussion_log
    FOR EACH ROW
    EXECUTE FUNCTION fn_block_discussion_log_update();

-- ============================================================================
-- 5. APPEND-ONLY ENFORCEMENT — Block DELETE
-- ============================================================================
CREATE OR REPLACE FUNCTION fn_block_discussion_log_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'DELETE denied on discussion_log. This table is append-only. '
        'No deletion, dilution, or distortion permitted. Row id: %',
        OLD.id;
    RETURN NULL;  -- never reached
END;
$$;

CREATE TRIGGER trg_block_discussion_log_delete
    BEFORE DELETE ON discussion_log
    FOR EACH ROW
    EXECUTE FUNCTION fn_block_discussion_log_delete();

-- ============================================================================
-- 6. APPEND-ONLY ENFORCEMENT — Block TRUNCATE
-- ============================================================================
CREATE OR REPLACE FUNCTION fn_block_discussion_log_truncate()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'TRUNCATE denied on discussion_log. This table is append-only. '
        'No deletion, dilution, or distortion permitted.';
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_block_discussion_log_truncate
    BEFORE TRUNCATE ON discussion_log
    FOR EACH STATEMENT
    EXECUTE FUNCTION fn_block_discussion_log_truncate();

-- ============================================================================
-- 7. UPSERT TEMPLATE — INSERT ... ON CONFLICT DO NOTHING
--
-- The pipeline calls this every 4 hours. If the same (being_id, topic,
-- 4-hour window) combination already exists, the INSERT is silently skipped.
-- ============================================================================

-- TEMPLATE: Replace $1..$7 with actual parameter bindings in your application.
/*
INSERT INTO discussion_log (
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
    $7     -- metadata      (jsonb)       — e.g. '{"lever":"L2","cluster":"Automator","tags":["crm","pipeline"]}'
)
ON CONFLICT (dedup_hash) DO NOTHING;
*/

-- ============================================================================
-- 7a. CONCRETE EXAMPLE — runnable upsert with literal values
-- ============================================================================
INSERT INTO discussion_log (
    captured_at,
    being_id,
    session_id,
    topic,
    summary,
    raw_excerpt,
    metadata
)
VALUES (
    now(),
    'the-technologist',
    'session-abc-123',
    'Postgres append-only schema design',
    'Designed discussion_log table with dedup hash, append-only triggers, and GIN indexes for the 4-hour snapshot pipeline.',
    'No deletion, dilution, or distortion. The table must be append-only.',
    '{"lever": "L7", "cluster": "Builder", "tags": ["postgres", "schema", "ddl"]}'::jsonb
)
ON CONFLICT (dedup_hash) DO NOTHING;

-- ============================================================================
-- 8. UTILITY VIEWS (optional but useful)
-- ============================================================================

-- Recent discussions (last 24 hours) by being
CREATE OR REPLACE VIEW v_recent_discussions AS
SELECT
    id,
    captured_at,
    being_id,
    session_id,
    topic,
    summary,
    metadata,
    created_at
FROM discussion_log
WHERE captured_at >= now() - INTERVAL '24 hours'
ORDER BY captured_at DESC, being_id;

-- Topic frequency across all beings
CREATE OR REPLACE VIEW v_topic_frequency AS
SELECT
    topic,
    COUNT(*)        AS occurrence_count,
    COUNT(DISTINCT being_id) AS being_count,
    MIN(captured_at) AS first_seen,
    MAX(captured_at) AS last_seen
FROM discussion_log
GROUP BY topic
ORDER BY occurrence_count DESC;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
