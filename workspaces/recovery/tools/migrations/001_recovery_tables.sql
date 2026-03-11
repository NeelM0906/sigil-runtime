-- SAI Recovery — Database Migration 001
-- Run this in Supabase Dashboard > SQL Editor
-- URL: https://supabase.com/dashboard/project/yncbtzqrherwyeybchet/sql

-- ─── CARRIER CONTRACTS ──────────────────────────────────────────
-- The engine's brain: stores contract rates per carrier/provider
CREATE TABLE IF NOT EXISTS carrier_contracts (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now(),
  carrier_name text NOT NULL,
  provider_name text,
  provider_npi text,
  cpt_code text NOT NULL,
  rate numeric,
  modifier text,
  effective_date date,
  expiration_date date,
  notes text
);

-- ─── RECOVERY CASES ─────────────────────────────────────────────
-- Individual case tracking
CREATE TABLE IF NOT EXISTS recovery_cases (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now(),
  case_number text,
  provider_name text,
  carrier_name text,
  date_of_service date,
  total_billed numeric,
  contract_allowed numeric,
  carrier_paid numeric,
  balance_due numeric,
  settlement_offered numeric,
  settlement_percentage numeric,
  status text DEFAULT 'open',
  notes text
);

-- ─── PIP CALCULATIONS ───────────────────────────────────────────
-- Log of every PIP fee schedule calculation run
CREATE TABLE IF NOT EXISTS pip_calculations (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now(),
  case_id uuid REFERENCES recovery_cases(id),
  state text CHECK (state IN ('NJ', 'NY')),
  cpt_code text,
  description text,
  billed_amount numeric,
  fee_schedule_rate numeric,
  region text,
  daily_max_applies boolean DEFAULT false,
  modifier_reduction numeric DEFAULT 0,
  allowed_amount numeric,
  carrier_paid numeric,
  balance numeric
);

-- ─── SESSION LOGS ───────────────────────────────────────────────
-- Track what Recovery does each session
CREATE TABLE IF NOT EXISTS session_logs (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now(),
  agent text DEFAULT 'sai-recovery',
  date date,
  session_type text,
  summary text,
  key_outcomes jsonb,
  next_steps jsonb
);
