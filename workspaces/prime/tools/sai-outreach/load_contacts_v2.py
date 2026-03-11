#!/usr/bin/env python3
"""
Sai's Outreach Arm - Load Contacts from Bland.ai CSV
Simplified version for the minimal table schema
"""

import os
import json
import csv
import sys
from pathlib import Path

# Load env
env_path = Path(__file__).resolve().parents[4] / ".env"
with env_path.open() as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

from supabase import create_client

supabase = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_SERVICE_KEY']
)

def parse_json_field(value):
    """Safely parse JSON from CSV field"""
    if not value or value == '-':
        return None
    try:
        return json.loads(value)
    except:
        return value

def determine_stage(outcome):
    """Map call outcome to pipeline stage"""
    if not outcome:
        return 'new'
    outcome = outcome.lower()
    if 'closed_won' in outcome:
        return 'closed_won'
    elif 'callback' in outcome or 'meeting' in outcome:
        return 'meeting_booked'
    elif 'needs_more' in outcome:
        return 'qualified'
    elif 'no_answer' in outcome or 'voicemail' in outcome:
        return 'contacted'
    else:
        return 'qualified'

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('BLAND_EXPORT_CSV')
    if not csv_path:
        raise SystemExit('Usage: load_contacts_v2.py /path/to/bland-export.csv or set BLAND_EXPORT_CSV')
    
    print(f"Parsing CSV: {csv_path}")
    
    success = 0
    errors = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse the nested JSON fields
            variables = parse_json_field(row.get('variables', '{}'))
            analysis = parse_json_field(row.get('analysis', '{}'))
            
            if isinstance(variables, str):
                try:
                    variables = json.loads(variables)
                except:
                    variables = {}
            
            if isinstance(analysis, str):
                try:
                    analysis = json.loads(analysis)
                except:
                    analysis = {}
            
            phone = row.get('to', '').strip()
            if not phone:
                continue
            
            # Only use columns that exist in the simplified table
            contact = {
                'phone': phone,
                'email': analysis.get('email') if isinstance(analysis, dict) else None,
                'first_name': variables.get('first_name') if isinstance(variables, dict) else None,
                'company': variables.get('company') if isinstance(variables, dict) else None,
                'location_city': variables.get('city') if isinstance(variables, dict) else None,
                'location_state': variables.get('state') if isinstance(variables, dict) else None,
                'source': 'bland_ai',
                'source_campaign': (variables.get('offer', '') or '')[:200] if isinstance(variables, dict) else None,
                'call_outcome': analysis.get('call_outcome') if isinstance(analysis, dict) else None,
                'close_confidence': analysis.get('close_confidence') if isinstance(analysis, dict) else None,
                'call_summary': row.get('summary', ''),
                'transcript': row.get('transcripts', ''),
                'raw_variables': json.dumps(variables) if variables else None,
                'raw_analysis': json.dumps(analysis) if analysis else None,
                'pipeline_stage': determine_stage(analysis.get('call_outcome') if isinstance(analysis, dict) else None),
                'sai_notes': f"Imported from Bland.ai",
                'next_action': 'Review and qualify'
            }
            
            # Clean up None values
            clean_contact = {k: v for k, v in contact.items() if v is not None and v != ''}
            
            try:
                result = supabase.table('sai_contacts').upsert(
                    clean_contact,
                    on_conflict='phone'
                ).execute()
                success += 1
                if success % 25 == 0:
                    print(f"✅ {success} contacts inserted...")
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"❌ Error for {phone}: {e}")
    
    print(f"\n✅ Success: {success} contacts")
    print(f"❌ Errors: {errors}")
    print("\nDone!")

if __name__ == '__main__':
    main()
