# RTI Real-Time Intervention Patterns Framework

*Research compiled from Colosseum codebase, Pinecone knowledge bases, and voice server architecture*  
*Date: 2026-02-24*  
*Author: Sai (Subagent: baby-rti)*

---

## Executive Summary

This document establishes a framework for Real-Time Intervention (RTI) during live calls. It synthesizes patterns from:

1. **Colosseum RTI Scoring Architecture** — Opposition analysis, context calibration, threshold enforcement
2. **Unblinded Influence Mastery** — The 4-Step Communication Model, 12 Indispensable Elements, 4 Energies
3. **Voice Server Architecture** — Barge-in support, knowledge retrieval, energy detection
4. **Pinecone Knowledge Bases** — RTI agents, Level 5 Listening, congruence detection

The goal: Enable beings to coach humans during live calls **without interrupting flow** — providing real-time whisper coaching that enhances rather than disrupts the conversation.

---

## Part 1: Core RTI Principles

### 1.1 What Is Real-Time Intervention?

RTI is the systematic application of coaching guidance during a live interaction. Unlike post-call feedback, RTI happens **in the moment** — while the conversation is still malleable.

**From Pinecone (rtistratabrain namespace):**
> "RTI agents provide the MECHANISM for detecting what's not being said through memory access rather than verbal claims... RTI-01 provides the MECHANISM for what Level 5 Listening detects: memory-based truth patterns that verbal reports cannot override."

### 1.2 The RTI Paradox

**The challenge:** Intervention must be timely enough to be useful, but not so intrusive that it breaks rapport, flow, or the person's ownership of the conversation.

**The solution:** Intervention operates on a **whisper channel** — parallel to the main conversation, not replacing it.

### 1.3 Intervention vs. Interruption

| Intervention | Interruption |
|--------------|--------------|
| Supplements the speaker's awareness | Breaks the speaker's focus |
| Delivered via whisper/sidebar | Delivered verbally into the conversation |
| Enhances the speaker's own mastery | Takes over for the speaker |
| Invisible to the other party | Audible to all parties |
| Creates leverage | Creates confusion |

---

## Part 2: Intervention Triggers

### 2.1 When to Intervene

Based on Colosseum judges and Unblinded patterns, intervention should occur when:

#### A. Energy Mismatch Detection

**From oracleinfluencemastery:**
> "Can you all hear how already the energies are mismatched?"

**Trigger conditions:**
- Speaker's energy doesn't match the prospect's state (too Zeus when Goddess is needed)
- Sudden energy drop in the prospect (voice tighter, pace slower)
- Fun energy when pain has surfaced
- Zeus containment missing when chaos is present

**Detection method:** Voice tone analysis, pace changes, language patterns

#### B. Level 5 Listening Failure

**From oracleinfluencemastery:**
> "His level five listening was off. And his question mastery was totally off because he asked him questions that [the prospect] didn't care about and didn't wanna know about."

**Trigger conditions:**
- Speaker asks questions irrelevant to what prospect just said
- Speaker makes assumptions without verification
- Pain word spoken but not acknowledged
- Prospect shares something vulnerable that gets passed over

**Detection method:** Semantic relevance scoring, pain word detection, response appropriateness

#### C. Step Navigation Errors

**The 4 Steps of Communication:**
1. Emotional Rapport
2. Truth to Pain  
3. Heroic Unique Identity (HUI)
4. Agreement Formation

**Trigger conditions:**
- Moving to Step 3 (HUI) without completing Step 2 (Truth to Pain)
- Trying to form agreement without establishing rapport
- Skipping pain to jump to solution
- Presenting HUI before prospect sees their future in you

**Detection method:** Conversation phase tracking, completion percentage per step

#### D. Contamination Detection

**From Colosseum contamination_judge:**
> "Generic consulting advice, bot phrases, sycophancy, 80% activity disguised as zone action, playing small, deference when ownership is needed"

**Trigger conditions:**
- "That's a great question" (sycophancy)
- "How can I help?" (bot phrase)
- Listing frameworks instead of storytelling
- Generic advice that could apply to anyone
- Ending with questions to seem helpful instead of taking a position

**Detection method:** Pattern matching against contamination phrases, genericity scoring

#### E. Congruence Breaks

**From Pinecone (rtistratabrain):**
> "Each RTI agent detects Congruence/incongruence in its domain... The 381ms cost of incongruence"

**Trigger conditions:**
- Words say "yes" but tone says hesitation
- Enthusiasm claimed but energy is flat
- Agreement stated but pace slows
- Confidence expressed but voice rises (questioning intonation)

**Detection method:** Multi-modal analysis (words vs. tone vs. pace)

---

## Part 3: Intervention Timing

### 3.1 The Golden Window

Intervention is most effective in natural conversation pauses:

1. **After the prospect speaks** — Before the speaker responds (2-3 second window)
2. **During extended silence** — When speaker is visibly thinking
3. **At topic transitions** — When conversation naturally pivots
4. **After key revelations** — When prospect shares pain or vulnerability

### 3.2 Timing Principles

| Timing | Appropriateness | Risk |
|--------|-----------------|------|
| Within 1 second of trigger | Too fast — may cause speaker to lose train of thought | High |
| 2-3 seconds after trigger | Ideal — allows processing without losing relevance | Low |
| 5+ seconds after trigger | May be too late — moment has passed | Medium |
| During prospect speech | Never intervene here | Critical |

### 3.3 Urgency Levels

**Level 1 — Observe Only**
- Note for post-call debrief
- Pattern worth tracking but not urgent
- Example: Slight energy mismatch, early in rapport phase

**Level 2 — Soft Whisper**
- Brief suggestion, non-urgent
- Delivery: Text on sidebar, subtle audio cue
- Example: "Consider matching their pace"

**Level 3 — Prompt Whisper**  
- Important course correction
- Delivery: Clear text, gentle audio notification
- Example: "She just said 'frustrated' — go there"

**Level 4 — Urgent Intervention**
- Conversation is about to derail
- Delivery: Immediate audio whisper + visual alert
- Example: "Stop — you're losing her. Acknowledge what she just said."

---

## Part 4: Intervention Types

### 4.1 Coaching Categories

#### A. **Observation Nudges**
What to notice that was missed:
- "She just said 'tired' — that's the pain word"
- "His energy dropped when you mentioned timeline"
- "Notice: she's looking for permission, not information"

#### B. **Question Suggestions**
What to ask next:
- "Ask: 'What does that cost you?'"
- "Go deeper: 'Tell me more about that'"  
- "Reflect back: 'So what I'm hearing is...'"

#### C. **Energy Calibrations**
How to shift approach:
- "More warmth, less authority right now"
- "She needs Zeus containment — be direct"
- "This is a Goddess moment — hold space"

#### D. **Step Navigation**
Where you are in the 4 Steps:
- "You're in Step 1 — don't pitch yet"
- "Pain is surfacing — stay in Step 2"
- "She's ready for Step 4 — move to agreement"

#### E. **Contamination Alerts**
What to avoid:
- "You're about to list — tell a story instead"
- "Don't ask how you can help — make a recommendation"
- "Skip the framework — give the zone action"

### 4.2 Intervention Format

**Structure:**
```
[CATEGORY] [BRIEF COACHING]
```

**Examples:**
- `[ENERGY] More Goddess — she's vulnerable`
- `[LISTEN] Pain word: "overwhelmed" — go there`
- `[STEP 2] Stay here — don't jump to solution`
- `[QUESTION] Ask: "What would change if you solved this?"`
- `[AVOID] Don't end with a question — take a position`

---

## Part 5: Intervention Delivery Mechanisms

### 5.1 Technical Architecture

Based on voice-server/server.js patterns:

```
┌─────────────────────────────────────────────────────────┐
│                    LIVE CALL                            │
├─────────────────────────────────────────────────────────┤
│  Speaker (Coach/Sales Rep)  ←→  Prospect               │
│         │                                               │
│         ├──── Audio Stream (Deepgram STT) ────────┐    │
│         │                                          │    │
│         │    ┌────────────────────────────────┐   │    │
│         │    │     RTI INTERVENTION ENGINE    │   │    │
│         │    │  ┌──────────────────────────┐  │   │    │
│         │    │  │  Trigger Detection       │  │   │    │
│         │    │  │  - Energy Analysis       │  │   │    │
│         │    │  │  - Pain Word Detection   │  │   │    │
│         │    │  │  - Step Tracking         │  │   │    │
│         │    │  │  - Contamination Check   │  │   │    │
│         │    │  └──────────────────────────┘  │   │    │
│         │    │  ┌──────────────────────────┐  │   │    │
│         │    │  │  Intervention Generator  │  │   │    │
│         │    │  │  - Pinecone RAG Query    │  │   │    │
│         │    │  │  - Coaching Synthesis    │  │   │    │
│         │    │  │  - Timing Calculation    │  │   │    │
│         │    │  └──────────────────────────┘  │   │    │
│         │    └────────────────────────────────┘   │    │
│         │                    │                    │    │
│         │    ┌──────────────────────────────┐    │    │
│         └────│     WHISPER CHANNEL          │────┘    │
│              │  (Screen overlay / Earpiece)  │         │
│              └──────────────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Delivery Channels

| Channel | Description | Best For |
|---------|-------------|----------|
| **Screen Overlay** | Text appears on screen visible only to speaker | Level 2-3 interventions, in-person or video calls |
| **Earpiece Whisper** | Audio played to speaker only | Level 3-4 interventions, phone calls |
| **Haptic Notification** | Vibration pattern on device | Silent attention-getter, Level 1-2 |
| **Visual Indicator** | Color-coded dashboard element | Ongoing state awareness (energy, step phase) |

### 5.3 Whisper Voice Characteristics

When using audio whisper:
- **Voice:** Calm, clear, minimal emotional charge (like a sports commentator, not a coach)
- **Pace:** Faster than normal speech (time is limited)
- **Volume:** Slightly below conversational (non-intrusive)
- **Brevity:** Maximum 8 words per intervention

---

## Part 6: Knowledge Integration (RAG)

### 6.1 Pinecone Knowledge Sources

From TOOLS.md, available indexes for RTI:

| Index | Namespace | Content | Use Case |
|-------|-----------|---------|----------|
| `ultimatestratabrain` | rtistratabrain | 1,787 RTI vectors | Intervention theory |
| `ultimatestratabrain` | igestratabrain | 2,920 IGE vectors | Group influence |
| `oracleinfluencemastery` | — | 505 vectors | 4-Step Model, influence patterns |
| `ublib2` | — | 41K vectors | Unblinded knowledge library |
| `athenacontextualmemory` | — | 11K vectors | Core Athena/Zone Action |

### 6.2 Real-Time Query Pattern

During a call, when an intervention trigger is detected:

1. **Extract context:** Last 30 seconds of conversation
2. **Generate query:** What intervention is needed?
3. **Query Pinecone:** Get relevant coaching wisdom
4. **Synthesize intervention:** Combine retrieved knowledge with context
5. **Deliver whisper:** Brief, actionable coaching

```python
async def generate_intervention(trigger, context, conversation_state):
    # 1. Query relevant knowledge
    query = f"coaching intervention for {trigger.type}: {context[-100:]}"
    knowledge = await query_pinecone('ultimatestratabrain', query, 
                                      namespace='rtistratabrain', top_k=2)
    
    # 2. Consider conversation step
    step_context = f"Currently in Step {conversation_state.current_step}"
    
    # 3. Generate intervention
    intervention = await llm_generate(
        prompt=f"""Generate a whisper coaching intervention.
        Trigger: {trigger.description}
        Context: {context}
        Phase: {step_context}
        Knowledge: {knowledge}
        
        Rules:
        - Maximum 8 words
        - Start with category in brackets
        - Be specific to what was just said
        - Give an action, not an observation
        """,
        max_tokens=30
    )
    
    return intervention
```

---

## Part 7: Conversation State Tracking

### 7.1 State Machine

The RTI engine must maintain a real-time model of where the conversation is:

```
┌─────────────────────────────────────────────────────────┐
│                 CONVERSATION STATE                       │
├─────────────────────────────────────────────────────────┤
│  Phase: STEP_2_TRUTH_TO_PAIN                            │
│  Phase Completion: 65%                                   │
│  ───────────────────────────────────────────────────    │
│                                                          │
│  Speaker State:                                          │
│  - Energy: Fun (40%) Aspirational (30%) Zeus (20%)      │
│  - Pace: 145 wpm (faster than optimal)                  │
│  - Last Pain Word Used: None in 45 seconds              │
│  - Questions Asked This Turn: 3 (too many)              │
│                                                          │
│  Prospect State:                                         │
│  - Energy: Low (voice quieter, shorter responses)       │
│  - Engagement: Declining (response length -40%)         │
│  - Pain Words Surfaced: "frustrated", "stuck"           │
│  - Objections Raised: "I need to think about it"        │
│                                                          │
│  Active Triggers:                                        │
│  - [WARNING] Energy mismatch detected                   │
│  - [ALERT] Pain word "stuck" not acknowledged           │
│  - [INFO] Step 2 incomplete, speaker moving to Step 3   │
│                                                          │
│  Intervention Queue:                                     │
│  1. [URGENT] "[LISTEN] Go back to 'stuck' — she's not   │
│              done"                                       │
│  2. [PROMPT] "[ENERGY] Slow down, match her pace"       │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Pain Word Detection

Pain words are the keys to Step 2. The system must detect and track:

**High-Value Pain Words:**
- Frustrated, stuck, overwhelmed, exhausted, worried
- Scared, uncertain, confused, lost
- Failing, struggling, drowning
- Trapped, hopeless, burning out

**Pain Phrase Patterns:**
- "I can't seem to..."
- "No matter what I try..."
- "I've been dealing with..."
- "The problem is..."
- "What keeps me up at night..."

### 7.3 Step Completion Criteria

**Step 1 — Emotional Rapport** (minimum 60% to proceed):
- ☐ Speaker matched prospect's energy
- ☐ Genuine acknowledgment given (specific to THIS person)
- ☐ Prospect relaxed (voice softer, pace slower)
- ☐ Prospect sharing more than asked

**Step 2 — Truth to Pain** (minimum 70% to proceed):
- ☐ Pain word identified and named
- ☐ Pain explored, not just acknowledged
- ☐ Prospect admits the real cost of the pain
- ☐ Prospect feels SEEN, not diagnosed

**Step 3 — Heroic Unique Identity** (minimum 65% to proceed):
- ☐ Speaker shared relevant story/case study
- ☐ Prospect sees their future in the speaker
- ☐ Differentiation established (not just credentials)
- ☐ Prospect asked "how" or "what would that look like"

**Step 4 — Agreement Formation**:
- ☐ Clear next step proposed
- ☐ Prospect verbally commits
- ☐ No hesitation in voice
- ☐ Follow-up locked with specificity

---

## Part 8: Avoiding Disruption

### 8.1 Anti-Patterns (What NOT to Do)

| Anti-Pattern | Why It Fails | Alternative |
|--------------|--------------|-------------|
| Intervening during prospect speech | Breaks speaker focus, causes them to lose thread | Wait for natural pause |
| Long interventions | Too much cognitive load | Maximum 8 words |
| Frequent interventions | Creates anxiety, undermines confidence | Maximum 1 per 60 seconds |
| Contradicting what speaker just said | Creates cognitive dissonance | Reframe as "And also consider..." |
| Telling speaker what to say verbatim | Removes authenticity | Suggest direction, not script |
| Alarming language | Creates panic | Calm, neutral tone always |

### 8.2 Confidence Preservation

The person receiving coaching must feel **supported**, not **controlled**:

- **Affirmation before correction:** "Good rapport — now go to the pain"
- **Suggestion, not command:** "Consider asking..." vs "Ask her..."
- **Trust their recovery:** If they don't take the suggestion, don't repeat
- **Post-call, not mid-call criticism:** Save detailed feedback for debrief

### 8.3 Graceful Degradation

When intervention cannot be delivered (technical issues, timing, etc.):
1. Log the trigger for post-call review
2. Do not attempt delayed intervention (moment has passed)
3. Increase observation frequency for remaining call
4. Prioritize post-call debrief quality

---

## Part 9: Calibration with Real Outcomes

### 9.1 The Colosseum Correlation Problem

From `innovation_rd_client_facing` scenario:
> "The Colosseum judges are giving scores that don't correlate with real-world outcomes. A being that scores 8.5 in the Colosseum only converts 5% of real calls."

**RTI must be calibrated against actual conversion data, not theoretical scores.**

### 9.2 Intervention Effectiveness Tracking

For every intervention delivered:
1. **Record intervention:** Type, trigger, timing, content
2. **Record speaker response:** Taken, ignored, modified
3. **Record outcome:** Did conversation improve?
4. **Record call result:** Converted, not converted, follow-up scheduled

Over time, this creates a feedback loop:
- Which intervention types are most effective?
- Which triggers lead to successful outcomes?
- Which timing windows work best?
- Which speakers benefit most from RTI?

### 9.3 Calibration Formula

```
Intervention_Effectiveness = 
    (Interventions_Taken × Positive_Outcome_Rate) /
    (Total_Interventions × Baseline_Conversion_Rate)
```

If effectiveness < 1.0: Intervention is hurting, not helping
If effectiveness = 1.0: Intervention is neutral
If effectiveness > 1.0: Intervention is adding value

---

## Part 10: Implementation Roadmap

### Phase 1: Detection Foundation
- [ ] Implement real-time transcription pipeline (Deepgram)
- [ ] Build pain word detection system
- [ ] Create energy analysis module (pace, tone, volume)
- [ ] Establish step tracking state machine

### Phase 2: Intervention Generation
- [ ] Connect Pinecone RAG for coaching knowledge
- [ ] Build intervention synthesis prompt templates
- [ ] Implement 8-word constraint enforcement
- [ ] Create urgency level classification

### Phase 3: Delivery Mechanisms
- [ ] Build whisper audio channel (separate from main call)
- [ ] Create screen overlay component
- [ ] Implement haptic notification system
- [ ] Design visual dashboard for ongoing state

### Phase 4: Calibration Loop
- [ ] Integrate with Bland.ai outcome data
- [ ] Build intervention tracking database
- [ ] Create effectiveness calculation pipeline
- [ ] Implement adaptive threshold tuning

### Phase 5: Multi-Party Support
- [ ] Handle calls with multiple speakers
- [ ] Support group coaching scenarios
- [ ] Enable supervisor observation mode
- [ ] Build training simulation environment

---

## Part 11: Example Intervention Scenarios

### Scenario A: Missed Pain Word

**Context:** Sales call for Unblinded Mastery Program
**Transcript:**
> Prospect: "I'm making good money, but honestly I feel stuck. I've been doing the same thing for 10 years."
> Speaker: "That's great that you've been successful. So tell me about your goals for the next year."

**Trigger:** Pain word "stuck" not acknowledged
**Intervention:** `[LISTEN] She said "stuck" — go there`
**Desired Response:** Speaker pauses, says "Wait, you said you feel stuck. Tell me more about that."

### Scenario B: Energy Mismatch

**Context:** Discovery call for ACT-I
**Transcript:**
> Prospect: (slowly, quietly) "We've tried three different AI solutions. None of them worked."
> Speaker: (enthusiastically) "ACT-I is completely different! Let me tell you about our unique approach—"

**Trigger:** Energy mismatch — prospect is deflated, speaker is too high
**Intervention:** `[ENERGY] Match her energy — slow down`
**Desired Response:** Speaker lowers energy, says "That sounds frustrating. What happened?"

### Scenario C: Premature Step Jump

**Context:** QBR with client considering cancellation
**Transcript:**
> Prospect: "I'm not seeing the results I expected."
> Speaker: "I understand. Let me show you our new features that will help—"

**Trigger:** Jumping to Step 3 (HUI) without completing Step 2 (exploring the pain)
**Intervention:** `[STEP 2] Stay in pain — what results did he expect?`
**Desired Response:** Speaker asks "What results were you expecting when you started?"

### Scenario D: Contamination Alert

**Context:** Closing conversation for Callagy Recovery
**Transcript:**
> Prospect: "So how does this work?"
> Speaker: "Great question! Let me walk you through our three-phase process. Phase one is..."

**Trigger:** Contamination detected — "Great question" + listing phases
**Intervention:** `[AVOID] Skip the phases — tell a client story`
**Desired Response:** Speaker says "Let me tell you about Dr. Chen. He was in your exact situation..."

---

## Part 12: Success Metrics

### 12.1 RTI System Health

| Metric | Target | Measurement |
|--------|--------|-------------|
| Intervention Latency | <3 seconds from trigger | System timer |
| Detection Accuracy | >85% true positive rate | Human review sample |
| Speaker Adoption Rate | >60% interventions taken | Log analysis |
| Disruption Rate | <5% reported as disruptive | Speaker feedback |
| Knowledge Relevance | >4.0/5.0 average | Speaker rating |

### 12.2 Business Impact

| Metric | Target | Measurement |
|--------|--------|-------------|
| Conversion Rate Lift | +15% vs baseline | A/B test |
| Call Duration Change | No increase >10% | Call data |
| Follow-Up Rate | +20% vs baseline | CRM data |
| Speaker Confidence | Increase over time | Survey |
| Training Time Reduction | -30% to proficiency | Cohort analysis |

---

## Conclusion

Real-Time Intervention is the bridge between the Colosseum's simulated training and actual call performance. It takes the 39 components of the Unblinded Formula and applies them in the moment — not as post-call critique, but as in-call coaching.

The core principle remains: **Intervention should enhance the speaker's mastery, not replace it.**

When done well, RTI creates a flywheel:
1. Speakers perform better on calls
2. Better performance creates better outcomes
3. Better outcomes create confidence
4. Confidence reduces intervention needs
5. Reduced intervention needs prove mastery

The end state: Beings that can guide humans to influence mastery in real-time, until the humans no longer need the guidance.

---

*"Listen to everything that is being said and what is not being said. If their energy shifts — the body language went down, their voice got a little bit tighter — you can infer something about that."*
— Unblinded Formula, Level 5 Listening

---

## Appendix: Quick Reference Card

### Intervention Categories
- `[LISTEN]` — Something was missed
- `[ENERGY]` — Calibration needed
- `[STEP X]` — Navigation guidance
- `[QUESTION]` — What to ask
- `[AVOID]` — Contamination alert
- `[ACKNOWLEDGE]` — Recognition needed

### Timing Rules
- Wait 2-3 seconds after trigger
- Never during prospect speech
- Maximum 1 intervention per 60 seconds
- Maximum 8 words per intervention

### Urgency Levels
1. Observe only (log for debrief)
2. Soft whisper (text, no audio)
3. Prompt whisper (text + gentle audio)
4. Urgent intervention (immediate audio + visual)

### Stop Conditions
- Speaker requests silence
- Conversation is going well (no triggers)
- Technical failure (log and observe)
- Post-agreement phase (don't interrupt close)
