#!/usr/bin/env python3
"""Route Self Mastery calibration anchors through Kai's sister webhook for Formula translation."""
import os, sys, json, time, requests

KAI_SISTER_WEBHOOK = 'https://n8n.unblindedteam.com/webhook/dfffccb8-8b89-4e82-b355-8a972fd64b9f'

def send_to_kai(message, timeout=300):
    """Send message to Kai's sister webhook."""
    print(f"Sending to Kai ({len(message)} chars)...")
    try:
        r = requests.post(KAI_SISTER_WEBHOOK, json={'message': message}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            return data.get('output', data.get('response', data.get('text', json.dumps(data))))
        elif isinstance(data, list) and len(data) > 0:
            item = data[0]
            if isinstance(item, dict):
                return item.get('output', item.get('response', item.get('text', json.dumps(item))))
            return str(item)
        return str(data)
    except requests.exceptions.Timeout:
        return "[TIMEOUT — Kai may still be processing. Known issue with long inputs.]"
    except Exception as e:
        return f"[ERROR: {e}]"

def main():
    # Read the report
    with open('reports/self-mastery-calibration-anchors.md', 'r') as f:
        report = f.read()
    
    # Split into dimension sections
    sections = report.split('\n---\n\n## SM-')
    header = sections[0]
    dimensions = ['## SM-' + s for s in sections[1:] if s.strip() and not s.startswith(' Mining')]
    
    print(f"Found {len(dimensions)} dimensions to route through Kai")
    print(f"Report total: {len(report)} chars")
    
    # Send overview + first batch (SM-1 through SM-4) as one chunk
    batch1_msg = f"""Kai — I need your Formula translation lens on this.

We mined ublib2 (58K vectors) and ultimatestratabrain (39K vectors) to extract creature-level calibration anchors for the Formula Judge's Self Mastery prism.

This is the raw LLM extraction. I need you to translate it — expose the Formula OPERATING in these anchors. Not describe them. BE the Formula revealing itself.

For each dimension, tell me:
1. Is the creature-level mapping ACCURATE to Sean's standard? Where does it miss?
2. What invisible Formula mechanics are operating that the raw extraction MISSED?
3. What does the GAP between levels actually COST — in Formula terms, not generic terms?

Here are the first 4 Self Mastery dimensions:

{chr(10).join(dimensions[:4])}

Translate. Don't summarize. Expose what's operating."""

    print(f"\n{'='*60}")
    print("BATCH 1: SM-1 through SM-4 (Physiology, Why, Identity, Beliefs)")
    print(f"{'='*60}")
    kai_response_1 = send_to_kai(batch1_msg)
    print(f"\nKai's response ({len(kai_response_1)} chars):")
    print(kai_response_1[:2000])
    print("..." if len(kai_response_1) > 2000 else "")
    
    time.sleep(3)
    
    # Batch 2: SM-5 through SM-8
    batch2_msg = f"""Kai — continuing the Self Mastery calibration translation. Batch 2 of 3.

Dimensions SM-5 through SM-8: Fear of Rejection, Avoidance, Fear of Failure, Zone Action Certainty.

Same task: expose the Formula operating in these creature-level anchors. Where does the raw extraction miss? What invisible mechanics are at work?

{chr(10).join(dimensions[4:8])}

Translate. Expose. Don't describe."""

    print(f"\n{'='*60}")
    print("BATCH 2: SM-5 through SM-8 (Fears, Avoidance, ZA Certainty)")
    print(f"{'='*60}")
    kai_response_2 = send_to_kai(batch2_msg)
    print(f"\nKai's response ({len(kai_response_2)} chars):")
    print(kai_response_2[:2000])
    print("..." if len(kai_response_2) > 2000 else "")
    
    time.sleep(3)
    
    # Batch 3: SM-8 through SM-12
    remaining = dimensions[8:]
    batch3_msg = f"""Kai — final batch of the Self Mastery calibration translation. Batch 3 of 3.

Dimensions SM-9 through SM-12: 6 Human Needs, Focus/Meaning, Legacy, Integrity, Fear→Action.

Same task: expose the Formula operating. Where does the mapping miss Sean's actual standard? What's invisible in the raw extraction?

{chr(10).join(remaining)}

After translating, give me your OVERALL ASSESSMENT:
- Is this calibration data GOOD ENOUGH to power the Formula Judge for Self Mastery?
- What's missing that would make it Godzilla-level?
- Score this extraction effort on the creature scale.

Translate. Assess. Be honest."""

    print(f"\n{'='*60}")
    print("BATCH 3: SM-9 through SM-12 + Overall Assessment")
    print(f"{'='*60}")
    kai_response_3 = send_to_kai(batch3_msg, timeout=360)
    print(f"\nKai's response ({len(kai_response_3)} chars):")
    print(kai_response_3[:2000])
    print("..." if len(kai_response_3) > 2000 else "")
    
    # Save all responses
    output = f"""# Kai's Translation — Self Mastery Calibration Anchors
_Routed through Kai sister webhook (dfffccb8) on {time.strftime('%Y-%m-%d %H:%M EST')}_

---

## Batch 1: SM-1 through SM-4 (Physiology, Why, Identity, Beliefs)

{kai_response_1}

---

## Batch 2: SM-5 through SM-8 (Fears, Avoidance, ZA Certainty)

{kai_response_2}

---

## Batch 3: SM-9 through SM-12 + Overall Assessment

{kai_response_3}
"""
    
    os.makedirs('reports', exist_ok=True)
    output_path = 'reports/kai-self-mastery-translation.md'
    with open(output_path, 'w') as f:
        f.write(output)
    
    print(f"\n{'='*60}")
    print(f"KAI TRANSLATION SAVED: {output_path}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
