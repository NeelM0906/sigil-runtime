-- Sai's Outreach CRM - Contact Management Table
-- Run this in Supabase SQL Editor or via psql

CREATE TABLE IF NOT EXISTS sai_contacts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Contact Info
    phone TEXT NOT NULL UNIQUE,
    email TEXT,
    first_name TEXT,
    last_name TEXT,
    company TEXT,
    role TEXT,
    location_city TEXT,
    location_state TEXT,
    location_country TEXT DEFAULT 'US',
    
    -- Source/Attribution
    source TEXT DEFAULT 'bland_ai',
    source_campaign TEXT,
    referrer TEXT,
    batch_id TEXT,
    
    -- Call History
    last_call_id TEXT,
    last_call_date TIMESTAMPTZ,
    total_calls INTEGER DEFAULT 1,
    call_outcome TEXT,
    
    -- Qualification
    is_decision_maker BOOLEAN,
    interested_in TEXT,
    pain_points JSONB,
    objections JSONB,
    
    -- Pipeline Status
    pipeline_stage TEXT DEFAULT 'new',
    appointment_time TIMESTAMPTZ,
    callback_time TIMESTAMPTZ,
    follow_up_date DATE,
    
    -- Insights
    motivation TEXT,
    desired_outcome TEXT,
    mission TEXT,
    vision TEXT,
    heroic_unique_identity TEXT,
    road_blocks TEXT,
    
    -- Scoring
    close_confidence INTEGER,
    budget_mentioned BOOLEAN DEFAULT FALSE,
    
    -- Full Data
    call_summary TEXT,
    transcript TEXT,
    raw_variables JSONB,
    raw_analysis JSONB,
    
    -- Sai's Notes
    sai_notes TEXT,
    next_action TEXT
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_sai_contacts_stage ON sai_contacts(pipeline_stage);
CREATE INDEX IF NOT EXISTS idx_sai_contacts_outcome ON sai_contacts(call_outcome);
CREATE INDEX IF NOT EXISTS idx_sai_contacts_appointment ON sai_contacts(appointment_time);
CREATE INDEX IF NOT EXISTS idx_sai_contacts_state ON sai_contacts(location_state);

-- Enable RLS but allow service key full access
ALTER TABLE sai_contacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service key has full access" ON sai_contacts
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Grant permissions
GRANT ALL ON sai_contacts TO authenticated;
GRANT ALL ON sai_contacts TO service_role;
