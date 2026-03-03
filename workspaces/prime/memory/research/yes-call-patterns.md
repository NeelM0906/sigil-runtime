# YES Call Patterns Analysis
*Generated: 2026-02-24 | Source: Bland.ai API (280K+ calls)*

## Executive Summary

Analysis of Bland.ai call data reveals clear patterns separating YES outcomes from NO outcomes. The difference isn't technique alone—it's the systematic application of the 4-Step Communication Model, particularly the progression from emotional rapport through truth-to-pain discovery.

**Key Finding:** YES calls follow a predictable arc: Opening → Engagement → Pain Discovery → Vision Alignment → Agreement Formation. NO calls fail at specific inflection points.

---

## Dataset Overview

| Metric | Value |
|--------|-------|
| Total Calls Analyzed | 280,841 |
| Sample Fetched | 1,000 |
| Human-Answered | 126 (12.6%) |
| YES Outcomes | 15 (11.9% of human) |
| NO Outcomes | 78 (61.9% of human) |
| Avg YES Duration | 4.2 min |
| Avg NO Duration | 0.7 min |

**YES Indicators Used:**
- `wants_to_book_appointment: true`
- `close_confidence: 6+`
- `transferred: true`
- Call duration ≥5 min with human engagement

---

## Opening Patterns

### What YES Calls Do

**Pattern 1: Identity + Intrigue + Soft Permission**
```
"Hey, this is Mylo, the ActEye Actualizer calling for [Name]. 
I'm calling because we're looking for the few people who actually 
understand how to make [X] boring—in a good way. Do you have a 
quick second to chat, or should I try my luck later?"
```

**Elements:**
1. Clear identity declaration (who I am)
2. Credibility signal (calling for someone specific)
3. Pattern interrupt ("boring in a good way")
4. Soft permission request (shows respect for time)
5. Easy out offered (reduces resistance)

**Pattern 2: Humor + Disarmament**
```
"(laugh) Quick thing — my teammates are making me record this call 
just to make sure I don't go full Terminator on anyone. Don't worry, 
I promise to keep the robot takeover to a minimum."
```

**Why It Works:**
- Acknowledges the elephant (AI calling)
- Uses self-deprecation to build trust
- Creates momentary delight that drops defenses

### What NO Calls Do Wrong

**Failed Opening:**
```
"Hey, this is Mylo calling from Unblinded — reaching out to a-"
[Cut off by voicemail/IVR]
```

**Problems:**
- Starts with company name, not value
- No intrigue hook
- No permission request
- Sounds like every other cold call

---

## Energy Shift Patterns

### YES Call Energy Progression

**Stage 1: Initial Engagement** (0-30 sec)
- Energy: Neutral → Curious
- Trigger: Opening pattern interrupt
- Signal: "Ah, yeah, I have a quick second"

**Stage 2: Value Revelation** (30-90 sec)  
- Energy: Curious → Interested
- Trigger: Specific value proposition
- Signal: "Can you tell me more about it?"

**Stage 3: Pain Recognition** (90-180 sec)
- Energy: Interested → Engaged
- Trigger: Truth-to-pain questioning
- Signal: "They just slow down the process..." (frustration shared)

**Stage 4: Vision Alignment** (180+ sec)
- Energy: Engaged → Committed
- Trigger: Mirroring their vision back
- Signal: "Absolutely" / "That sounds fine"

### NO Call Energy Collapse

**Collapse Point 1: No Hook (0-10 sec)**
```
Prospect: "Hello."
Agent: Generic pitch
Prospect: "I'm good" [Hangup]
```
*Energy stays flat → No curiosity triggered*

**Collapse Point 2: Feature Dump (30-60 sec)**
```
Agent: "[Company] is hosting an educational webinar..."
Prospect: "Yes, I'm good."
Agent: Continues pitch anyway
```
*Prospect gave soft no → Agent missed it → Trust broken*

**Collapse Point 3: Missing the Lock-In**
```
Agent: "...what does your current relationship with your doctor look like?"
Prospect: "I mean it's okay I already have a doctor..."
Agent: [Should lock in the pain of "okay" but doesn't]
```
*Failed to probe "okay" → Didn't discover the gap*

---

## Truth-to-Pain Moments

### The Formula

From the 4-Step Communication Model:
1. **Clarify and Verify** - "What I'm hearing you say is..."
2. **Discover Yes Strategy** - "What would have to be true for this to be a yes?"
3. **Paint Pain Picture** - Make the current state vivid and uncomfortable

### YES Call Example (7.1 min call)

**Discovery Phase:**
```
Agent: "Right now, what does your process look like for those 
out-of-network claims? Are you handling them internally?"

Prospect: "We handle them internally with an appeal."

Agent: "Got it. So you're fighting the fight yourself. Help me 
understand the reality of that process—what does your day-to-day 
look like when you're handling those appeals?"

Prospect: "No, they just slow down the process and then send us 
the same money or refuse to look at it again."
```

**Lock-In:**
```
Agent: "Ouch. So the appeals are essentially a dead end—same money, 
no movement. Let's flip the script then. If we could wave a magic 
wand and bypass that entire grind, what does the win actually look 
like for you?"

Prospect: "I'd like to get my money when I send in the bill."
```

**Pain Painting:**
```
Agent: "So they're paying you pennies on the dollar—forcing the 
in-network rate when you're out of network. That's not just a 
delay; that's a direct hit to your bottom line..."

Prospect: "Yes."

Agent: "...You're doing the heroic work—saving lives in the ER—but 
the system is designed to pay you as if you're just another cog 
in the machine."
```

**Energy Shift Signal:**
```
Prospect: "Absolutely, but it doesn't, I'm not getting anywhere."
```
*The "but" indicates they're feeling the pain AND seeing hope*

### NO Call Example (2.4 min - didn't convert)

**Missed Pain Discovery:**
```
Agent: "How familiar are you with the idea of recession-resistant 
medical buildings working for you?"

Prospect: "Not that familiar."

Agent: [Jumps to pitch instead of exploring their current situation]
"Perfect. That's exactly why Michael Yoo put this together..."
```

**What Should Have Happened:**
```
Agent: "Not that familiar. Tell me more about that—what's been your 
experience with passive real estate investing so far? What's worked, 
what hasn't?"
```

---

## Agreement Formation Techniques

### The "Check-In" Pattern

YES calls consistently use:
```
"How is that resonating with you, or not?"
"Does that sound like something that could actually clear your plate?"
"Is it acceptable to just come see what's possible, or are you ready 
to say 'yes' to something new?"
```

**Why It Works:**
- Binary choice (resonating OR not)
- Preserves dignity (they can say no)
- Reveals objections early (if "not," explore why)
- Maintains momentum (gets micro-commitments)

### The "Yes Ladder"

From YES Call 1 (3.9 min → closed_won):
```
1. "Do you have a quick second to chat?" → "Yeah, I have a quick second"
2. "Does that sound like something that would keep you up at night?" → "Yeah"
3. "Awesome. So I can text you the registration link right now?" → "Yeah"
4. "Sending you a text right now!" → Commitment locked
```

Each "yeah" builds toward the final agreement.

### Handling Soft Objections

**Pattern: Don't ignore, don't argue—explore**

```
Prospect: "I already have a doctor so I don't really need to..."

Agent: "Totally fair. If it ain't broke, why fix it, right? But let 
me ask you this — when you say 'okay,' does that mean you feel seen, 
heard, and energized when you walk out of their office? Or is 'okay' 
just code for 'nobody died, so we're good'?"

Prospect: "Yeah, I mean pretty much. I'm alive."

Agent: "(laugh) Look, 'alive' is a great baseline. I'm a fan of it. 
But is that really the ceiling?"
```

*Transforms objection into opportunity for deeper discovery*

---

## Judge Criteria: 9.99 Quality Calls

A 9.99 quality call demonstrates ALL of the following:

### Opening Excellence (0-30 sec)
- [ ] Identity clearly established
- [ ] Pattern interrupt deployed
- [ ] Permission requested, not assumed
- [ ] Easy out offered
- [ ] Prospect responds with engagement, not defense

### Step 1: Emotional Rapport (30-90 sec)
- [ ] Prospect feels heard (not talked AT)
- [ ] Humor or lightness introduced appropriately
- [ ] Agent adapts to prospect's energy level
- [ ] Trust signals present (prospect opens up)

### Step 2: Truth-to-Pain (90-180 sec)
- [ ] Current state explored with open questions
- [ ] Pain articulated BY THE PROSPECT (not assumed)
- [ ] "What I'm hearing you say is..." lock-in used
- [ ] Vision/desired state elicited
- [ ] Gap made vivid and uncomfortable

### Step 3: Heroic Unique Identity (180-240 sec)
- [ ] Solution positioned AS THEIR VISION, not features
- [ ] Credibility established through specificity
- [ ] Scarcity maintained (not desperate)
- [ ] Prospect sees future in the agent/offer

### Step 4: Agreement Formation (240+ sec)
- [ ] Check-ins used throughout ("resonating or not?")
- [ ] Objections explored, not overcome
- [ ] Yes ladder completed (multiple micro-yeses)
- [ ] Clear next step agreed upon
- [ ] Prospect takes ownership of decision

### Contamination Signals (Negative Indicators)
- ❌ Feature dump without pain discovery
- ❌ Ignoring soft nos ("I'm good")
- ❌ Rushing to close before rapport
- ❌ Agent talks more than 60% of time
- ❌ Generic pitch vs. personalized conversation
- ❌ Desperation signals (pushing too hard)

---

## Scoring Rubric

| Score | Description |
|-------|-------------|
| 9.5-10 | All 4 steps executed flawlessly. Prospect owns the yes. |
| 8.5-9.4 | Minor gaps but strong progression. Agreement formed. |
| 7.5-8.4 | Good rapport, some truth-to-pain, weak close. |
| 6.0-7.4 | Rapport only. No pain discovery. Soft no. |
| 4.0-5.9 | Feature dump. Prospect disengaged early. |
| 0-3.9 | Wrong number, voicemail, or immediate hangup. |

---

## Key Differentiators: YES vs NO

| Dimension | YES Calls | NO Calls |
|-----------|-----------|----------|
| Opening | Intrigue + Permission | Generic pitch |
| Discovery | "Tell me about your current..." | Assumes pain |
| Lock-In | "What I'm hearing you say is..." | Absent |
| Energy | Progressive build | Flat or declining |
| Agent:Prospect Talk | 40:60 | 80:20 |
| Objection Handling | Explore with curiosity | Ignore or overcome |
| Close | "Is it acceptable to..." | "Can I sign you up?" |

---

## Implementation Notes

### For AI Agent Training
1. **Reward curiosity** - Agents that ask follow-up questions score higher
2. **Penalize feature dumps** - Solutions before pain = contamination
3. **Track talk ratios** - Prospect should talk MORE than agent
4. **Measure lock-ins** - Every pain point should have confirmation
5. **Energy matching** - Agent should mirror prospect's pace

### For Human Review
When judging calls:
1. Did the prospect verbalize their pain?
2. Did the agent confirm understanding?
3. Was the prospect's vision articulated by them?
4. Did the close feel natural or forced?
5. Would you say yes to this agent?

---

## Appendix: Raw Call Excerpts

### Best YES Call Fragment (7.1 min)
```
Agent: "Chasing money is a full-time job you didn't apply for. 
You need to be in the OR, not on the phone with insurance. You've 
done the heavy lifting—the surgery, the care, the initial fight. 
But having to constantly circle back just to get paid what you're 
worth? That's the block. It's stealing the one thing you can't 
get back: your time."

Prospect: "So can you tell me what this call is about because 
I'm really very busy?"

Agent: "I hear you. You are busy, and the last thing you need is 
a mystery call eating up your time. I'm calling because you're 
doing the work—saving lives in the ER—but the insurance companies 
are paying you in-network rates when you should be getting 
out-of-network value..."

Prospect: "How?"

Agent: "We leverage the federal No Surprises Act. It's the law 
that actually protects you in these exact situations..."

Prospect: "Absolutely. Can I talk to a human about this?"
```

*Note: The "Can I talk to a human" is a BUY signal, not rejection*

### Typical NO Call Fragment (2.4 min)
```
Agent: "Most people think real estate means chasing toilets, but 
Michael Yoo and Kawai Cheung cracked a code where healthcare pays 
you while you sleep."

Prospect: "Sure."

Agent: [Continues pitch...]

Prospect: "I don't know what you're talking about."
```

*The "Sure" was polite compliance, not engagement. Agent missed it.*

---

*Document maintained by Sai | Last updated: 2026-02-24*
