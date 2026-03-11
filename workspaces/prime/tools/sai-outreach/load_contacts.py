#!/usr/bin/env python3
"""
Sai's Outreach Arm - Load Contacts from Bland.ai CSV
Parses call export and loads into Supabase
"""

import os
import json
import csv
import sys
from pathlib import Path
from datetime import datetime

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

def parse_bland_csv(csv_path):
    """Parse Bland.ai call export CSV"""
    contacts = []
    
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
            
            # Extract contact info
            phone = row.get('to', '').strip()
            if not phone:
                continue
                
            # Build contact record
            contact = {
                'phone': phone,
                'email': analysis.get('email') if isinstance(analysis, dict) else None,
                'first_name': variables.get('first_name') if isinstance(variables, dict) else None,
                'company': variables.get('company') if isinstance(variables, dict) else None,
                'location_city': variables.get('city') if isinstance(variables, dict) else None,
                'location_state': variables.get('state') if isinstance(variables, dict) else None,
                'location_country': variables.get('country', 'US') if isinstance(variables, dict) else 'US',
                
                'source': 'bland_ai',
                'source_campaign': variables.get('offer', '')[:200] if isinstance(variables, dict) else None,
                'batch_id': row.get('batch_id') if row.get('batch_id') != '-' else None,
                
                'last_call_id': row.get('call_id') if isinstance(variables, dict) else None,
                'last_call_date': variables.get('timestamp') if isinstance(variables, dict) else None,
                'call_outcome': analysis.get('call_outcome') if isinstance(analysis, dict) else None,
                
                'is_decision_maker': analysis.get('decision_maker') if isinstance(analysis, dict) else None,
                'interested_in': analysis.get('interested_in') if isinstance(analysis, dict) else None,
                'pain_points': json.dumps(analysis.get('pain_points', [])) if isinstance(analysis, dict) else None,
                'objections': json.dumps(analysis.get('objections', [])) if isinstance(analysis, dict) else None,
                
                'close_confidence': analysis.get('close_confidence') if isinstance(analysis, dict) else None,
                'budget_mentioned': analysis.get('budget_mentioned', False) if isinstance(analysis, dict) else False,
                
                'motivation': variables.get('motivation') if isinstance(variables, dict) else None,
                'desired_outcome': variables.get('desired_outcome') if isinstance(variables, dict) else None,
                'mission': variables.get('mission') if isinstance(variables, dict) else None,
                'vision': variables.get('vision') if isinstance(variables, dict) else None,
                'heroic_unique_identity': variables.get('heroic_unique_identity', '')[:500] if isinstance(variables, dict) else None,
                'road_blocks': variables.get('road_block') if isinstance(variables, dict) else None,
                
                'call_summary': row.get('summary', ''),
                'transcript': row.get('transcripts', ''),
                
                'raw_variables': json.dumps(variables) if variables else None,
                'raw_analysis': json.dumps(analysis) if analysis else None,
                
                # Determine pipeline stage based on outcome
                'pipeline_stage': determine_stage(analysis.get('call_outcome') if isinstance(analysis, dict) else None),
                
                # Extract appointment info
                'appointment_time': analysis.get('appointment_time') if isinstance(analysis, dict) else None,
                'callback_time': analysis.get('callback_time') if isinstance(analysis, dict) else None,
            }
            
            # Add Sai's initial notes
            outcome = analysis.get('call_outcome', 'unknown') if isinstance(analysis, dict) else 'unknown'
            confidence = analysis.get('close_confidence', 0) if isinstance(analysis, dict) else 0
            contact['sai_notes'] = f"Imported from Bland.ai. Outcome: {outcome}, Confidence: {confidence}/10"
            
            # Determine next action
            contact['next_action'] = determine_next_action(contact)
            
            contacts.append(contact)
    
    return contacts

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

def determine_next_action(contact):
    """Determine next action based on contact data"""
    stage = contact.get('pipeline_stage', 'new')
    
    if stage == 'meeting_booked':
        appt = contact.get('appointment_time')
        if appt:
            return f"Prepare for meeting: {appt}"
        return "Confirm meeting time"
    elif stage == 'qualified':
        return "Follow up call to address objections"
    elif stage == 'closed_won':
        return "Onboarding sequence"
    elif stage == 'contacted':
        return "Re-attempt call"
    else:
        return "Initial qualification call"

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('BLAND_EXPORT_CSV')
    if not csv_path:
        raise SystemExit('Usage: load_contacts.py /path/to/bland-export.csv or set BLAND_EXPORT_CSV')
    
    print(f"Parsing CSV: {csv_path}")
    contacts = parse_bland_csv(csv_path)
    print(f"Found {len(contacts)} contacts")
    
    # Print summary of each contact
    for i, c in enumerate(contacts, 1):
        print(f"\n--- Contact {i} ---")
        print(f"Phone: {c['phone']}")
        print(f"Name: {c['first_name']}")
        print(f"Company: {c['company']}")
        print(f"Location: {c['location_city']}, {c['location_state']}")
        print(f"Outcome: {c['call_outcome']}")
        print(f"Stage: {c['pipeline_stage']}")
        print(f"Confidence: {c['close_confidence']}")
        print(f"Next Action: {c['next_action']}")
        if c['pain_points']:
            print(f"Pain Points: {c['pain_points'][:100]}...")
    
    # Try to insert into Supabase
    print("\n\nAttempting to insert into Supabase...")
    
    for contact in contacts:
        try:
            # Clean up None values and empty strings
            clean_contact = {k: v for k, v in contact.items() if v is not None and v != ''}
            
            result = supabase.table('sai_contacts').upsert(
                clean_contact,
                on_conflict='phone'
            ).execute()
            print(f"✅ Inserted/Updated: {contact['phone']}")
        except Exception as e:
            print(f"❌ Error for {contact['phone']}: {e}")
    
    print("\nDone!")

if __name__ == '__main__':
    main()
