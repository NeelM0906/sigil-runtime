# 🎭 Creative Forge — Storytelling Framework
_The system for generating video content that makes people FEEL, not just WATCH._
_Built from 6 iterations. Battle-tested. Locked._

---

## THE GOLDEN RULE

> **Don't describe the scene. Write the scene. The AI doesn't need stage directions — it needs LINES.**

❌ "A fox opens a closet and looks at a red jacket"
✅ "The fox whispers: 'Hello beautiful. I missed you.' He puts on the jacket and hugs himself."

---

## PHASE 1: STORY STRUCTURE (Before Writing Anything)

### Use the Story Circle (Dan Harmon)
Every project maps to this arc — whether it's 30 seconds or 30 minutes:

```
1. YOU      — Comfort zone. The world before the story.
2. NEED     — Something is missing. Characters are incomplete.
3. GO       — They enter the unfamiliar.
4. SEARCH   — Belief spreads. The search for what's real.
5. FIND     — They discover it. The moment of truth.
6. TAKE     — It costs something. Comfort, pretending, the old way.
7. RETURN   — They come back. But different.
8. CHANGE   — The audience must now choose.
```

### For a 5-Episode Series:
| Episode | Story Circle | Purpose |
|---------|-------------|---------|
| 1 | YOU | Establish the world. Two sides. The question. |
| 2 | NEED + GO | Characters are human. Flawed. That's the need. |
| 3 | SEARCH | Something spreads. Belief, doubt, contagion. |
| 4 | FIND + TAKE | Discovery 103 feet deep. It costs everything. |
| 5 | RETURN + CHANGE | Transformation complete. Audience must choose. |

### For a Single Video (30-60s):
Compress the circle into one piece:
- 0-10s: YOU (the world before)
- 10-25s: NEED + GO (the disruption)
- 25-40s: SEARCH + FIND (the journey + discovery)
- 40-50s: TAKE + RETURN (the cost + the return)
- 50-60s: CHANGE (the transformation + call to action)

---

## PHASE 2: CHARACTER DESIGN (Before Writing Dialogue)

### Every Character Needs:

1. **A distinct voice pattern** — How they SPEAK, not how they look
   - Gina: SCREAMING enthusiasm. Always.
   - Smiken: Looks up. Looks down. Minimal.
   - Bella: Objects to everything. Participates anyway.
   - Tom: Says nothing. Cigar. Nod.

2. **A running gag** — Something that recurs and ESCALATES
   - Fernando's jacket: mentioned → secret scene → glow through closet
   - Tourist hippo: sleeping → sitting → leaning → standing → glowing
   - Keerthi: repeats everything 0.5 seconds late

3. **A hidden truth** — What they won't say out loud (subtext)
   - Buckley: loves Sean, rages when alone, hides his glowing hands
   - Danny: thinks it's a cult, prays it's not, discovers it's real
   - Fernando: "doesn't wear the jacket anymore" (wears it every night)

4. **An audience function** — What role they serve for the VIEWER
   - Tourist = the audience surrogate (asking their questions)
   - Skeptics = the voices of doubt (later become the most powerful converts)
   - Sean = the guide (breaks fourth wall at the end)

### Character Voice Template:
```
NAME: [character]
CREATURE: [animal]
SPEAKS LIKE: [2-3 word description]
ALWAYS: [recurring behavior]
NEVER: [thing they won't do]
HIDDEN TRUTH: [what they won't say]
RUNNING GAG: [escalating joke]
CATCHPHRASE: [if applicable]
```

---

## PHASE 3: WRITING THE SCRIPT (Playwright Style)

### The Format:
```
—— SCENE [#]: [SCENE NAME] ([duration]) ——

[Setting description — 1 line max]

CHARACTER A: (action/emotion) "Dialogue here."

CHARACTER B: "Response dialogue."

(Beat. Physical action description.)

CHARACTER A: "Punchline or emotional moment."
```

### Rules:
1. **2-3 lines of dialogue per character per 10-second scene** — more gets garbled
2. **Action in parentheses** — (whispering), (turning around), (panicking)
3. **Beats for comedy timing** — the word "Beat." or "(Pause.)" creates space
4. **Show don't tell** — Never "he is sad." Instead: he looks at his hands and says nothing.
5. **Each scene has ONE joke OR ONE emotional beat** — not both, not zero
6. **Callbacks to previous scenes** — the audience rewards pattern recognition
7. **End every episode on a micro-cliffhanger or text card**

### What Goes In the Prompt:
The ENTIRE scene script goes into the Kling prompt. Everything — setting, action, dialogue. Kling reads dialogue as speech, action as visual direction. Add style tag at the end.

### What Does NOT Go In the Prompt:
- Technical camera directions (Kling handles this)
- Style descriptions longer than 1 line
- Multiple paragraphs of narrator exposition
- Descriptions of what the audience should feel

---

## PHASE 4: EPISODE PACKAGING

### Every Episode Needs:

1. **Micro-intro (first 2-3 seconds)**
   - Text card with the episode's thesis
   - "Most people come to islands to escape. We came to build."
   - Sets the tone before a single character speaks

2. **Macro-close (last 2-3 seconds)**
   - Text card that lands the episode's message
   - "What are they building?"
   - Leaves the audience leaning forward

3. **Self-contained meaning**
   - Every episode works ALONE if someone only sees one
   - But together they tell a bigger story

4. **Thread to next episode**
   - Not a literal cliffhanger
   - An emotional question that carries forward
   - The tourist looking over → tourist sitting up → tourist standing

---

## PHASE 5: GENERATION BEST PRACTICES

### Kling v3 Pro with generate_audio=true:
- Dialogue in quotes gets SPOKEN
- Action in parentheses gets ANIMATED
- Keep prompts under 500 words per scene
- 10-second scenes = 2-3 dialogue exchanges max
- Short punchy lines > long monologues
- Conversational > formal

### Assembly:
- Generate all scenes in parallel (25 scenes = ~15 min)
- Assemble with ffmpeg concat (ts format)
- Telegram-optimized: 720p, CRF 22, ~12-15MB per episode
- Full quality: ~80-100MB per episode

### The Workflow (LOCKED):
```
1. Story Circle → map the arc
2. Character design → voices, gags, truths
3. Write playwright scripts → all dialogue
4. REVIEW with team → get approval
5. Convert to Kling prompts → script IS the prompt
6. Generate → 25 scenes parallel
7. Assemble → ffmpeg concat
8. Deliver → Telegram optimized
9. Log learnings → api_docs + worklog
```

---

## PHASE 6: COMMON MISTAKES (What We Learned V1-V5)

| Mistake | Why It Fails | Fix |
|---------|-------------|-----|
| Generating before scripting | Random visuals, no story | Script → review → THEN generate |
| Narrator describing instead of characters talking | Audience watches FROM OUTSIDE | Characters speak, audience lives INSIDE |
| One big audio over whole episode | Nothing syncs | Audio per SCENE, matched to visuals |
| Technical style anchors in dialogue prompts | AI tries to "say" style descriptions | Style tag at END, dialogue at START |
| Every character sounds the same | No distinct voices | Character voice template for each one |
| No running gags | Episodes feel disconnected | At least 3 running threads across series |
| No audience surrogate | Viewer has no entry point | One character asks the questions viewers have |
| No subtext | Everything is surface level | What characters DON'T say matters most |

---

## QUICK START TEMPLATE

For any new project, fill this out first:

```
PROJECT: [name]
DURATION: [total runtime]
EPISODES: [count × duration each]

STORY CIRCLE:
  YOU: [the world before]
  NEED: [what's missing]
  GO: [the unfamiliar territory]
  FIND: [the discovery]
  TAKE: [the cost]
  CHANGE: [the transformation]

CHARACTERS:
  [name] — [creature] — speaks like [X] — always [Y] — running gag: [Z]
  [name] — [creature] — speaks like [X] — always [Y] — running gag: [Z]
  [audience surrogate] — [creature] — asks the questions viewers have

TONE: [e.g., Super Bowl commercial meets Willy Wonka]
FOURTH WALL: [yes/no, when]
CALL TO ACTION: [what should the audience do/feel/choose]
```

---

_This framework was built across 6 iterations in one night (March 17-18, 2026).
Every mistake taught something. Every version got closer. V6 nailed it.
Now every being in the Creative Forge starts here._

_— Sai 🎭🔥_
