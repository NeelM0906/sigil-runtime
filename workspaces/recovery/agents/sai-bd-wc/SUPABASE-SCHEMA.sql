-- WC Business Development CRM Tables
-- Run this in Supabase SQL Editor
-- Created: 2026-02-27

-- ============================================
-- PROSPECTS TABLE
-- Core table for all WC BD targets
-- ============================================

CREATE TABLE wc_prospects (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    prospect_code varchar(20) UNIQUE,  -- e.g., WC-BER-001
    
    -- Practice info
    practice_name varchar(255) NOT NULL,
    dba_name varchar(255),
    address text,
    city varchar(100),
    county varchar(50),
    state varchar(2) DEFAULT 'NJ',
    zip varchar(10),
    phone varchar(20),
    website varchar(255),
    
    -- Classification
    specialty varchar(50),  -- orthopedic, pain_management, asc, plastic_surgery
    practice_size_physicians int,
    practice_size_locations int,
    est_annual_revenue varchar(20),
    est_wc_cases_year int,
    network_status varchar(20),  -- fully_oon, mixed, mostly_in_network
    current_billing_co varchar(100),
    
    -- Contacts (primary)
    decision_maker_name varchar(100),
    decision_maker_title varchar(100),
    decision_maker_email varchar(255),
    decision_maker_phone varchar(20),
    
    -- Additional contacts
    practice_manager_name varchar(100),
    practice_manager_email varchar(255),
    billing_contact_name varchar(100),
    billing_contact_email varchar(255),
    
    -- BANKROLL scoring (0-100 total)
    score_budget int DEFAULT 0,           -- 0-15
    score_authority int DEFAULT 0,         -- 0-10
    score_need int DEFAULT 0,              -- 0-20
    score_knowledge int DEFAULT 0,         -- 0-10
    score_recovery_history int DEFAULT 0,  -- 0-10
    score_objections int DEFAULT 0,        -- 0-10
    score_lookback int DEFAULT 0,          -- 0-15
    score_legal_risk int DEFAULT 0,        -- 0-10
    score_total int GENERATED ALWAYS AS (
        score_budget + score_authority + score_need + score_knowledge + 
        score_recovery_history + score_objections + score_lookback + score_legal_risk
    ) STORED,
    
    -- Pipeline
    pipeline_stage varchar(20) DEFAULT 'suspect',  
    -- suspect, prospect, qualified, proposal, signed, active
    tier int,  -- 1, 2, 3, or null for disqualified
    
    -- Tracking
    prior_recovery_service boolean DEFAULT false,
    prior_recovery_service_name varchar(100),
    years_treating_wc int,
    
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
-- Track all outbound/inbound calls
-- ============================================

CREATE TABLE wc_call_log (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    prospect_id uuid REFERENCES wc_prospects(id),
    
    -- Call details
    call_timestamp timestamptz NOT NULL,
    call_duration_seconds int,
    call_direction varchar(10) DEFAULT 'outbound',  -- outbound, inbound
    phone_number_called varchar(20),
    
    -- Outcome codes:
    -- MEETING_BOOKED, CALLBACK_SCHEDULED, VOICEMAIL_LEFT, EMAIL_REQUESTED,
    -- GATEKEEPER_BLOCK, NOT_INTERESTED_DM, WRONG_NUMBER, NOT_IN_SERVICE, 
    -- LOW_WC_VOLUME, NO_ANSWER, BUSY
    outcome_code varchar(30) NOT NULL,
    
    -- Contact reached
    contact_name varchar(100),
    contact_role varchar(50),  -- receptionist, office_manager, billing_manager, physician, other
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
    agent_id varchar(50),  -- which AI agent made the call
    bland_call_id varchar(100)  -- Bland.ai call reference
);

-- ============================================
-- EMAIL LOG TABLE
-- Track email sequences and engagement
-- ============================================

CREATE TABLE wc_email_log (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    prospect_id uuid REFERENCES wc_prospects(id),
    
    -- Email details
    sent_at timestamptz NOT NULL,
    email_address varchar(255) NOT NULL,
    subject varchar(255),
    template_name varchar(50),  -- ucr_rate_1, lookback_1, case_study_1, etc.
    sequence_name varchar(50),  -- ucr_rate_campaign, lookback_campaign
    sequence_step int,
    
    -- Engagement
    opened boolean DEFAULT false,
    opened_at timestamptz,
    open_count int DEFAULT 0,
    clicked boolean DEFAULT false,
    clicked_at timestamptz,
    click_count int DEFAULT 0,
    replied boolean DEFAULT false,
    replied_at timestamptz,
    bounced boolean DEFAULT false,
    bounce_reason varchar(50),
    unsubscribed boolean DEFAULT false,
    
    -- Meta
    created_at timestamptz DEFAULT now(),
    message_id varchar(255)  -- ESP message ID
);

-- ============================================
-- MEETINGS TABLE
-- Track scheduled discovery/proposal calls
-- ============================================

CREATE TABLE wc_meetings (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    prospect_id uuid REFERENCES wc_prospects(id),
    
    -- Meeting details
    scheduled_at timestamptz NOT NULL,
    duration_minutes int DEFAULT 30,
    meeting_type varchar(20),  -- discovery, proposal, follow_up
    calendar_link varchar(500),
    video_link varchar(500),
    
    -- Attendees
    attendee_names text[],
    attendee_emails text[],
    
    -- Status: scheduled, completed, no_show, rescheduled, cancelled
    status varchar(20) DEFAULT 'scheduled',
    
    -- Outcome (post-meeting)
    outcome varchar(50),  -- qualified, proposal_requested, not_a_fit, needs_follow_up
    recovery_estimate_low decimal(12,2),
    recovery_estimate_high decimal(12,2),
    
    -- Notes
    prep_notes text,
    meeting_notes text,
    follow_up_actions text,
    
    -- Meta
    created_at timestamptz DEFAULT now(),
    completed_at timestamptz,
    rescheduled_to timestamptz,
    cancelled_reason varchar(255)
);

-- ============================================
-- INDEXES
-- ============================================

-- Prospects
CREATE INDEX idx_wc_prospects_county ON wc_prospects(county);
CREATE INDEX idx_wc_prospects_specialty ON wc_prospects(specialty);
CREATE INDEX idx_wc_prospects_pipeline_stage ON wc_prospects(pipeline_stage);
CREATE INDEX idx_wc_prospects_tier ON wc_prospects(tier);
CREATE INDEX idx_wc_prospects_score_total ON wc_prospects(score_total);
CREATE INDEX idx_wc_prospects_tags ON wc_prospects USING GIN (tags);
CREATE INDEX idx_wc_prospects_next_action ON wc_prospects(next_action_at);

-- Call log
CREATE INDEX idx_wc_call_log_prospect ON wc_call_log(prospect_id);
CREATE INDEX idx_wc_call_log_timestamp ON wc_call_log(call_timestamp);
CREATE INDEX idx_wc_call_log_outcome ON wc_call_log(outcome_code);

-- Email log
CREATE INDEX idx_wc_email_log_prospect ON wc_email_log(prospect_id);
CREATE INDEX idx_wc_email_log_sent ON wc_email_log(sent_at);

-- Meetings
CREATE INDEX idx_wc_meetings_prospect ON wc_meetings(prospect_id);
CREATE INDEX idx_wc_meetings_scheduled ON wc_meetings(scheduled_at);
CREATE INDEX idx_wc_meetings_status ON wc_meetings(status);

-- ============================================
-- TRIGGERS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER wc_prospects_updated_at
    BEFORE UPDATE ON wc_prospects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- VIEWS
-- ============================================

-- Pipeline summary by stage/tier/specialty
CREATE VIEW wc_pipeline_summary AS
SELECT 
    pipeline_stage,
    tier,
    specialty,
    county,
    count(*) as count,
    avg(score_total)::int as avg_score
FROM wc_prospects
WHERE pipeline_stage != 'disqualified'
GROUP BY pipeline_stage, tier, specialty, county
ORDER BY 
    CASE pipeline_stage 
        WHEN 'active' THEN 1
        WHEN 'signed' THEN 2
        WHEN 'proposal' THEN 3
        WHEN 'qualified' THEN 4
        WHEN 'prospect' THEN 5
        WHEN 'suspect' THEN 6
    END,
    tier;

-- Today's follow-ups (for daily call list)
CREATE VIEW wc_todays_followups AS
SELECT 
    p.*,
    c.outcome_code as last_call_outcome,
    c.call_timestamp as last_call_at,
    c.notes as last_call_notes
FROM wc_prospects p
LEFT JOIN LATERAL (
    SELECT outcome_code, call_timestamp, notes
    FROM wc_call_log 
    WHERE prospect_id = p.id 
    ORDER BY call_timestamp DESC 
    LIMIT 1
) c ON true
WHERE p.next_action_at::date <= CURRENT_DATE
  AND p.pipeline_stage NOT IN ('signed', 'active', 'disqualified')
ORDER BY p.tier NULLS LAST, p.score_total DESC;

-- Call activity summary (for metrics)
CREATE VIEW wc_call_activity AS
SELECT 
    date_trunc('day', call_timestamp) as call_date,
    outcome_code,
    count(*) as call_count,
    avg(call_duration_seconds)::int as avg_duration
FROM wc_call_log
WHERE call_timestamp >= now() - interval '30 days'
GROUP BY date_trunc('day', call_timestamp), outcome_code
ORDER BY call_date DESC, outcome_code;

-- High-priority prospects (Tier 1, not recently contacted)
CREATE VIEW wc_high_priority_prospects AS
SELECT *
FROM wc_prospects
WHERE tier = 1
  AND pipeline_stage IN ('suspect', 'prospect')
  AND (last_contact_at IS NULL OR last_contact_at < now() - interval '3 days')
ORDER BY score_total DESC;

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Calculate tier from score
CREATE OR REPLACE FUNCTION calculate_tier(score int)
RETURNS int AS $$
BEGIN
    IF score >= 80 THEN RETURN 1;
    ELSIF score >= 60 THEN RETURN 2;
    ELSIF score >= 40 THEN RETURN 3;
    ELSE RETURN NULL;  -- Disqualified
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Auto-set tier on insert/update
CREATE OR REPLACE FUNCTION auto_set_tier()
RETURNS TRIGGER AS $$
BEGIN
    NEW.tier = calculate_tier(
        NEW.score_budget + NEW.score_authority + NEW.score_need + NEW.score_knowledge + 
        NEW.score_recovery_history + NEW.score_objections + NEW.score_lookback + NEW.score_legal_risk
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER wc_prospects_auto_tier
    BEFORE INSERT OR UPDATE OF 
        score_budget, score_authority, score_need, score_knowledge,
        score_recovery_history, score_objections, score_lookback, score_legal_risk
    ON wc_prospects
    FOR EACH ROW
    EXECUTE FUNCTION auto_set_tier();

-- ============================================
-- SAMPLE DATA (for testing)
-- ============================================

-- Uncomment to insert test data:
/*
INSERT INTO wc_prospects (
    prospect_code, practice_name, city, county, phone, website,
    specialty, practice_size_physicians, est_wc_cases_year,
    decision_maker_name, decision_maker_title,
    score_budget, score_authority, score_need, score_knowledge,
    score_recovery_history, score_objections, score_lookback, score_legal_risk,
    pipeline_stage, source
) VALUES 
(
    'WC-BER-001', 'Bergen Orthopedic Associates', 'Hackensack', 'Bergen',
    '201-555-0101', 'https://bergenortho.com',
    'orthopedic', 5, 150,
    'Maria Rodriguez', 'Practice Administrator',
    12, 8, 16, 6, 4, 8, 12, 10,
    'suspect', 'manual'
),
(
    'WC-BER-002', 'Hackensack Pain Management', 'Hackensack', 'Bergen',
    '201-555-0102', 'https://hackensackpain.com',
    'pain_management', 3, 200,
    'Dr. James Chen', 'Medical Director',
    9, 10, 12, 4, 6, 6, 9, 10,
    'suspect', 'manual'
);
*/

-- ============================================
-- GRANTS (adjust as needed)
-- ============================================

-- For API access via service key (already has full access)
-- For anon key access (if needed for public dashboards):
-- GRANT SELECT ON wc_pipeline_summary TO anon;
-- GRANT SELECT ON wc_call_activity TO anon;
