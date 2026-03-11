#!/usr/bin/env python3
"""
Import lawyers to Supabase CRM
Geographic segmentation: Austin/Dallas pilot
"""

import csv
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

if not supabase_url or not supabase_key:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    exit(1)

client = create_client(supabase_url, supabase_key)

# Check existing structure
print("Checking existing contacts...")
result = client.table('sai_contacts').select('*').limit(1).execute()
print(f"Existing records: {len(result.data)}")

if result.data:
    print(f"Columns: {list(result.data[0].keys())}")

# Read Austin lawyers
print("\nReading Austin lawyers...")
austin_lawyers = []
with open('../data/austin_lawyers.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Map to existing schema
        full_name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
        city = row.get('Contact City', '') or row.get('Company City', '')
        state = row.get('Contact State Abbr', '') or row.get('Company State Abbr', '')
        
        # Get phone (required field)
        phone = row.get('Contact Phone 1', '') or row.get('Contact Mobile Phone', '')
        
        # Skip if no phone number
        if not phone or phone.strip() == '':
            continue
        
        austin_lawyers.append({
            'first_name': full_name,  # Store full name since no last_name column
            'email': row.get('Email 1', ''),
            'phone': phone.strip(),
            'company': row.get('Company Name - Cleaned', ''),
            'location_city': city,
            'location_state': state,
            'source': 'seamless_ai',
            'source_campaign': 'austin_pilot_2026_02_28'
        })

print(f"Austin lawyers to import: {len(austin_lawyers)}")

# Read Dallas lawyers
print("\nReading Dallas lawyers...")
dallas_lawyers = []
with open('../data/dallas_lawyers.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Map to existing schema
        full_name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
        city = row.get('Contact City', '') or row.get('Company City', '')
        state = row.get('Contact State Abbr', '') or row.get('Company State Abbr', '')
        
        # Get phone (required field)
        phone = row.get('Contact Phone 1', '') or row.get('Contact Mobile Phone', '')
        
        # Skip if no phone number
        if not phone or phone.strip() == '':
            continue
        
        dallas_lawyers.append({
            'first_name': full_name,  # Store full name since no last_name column
            'email': row.get('Email 1', ''),
            'phone': phone.strip(),
            'company': row.get('Company Name - Cleaned', ''),
            'location_city': city,
            'location_state': state,
            'source': 'seamless_ai',
            'source_campaign': 'dallas_pilot_2026_02_28'
        })

print(f"Dallas lawyers to import: {len(dallas_lawyers)}")

# Combine for pilot
pilot_lawyers = austin_lawyers + dallas_lawyers
print(f"\nTotal pilot lawyers: {len(pilot_lawyers)}")

# Import in batches of 100, handling duplicates
print("\nImporting to Supabase in batches...")
batch_size = 100
total_imported = 0
skipped_duplicates = 0
skipped_invalid = 0

# Get existing phones from database
existing_phones = set()
result = client.table('sai_contacts').select('phone').execute()
for row in result.data:
    if row.get('phone'):
        existing_phones.add(row['phone'])

print(f"Existing phones in database: {len(existing_phones)}")

# Filter out duplicates and invalid phones
filtered_lawyers = []
seen_phones = set()
for lawyer in pilot_lawyers:
    phone = lawyer['phone']
    
    # Skip if phone already in database
    if phone in existing_phones:
        skipped_duplicates += 1
        continue
    
    # Skip if phone already seen in this batch
    if phone in seen_phones:
        skipped_duplicates += 1
        continue
    
    # Skip if phone looks invalid (contains letters or is too short)
    if any(c.isalpha() for c in phone) or len(phone) < 10:
        skipped_invalid += 1
        continue
    
    seen_phones.add(phone)
    filtered_lawyers.append(lawyer)

print(f"Skipped duplicates: {skipped_duplicates}")
print(f"Skipped invalid phones: {skipped_invalid}")
print(f"Remaining to import: {len(filtered_lawyers)}")

for i in range(0, len(filtered_lawyers), batch_size):
    batch = filtered_lawyers[i:i+batch_size]
    try:
        result = client.table('sai_contacts').insert(batch).execute()
        total_imported += len(batch)
        print(f"Batch {i//batch_size + 1}: {len(batch)} lawyers imported (Total: {total_imported})")
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR in batch {i//batch_size + 1}: {error_msg[:100]}")

print(f"\n=== IMPORT COMPLETE ===")
print(f"Total imported: {total_imported}")
print(f"Skipped (duplicates): {skipped_duplicates}")
print(f"Skipped (invalid phones): {skipped_invalid}")

# Verify final count
result = client.table('sai_contacts').select('id', count='exact').execute()
print(f"\nTotal contacts in database: {result.count}")
