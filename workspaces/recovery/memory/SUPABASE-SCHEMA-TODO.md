# Supabase Schema — Recovery Needs

## Current Tables
- `sai_contacts` — 169 contacts, CRM data

## Tables Needed for Contract Intelligence Engine

### `session_logs`
Track what Recovery does each session
```sql
CREATE TABLE session_logs (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now(),
  agent text,
  date date,
  session_type text,
  summary text,
  key_outcomes jsonb,
  next_steps jsonb
);
```

### `carrier_contracts`
Store contract rates per carrier/provider — the engine's brain
```sql
CREATE TABLE carrier_contracts (
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
```

### `recovery_cases`
Track individual recovery cases
```sql
CREATE TABLE recovery_cases (
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
  status text,
  notes text
);
```

### `pip_calculations`
Log each PIP fee schedule calculation
```sql
CREATE TABLE pip_calculations (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at timestamptz DEFAULT now(),
  case_id uuid REFERENCES recovery_cases(id),
  state text CHECK (state IN ('NJ', 'NY')),
  cpt_code text,
  description text,
  billed_amount numeric,
  fee_schedule_rate numeric,
  region text,
  daily_max_applies boolean,
  modifier_reduction numeric,
  allowed_amount numeric,
  carrier_paid numeric,
  balance numeric
);
```

---
_Created: 2026-02-28 | Ask Aiko or Mark to create these tables_
