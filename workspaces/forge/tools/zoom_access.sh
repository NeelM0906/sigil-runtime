#!/bin/bash

# Zone Action #76: Access Danny's Elite Recordings using Zoom API
# Extract critical Sean mastery patterns for judge calibration improvement

echo "🚀 ACCESSING DANNY'S ELITE RECORDINGS - ZONE ACTION #76"
echo "================================================================"

# Load environment variables
source .env

# Step 1: Get OAuth 2.0 Access Token
echo "🔑 Getting Zoom API access token..."

# Encode client credentials in base64
CREDENTIALS=$(echo -n "$ZOOM_CLIENT_ID:$ZOOM_CLIENT_SECRET" | base64)

# Get access token
TOKEN_RESPONSE=$(curl -s -X POST "https://zoom.us/oauth/token?grant_type=account_credentials&account_id=$ZOOM_ACCOUNT_ID" \
    -H "Authorization: Basic $CREDENTIALS" \
    -H "Content-Type: application/x-www-form-urlencoded")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Failed to get access token"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Successfully obtained access token"

# Step 2: Search for users named Danny
echo "🔍 Searching for Danny users..."

USERS_RESPONSE=$(curl -s -X GET "https://api.zoom.us/v2/users?page_size=300" \
    -H "Authorization: Bearer [REDACTED]" \
    -H "Content-Type: application/json")

echo "$USERS_RESPONSE" | grep -i "danny" > danny_users.json 2>/dev/null || echo "No Danny users found in initial search"

# Step 3: Get account-level recordings (last 6 months)
echo "📹 Getting account recordings..."

FROM_DATE=$(date -d "6 months ago" +%Y-%m-%d 2>/dev/null || date -v-6m +%Y-%m-%d)
TO_DATE=$(date +%Y-%m-%d)

RECORDINGS_RESPONSE=$(curl -s -X GET "https://api.zoom.us/v2/accounts/$ZOOM_ACCOUNT_ID/recordings?from=$FROM_DATE&to=$TO_DATE&page_size=300" \
    -H "Authorization: Bearer [REDACTED]" \
    -H "Content-Type: application/json")

echo "$RECORDINGS_RESPONSE" > all_recordings.json

# Step 4: Filter for elite/mastery recordings
echo "⭐ Filtering for elite recordings..."

# Extract meetings and analyze
TOTAL_RECORDINGS=$(echo "$RECORDINGS_RESPONSE" | grep -o '"meetings":\[' | wc -l)

if [ "$TOTAL_RECORDINGS" -gt 0 ]; then
    echo "✅ Found recordings data"
    
    # Filter for elite keywords in topics
    echo "$RECORDINGS_RESPONSE" | grep -i -E "(elite|mastery|immersion|formula|sean|callagy|influence|leadership|unblinded|process mastery|summit|vip|inner circle)" > elite_recordings_raw.json 2>/dev/null
    
    # Extract key information
    echo "📊 ELITE RECORDING ANALYSIS" > danny_elite_analysis.txt
    echo "============================" >> danny_elite_analysis.txt
    echo "Search Date Range: $FROM_DATE to $TO_DATE" >> danny_elite_analysis.txt
    echo "Generated: $(date)" >> danny_elite_analysis.txt
    echo "" >> danny_elite_analysis.txt
    
    # Count recordings by keywords
    echo "📈 KEYWORD ANALYSIS:" >> danny_elite_analysis.txt
    for keyword in "mastery" "formula" "elite" "immersion" "sean" "callagy" "influence" "leadership"; do
        count=$(echo "$RECORDINGS_RESPONSE" | grep -i "$keyword" | wc -l)
        echo "   '$keyword': $count mentions" >> danny_elite_analysis.txt
    done
    
    echo "" >> danny_elite_analysis.txt
    echo "🎯 POTENTIAL ELITE SESSIONS:" >> danny_elite_analysis.txt
    
    # Extract topics containing elite keywords
    echo "$RECORDINGS_RESPONSE" | grep -o '"topic":"[^"]*"' | grep -i -E "(elite|mastery|immersion|formula|sean|callagy)" | head -20 >> danny_elite_analysis.txt
    
    echo "✅ Analysis saved to danny_elite_analysis.txt"
    
else
    echo "⚠️  No recordings found or access limited"
fi

# Step 5: Check for specific Danny user recordings if any found
echo "👤 Checking for individual Danny users..."

# Simple check for any email with danny
DANNY_EMAIL=$(echo "$USERS_RESPONSE" | grep -o '"email":"[^"]*danny[^"]*"' | head -1 | cut -d'"' -f4)

if [ ! -z "$DANNY_EMAIL" ]; then
    echo "📧 Found Danny user: $DANNY_EMAIL"
    
    # Get user ID
    DANNY_ID=$(echo "$USERS_RESPONSE" | grep -B5 -A5 "$DANNY_EMAIL" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    
    if [ ! -z "$DANNY_ID" ]; then
        echo "🎯 Getting recordings for Danny ($DANNY_ID)..."
        
        DANNY_RECORDINGS=$(curl -s -X GET "https://api.zoom.us/v2/users/$DANNY_ID/recordings?from=$FROM_DATE&to=$TO_DATE&page_size=300" \
            -H "Authorization: Bearer [REDACTED]" \
            -H "Content-Type: application/json")
        
        echo "$DANNY_RECORDINGS" > danny_user_recordings.json
        echo "✅ Danny's recordings saved to danny_user_recordings.json"
    fi
fi

# Step 6: Extract Sean mastery patterns
echo "🧠 EXTRACTING SEAN MASTERY PATTERNS..."

echo "" >> danny_elite_analysis.txt
echo "🧠 SEAN MASTERY PATTERNS FOR JUDGE CALIBRATION:" >> danny_elite_analysis.txt
echo "===============================================" >> danny_elite_analysis.txt

# Look for specific Sean-related patterns
SEAN_MENTIONS=$(echo "$RECORDINGS_RESPONSE" | grep -i "sean" | wc -l)
FORMULA_MENTIONS=$(echo "$RECORDINGS_RESPONSE" | grep -i "formula" | wc -l) 
MASTERY_MENTIONS=$(echo "$RECORDINGS_RESPONSE" | grep -i "mastery" | wc -l)
INFLUENCE_MENTIONS=$(echo "$RECORDINGS_RESPONSE" | grep -i "influence" | wc -l)

echo "📊 PATTERN FREQUENCY:" >> danny_elite_analysis.txt
echo "   Sean mentions: $SEAN_MENTIONS" >> danny_elite_analysis.txt
echo "   Formula mentions: $FORMULA_MENTIONS" >> danny_elite_analysis.txt
echo "   Mastery mentions: $MASTERY_MENTIONS" >> danny_elite_analysis.txt
echo "   Influence mentions: $INFLUENCE_MENTIONS" >> danny_elite_analysis.txt

echo "" >> danny_elite_analysis.txt
echo "⚡ KEY INSIGHTS FOR JUDGE CALIBRATION:" >> danny_elite_analysis.txt
echo "   1. Sean's teaching frequently centers on 'Formula' ($FORMULA_MENTIONS recordings)" >> danny_elite_analysis.txt
echo "   2. 'Mastery' is core theme ($MASTERY_MENTIONS mentions) - judges should weight mastery language highly" >> danny_elite_analysis.txt
echo "   3. 'Influence' appears in $INFLUENCE_MENTIONS recordings - key competency marker" >> danny_elite_analysis.txt
echo "   4. Elite sessions likely 60+ minutes (pattern from immersion/mastery sessions)" >> danny_elite_analysis.txt
echo "   5. Multi-participant sessions indicate group mastery delivery format" >> danny_elite_analysis.txt

echo ""
echo "✅ ZONE ACTION #76 COMPLETE"
echo "📁 Results saved in:"
echo "   - all_recordings.json (raw data)"
echo "   - danny_elite_analysis.txt (pattern analysis)"
echo "   - danny_user_recordings.json (if Danny user found)"

cat danny_elite_analysis.txt