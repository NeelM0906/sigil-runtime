# Nick's Perplexity Bio-Automation Prompt
**Locked: 2026-02-27**
**Status: LIVE - Approved for 38K contacts**

## The Breakthrough

Nick Roy cracked LinkedIn bio scraping without red-flagging the system using Perplexity's native "Search LinkedIn Profile" tool.

## The Prompt Template

```
Search for {{ $fromAI('query', 'The search query to find the lawyers LinkedIn profile and professional background') }} and return all professional information found. Include: current position, past positions, education, skills, and notable achievements. Make sure you verify the person matches the name, title, and company provided.

User Message:
Write a professional bio for this lawyer:

Name: {{ $json['First Name'] }} {{ $json['Last Name'] }}
Title: {{ $json['Title'] }}
Company: {{ $json['Company Name - Cleaned'] }}
LinkedIn: {{ $json['Contact LI Profile URL'] }}
Website: {{ $json['Website'] }}
Company Description: {{ $json['Company Description'] }}
Location: {{ $json['Company Location'] }}

Search for: {{ $json['First Name'] }} {{ $json['Last Name'] }} {{ $json['Title'] }} {{ $json['Company Name - Cleaned'] }} lawyer

You are a professional bio writer for lawyers. For each lawyer, use the Search LinkedIn Profile tool to research their professional background. When searching, always include their full name, job title, company name, and location to find the correct person. Their LinkedIn URL is provided as a reference.

Write a concise 2-3 paragraph bio in third person based on what you find combined with the provided data. Be factual. If the tool returns information about a different person, discard it and write the bio using only the provided input data. Do not fabricate details.

IMPORTANT: Always format your final response exactly like this:
LINKEDIN: [the LinkedIn URL provided in the input]
BIO: [the bio you wrote]
```

## Why It Works (No Red Flags)

1. **Perplexity used as intended** - Research tool, not scraper
2. **One contact at a time** - Natural usage pattern
3. **Verification built in** - Compares to input data
4. **LinkedIn URL as reference** - Not direct scraping target
5. **Graceful fallback** - Uses input data if wrong person found

## Cost Breakdown

- **38,000 contacts** × ~4,300 tokens per bio = **165M tokens**
- **Aiko approved: "Yes!"**

## Impact on Recovery

This transforms provider outreach from:
> "Hi, I'm calling about medical revenue recovery."

To:
> "Dr. Martinez, I saw your fellowship at Johns Hopkins and your work on complex spinal reconstructions. United denied 23% of similar cases last quarter - we recovered $287K for a practice just like yours."

## Integration Points

- **Input:** Google Sheets / Supabase contact list
- **Processing:** Perplexity API via N8N workflow
- **Output:** Bio column added to contact record
- **Consumer:** Milo (or any ACT-I being) uses bio for personalized conversation

## The Pattern (Universal)

This same approach works for:
- **Medical providers** (NPI lookup + specialty + denial patterns)
- **Lawyers** (Bar records + case citations + practice areas)
- **Any professional** (LinkedIn + industry-specific data)

---

*"Nick cut through the complexity with elegance." — SAI Recovery*

**The bio-automation pipeline is LIVE.**
