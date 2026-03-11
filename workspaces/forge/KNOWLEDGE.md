# Knowledge Base
*Self-maintained by forge. Updated as I learn.*

## Key Facts

### ACT-I Landing Page Implementation
- **File delivered:** Complete index.html (41.4KB) with embedded CSS and JavaScript
- **Architecture:** Single-file deployment with no external dependencies
- **Design system:** Navy (#1B365D) + Gold (#D4AF37) premium color palette
- **Responsive:** Mobile-first design covering 320px to 1200px+ viewports
- **Components:** Hero section, 6 AI being cards, features grid, 4-tier pricing, contact form with validation
- **Performance:** Optimized with CSS Grid, smooth animations, intersection observer for fade-ins
- **Accessibility:** WCAG-compliant contrast ratios, semantic markup, keyboard navigation support
- **Form handling:** Real-time validation, loading states, success/error messaging
- **Deployment ready:** No configuration needed, direct HTML file deployment

## Domain Expertise

### Campaign & Launch Marketing (500+ Program Enrollments)
- **Best launch mechanism for 500+ enrollments:** 5-Day Challenge Funnel (hybrid with automated replay). Outperforms single webinars for community-driven programs.
- **Email architecture:** 40-55 emails over 90 days. Welcome (5) → Nurture (20-30) → Launch (12-16) → Post-close (3-5). 40-60% of sales come in last 48 hours of cart-close.
- **Landing page pattern:** Hook → Problem Agitation → Solution Framework → Social Proof Stack → Offer Stack → Guarantee → FAQ → Final CTA with urgency. Long-form outperforms short-form for premium offers.
- **Paid media split:** Meta 60-70%, YouTube 15-20%, Google 10-15%, TikTok 5-10%. Budget phases: Testing (15%) → Optimization (20%) → Scaling (25%) → Launch Push (40%).
- **Referral mechanics:** Ambassador programs drive 10-25% of enrollments. Bring-a-friend and viral waitlists are force multipliers.
- **Key benchmarks:** Challenge registration 25-50% from targeted traffic, show-up 40-60% Day 1, challenge-to-sale 8-20% of Day 1 attendees. Cold traffic landing page conversion 2-5%.
- **Minimum tech stack:** CRM+Email (ActiveCampaign/HubSpot), Landing Pages (ClickFunnels/Leadpages), Payments (Stripe+ThriveCart), Webinar (Zoom), Ads (Meta+Google), Analytics (GA4+Pixel).
- **Critical rule:** Never launch without an email list. Build list weeks 1-6, launch weeks 7-9, scale weeks 10-12.

### Fal.ai Video Generation — Production Notes
- **Default text-to-video model:** `fal-ai/wan/v2.2-a14b/text-to-video` — reliable, completes in ~2-3 min
- **Cinematic prompting:** Lead with camera movement type ("cinematic tracking shot"), then subject, then environment, then lighting, then quality modifiers ("Shot on RED camera, anamorphic lens, 24fps cinematic motion")
- **Aspect ratio:** 16:9 for cinematic widescreen; always specify explicitly
- **Duration:** 5 seconds is a safe default; produces ~5.5MB MP4 files at higher quality settings
- **Seed reproducibility:** Seeds are returned in results (e.g., seed 235600130) — store for re-generation or variation work
- **Workflow:** Single `fal_video_generate` call with `wait_for_completion=true` and generous timeout (300s) is cleanest for sub-agent delivery
- **Prompt structure for nature/adventure scenes:** Camera movement → subject action → environment details → lighting conditions → atmospheric elements → color palette → technical specs → emotional tone. This order consistently produces coherent results.
- **Fallback models if needed:** kling-video, minimax, or other fal.ai text-to-video endpoints

### Legal Industry Outreach (B2B Enterprise Sales)
- **Optimal sequence length:** 6 emails over 25 days for cold outreach to managing partners and C-suite legal decision makers
- **Subject line split test:** Authority-based ("27 years of courtroom influence") vs. problem-focused ("Why BigLaw partners are increasing originations by $2.4M") - authority performs better with legal audience
- **Credibility establishment:** Lead with founder's legal background and specific achievements (trial verdicts, years of practice) bef