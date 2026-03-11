#!/usr/bin/env python3
"""
Sai's Outreach Arm - Contact Management
Creates and populates contacts table from Bland.ai call exports
"""

import os
import json
import csv
from datetime import datetime

# Load env
env_path = "~/.openclaw/workspace-forge/.env"
with open(env_path) as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

from supabase import create_client

supabase = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_SERVICE_KEY']
)

print("Connected to Supabase!")
print(f"URL: {os.environ['SUPABASE_URL']}")

# Test connection by listing tables
try:
    # Simple test query
    result = supabase.table('sai_contacts').select('id').limit(1).execute()
    print(f"sai_contacts table exists! Records: checking...")
except Exception as e:
    print(f"Table doesn't exist yet or error: {e}")
    print("\nNeed to create table via Supabase dashboard SQL editor:")
    print("""
CREATE TABLE sai_contacts (
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

CREATE INDEX idx_sai_contacts_stage ON sai_contacts(pipeline_stage);
CREATE INDEX idx_sai_contacts_outcome ON sai_contacts(call_outcome);
CREATE INDEX idx_sai_contacts_appointment ON sai_contacts(appointment_time);
CREATE INDEX idx_sai_contacts_state ON sai_contacts(location_state);
""")

print("\nSetup script ready!")
