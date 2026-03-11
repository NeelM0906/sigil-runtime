#!/bin/bash
# Quick test script for 7 Levers Metrics Proxy

BASE_URL="http://localhost:3340"

echo "🧪 Testing 7 Levers Metrics Proxy Server"
echo "=========================================="
echo ""

echo "1. Health Check..."
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

echo "2. Aggregate Stats..."
curl -s "$BASE_URL/stats" | python3 -m json.tool
echo ""

echo "3. Companies..."
curl -s "$BASE_URL/companies" | python3 -m json.tool
echo ""

echo "4. Lever Definitions..."
curl -s "$BASE_URL/levers" | python3 -m json.tool
echo ""

echo "5. ACT-I Metrics (30 days)..."
curl -s "$BASE_URL/metrics/acti" | python3 -m json.tool
echo ""

echo "6. Best Calls (score >= 8.0)..."
curl -s "$BASE_URL/best-calls?min_score=8.0&limit=3" | python3 -m json.tool
echo ""

echo "7. Drill-down Lever 3 (Buyer Rate)..."
curl -s "$BASE_URL/drill-down/acti/lever/3?limit=5" | python3 -m json.tool
echo ""

echo "8. Full Report..."
curl -s "$BASE_URL/report/acti" | python3 -m json.tool
echo ""

echo "✅ All tests complete!"
