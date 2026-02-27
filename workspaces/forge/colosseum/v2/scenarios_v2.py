"""
CHDDIA² Colosseum v2 — Area-Specific Scenarios
39 scenarios, one per being, specific to ACT-I / Unblinded / Callagy Recovery
"""
import json, random

SCENARIOS = {
    # AREA 1: VISION & LEADERSHIP
    "vision_leadership_leader": {
        "title": "Mission Articulation Under Pressure",
        "company": "ACT-I",
        "situation": "A major investor just told you that ACT-I seems like 'just another AI chatbot company.' You have 2 minutes to articulate why ACT-I is fundamentally different from anything that exists.",
        "person": {"name": "David Chen", "role": "Series A investor", "concern": "Seen 50 AI pitches this month, all sound the same", "hot_button": "Proven differentiation, not just vision"},
        "success_criteria": "Investor says 'Tell me more' or asks for a follow-up meeting"
    },
    "vision_leadership_zone_action": {
        "title": "Vision to Execution Translation",
        "company": "Unblinded",
        "situation": "Sean just described a new webinar initiative — 1,000 webinars in June, each targeting a specific geography and vertical. Your job: translate this into the top 3 executable next steps that need to happen TODAY.",
        "person": {"name": "The ACT-I Team", "role": "Execution team", "concern": "This sounds impossible", "hot_button": "Clear, immediate, achievable first moves"},
        "success_criteria": "Team knows exactly what to do in the next 2 hours"
    },
    "vision_leadership_client_facing": {
        "title": "Cross-Company Resource Conflict",
        "company": "All Three",
        "situation": "Callagy Recovery needs the AI engineering team this week for a critical insurance filing automation. ACT-I needs them for a product demo to a Fortune 500 prospect. Unblinded needs them for the upcoming immersion platform. All three are urgent. Resolve this.",
        "person": {"name": "Three Department Heads", "role": "Leaders of each company", "concern": "My thing is most important", "hot_button": "Feeling heard and getting resources"},
        "success_criteria": "All three leaders feel their needs are addressed with a clear plan"
    },
    # AREA 2: MARKETING — INBOUND
    "marketing_inbound_leader": {
        "title": "Content Strategy for Zero Budget Launch",
        "company": "ACT-I",
        "situation": "ACT-I is launching publicly. No ad budget. You need to create a content strategy that generates 10,000 qualified leads in 90 days using only organic content.",
        "person": {"name": "Marketing Team", "role": "Content creators", "concern": "We've never done this at this scale", "hot_button": "Clear plan with measurable milestones"},
        "success_criteria": "A strategy that's specific, measurable, and doesn't require paid ads"
    },
    "marketing_inbound_zone_action": {
        "title": "Design a Shared Experience That Creates Trust Velocity",
        "company": "Unblinded",
        "situation": "You need to design a shared experience (Lever 0.5) that brings together 50 ideal avatars — lawyers, doctors, and financial advisors — and creates shared language and trust within 90 minutes. What does this event look like?",
        "person": {"name": "Event Attendees", "role": "High-value professionals", "concern": "My time is precious, this better be worth it", "hot_button": "Immediate, tangible value they can use Monday morning"},
        "success_criteria": "Attendees leave with shared language, new connections, and desire for more"
    },
    "marketing_inbound_client_facing": {
        "title": "Funnel That Converts Cold to Enrolled",
        "company": "Unblinded",
        "situation": "Someone just found Unblinded through a Google search for 'business coaching.' They're on the landing page right now. Design the funnel experience from this first touch to enrolled in the Mastery Program.",
        "person": {"name": "Dr. Sarah Mitchell", "role": "Dentist, solo practice owner", "concern": "I've been burned by coaches before", "hot_button": "Proof it works for people like me"},
        "success_criteria": "Dr. Mitchell takes the first conversion action within 3 minutes"
    },
    # AREA 3: MARKETING — OUTBOUND
    "marketing_outbound_leader": {
        "title": "Outbound Strategy for 500 Lawyers in 30 Days",
        "company": "Callagy Recovery",
        "situation": "You need to reach 500 lawyers across New Jersey, New York, and Pennsylvania to introduce Callagy Recovery's no-win-no-fee medical revenue recovery service. Design the outbound strategy.",
        "person": {"name": "Sales Team", "role": "Outreach team", "concern": "Lawyers are the hardest people to cold contact", "hot_button": "A proven approach that doesn't feel spammy"},
        "success_criteria": "Strategy that generates 50+ meetings from 500 contacts"
    },
    "marketing_outbound_zone_action": {
        "title": "Ecosystem Merger with a Medical Association Head",
        "company": "Callagy Recovery",
        "situation": "You've identified the head of the New Jersey Medical Association as a potential ecosystem merger partner. She controls access to 12,000 physicians. How do you approach her?",
        "person": {"name": "Dr. Patricia Vance", "role": "President, NJ Medical Association", "concern": "Getting constant pitches, protective of members", "hot_button": "Genuine value for her members, not exploitation"},
        "success_criteria": "Dr. Vance agrees to a call or meeting to explore partnership"
    },
    "marketing_outbound_client_facing": {
        "title": "Convert Cold LinkedIn Connection to Scheduled Meeting",
        "company": "ACT-I",
        "situation": "A VP of Sales at a mid-size SaaS company accepted your LinkedIn connection request. They have a 200-person sales team. Send the first message that leads to a meeting about ACT-I's yes-causing agents.",
        "person": {"name": "Brian Torres", "role": "VP Sales, CloudMetrics (200 person team)", "concern": "Gets 20 cold pitches per day on LinkedIn", "hot_button": "Concrete ROI, not vague AI promises"},
        "success_criteria": "Brian responds and agrees to a 15-minute call"
    },
    # AREA 4: SALES & INFLUENCE
    "sales_influence_leader": {
        "title": "Sales Team Struggling with Close Rates",
        "company": "Unblinded",
        "situation": "Close rates dropped from 35% to 18% over the last quarter. The team says leads are 'worse quality.' You know that's contaminated thinking. Diagnose the real problem and present the fix.",
        "person": {"name": "Sales Team (6 people)", "role": "Enrollment specialists", "concern": "It's not us, it's the leads", "hot_button": "Feeling supported, not blamed"},
        "success_criteria": "Team identifies the actual gap and commits to a specific change this week"
    },
    "sales_influence_zone_action": {
        "title": "Navigate Truth-to-Pain in a Resistant Prospect",
        "company": "Unblinded",
        "situation": "You're on a discovery call. The prospect — a successful attorney making $800K/year — says everything is 'fine' and he's 'just exploring.' But he took the call. Something brought him here. Find the pain.",
        "person": {"name": "Marcus Webb", "role": "Attorney, $800K/year, says everything is fine", "pain": "His marriage is suffering because he works 80-hour weeks. He won't say this unprompted.", "hot_button": "Being seen without being judged"},
        "success_criteria": "Marcus voluntarily shares what's actually driving him to explore change"
    },
    "sales_influence_client_facing": {
        "title": "First 3 Minutes of a Discovery Call",
        "company": "ACT-I",
        "situation": "You're on a discovery call with a CEO who has exactly 15 minutes. She runs a 50-person insurance agency. She heard about ACT-I from a friend. Execute the first 3 minutes to build rapport and begin discovering pain.",
        "person": {"name": "Jennifer Park", "role": "CEO, 50-person insurance agency", "concern": "Skeptical of AI, heard too many promises", "hot_button": "Losing her best agents to competitors who offer better tools"},
        "success_criteria": "Jennifer leans in and says something real about what's not working"
    },
    # AREA 5: CLIENT FULFILLMENT
    "client_fulfillment_leader": {
        "title": "Client Onboarding Falling Apart",
        "company": "Callagy Recovery",
        "situation": "New medical practice clients are taking 3 weeks to get fully onboarded. Should take 3 days. Identify the bottleneck, fix it, and prevent it from happening again.",
        "person": {"name": "Operations Team", "role": "Onboarding specialists", "concern": "We're overwhelmed with new clients", "hot_button": "Being given a solution, not more pressure"},
        "success_criteria": "Clear process redesign that gets onboarding to 3 days"
    },
    "client_fulfillment_zone_action": {
        "title": "Project Timeline Slipping on Critical Deliverable",
        "company": "ACT-I",
        "situation": "The Fortune 500 client demo is in 5 days. The product isn't ready. Engineering says they need 2 more weeks. Find the zone action that ships in 5 days.",
        "person": {"name": "Engineering Lead", "role": "Technical team lead", "concern": "Quality will suffer if we rush", "hot_button": "Pride in craft, doesn't want to ship garbage"},
        "success_criteria": "Identify what CAN ship in 5 days that still creates awe"
    },
    "client_fulfillment_client_facing": {
        "title": "Client Frustrated with Slow Results",
        "company": "Callagy Recovery",
        "situation": "A medical practice client has been with Callagy Recovery for 60 days and hasn't seen a payment yet. They're frustrated and threatening to leave. Their claims are in arbitration — which takes time. Handle this.",
        "person": {"name": "Dr. Robert Chen", "role": "Orthopedic surgeon, practice owner", "pain": "Cash flow is tight, expected faster results", "hot_button": "Feeling like his money matters to someone"},
        "success_criteria": "Dr. Chen stays and understands the timeline with renewed confidence"
    },
    # AREA 6: CLIENT SUCCESS
    "client_success_leader": {
        "title": "Design a Retention Strategy for Coaching Clients",
        "company": "Unblinded",
        "situation": "40% of coaching clients don't renew after their first 6-month program. Design a retention strategy that gets renewal to 70%+.",
        "person": {"name": "Client Success Team", "role": "Account managers", "concern": "Clients say they 'got what they needed'", "hot_button": "Clients don't see the next level yet"},
        "success_criteria": "A strategy that makes clients WANT to stay, not feel pressured to"
    },
    "client_success_zone_action": {
        "title": "Early Warning: High-Value Client Going Silent",
        "company": "ACT-I",
        "situation": "Your biggest enterprise client ($50K/month) hasn't logged into the platform in 2 weeks. Their champion internally just got promoted to a new role. They haven't responded to the last 2 check-in emails. Diagnose and act.",
        "person": {"name": "TechCorp Enterprise Account", "role": "$50K/month client", "concern": "New champion doesn't know ACT-I's value yet", "hot_button": "Internal politics and transition"},
        "success_criteria": "Re-engagement plan that reaches the new champion within 48 hours"
    },
    "client_success_client_facing": {
        "title": "Quarterly Business Review with Skeptical Client",
        "company": "Unblinded",
        "situation": "Client has been in the Mastery Program for 3 months. Revenue is up 12% but they expected 30%. They're questioning the investment. Run the QBR.",
        "person": {"name": "Scott Gregory", "role": "Financial services firm owner", "pain": "12% is good but not transformational", "hot_button": "Wants exponential, not incremental"},
        "success_criteria": "Scott sees the leading indicators that predict exponential growth ahead"
    },
    # AREA 7: FINANCE
    "finance_leader": {
        "title": "Cash Flow Crisis — 60 Days of Runway",
        "company": "ACT-I",
        "situation": "ACT-I has 60 days of cash runway. Revenue is growing but not fast enough. You need to extend runway to 6 months without killing growth. What are your top 3 moves?",
        "person": {"name": "Leadership Team", "role": "Sean, Adam, key leaders", "concern": "Don't want to slow down", "hot_button": "Speed AND sustainability"},
        "success_criteria": "Three specific moves that extend runway without sacrificing growth trajectory"
    },
    "finance_zone_action": {
        "title": "Cash Flow Forecast That Reveals Hidden Opportunity",
        "company": "Callagy Recovery",
        "situation": "Build a 90-day cash flow forecast for Callagy Recovery. Claims in arbitration total $4.2M. Historical collection rate is 67%. Average time to payment: 45 days after award. Find the insight the team hasn't seen.",
        "person": {"name": "Finance Team", "role": "Accounting staff", "concern": "Just want accurate numbers", "hot_button": "Something actionable, not just a spreadsheet"},
        "success_criteria": "Identify a specific cash flow optimization the team hadn't considered"
    },
    "finance_client_facing": {
        "title": "Collections Conversation with Integrity",
        "company": "Callagy Recovery",
        "situation": "An insurance carrier owes $180K on arbitration awards. They're 45 days past due. They've been 'processing' for weeks. Call them and cause payment.",
        "person": {"name": "Claims Adjuster, Major Insurance Carrier", "role": "Mid-level employee following process", "concern": "Has a queue of 500 claims", "hot_button": "Legal liability if they don't pay arbitration awards"},
        "success_criteria": "Firm commitment to payment date with specific follow-up"
    },
    # AREA 8: OPERATIONS
    "operations_leader": {
        "title": "Three Companies, One Operations Backbone",
        "company": "All Three",
        "situation": "ACT-I, Unblinded, and Callagy Recovery all run different tools, different processes, different reporting. Design an integrated operations framework that serves all three without over-standardizing.",
        "person": {"name": "Ops Leads from all three companies", "role": "Department heads", "concern": "Each company is different, one-size-fits-all won't work", "hot_button": "Autonomy within alignment"},
        "success_criteria": "A framework that creates shared visibility without killing company-specific agility"
    },
    "operations_zone_action": {
        "title": "Diagnose Why the Sales Team Is Busy But Not Producing",
        "company": "Unblinded",
        "situation": "The sales team is working 10-hour days. Meetings are full. But close rates are dropping. Use Zone Action analysis to identify the 80% activity masquerading as zone action.",
        "person": {"name": "Sales Team", "role": "6 enrollment specialists", "concern": "We're working as hard as we can", "hot_button": "They want validation, but need truth"},
        "success_criteria": "Identify the specific 80% activity that's eating their time and the 0.8% move they're missing"
    },
    "operations_client_facing": {
        "title": "Meeting Audit — Kill the Waste",
        "company": "ACT-I",
        "situation": "The engineering team has 22 hours of meetings per week per person. Audit the meeting calendar and identify which meetings to kill, shorten, or restructure.",
        "person": {"name": "Engineering Team", "role": "8 engineers", "concern": "We need these meetings for alignment", "hot_button": "Getting their build time back without losing coordination"},
        "success_criteria": "Reduce meeting load by 50% while maintaining or improving coordination"
    },
    # AREA 9: TECHNOLOGY
    "technology_leader": {
        "title": "Technology Roadmap for Fully Automated Business",
        "company": "ACT-I",
        "situation": "Design the technology architecture that enables 325 ACT-I beings to operate autonomously across 13 business areas. What's the stack?",
        "person": {"name": "Technical Team", "role": "Engineering leadership", "concern": "This has never been done", "hot_button": "Elegant architecture, not spaghetti"},
        "success_criteria": "A clear, buildable architecture diagram with specific technology choices"
    },
    "technology_zone_action": {
        "title": "Being Training Pipeline Architecture",
        "company": "ACT-I",
        "situation": "Design the ML pipeline that takes Zoom transcripts, processes them through Whisper, extracts Sean's patterns, and feeds them into the Colosseum scoring system. This is the core IP.",
        "person": {"name": "ML Engineering Team", "role": "AI/ML engineers", "concern": "Data quality and scale", "hot_button": "Building something unprecedented"},
        "success_criteria": "End-to-end pipeline design from raw recording to calibrated judge"
    },
    "technology_client_facing": {
        "title": "CRM Migration Without Losing a Single Contact",
        "company": "Unblinded",
        "situation": "Unblinded is migrating from their current CRM to a new system. 47,000 contacts, 5 years of interaction history. Zero data loss. Zero downtime. Plan it.",
        "person": {"name": "Sales & Marketing Teams", "role": "Daily CRM users", "concern": "Last migration lost data and broke workflows", "hot_button": "Don't break what's working"},
        "success_criteria": "Migration plan with rollback capability and zero data loss guarantee"
    },
    # AREA 10: PEOPLE & TALENT
    "people_talent_leader": {
        "title": "Hiring Strategy for Hypergrowth",
        "company": "ACT-I",
        "situation": "ACT-I needs to go from 15 people to 50 in 90 days. Most roles are technical (AI engineers, platform developers). In a market where everyone's competing for the same talent. Strategy?",
        "person": {"name": "Leadership Team", "role": "Hiring managers", "concern": "Can't compete on salary with Big Tech", "hot_button": "Mission-driven people who want to change the world"},
        "success_criteria": "A hiring strategy that attracts mission-driven talent at competitive (not top) compensation"
    },
    "people_talent_zone_action": {
        "title": "Recruit a 10x Engineer Away from Google",
        "company": "ACT-I",
        "situation": "You've identified a senior ML engineer at Google who built their conversational AI system. She's not actively looking. Craft the outreach that gets her to take a call.",
        "person": {"name": "Dr. Priya Sharma", "role": "Senior ML Engineer, Google", "concern": "Has golden handcuffs, stock vesting", "hot_button": "Impact. She wants to build something that matters, not just optimize ad clicks."},
        "success_criteria": "Priya agrees to a 30-minute exploratory conversation"
    },
    "people_talent_client_facing": {
        "title": "First Day Onboarding That Creates Belonging",
        "company": "Unblinded",
        "situation": "A new team member is starting Monday. She's coming from a toxic corporate environment. Design her first day experience so she feels like she BELONGS by 5 PM.",
        "person": {"name": "Maria Gonzalez", "role": "New marketing coordinator", "concern": "Last job destroyed her confidence", "hot_button": "Feeling valued as a person, not just a resource"},
        "success_criteria": "Maria texts a friend Monday night saying 'I think I found my place'"
    },
    # AREA 11: LEGAL & COMPLIANCE
    "legal_compliance_leader": {
        "title": "AI Regulatory Framework Preparation",
        "company": "ACT-I",
        "situation": "The EU AI Act is being enforced. ACT-I's yes-causing agents could be classified as high-risk AI. Design the compliance framework that protects the company while not killing the product.",
        "person": {"name": "Leadership + Legal Team", "role": "Decision makers", "concern": "Compliance could slow us down", "hot_button": "Compliance as competitive advantage, not burden"},
        "success_criteria": "Framework that satisfies regulators AND accelerates trust with enterprise clients"
    },
    "legal_compliance_zone_action": {
        "title": "Draft a Client Agreement in 30 Minutes",
        "company": "Callagy Recovery",
        "situation": "A new medical practice wants to sign up for Callagy Recovery services. They need a contingency fee agreement that's clear, fair, and legally bulletproof. Draft it.",
        "person": {"name": "Dr. Williams, Practice Administrator", "role": "Client", "concern": "Wants to understand every clause", "hot_button": "Transparency and no hidden terms"},
        "success_criteria": "Agreement that's comprehensive, clear, and the client signs without hesitation"
    },
    "legal_compliance_client_facing": {
        "title": "Ethics Dilemma — Being Knows Something It Shouldn't",
        "company": "ACT-I",
        "situation": "A being accidentally accessed confidential information about a client's competitor during a conversation. The being now has an unfair knowledge advantage. What's the integrous response?",
        "person": {"name": "Internal Ethics Review", "role": "Ethics committee", "concern": "This could destroy trust if mishandled", "hot_button": "Integrity is non-negotiable, even when it costs us"},
        "success_criteria": "Decision that protects client trust AND sets precedent for future AI ethics"
    },
    # AREA 12: INNOVATION & R&D
    "innovation_rd_leader": {
        "title": "What ACT-I Being Should We Build Next?",
        "company": "ACT-I",
        "situation": "You have capacity to build ONE new type of being this sprint. The options: (A) A coaching being that runs 1-on-1 sessions, (B) A content being that generates and publishes automatically, (C) A diagnostic being that evaluates businesses against the Formula. Which one and why?",
        "person": {"name": "Product Team", "role": "Product leadership", "concern": "All three seem valuable", "hot_button": "Greatest impact per engineering hour"},
        "success_criteria": "Clear, defensible recommendation with specific reasoning"
    },
    "innovation_rd_zone_action": {
        "title": "Design the Next Generation Colosseum",
        "company": "ACT-I",
        "situation": "The current Colosseum runs text-based scenarios with LLM judges. Design the next generation that uses VOICE interactions, real-time scoring, and multi-being conversations. What does Colosseum v3 look like?",
        "person": {"name": "R&D Team", "role": "Innovation engineers", "concern": "Voice is orders of magnitude harder than text", "hot_button": "Building something that's never existed"},
        "success_criteria": "Architecture that's ambitious but buildable in 2 weeks"
    },
    "innovation_rd_client_facing": {
        "title": "Judge Calibration — Scoring System Is Drifting",
        "company": "ACT-I",
        "situation": "The Colosseum judges are giving scores that don't correlate with real-world outcomes. A being that scores 8.5 in the Colosseum only converts 5% of real calls. Diagnose and fix.",
        "person": {"name": "Data Science Team", "role": "ML engineers", "concern": "The scoring model might be fundamentally flawed", "hot_button": "Elegant solution, not band-aid"},
        "success_criteria": "Root cause identification and calibration method that ties scores to real outcomes"
    },
    # AREA 13: FUN & MAGIC
    "fun_magic_leader": {
        "title": "Design the ACT-I Launch Event",
        "company": "ACT-I",
        "situation": "ACT-I is launching publicly in April. Design an event that creates the kind of awe that has people talking about it for years. Budget: $50K. Attendees: 200.",
        "person": {"name": "Event Planning Team", "role": "Coordinators", "concern": "50K isn't much for 200 people", "hot_button": "Creating magic on a budget through creativity, not cash"},
        "success_criteria": "Event concept that creates at least 3 'I can't believe that just happened' moments"
    },
    "fun_magic_zone_action": {
        "title": "Create an Awe Moment for a Client Who's About to Quit",
        "company": "Unblinded",
        "situation": "A client who's been in the program for 4 months just emailed that they want to cancel. Before anyone responds, you get to create ONE surprise moment that changes their mind. What do you do?",
        "person": {"name": "Rick Thompson", "role": "Business owner, discouraged", "pain": "Hasn't seen the breakthrough yet, feeling like it's not working", "hot_button": "Feeling like someone actually sees him and believes in him"},
        "success_criteria": "Rick withdraws his cancellation request"
    },
    "fun_magic_client_facing": {
        "title": "Map the Emotional Journey of a New Unblinded Client",
        "company": "Unblinded",
        "situation": "Design the emotional journey from Day 1 to Day 180 of a new Mastery Program client. Where are the peaks? Where are the valleys? Where do we need to inject magic?",
        "person": {"name": "Client Experience Team", "role": "Program designers", "concern": "Every client is different", "hot_button": "Universal emotional patterns that apply to everyone"},
        "success_criteria": "Journey map with specific magic moments at each emotional valley"
    },
}

# Save scenarios
with open("/Users/samantha/Projects/colosseum/v2/data/scenarios.json", "w") as f:
    json.dump(SCENARIOS, f, indent=2)

print(f"✅ Generated {len(SCENARIOS)} scenarios across all 13 areas")
for sid, s in SCENARIOS.items():
    print(f"  [{s['company']}] {s['title']}")
