-- PIP Business Development CRM Tables
-- Run this in Supabase SQL Editor
-- Created: 2026-02-27
-- Adapted from WC BD schema for PIP arbitration services

-- ============================================
-- PROSPECTS TABLE
-- Core table for all PIP BD targets
-- ============================================

CREATE TABLE pip_prospects (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    prospect_code varchar(20) UNIQUE,  -- e.g., PIP-BER-001
    
    -- Practice info
    practice_name varchar(255) NOT NULL,
    dba_name varchar(255),
    address text,
    city varchar(100),
    county varchar(50),
    state varchar(2) NOT NULL,  -- NJ or NY
    zip varchar(10),
    phone varchar(20),
    website varchar(255),
    
    -- Classification
    specialty varchar(50),  -- emergency_medicine, orthopedic, urgent_care, trauma_center
    practice_type varchar(30),  -- private, hospital_based, urgent_care
    practice_size_physicians int,
    practice_size_locations int,
    est_annual_revenue varchar(20),
    est_auto_accident_pct int,  -- Percentage of patients that are auto accident
    est_annual_pip_billing decimal(12,2),
    
    -- Contacts (primary)
    decision_maker_name varchar(100),
    decision_maker_title varchar(100),
    decision_maker_email varchar(255),
    decision_maker_phone varchar(20),
    
    -- Additional contacts
    billing_manager_name varchar(100),
    billing_manager_email varchar(255),
    revenue_cycle_contact varchar(100),
    
    -- PIP-specific scoring (adapted from BANKROLL)
    score_volume int DEFAULT 0,           -- 0-20 (auto accident volume)
    score_authority int DEFAULT 0,         -- 0-10 (decision maker access)
    score_aging int DEFAULT 0,             -- 0-20 (outstanding AR over 60/30 days)
    score_awareness int DEFAULT 0,         -- 0-10 (understands arbitration opportunity)
    score_prior_experience int DEFAULT 0,  -- 0-10 (prior arbitration experience)
    score_objections int DEFAULT 0,        -- 0-10 (manageable concerns)
    score_data_access int DEFAULT 0,       -- 0-10 (can provide billing data easily)
    score_legal_clean int DEFAULT 0,       -- 0-10 (no compliance issues)
    score_total int GENERATED ALWAYS AS (
        score_volume + score_authority + score_aging + score_awareness + 
        score_prior_experience + score_objections + score_data_access + score_legal_clean
    ) STORED,
    
    -- Pipeline
    pipeline_stage varchar(20) DEFAULT 'suspect',  
    -- suspect, prospect, qualified, proposal, signed, active
    tier int,  -- 1, 2, 3, or null for disqualified
    
    -- Tracking
    prior_arbitration_service boolean DEFAULT false,
    prior_arbitration_service_name varchar(100),
    current_pip_ar_outstanding decimal(12,2),  -- Estimated outstanding PIP AR
    
    -- Meta
    notes text,
    tags varchar[] DEFAULT '{}',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    last_contact_at timestamptz,
    next_action_at timestamptz,
    next_action varchar(255),
    
    -- Source tracking
    source varchar(50),  -- manual, scrape, referral, inbound
    source_detail varchar(255)
);

-- ============================================
-- CALL LOG TABLE
-- ============================================

CREATE TABLE pip_call_log (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    prospect_id uuid REFERENCES pip_prospects(id),
    
    -- Call details
    call_timestamp timestamptz NOT NULL,
    call_duration_seconds int,
    call_direction varchar(10) DEFAULT 'outbound',
    phone_number_called varchar(20),
    
    -- Outcome
    outcome_code varchar(30) NOT NULL,
    
    -- Contact reached
    contact_name varchar(100),
    contact_role varchar(50),
    contact_email varchar(255),
    
    -- Meeting (if booked)
    meeting_datetime timestamptz,
    meeting_notes text,
    
    -- Next steps
    next_action varchar(255),
    next_action_at timestamptz,
    follow_up_scheduled boolean DEFAULT false,
    
    -- Recording
    recording_url text,
    transcript text,
    
    -- Notes
    notes text,
    objections_raised varchar[],
    
    -- Meta
    created_at timestamptz DEFAULT now(),
    agent_id varchar(50),
    bland_call_id varchar(100)
);

-- ============================================
-- EMAIL LOG TABLE
-- ============================================

CREATE TABLE pip_email_log (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    prospect_id uuid REFERENCES pip_prospects(id),
    
    sent_at timestamptz NOT NULL,
    email_address varchar(255) NOT NULL,
    subject varchar(255),
    template_name varchar(50),
    sequence_name varchar(50),
    sequence_step int,
    
    -- Engagement
    opened boolean DEFAULT false,
    opened_at timestamptz,
    clicked boolean DEFAULT false,
    clicked_at timestamptz,
    replied boolean DEFAULT false,
    replied_at timestamptz,
    bounced boolean DEFAULT false,
    unsubscribed boolean DEFAULT false,
    
    created_at timestamptz DEFAULT now()
);

-- ============================================
-- MEETINGS TABLE
-- ============================================

CREATE TABLE pip_meetings (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    prospect_id uuid REFERENCES pip_prospects(id),
    
    scheduled_at timestamptz NOT NULL,
    duration_minutes int DEFAULT 30,
    meeting_type varchar(20),
    
    attendee_names text[],
    attendee_emails text[],
    
    status varchar(20) DEFAULT 'scheduled',
    
    -- Outcome
    outcome varchar(50),
    estimated_pip_ar decimal(12,2),
    estimated_recovery decimal(12,2),
    
    -- Notes
    prep_notes text,
    meeting_notes text,
    follow_up_actions text,
    
    created_at timestamptz DEFAULT now(),
    completed_at timestamptz
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX idx_pip_prospects_state ON pip_prospects(state);
CREATE INDEX idx_pip_prospects_county ON pip_prospects(county);
CREATE INDEX idx_pip_prospects_specialty ON pip_prospects(specialty);
CREATE INDEX idx_pip_prospects_pipeline ON pip_prospects(pipeline_stage);
CREATE INDEX idx_pip_prospects_tier ON pip_prospects(tier);
CREATE INDEX idx_pip_prospects_score ON pip_prospects(score_total);
CREATE INDEX idx_pip_prospects_next_action ON pip_prospects(next_action_at);

CREATE INDEX idx_pip_call_log_prospect ON pip_call_log(prospect_id);
CREATE INDEX idx_pip_call_log_timestamp ON pip_call_log(call_timestamp);
CREATE INDEX idx_pip_call_log_outcome ON pip_call_log(outcome_code);

CREATE INDEX idx_pip_email_log_prospect ON pip_email_log(prospect_id);
CREATE INDEX idx_pip_meetings_prospect ON pip_meetings(prospect_id);
CREATE INDEX idx_pip_meetings_scheduled ON pip_meetings(scheduled_at);

-- ============================================
-- TRIGGERS
-- ============================================

CREATE TRIGGER pip_prospects_updated_at
    BEFORE UPDATE ON pip_prospects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Auto-set tier from score
CREATE OR REPLACE FUNCTION pip_auto_set_tier()
RETURNS TRIGGER AS $$
BEGIN
    IF (NEW.score_volume + NEW.score_authority + NEW.score_aging + NEW.score_awareness + 
        NEW.score_prior_experience + NEW.score_objections + NEW.score_data_access + NEW.score_legal_clean) >= 80 THEN
        NEW.tier = 1;
    ELSIF (NEW.score_volume + NEW.score_authority + NEW.score_aging + NEW.score_awareness + 
           NEW.score_prior_experience + NEW.score_objections + NEW.score_data_access + NEW.score_legal_clean) >= 60 THEN
        NEW.tier = 2;
    ELSIF (NEW.score_volume + NEW.score_authority + NEW.score_aging + NEW.score_awareness + 
           NEW.score_prior_experience + NEW.score_objections + NEW.score_data_access + NEW.score_legal_clean) >= 40 THEN
        NEW.tier = 3;
    ELSE
        NEW.tier = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER pip_prospects_auto_tier
    BEFORE INSERT OR UPDATE OF 
        score_volume, score_authority, score_aging, score_awareness,
        score_prior_experience, score_objections, score_data_access, score_legal_clean
    ON pip_prospects
    FOR EACH ROW
    EXECUTE FUNCTION pip_auto_set_tier();

-- ============================================
-- VIEWS
-- ============================================

CREATE VIEW pip_pipeline_summary AS
SELECT 
    pipeline_stage,
    tier,
    specialty,
    state,
    county,
    count(*) as count,
    avg(score_total)::int as avg_score,
    sum(est_annual_pip_billing) as total_pip_billing
FROM pip_prospects
WHERE pipeline_stage != 'disqualified'
GROUP BY pipeline_stage, tier, specialty, state, county
ORDER BY tier, pipeline_stage;

CREATE VIEW pip_todays_followups AS
SELECT 
    p.*,
    c.outcome_code as last_call_outcome,
    c.call_timestamp as last_call_at
FROM pip_prospects p
LEFT JOIN LATERAL (
    SELECT outcome_code, call_timestamp
    FROM pip_call_log 
    WHERE prospect_id = p.id 
    ORDER BY call_timestamp DESC 
    LIMIT 1
) c ON true
WHERE p.next_action_at::date <= CURRENT_DATE
  AND p.pipeline_stage NOT IN ('signed', 'active', 'disqualified')
ORDER BY p.tier NULLS LAST, p.score_total DESC;

CREATE VIEW pip_high_priority AS
SELECT *
FROM pip_prospects
WHERE tier = 1
  AND pipeline_stage IN ('suspect', 'prospect')
  AND (last_contact_at IS NULL OR last_contact_at < now() - interval '3 days')
ORDER BY score_total DESC;

-- ============================================
-- NJ vs NY specific views
-- ============================================

CREATE VIEW pip_nj_prospects AS
SELECT * FROM pip_prospects WHERE state = 'NJ';

CREATE VIEW pip_ny_prospects AS
SELECT * FROM pip_prospects WHERE state = 'NY';
