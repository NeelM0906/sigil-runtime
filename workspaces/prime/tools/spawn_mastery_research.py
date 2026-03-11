#!/usr/bin/env python3
"""
Spawn 80 mastery research babies — 4 positions × 20 clusters.
Each baby researches one position and saves a JSON file.
"""

# 20 clusters × 4 positions each = 80 total
CLUSTERS = {
    "Marketing & Advertising": [
        "Chief Marketing Officer (CMO)",
        "Media Buyer",
        "Copywriter",
        "Creative Director"
    ],
    "Content & Communications": [
        "Content Strategist",
        "Public Relations Director",
        "Social Media Manager",
        "Brand Voice Architect"
    ],
    "Legal Operations": [
        "Personal Injury Trial Attorney",
        "Commercial Litigation Partner",
        "Family Law Attorney",
        "Compliance Officer"
    ],
    "Sales & Revenue": [
        "VP of Sales",
        "Account Executive",
        "Revenue Operations Manager",
        "Pricing Strategist"
    ],
    "Technical Operations": [
        "Data Engineer",
        "API Architect",
        "Infrastructure Lead (DevOps)",
        "Systems Reliability Engineer"
    ],
    "AI/ML Operations": [
        "ML Engineer",
        "Prompt Engineer",
        "RAG Systems Architect",
        "AI Product Manager"
    ],
    "Testing & QA": [
        "QA Engineering Lead",
        "Performance Test Engineer",
        "A/B Testing Analyst",
        "User Acceptance Testing Manager"
    ],
    "Product & Platform": [
        "Product Manager",
        "UX Designer",
        "Frontend Engineering Lead",
        "Platform Architect"
    ],
    "Research & Analysis": [
        "Market Research Director",
        "Competitive Intelligence Analyst",
        "Trend Forecaster",
        "Consumer Insights Manager"
    ],
    "Education & Training": [
        "Executive Coach",
        "Curriculum Designer",
        "Corporate Training Director",
        "Certification Program Manager"
    ],
    "Knowledge Management": [
        "Knowledge Management Director",
        "Technical Documentation Lead",
        "SOP Architect",
        "Information Architect"
    ],
    "Strategic Planning": [
        "Chief Strategy Officer",
        "Business Development Director",
        "OKR Program Manager",
        "Corporate Development Lead"
    ],
    "Data & Analytics": [
        "Chief Data Officer",
        "Business Intelligence Manager",
        "Data Visualization Specialist",
        "Analytics Engineering Lead"
    ],
    "CRM & Contact Management": [
        "CRM Director",
        "Marketing Automation Manager",
        "Customer Segmentation Analyst",
        "Lead Nurturing Specialist"
    ],
    "Meeting & Communication": [
        "Chief of Staff",
        "Executive Communications Director",
        "Meeting Facilitation Expert",
        "Internal Communications Manager"
    ],
    "Memory & Continuity": [
        "Enterprise Architect",
        "Business Continuity Manager",
        "Records Management Director",
        "Institutional Knowledge Lead"
    ],
    "Medical Revenue Recovery": [
        "Medical Billing Director",
        "Revenue Cycle Manager",
        "Medical Coding Specialist (CPC)",
        "Collections Strategy Manager"
    ],
    "Healthcare Operations": [
        "Healthcare Operations Director",
        "Provider Relations Manager",
        "Insurance Authorization Specialist",
        "Clinical Documentation Improvement Lead"
    ],
    "Financial Operations": [
        "Controller",
        "Financial Planning & Analysis Director",
        "Accounts Receivable Manager",
        "Revenue Forecasting Analyst"
    ],
    "Client Services": [
        "Client Success Director",
        "Onboarding Program Manager",
        "Customer Support Operations Lead",
        "Client Retention Strategist"
    ]
}

# Verify count
total = sum(len(v) for v in CLUSTERS.values())
print(f"Total positions: {total}")
assert total == 80, f"Expected 80, got {total}"

# Print all for reference
for i, (cluster, positions) in enumerate(CLUSTERS.items(), 1):
    print(f"\n{i}. {cluster}:")
    for p in positions:
        print(f"   - {p}")
