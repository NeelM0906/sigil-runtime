#!/usr/bin/env python3
"""
Zoom Recording Access Tool for Danny's Elite Sessions
Zone Action #76: Access and analyze Danny's elite recording files using Prime's Zoom API credentials.
Extract critical Sean mastery patterns for immediate judge calibration improvement.
"""

import os
import requests
import json
from datetime import datetime, timedelta
import base64

class ZoomRecordingAccess:
    def __init__(self):
        self.account_id = os.getenv('ZOOM_ACCOUNT_ID')
        self.client_id = os.getenv('ZOOM_CLIENT_ID') 
        self.client_secret = os.getenv('ZOOM_CLIENT_SECRET')
        self.access_token = None
        self.base_url = 'https://api.zoom.us/v2'
        
    def get_access_token(self):
        """Get OAuth 2.0 access token using Server-to-Server OAuth"""
        auth_url = f'https://zoom.us/oauth/token?grant_type=account_credentials&account_id={self.account_id}'
        
        # Encode client credentials
        credentials = base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(auth_url, headers=headers)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            print(f"✅ Successfully obtained access token")
            return True
        else:
            print(f"❌ Failed to get access token: {response.status_code} - {response.text}")
            return False
    
    def get_api_headers(self):
        """Get headers for API requests"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def search_users(self, email_pattern="danny"):
        """Search for users matching Danny"""
        if not self.access_token:
            if not self.get_access_token():
                return None
                
        url = f'{self.base_url}/users'
        headers = self.get_api_headers()
        
        response = requests.get(url, headers=headers, params={'page_size': 300})
        
        if response.status_code == 200:
            users = response.json()
            danny_users = []
            
            for user in users.get('users', []):
                if 'danny' in user.get('email', '').lower() or 'danny' in user.get('first_name', '').lower():
                    danny_users.append(user)
            
            print(f"🔍 Found {len(danny_users)} users matching 'Danny':")
            for user in danny_users:
                print(f"   📧 {user.get('email')} - {user.get('first_name', '')} {user.get('last_name', '')}")
                print(f"      ID: {user.get('id')}")
            
            return danny_users
        else:
            print(f"❌ Failed to search users: {response.status_code} - {response.text}")
            return None
    
    def get_account_recordings(self, from_date=None, to_date=None):
        """Get all account-level recordings"""
        if not self.access_token:
            if not self.get_access_token():
                return None
        
        # Default to last 6 months
        if not from_date:
            from_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        url = f'{self.base_url}/accounts/{self.account_id}/recordings'
        headers = self.get_api_headers()
        
        params = {
            'from': from_date,
            'to': to_date,
            'page_size': 300
        }
        
        all_recordings = []
        
        while url:
            response = requests.get(url, headers=headers, params=params if 'accounts' in url else None)
            
            if response.status_code == 200:
                data = response.json()
                meetings = data.get('meetings', [])
                all_recordings.extend(meetings)
                
                # Check for next page
                next_page_token = data.get('next_page_token')
                if next_page_token:
                    params['next_page_token'] = next_page_token
                    url = f'{self.base_url}/accounts/{self.account_id}/recordings'
                else:
                    url = None
            else:
                print(f"❌ Failed to get recordings: {response.status_code} - {response.text}")
                break
        
        return all_recordings
    
    def get_user_recordings(self, user_id, from_date=None, to_date=None):
        """Get recordings for a specific user"""
        if not self.access_token:
            if not self.get_access_token():
                return None
        
        # Default to last 6 months  
        if not from_date:
            from_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
            
        url = f'{self.base_url}/users/{user_id}/recordings'
        headers = self.get_api_headers()
        
        params = {
            'from': from_date,
            'to': to_date,
            'page_size': 300
        }
        
        all_recordings = []
        
        while url:
            response = requests.get(url, headers=headers, params=params if 'users' in url else None)
            
            if response.status_code == 200:
                data = response.json()
                meetings = data.get('meetings', [])
                all_recordings.extend(meetings)
                
                # Check for next page
                next_page_token = data.get('next_page_token')
                if next_page_token:
                    params['next_page_token'] = next_page_token
                    url = f'{self.base_url}/users/{user_id}/recordings'
                else:
                    url = None
            else:
                print(f"❌ Failed to get user recordings: {response.status_code} - {response.text}")
                break
        
        return all_recordings
    
    def filter_elite_recordings(self, recordings):
        """Filter recordings for elite/mastery content"""
        elite_keywords = [
            'elite', 'mastery', 'immersion', 'formula', 'sean', 'callagy', 
            'influence', 'leadership', 'unblinded', 'process mastery',
            'summit', 'vip', 'inner circle', 'coaching', 'strategic'
        ]
        
        elite_recordings = []
        
        for meeting in recordings:
            topic = meeting.get('topic', '').lower()
            
            # Check if topic contains elite keywords
            if any(keyword in topic for keyword in elite_keywords):
                # Check duration - elite sessions typically longer
                if meeting.get('duration', 0) > 30:  # At least 30 minutes
                    elite_recordings.append(meeting)
        
        return elite_recordings
    
    def analyze_recording_patterns(self, recordings):
        """Extract Sean mastery patterns from recording metadata"""
        print(f"\n📊 ANALYZING {len(recordings)} RECORDINGS FOR SEAN MASTERY PATTERNS")
        print("="*80)
        
        patterns = {
            'duration_analysis': {},
            'topic_patterns': {},
            'participant_insights': {},
            'elite_sessions': []
        }
        
        total_duration = 0
        for recording in recordings:
            duration = recording.get('duration', 0)
            total_duration += duration
            
            # Duration analysis
            if duration > 180:  # 3+ hours = deep immersion
                category = 'deep_immersion'
            elif duration > 90:  # 1.5-3 hours = intensive
                category = 'intensive'
            elif duration > 30:  # 30min-1.5hr = standard
                category = 'standard'
            else:
                category = 'brief'
            
            patterns['duration_analysis'][category] = patterns['duration_analysis'].get(category, 0) + 1
            
            # Topic pattern analysis
            topic = recording.get('topic', '').lower()
            for keyword in ['formula', 'mastery', 'influence', 'leadership', 'immersion']:
                if keyword in topic:
                    patterns['topic_patterns'][keyword] = patterns['topic_patterns'].get(keyword, 0) + 1
            
            # Elite session identification
            if self.is_elite_recording(recording):
                patterns['elite_sessions'].append({
                    'topic': recording.get('topic'),
                    'duration': duration,
                    'start_time': recording.get('start_time'),
                    'participant_count': recording.get('participant_count', 0),
                    'recording_files': len(recording.get('recording_files', []))
                })
        
        # Print analysis
        print(f"📈 TOTAL RECORDINGS ANALYZED: {len(recordings)}")
        print(f"⏱️  TOTAL CONTENT TIME: {total_duration} minutes ({total_duration/60:.1f} hours)")
        print(f"🎯 ELITE SESSIONS FOUND: {len(patterns['elite_sessions'])}")
        
        print(f"\n📊 DURATION PATTERNS:")
        for category, count in patterns['duration_analysis'].items():
            print(f"   {category.replace('_', ' ').title()}: {count} sessions")
        
        print(f"\n🔍 TOPIC PATTERNS:")
        for topic, count in patterns['topic_patterns'].items():
            print(f"   '{topic}' mentioned: {count} times")
        
        print(f"\n⭐ TOP ELITE SESSIONS:")
        sorted_elite = sorted(patterns['elite_sessions'], key=lambda x: x['duration'], reverse=True)
        for i, session in enumerate(sorted_elite[:5]):
            print(f"   {i+1}. {session['topic']} ({session['duration']}min, {session['participant_count']} participants)")
        
        return patterns
    
    def is_elite_recording(self, recording):
        """Determine if this is an elite/mastery recording"""
        topic = recording.get('topic', '').lower()
        duration = recording.get('duration', 0)
        
        # Elite criteria
        elite_keywords = ['elite', 'mastery', 'immersion', 'formula', 'leadership', 'influence', 'vip', 'inner circle']
        has_elite_keyword = any(keyword in topic for keyword in elite_keywords)
        is_substantial = duration > 45  # At least 45 minutes
        
        return has_elite_keyword and is_substantial
    
    def download_recording_file(self, download_url, file_name):
        """Download a recording file"""
        if not self.access_token:
            return False
        
        headers = self.get_api_headers()
        response = requests.get(download_url, headers=headers)
        
        if response.status_code == 200:
            with open(file_name, 'wb') as f:
                f.write(response.content)
            print(f"✅ Downloaded: {file_name}")
            return True
        else:
            print(f"❌ Failed to download {file_name}: {response.status_code}")
            return False

def main():
    print("🚀 ACCESSING DANNY'S ELITE RECORDINGS - ZONE ACTION #76")
    print("="*60)
    
    zoom = ZoomRecordingAccess()
    
    # Step 1: Get access token
    if not zoom.get_access_token():
        return
    
    # Step 2: Search for Danny users
    print("\n🔍 SEARCHING FOR DANNY...")
    danny_users = zoom.search_users()
    
    if not danny_users:
        print("⚠️  No users found matching 'Danny' - checking account-level recordings...")
        danny_users = []
    
    # Step 3: Get recordings from account level (comprehensive search)
    print(f"\n📹 GETTING ACCOUNT RECORDINGS...")
    account_recordings = zoom.get_account_recordings()
    
    if account_recordings:
        print(f"✅ Found {len(account_recordings)} total recordings")
        
        # Filter for elite content
        elite_recordings = zoom.filter_elite_recordings(account_recordings)
        print(f"⭐ Found {len(elite_recordings)} elite recordings")
        
        # Analyze patterns
        patterns = zoom.analyze_recording_patterns(elite_recordings)
        
        # Save results
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_recordings': len(account_recordings),
            'elite_recordings': len(elite_recordings),
            'patterns': patterns,
            'elite_sessions': elite_recordings[:10]  # Top 10 for detailed review
        }
        
        with open('danny_elite_recordings_analysis.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ ANALYSIS COMPLETE - RESULTS SAVED TO 'danny_elite_recordings_analysis.json'")
        
    # Step 4: Check individual Danny user recordings if found
    for user in danny_users:
        print(f"\n👤 CHECKING RECORDINGS FOR: {user.get('email')}")
        user_recordings = zoom.get_user_recordings(user.get('id'))
        
        if user_recordings:
            print(f"   📹 Found {len(user_recordings)} recordings")
            user_elite = zoom.filter_elite_recordings(user_recordings)
            print(f"   ⭐ {len(user_elite)} elite sessions")

if __name__ == "__main__":
    main()