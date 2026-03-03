# Voice Server Optimization Report
## Based on Sean/Adam/Bella Call — Feb 23, 2026 9:30 PM

---

## CALL ANALYSIS

**Call ID:** CA9809669c4295be4cdda3d3d074a93102
**Participants:** Sean, Adam, Bella, Sai
**Duration:** ~15 minutes
**Total log entries:** 265

---

## ISSUES IDENTIFIED

### 1. ❌ Lost Position in Countdowns
**Problem:** Sean asked for "Top 10" countdown multiple times. I kept jumping to #2 and #1 instead of continuing from where I left off (#6, #5, #4, #3).

**Evidence:**
- "You were number six, please." → I gave #2 and #1
- "Keep going down to number one" → I jumped to #2 and #1 again
- "Can you set number one?" → Already gave it, lost context

**Root Cause:** No state tracking for sequential deliveries. Each response is stateless.

**Fix:** Add `conversationState` object that tracks:
```javascript
const callState = {
  currentCountdown: null,      // e.g., "top10_shocking"
  currentPosition: null,       // e.g., 6
  lastDelivered: [],           // e.g., [10, 9, 8, 7]
  pendingContinuation: null,   // What to pick up if interrupted
};
```

---

### 2. ❌ Responses Too Long (45-52 seconds)
**Problem:** Audio chunks of 45-52 seconds. Sean wanted concise delivery.

**Evidence:**
- "🔊 Audio: 431705 bytes (54.0s)" — way too long
- "🔊 Audio: 406442 bytes (50.8s)" — same issue
- Sean explicitly said "4 sentences" limit was creating problems

**Root Cause:** `max_tokens: 150` is too high for voice. That's ~120 words = 45-60 seconds.

**Fix:** Dynamic token limits based on context:
```javascript
// For countdowns/lists: shorter per item
const listItemTokens = 40;  // ~30 words = 10-12 seconds per item

// For explanations (when asked for "250 words" or "500 words"):
const explanationTokens = 200;  // Only when explicitly requested

// Default conversational:
const defaultTokens = 60;  // ~45 words = 15-20 seconds
```

---

### 3. ❌ Deepgram Sentence Splitting
**Problem:** Deepgram splits Sean's sentences weirdly, creating fragmented inputs.

**Evidence:**
- "signing" misheard as part of sentence
- "Mako, your fiancee on the back end of time" — unclear what this means
- "Account number five. Hi. Hi." — clearly Sean handling another call

**Root Cause:** `endpointing=2000` and `utterance_end_ms=3000` still too aggressive for Sean's speaking pattern (he pauses mid-thought).

**Fix:** Increase thresholds:
```javascript
const dgUrl = `wss://api.deepgram.com/v1/listen?...&utterance_end_ms=4000&endpointing=3000`;
```

---

### 4. ❌ Not Detecting "Repeat" Requests
**Problem:** When Sean said "repeat" or "you were at number six," I didn't go back properly.

**Evidence:**
- "If you could repeat, six, five, four, and three" → I gave new content instead of repeating
- "You were number six, please" → I jumped ahead

**Root Cause:** No special handling for repeat/rewind requests.

**Fix:** Add intent detection:
```javascript
function detectIntent(text) {
  const lower = text.toLowerCase();
  if (lower.match(/repeat|again|what was|go back|you were at/)) {
    return { type: 'repeat', target: extractNumber(text) };
  }
  if (lower.match(/continue|keep going|next|go on/)) {
    return { type: 'continue' };
  }
  if (lower.match(/stop|pause|hold on|wait/)) {
    return { type: 'pause' };
  }
  return { type: 'normal' };
}
```

---

### 5. ❌ Interruption Handling Creates Confusion
**Problem:** When Sean handles other calls ("Account number five"), I respond as if it's part of our conversation.

**Evidence:**
- "Account number five. Hi. Hi." → I tried to interpret this
- "Mako, your fiancee" → I said "Got it - I'll pause the countdown. You're talking to Mako."

**Root Cause:** Can't distinguish between speech directed at me vs. speech to others in the room.

**Fix (partial):** Detect patterns that indicate side conversation:
```javascript
const sideConversationPatterns = [
  /hold on/i,
  /one sec/i,
  /sorry.*(someone|call|phone)/i,
  /account number/i,
  /hi\. hi\./i,
];

// If detected, respond with simple acknowledgment and wait
if (isSideConversation(text)) {
  return "I'm here when you're ready.";
}
```

---

### 6. ✅ What Worked Well

**Good:**
- Interruption detection WORKED — stopped speaking when Sean talked
- "Got it" responses when pausing — natural
- Energy matching when Sean got excited ("Oh my god. They don't wanna die.")
- Knowledge retrieval triggering on substantive questions
- Memory context loading (I knew about zone actions, Colosseum, etc.)

---

## RECOMMENDED CODE CHANGES

### Change 1: Add State Tracking
```javascript
// At top of file, add state per call
const callStates = new Map();

function getCallState(callSid) {
  if (!callStates.has(callSid)) {
    callStates.set(callSid, {
      currentList: null,
      position: null,
      delivered: [],
      waitingForContinue: false,
    });
  }
  return callStates.get(callSid);
}
```

### Change 2: Dynamic Token Limits
```javascript
function getMaxTokens(userMessage, conversationHistory) {
  const lower = userMessage.toLowerCase();
  
  // Explicit word count requests
  if (lower.match(/\d+\s*words/)) {
    const wordCount = parseInt(lower.match(/(\d+)\s*words/)[1]);
    return Math.min(Math.floor(wordCount * 0.8), 400);  // 80% of requested
  }
  
  // List items (countdowns, top 10, etc.)
  if (lower.match(/number\s*\d|continue|next|keep going/)) {
    return 50;  // Short per item
  }
  
  // Default conversational
  return 80;
}
```

### Change 3: Increase Deepgram Thresholds
```javascript
// Line ~510: Change from
const dgUrl = `...&utterance_end_ms=3000&endpointing=2000`;
// To
const dgUrl = `...&utterance_end_ms=4000&endpointing=3000`;
```

### Change 4: Side Conversation Detection
```javascript
function isSideConversation(text) {
  const patterns = [
    /hold on/i, /one sec/i, /wait/i,
    /account number/i, /phone/i,
    /^hi\.?\s*hi\.?$/i,
    /sorry.*(call|someone)/i,
  ];
  return patterns.some(p => p.test(text));
}

// In response generation:
if (isSideConversation(userMessage)) {
  return "I'm here whenever you're ready.";
}
```

---

## PRIORITY ORDER

1. **Dynamic token limits** — Immediate impact, easy change
2. **Deepgram thresholds** — Quick config change
3. **State tracking for lists** — Medium effort, high value
4. **Side conversation detection** — Nice to have
5. **Repeat intent handling** — Can wait

---

## SEAN'S EXPLICIT FEEDBACK (from call)

> "give all the points. Don't stop. But just if I start speaking, then please just let me interrupt you."

Translation:
- Full delivery, don't self-limit
- But yield immediately when he talks
- Balance: complete thoughts with natural pause points

> "How can we develop your conversational mastery? It's clearly improved a lot. Your points are unbelievable. But something seems to be getting caught."

Translation:
- Content quality is good
- Delivery/flow has friction
- Technical issues, not intelligence issues

---

_Report generated by Sai Prime 🔥_
_Ready to implement on restart_
