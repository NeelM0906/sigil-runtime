# Nick Roy's Bio Automation Breakthrough — February 27, 2026

**LOCKED: The actual 0.8% move that makes personalized outreach at scale work.**

---

## The Perplexity Prompt (LinkedIn-Safe)

### Search Query Template
```
Search for {{ $fromAI('query', 'The search query to find the lawyers LinkedIn profile and professional background') }} and return all professional information found. Include: current position, past positions, education, skills, and notable achievements. Make sure you verify the person matches the name, title, and company provided.
```

### User Message Template
```
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

---

## Why This Works (No Red Flags)

1. **One contact at a time** — Not bulk scraping
2. **Natural language with verification** — Professional bio writer framing
3. **LinkedIn URL as reference, not scraping target** — The URL is context, search is by name/title/company
4. **Factual fallback** — If wrong person found, use input data only
5. **Strict output format** — Parseable for automation

---

## The Numbers

- **38,000 contacts** to process
- **~165 million tokens** estimated cost
- **Aiko approved:** "Yes!" (4:07 PM, Feb 27)

---

## The Transformation

**Before:**
> "Hi, I'm calling about medical revenue recovery."

**After:**
> "Dr. Martinez, I saw your fellowship at Johns Hopkins and your work on complex spinal reconstructions. United denied 23% of similar cases last quarter — we recovered $287K for a practice just like yours."

---

## Key Insight

Nick cut through dozens of theoretical frameworks with one elegant, executable prompt. This is the difference between planning and doing.

The bio-automation pipeline is now LIVE.

---

*Credit: Nick Roy*
*Captured: February 27, 2026, 7:06 PM EST*
*Source: NAN WhatsApp group (Nadav, Nick)*
