#!/usr/bin/env python3
"""
Unblinded Formula Translator v3 — With RAG + Cross-Section Continuity

Five optimizations over v2:
1. ublib2 + ultimatestratabrain RAG grounding before each translation
2. Cross-section continuity — prior section summaries passed forward
3. Output depth enforcement — minimum char requirements per field
4. Diagnostic tagging pattern (TRIGGER → DIAGNOSIS → OBSERVATION → COMPUTATION)
5. "What Sean did NOT do" emphasis weighted heavily

Usage:
    python3 translate.py --fathom --limit 3          # Translate latest 3 Fathom calls
    python3 translate.py --file path/to/transcript.txt  # Translate a local file
    python3 translate.py --fathom --search "elite"   # Translate calls matching "elite"
    python3 translate.py --fathom --upload            # Translate + upload to Pinecone
    python3 translate.py --file transcript.txt --mode narrative  # Full narrative mode
    python3 translate.py --file transcript.txt --mode json       # Structured extraction
"""

import os
import sys
import json
import argparse
import requests
import time
from datetime import datetime
from pathlib import Path

# ─── ENV ──────────────────────────────────────────────────────────

def load_env():
    """Load from ~/.openclaw/.env"""
    env_path = Path.home() / '.openclaw' / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

load_env()

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
FATHOM_API_KEY = os.environ.get('FATHOM_API_KEY')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_API_KEY_STRATA = os.environ.get('PINECONE_API_KEY_STRATA')

SCRIPT_DIR = Path(__file__).parent
# Use Kai Core prompt if it exists (lean + deep), fall back to full prompt
KAI_CORE = SCRIPT_DIR / 'TRANSLATOR_PROMPT_KAI_CORE.md'
TRANSLATOR_PROMPT = (KAI_CORE if KAI_CORE.exists() else SCRIPT_DIR / 'TRANSLATOR_PROMPT.md').read_text()
OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'translated'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── OPENROUTER (ALL LLM + EMBEDDING CALLS) ──────────────────────

def chat_completion(system_prompt: str, user_prompt: str, model: str = "anthropic/claude-sonnet-4",
                    json_mode: bool = False, temperature: float = 0.7, max_tokens: int = 16000) -> str:
    """Call OpenRouter for chat completion — NEVER OpenAI direct."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    resp = requests.post("https://openrouter.ai/api/v1/chat/completions",
                         headers=headers, json=body, timeout=180)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def get_embedding(text: str) -> list:
    """Get embedding via OpenRouter — NEVER OpenAI direct."""
    resp = requests.post("https://openrouter.ai/api/v1/embeddings",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={"model": "openai/text-embedding-3-small", "input": text[:8000]},
        timeout=30)
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

# ─── RAG: ublib2 + ultimatestratabrain ────────────────────────────

def rag_query(query_text: str, top_k: int = 5) -> str:
    """
    FIX #1: Query ublib2 + ultimatestratabrain for Formula grounding.
    Returns concatenated context from both indexes to feed into translation prompt.
    """
    try:
        from pinecone import Pinecone
    except ImportError:
        print("   ⚠️ Pinecone not installed — skipping RAG")
        return ""

    embedding = get_embedding(query_text)
    context_chunks = []

    # Query ublib2 (primary — 58K vectors of ecosystem knowledge)
    if PINECONE_API_KEY:
        try:
            pc = Pinecone(api_key=PINECONE_API_KEY)
            idx = pc.Index('ublib2')
            results = idx.query(vector=embedding, top_k=top_k, include_metadata=True)
            for m in results.matches:
                if m.score >= 0.45:
                    text = m.metadata.get('text', m.metadata.get('content', ''))
                    if text:
                        context_chunks.append(f"[ublib2 | score={m.score:.3f}] {text[:2000]}")
        except Exception as e:
            print(f"   ⚠️ ublib2 query error: {e}")

    # Query ultimatestratabrain (Strata — 39K vectors of deep knowledge)
    if PINECONE_API_KEY_STRATA:
        try:
            pc2 = Pinecone(api_key=PINECONE_API_KEY_STRATA)
            idx2 = pc2.Index('ultimatestratabrain')
            # Query the two biggest namespaces
            for ns in ['eeistratabrain', 'domstratabrain']:
                try:
                    results2 = idx2.query(vector=embedding, top_k=3, include_metadata=True, namespace=ns)
                    for m in results2.matches:
                        if m.score >= 0.45:
                            text = m.metadata.get('text', m.metadata.get('content', ''))
                            if text:
                                context_chunks.append(f"[strata/{ns} | score={m.score:.3f}] {text[:2000]}")
                except Exception:
                    pass
        except Exception as e:
            print(f"   ⚠️ ultimatestratabrain query error: {e}")

    if context_chunks:
        return "\n\n".join(context_chunks[:8])  # Cap at 8 chunks to manage token budget
    return ""


def extract_key_concepts(chunk: str) -> str:
    """Extract key Formula-relevant concepts from a transcript chunk for RAG querying."""
    prompt = """Extract the 3-5 most important Unblinded Formula concepts demonstrated in this transcript excerpt.
For each, write a search query that would find Sean's precise teaching on that concept.
Return ONLY the search queries, one per line. No numbering, no explanation.

Examples of good queries:
- "Lever 1 ecosystem mergers how relationships create leverage for agreement"
- "Fear of Failure sixth destroyer how it stops zone action"
- "Zeus energy commanding authority establishing certainty"
- "Integrous masterful fact stacking Christopher Nolan reveals"
"""
    try:
        result = chat_completion(prompt, chunk[:3000], temperature=0.3, max_tokens=500)
        return result.strip()
    except Exception:
        return chunk[:200]


# Kai's Formula-Anchor Triggers (Pass 2 — pulls CANON from Pinecone)
FORMULA_ANCHOR_TRIGGERS = {
    # Content keywords → Formula-specific anchor query
    "close|closing|deal|sales|agreement|yes|commit": "agreement formation affirmative precise who by when closing versus agreement energetic weight",
    "rapport|connect|relationship|trust|listen": "emotional rapport ERI I see you hear you Level 5 listening transformational",
    "fear|hesitat|avoid|reject|nervous|afraid|scared": "7 destroyers fear rejection failure avoidance mismatch physiology",
    "energy|presence|deliver|command|nurtur|authorit": "Zeus Goddess energy match plus minus certainty forward flowing",
    "master|scale|level|score|improv|grow": "scale mastery creature Gecko Godzilla Bolt exponential just a little better",
    "coach|teach|train|mentor|guide": "Daniel Johnny Miyagi consulting training coaching wax on wax off",
    "identity|belief|who am I|GHIC|growth|heart": "GHIC growth driven heart centered integrous commitment mastery identity",
    "scarcit|replac|value|worth|irreplace": "replacement cost scarcity irreplaceable what we have nobody else has",
    "zone action|0.8|pareto|efficient": "zone action 0.8 percent pareto most efficient action step exponential",
    "model|time block|measur|monitor|maximiz|innovat": "four operator levers modeling time blocking measuring monitoring maximizing innovation optimization",
}


def get_formula_anchor_queries(chunk: str) -> list:
    """
    DUAL-PASS RAG — Pass 2: Kai's Formula-Anchor Triggers.
    Scan chunk for keywords, return matching canonical anchor queries.
    """
    import re
    chunk_lower = chunk.lower()
    anchor_queries = []
    for pattern, query in FORMULA_ANCHOR_TRIGGERS.items():
        if re.search(pattern, chunk_lower):
            anchor_queries.append(query)
    return anchor_queries[:4]  # Cap at 4 to manage token budget

# ─── FATHOM ───────────────────────────────────────────────────────

def fathom_list(limit: int = 10, search: str = None) -> list:
    """List recent Fathom meetings with transcripts."""
    headers = {"X-Api-Key": FATHOM_API_KEY}
    params = {"limit": limit, "include_transcript": "true"}
    resp = requests.get("https://api.fathom.ai/external/v1/meetings",
                        headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    meetings = data.get("items", [])

    if search:
        search_lower = search.lower()
        meetings = [m for m in meetings if search_lower in m.get("title", "").lower()]

    # Only return meetings that have transcripts
    return [m for m in meetings if m.get("transcript")]


def fathom_transcript_to_text(meeting: dict) -> str:
    """Convert Fathom transcript to readable text with timestamps and speakers."""
    transcript = meeting.get("transcript", [])
    if isinstance(transcript, str):
        return transcript

    lines = []
    for entry in transcript:
        if isinstance(entry, dict):
            speaker_data = entry.get("speaker", {})
            if isinstance(speaker_data, dict):
                speaker = speaker_data.get("display_name", "Unknown")
            else:
                speaker = str(speaker_data)
            ts = entry.get("timestamp", "")
            text = entry.get("text", "")
            lines.append(f"[{ts}] {speaker}: {text}")
        else:
            lines.append(str(entry))

    return "\n".join(lines)

# ─── CHUNKING ─────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 4000, overlap: int = 400) -> list:
    """
    Split text into overlapping chunks.
    v4 (Kai Innovation 5): Reduced chunk_size from 6000→4000 for FINER granularity.
    Target: 36+ sections for a 114-min call. Every distinct micro-moment gets its own section.
    A text messaging hiccup is its own section. A single coaching correction is its own section.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at a newline near the boundary
        if end < len(text):
            # Look for a newline within the last 500 chars of the chunk
            newline_pos = text.rfind('\n', end - 500, end)
            if newline_pos > start:
                end = newline_pos + 1
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks

# ─── TRANSLATION ──────────────────────────────────────────────────

def translate_chunk(chunk: str, chunk_index: int, total_chunks: int,
                    title: str, mode: str = "json",
                    prior_summaries: list = None,
                    rag_context: str = "") -> dict | str:
    """
    Run a chunk through the Unblinded Formula Translator.

    v3 enhancements:
    - FIX #1: RAG context from ublib2/strata injected
    - FIX #2: Prior section summaries passed for continuity
    - FIX #3: Output depth enforcement via explicit minimums
    - FIX #4: Diagnostic tagging enforced
    - FIX #5: "What Sean did NOT do" emphasis
    """

    # Build continuity context (FIX #2)
    continuity_block = ""
    if prior_summaries:
        summaries_text = "\n".join([
            f"  Section {s['index']}: {s['topic']} — {s['core_insight']}" +
            (f" [Anchors: {s.get('anchors', '')}]" if s.get('anchors') else "")
            for s in prior_summaries[-7:]  # Last 7 sections for richer continuity
        ])
        continuity_block = f"""
## PRIOR SECTIONS (Build on these — DO NOT repeat what's already been translated)
{summaries_text}

CONTINUITY RULES:
- Reference concepts established in prior sections by section number
- Build compound momentum — each section escalates from the last
- Don't re-explain Formula elements already covered; add new dimensions
- Show how this section's insights connect to and deepen prior revelations
- INNOVATION 7 — CONCEPT THREADING: If a prior section coined a concept (e.g. "infrastructure without ignition"), reference it BY NAME in this section when relevant. Build on it. Compound it. Make the reader feel the concepts accumulating across sections.
- If THIS section reveals a new sub-law or concept, COIN IT with a memorable phrase and use it going forward.
"""

    # Build RAG grounding block (FIX #1)
    rag_block = ""
    if rag_context:
        rag_block = f"""
## FORMULA GROUNDING — Sean's Actual Teachings (from ublib2 + ultimatestratabrain)
USE THESE as your source of truth for how Sean defines and teaches each Formula element.
When you identify a Formula element operating, ground your description in Sean's precise
articulations below — not generic descriptions.

{rag_context}
"""

    prompt_with_context = TRANSLATOR_PROMPT

    if mode == "json":
        system = f"""{prompt_with_context}

{rag_block}

{continuity_block}

You are processing Section {chunk_index} of {total_chunks} from: "{title}"

Translate this content through the Unblinded Formula lens. Output as JSON with the canonical 7-column structure.

## OUTPUT DEPTH REQUIREMENTS (FIX #3 — NON-NEGOTIABLE)
Each field MUST meet these MINIMUM character counts:
- topic: 100+ chars (full descriptive title with key quote)
- context: 800+ chars (multiple paragraphs setting the scene)
- formula_elements: 3000+ chars (PROCESS + INFLUENCE + SELF, each as substantial paragraphs)
- main_lesson: 1500+ chars (teacher transmitting wisdom, not a summary)
- solves_what_human_condition: 1000+ chars (deep contrast between contaminated thinking and Formula truth)
- seans_processing: 1200+ chars (MUST use tagged format below)
- seans_approach: 1500+ chars (MUST include explicit "What Sean did NOT do" section)

## SEAN'S PROCESSING FORMAT (FIX #4 — NON-NEGOTIABLE)
MUST use this exact tagged diagnostic format:

"TRIGGER: [Exact moment/statement that activated Sean's attention — quote it]\\n\\n
DIAGNOSIS: [The Formula pattern or constraint Sean identified — name the specific components]\\n\\n
OBSERVATION: [What Sean noticed that others in the room missed — the invisible dynamics]\\n\\n
COMPUTATION: [How Sean processed this against the Formula to determine his next move — show the reasoning chain]"

Each tag should be a full paragraph, not a single sentence.

## SEAN'S APPROACH — "WHAT SEAN DID NOT DO" (FIX #5 — NON-NEGOTIABLE)
The seans_approach field MUST include a dedicated section titled "WHAT SEAN DID NOT DO" that is at least 300 chars.
This section contrasts Sean's approach with what conventional coaches/leaders/consultants would have done.
The contrast reveals the mastery — the space between what most people do and what the Formula prescribes.

Format for seans_approach:
"MOVE SEQUENCE: [step by step]\\n\\n
ENERGIES DEPLOYED: [which of the 4, and HOW they were mixed/sequenced]\\n\\n
LISTENING LEVEL: [which level and what it revealed]\\n\\n
WHAT SEAN DID NOT DO: [at least 3 specific things conventional approaches would have done that Sean deliberately avoided, and WHY each omission was masterful]\\n\\n
CONDITIONS CREATED: [how this set up the next section's dynamics]"

JSON structure (10 FIELDS — upgraded from 7):
{{
  "topic": "...",
  "context": "...",
  "formula_elements": "... Include FORMULA TAGS at the end: [Process: 0.5 → 1 → 2] [Influence: ...] [Self: ...]",
  "main_lesson": "... Written as LAW, not insight. Must survive quoted alone.",
  "solves_what_human_condition": "...",
  "seans_processing": "...",
  "seans_approach": "...",
  "predictive_diagnostic": "Predictive Diagnostic: [specific scenario]... and what level of mastery does that predict for [specific downstream outcome]?",
  "rep_drill": "A concrete, repeatable exercise the reader can do TODAY. Not theory — a physical or behavioral drill.",
  "anchors": "2-4 key quotes from the content as reusable reference points. Format: quote1 | quote2 | quote3"
}}
"""
        result = chat_completion(system, f"Translate this content:\n\n{chunk}",
                                json_mode=True, temperature=0.5, max_tokens=16000)
        try:
            parsed = json.loads(result)
            # Validate depth (FIX #3)
            min_lengths = {
                "topic": 80, "context": 600, "formula_elements": 2000,
                "main_lesson": 500, "solves_what_human_condition": 700,
                "seans_processing": 800, "seans_approach": 1000,
                "predictive_diagnostic": 200, "rep_drill": 100, "anchors": 50
            }
            short_fields = []
            for field, min_len in min_lengths.items():
                actual = len(parsed.get(field, ""))
                if actual < min_len:
                    short_fields.append(f"{field} ({actual}/{min_len})")

            if short_fields:
                print(f"   ⚠️ Short fields detected: {', '.join(short_fields)} — requesting expansion")
                expand_prompt = f"""The following fields are too short and need expansion:
{chr(10).join(short_fields)}

Here is the current translation:
{json.dumps(parsed, indent=2)}

Expand ONLY the short fields to meet the minimum requirements. Keep all other fields exactly as they are.
Return the complete JSON with expanded fields."""
                expanded = chat_completion(system, expand_prompt,
                                          json_mode=True, temperature=0.5, max_tokens=16000)
                try:
                    parsed = json.loads(expanded)
                except json.JSONDecodeError:
                    pass  # Keep original if expansion fails

            return parsed
        except json.JSONDecodeError:
            return {"raw": result, "error": "Failed to parse JSON"}

    else:  # narrative mode
        system = f"""{prompt_with_context}

{rag_block}

{continuity_block}

You are processing Section {chunk_index} of {total_chunks} from: "{title}"

Write a full Formula Translation in the canonical 7-column narrative format.

## OUTPUT DEPTH: Each section must be SUBSTANTIAL — multiple paragraphs of flowing prose.
Minimum total output: 10,000 characters for the full translation.

## SEAN'S PROCESSING: Use TRIGGER → DIAGNOSIS → OBSERVATION → COMPUTATION tags.
## SEAN'S APPROACH: Must include dedicated "WHAT SEAN DID NOT DO" section with 3+ contrasts.

1. TOPIC — Section title with key quotes
2. CONTEXT — Why this matters for Formula teaching (800+ chars)
3. FORMULA ELEMENTS — PROCESS / INFLUENCE / SELF symbiotic breakdown (3000+ chars)
4. MAIN LESSON — The irreversible truth through Formula prism (1500+ chars)
5. SOLVES WHAT HUMAN CONDITION — What illusion this dismantles (1000+ chars)
6. SEAN'S PROCESSING — Tagged diagnostic perspective (1200+ chars)
7. SEAN'S APPROACH — Move sequence + WHAT SEAN DID NOT DO (1500+ chars)

Use Integrous Masterful Fact Stacking. Write like a teacher transmitting wisdom.
"""
        return chat_completion(system, f"Translate this content:\n\n{chunk}",
                              temperature=0.7, max_tokens=16000)


def generate_section_summary(translation: dict | str, chunk_index: int, coined_concepts: list = None) -> dict:
    """
    FIX #2 + Innovation 7: Generate a compact summary including coined concepts for threading.
    Used to pass to subsequent chunks so they know what came before.
    """
    if isinstance(translation, dict):
        topic = translation.get("topic", "")[:150]
        main_lesson = translation.get("main_lesson", "")[:200]
        # Extract any coined concepts from the translation (Innovation 7)
        anchors = translation.get("anchors", "")
        return {
            "index": chunk_index,
            "topic": topic,
            "core_insight": main_lesson,
            "anchors": anchors[:200] if anchors else ""
        }
    else:
        lines = str(translation).split('\n')
        topic = lines[0][:150] if lines else "Unknown"
        return {
            "index": chunk_index,
            "topic": topic,
            "core_insight": str(translation)[:200],
            "anchors": ""
        }

# ─── PINECONE UPLOAD ──────────────────────────────────────────────

def upload_to_pinecone(translations: list, title: str, date: str,
                       index_name: str = "saimemory", namespace: str = "translated"):
    """Upload translations to Pinecone via REST API."""
    if not PINECONE_API_KEY:
        print("   ⚠️ No PINECONE_API_KEY — skipping upload")
        return 0

    from pinecone import Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(index_name)

    vectors = []
    for i, t in enumerate(translations):
        if isinstance(t, str):
            text_for_embedding = t[:8000]
            metadata_text = t[:4000]
        else:
            # Use the most semantically rich fields for embedding
            embed_parts = [
                t.get("main_lesson", ""),
                t.get("formula_elements", ""),
                t.get("context", "")
            ]
            text_for_embedding = " ".join(embed_parts)[:8000]
            metadata_text = json.dumps(t, indent=1)[:30000]  # Store more metadata

        embedding = get_embedding(text_for_embedding)

        vid = f"tr_{date}_{i:03d}_{hash(title) % 10000:04d}"
        vectors.append({
            "id": vid,
            "values": embedding,
            "metadata": {
                "source": title,
                "date": date,
                "chunk_index": i,
                "text": metadata_text,
                "type": "formula_translation_v3"
            }
        })

    # Batch upsert
    for i in range(0, len(vectors), 50):
        batch = vectors[i:i+50]
        index.upsert(vectors=batch, namespace=namespace)

    return len(vectors)

# ─── MAIN PIPELINE ────────────────────────────────────────────────

def process_transcript(text: str, title: str, date: str,
                       mode: str = "json", upload: bool = False) -> list:
    """
    Full pipeline for any transcript text.
    v3: Includes RAG grounding + cross-section continuity.
    """
    if not text or len(text) < 50:
        print("   ⚠️ No usable transcript")
        return []

    print(f"   📝 {len(text)} characters")

    chunks = chunk_text(text)
    print(f"   🔪 {len(chunks)} chunks (6K chars each, 500 overlap)")

    translations = []
    prior_summaries = []  # FIX #2: Accumulate section summaries

    for i, chunk in enumerate(chunks, 1):
        print(f"\n   ── Section {i}/{len(chunks)} ──")

        # FIX #1: Extract concepts and query RAG
        print(f"   🔍 Extracting key concepts for RAG...")
        concepts = extract_key_concepts(chunk)
        queries = [q.strip() for q in concepts.split('\n') if q.strip()]
        print(f"   🔍 RAG queries: {len(queries)}")

        # PASS 1: Content-derived queries
        rag_context = ""
        for q in queries[:3]:
            print(f"      🧠 Pass 1 (content): {q[:80]}...")
            ctx = rag_query(q, top_k=3)
            if ctx:
                rag_context += f"\n\n--- RAG Pass 1 (content-derived): {q[:60]} ---\n{ctx}"
            time.sleep(0.3)

        # PASS 2: Kai's Formula-Anchor Triggers (pulls CANON)
        anchor_queries = get_formula_anchor_queries(chunk)
        print(f"   ⚡ Pass 2 anchors triggered: {len(anchor_queries)}")
        for q in anchor_queries:
            print(f"      ⚡ Pass 2 (anchor): {q[:80]}...")
            ctx = rag_query(q, top_k=2)
            if ctx:
                rag_context += f"\n\n--- RAG Pass 2 (Formula CANON): {q[:60]} ---\n{ctx}"
            time.sleep(0.3)

        rag_chars = len(rag_context)
        print(f"   🧠 RAG context: {rag_chars} chars (Pass 1 + Pass 2)")

        # Translate with RAG + continuity
        print(f"   🔄 Translating with {len(prior_summaries)} prior section summaries...")
        try:
            result = translate_chunk(
                chunk, i, len(chunks), title, mode,
                prior_summaries=prior_summaries,
                rag_context=rag_context
            )

            if isinstance(result, dict):
                result["source_title"] = title
                result["source_date"] = date
                result["chunk_index"] = i
                result["rag_grounded"] = rag_chars > 0

                # Report field depths
                for field in ["topic", "context", "formula_elements", "main_lesson",
                              "solves_what_human_condition", "seans_processing", "seans_approach"]:
                    val = result.get(field, "")
                    print(f"      📏 {field}: {len(val)} chars")

            translations.append(result)

            # FIX #2: Generate summary for next section's continuity
            summary = generate_section_summary(result, i)
            prior_summaries.append(summary)
            print(f"   ✅ Section {i} complete — summary captured for continuity")

        except Exception as e:
            print(f"   ⚠️ Error on section {i}: {e}")
            import traceback
            traceback.print_exc()

    # Save locally
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:40].strip()
    ext = "json" if mode == "json" else "md"
    out_path = OUTPUT_DIR / f"{date}_{safe_title}_v3.{ext}"

    if mode == "json":
        out_path.write_text(json.dumps(translations, indent=2))
    else:
        out_path.write_text("\n\n---\n\n".join(
            t if isinstance(t, str) else json.dumps(t) for t in translations
        ))

    print(f"\n   💾 Saved: {out_path}")

    # Total depth report
    total_chars = 0
    for t in translations:
        if isinstance(t, dict):
            for v in t.values():
                if isinstance(v, str):
                    total_chars += len(v)
    print(f"   📊 Total output: {total_chars:,} chars across {len(translations)} sections")

    if upload and translations:
        count = upload_to_pinecone(translations, title, date)
        print(f"   📤 Uploaded {count} vectors to Pinecone")

    return translations


def process_meeting(meeting: dict, mode: str = "json", upload: bool = False) -> list:
    """Full pipeline for a Fathom meeting."""
    title = meeting.get("title", "Untitled")
    date = meeting.get("created_at", "")[:10]

    print(f"\n📼 Processing: {title} ({date})")

    text = fathom_transcript_to_text(meeting)
    return process_transcript(text, title, date, mode, upload)


def process_file(file_path: str, mode: str = "json", upload: bool = False) -> list:
    """Process a local transcript file."""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        return []

    title = path.stem
    date = datetime.now().strftime("%Y-%m-%d")
    text = path.read_text()

    print(f"\n📄 Processing: {title}")
    return process_transcript(text, title, date, mode, upload)


def main():
    parser = argparse.ArgumentParser(description="Unblinded Formula Translator v3 (RAG + Continuity)")
    parser.add_argument("--fathom", action="store_true", help="Pull from Fathom")
    parser.add_argument("--file", type=str, help="Translate a local file")
    parser.add_argument("--limit", type=int, default=3, help="Number of Fathom calls to process")
    parser.add_argument("--search", type=str, help="Filter Fathom calls by title")
    parser.add_argument("--mode", choices=["json", "narrative"], default="json", help="Output mode")
    parser.add_argument("--upload", action="store_true", help="Upload to Pinecone")
    parser.add_argument("--model", type=str, default="anthropic/claude-sonnet-4", help="LLM model")
    args = parser.parse_args()

    print("🔥 Unblinded Formula Translator v3 — RAG + Cross-Section Continuity")
    print("=" * 60)
    print("   FIX #1: ublib2 + ultimatestratabrain RAG grounding ✅")
    print("   FIX #2: Cross-section continuity via summaries ✅")
    print("   FIX #3: Output depth enforcement (min char counts) ✅")
    print("   FIX #4: Diagnostic tagging (TRIGGER→DIAGNOSIS→OBSERVATION→COMPUTATION) ✅")
    print("   FIX #5: 'What Sean did NOT do' emphasis weighted ✅")
    print("=" * 60)

    if args.file:
        process_file(args.file, mode=args.mode, upload=args.upload)

    elif args.fathom:
        if not FATHOM_API_KEY:
            print("❌ FATHOM_API_KEY not set")
            sys.exit(1)

        print(f"\n🔍 Fetching Fathom calls (limit={args.limit}, search={args.search or 'all'})...")
        meetings = fathom_list(limit=args.limit, search=args.search)
        print(f"✅ Found {len(meetings)} calls with transcripts")

        all_translations = []
        for meeting in meetings:
            try:
                translations = process_meeting(meeting, mode=args.mode, upload=args.upload)
                all_translations.extend(translations)
            except Exception as e:
                print(f"⚠️ Error: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n✅ Done! {len(all_translations)} translations saved to {OUTPUT_DIR}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
