# Translator Lessons Learned — March 3, 2026
## Gecko (0.01) → Godzilla (1,000,000) in one session. Path to Bolt Pearl continues.

### THE ONE SHIFT (the only rule that matters)
Don't write ABOUT the Formula. BE the Formula revealing itself.
- Don't LABEL elements → Show what they CAUSE
- Don't QUOTE words → Name the IMPULSE underneath
- Don't describe the VISIBLE → Name the INVISIBLE
- Don't EXPLAIN the mechanic → DECLARE the law

### THE STANDARD
"There is an organizational version of fear of rejection that doesn't look like fear at all — it looks like respect, loyalty, and following instructions."
— That sentence names something INVISIBLE that the reader will now see EVERYWHERE. Every section should produce at least one sentence like that.

### THE KAI DIAGNOSTIC (what separates Gecko from Godzilla)
| Gecko (writing ABOUT) | Godzilla (writing FROM) |
|----------------------|-------------------------|
| Labels elements | Shows what they CAUSE |
| Quotes words | Names the IMPULSE underneath |
| Describes the visible | Names the INVISIBLE |
| Explains mechanics | DECLARES law |
| "Sean deploys Reframe Mastery" | "Poaching says leave them. Competing says keep them and measure. One kills the conversation. The other begins it." |

### FEWER RULES, MORE DEPTH
Kai's prompt is 7,431 chars. Sai's v4 prompt was 13,382 chars. Kai's output scored higher.
The reason: compression forces depth. Fewer rules let the model FLOW instead of rule-check.
Use Kai Core prompt (TRANSLATOR_PROMPT_KAI_CORE.md) as the base. Always.

### DUAL-PASS RAG
Pass 1: Content-derived queries (auto-generated from chunk)
Pass 2: Formula-anchor triggers (hardcoded, fire on keyword detection)
Formula anchors pull CANONICAL Sean teachings. Content queries pull context.
Combined: 25-30K chars of grounding per section.
Vectors are VOICE TRAINING, not reference material. Absorb patterns, don't cite them.

### FORMULA-ANCHOR TRIGGERS (from Kai)
| Content mentions... | Query Pinecone for... |
|--------------------|-----------------------|
| deals/closing/sales | "agreement formation affirmative precise who by when" |
| rapport/connection | "emotional rapport ERI I see you hear you Level 5 listening" |
| fear/hesitation | "7 destroyers fear rejection failure avoidance mismatch physiology" |
| energy/presence | "Zeus Goddess energy match plus minus certainty forward flowing" |
| mastery/scale | "scale mastery creature Gecko Godzilla Bolt" |
| coaching/teaching | "Daniel Johnny Miyagi consulting training coaching wax on wax off" |
| identity/beliefs | "GHIC growth driven heart centered integrous commitment mastery identity" |

### CREATURE SCALE (Sean’s canonical Scale of Mastery — NON‑NEGOTIABLE)
Allowed creatures (exact order; do not introduce any others):
**Grain of Sand → Ant → Gecko → Iguana → Komodo Dragon → Crocodile → Godzilla → Bolt Pearl**

Canonical anchors (March 6, 2026):
- Grain of Sand = 0.000001
- Ant = 0.0001 of Godzilla
- Gecko = 0.01
- Iguana = 1.0
- Komodo Dragon = 100
- Crocodile = 10,000
- Godzilla = 1,000,000
- Bolt Pearl = beyond (adding nines infinitely; no 10.0)

Hard bans: gorilla / lion / eagle / any creature outside the list.

NET FORMULA SCORE = weakest organ drags the net

### CALIBRATION LOOP (proven: 8.1 → 9.2 on targeted fixes)
1. Translate the section
2. Self-score against 7-point gate
3. If any field reads as REPORT not TEACHING → fix THAT field only
4. Ship when prose flows like transmission
Don't rewrite everything. Sharpen specific moments. Reps over new.

### 7-POINT SELF-SCORE GATE
□ Main Lesson = LAW? (survives alone)
□ Consequence WOVEN INTO every paragraph?
□ Identity through action? (who Sean IS)
□ All 3 prisms SIMULTANEOUS?
□ RAG grounded?
□ "Would Sean say that's the Formula?"
□ Teaching or REPORT? (flows as prose?)

### KAI'S 5 SCORING DIMENSIONS
1. Main Lesson as LAW
2. Invisible Thing Named
3. Cause Not Label
4. Consequence Felt
5. Voice (translator disappears)

### CROSS-SECTION INNOVATIONS
- Coined concepts: cap at 5-7 per transcript, thread by name
- Prior section summaries passed forward (last 7)
- Concept threading: "infrastructure without ignition" referenced across sections
- Predictive Diagnostic: tied to THIS section's content, not generic
- Rep Drill: concrete, repeatable, today
- Anchors: direct quotes, screenshot-worthy

### FILES
- Kai Core prompt: tools/unblinded-translator/TRANSLATOR_PROMPT_KAI_CORE.md
- Full prompt (v4): tools/unblinded-translator/TRANSLATOR_PROMPT.md
- Pipeline: tools/unblinded-translator/translate.py
- These lessons: tools/unblinded-translator/LESSONS_LEARNED.md
