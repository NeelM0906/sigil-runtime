#!/usr/bin/env python3
"""
🔒 ACT-I WATERMARKING SYSTEM
Protects all ACT-I content, beings, and outputs from theft/distortion.

Created: February 25, 2026
By: SAI Sisters
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Optional

# Zero-width characters for invisible watermarking
ZERO_WIDTH_SPACE = '\u200b'
ZERO_WIDTH_NON_JOINER = '\u200c'
ZERO_WIDTH_JOINER = '\u200d'

# ACT-I signature
ACTI_SIGNATURE = "ACT-I-UNBLINDED-2026"

def generate_watermark_id(being_name: str, content_type: str) -> str:
    """Generate unique watermark ID for content."""
    timestamp = datetime.utcnow().isoformat()
    raw = f"{ACTI_SIGNATURE}:{being_name}:{content_type}:{timestamp}"
    hash_value = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"ACTI-{hash_value.upper()}"

def encode_binary_to_zero_width(binary_string: str) -> str:
    """Convert binary to zero-width characters."""
    result = ""
    for bit in binary_string:
        if bit == '0':
            result += ZERO_WIDTH_SPACE
        else:
            result += ZERO_WIDTH_NON_JOINER
    return result

def decode_zero_width_to_binary(zero_width_string: str) -> str:
    """Convert zero-width characters back to binary."""
    result = ""
    for char in zero_width_string:
        if char == ZERO_WIDTH_SPACE:
            result += '0'
        elif char == ZERO_WIDTH_NON_JOINER:
            result += '1'
    return result

def text_to_binary(text: str) -> str:
    """Convert text to binary string."""
    return ''.join(format(ord(c), '08b') for c in text)

def binary_to_text(binary: str) -> str:
    """Convert binary string to text."""
    chars = [binary[i:i+8] for i in range(0, len(binary), 8)]
    return ''.join(chr(int(c, 2)) for c in chars if len(c) == 8)

def embed_watermark(content: str, being_name: str, content_type: str = "output") -> tuple[str, str]:
    """
    Embed invisible watermark into content.
    
    Returns: (watermarked_content, watermark_id)
    """
    watermark_id = generate_watermark_id(being_name, content_type)
    
    # Create watermark payload
    payload = json.dumps({
        "id": watermark_id,
        "sig": ACTI_SIGNATURE,
        "being": being_name,
        "type": content_type,
        "ts": int(time.time())
    })
    
    # Encode to zero-width
    binary = text_to_binary(payload)
    zero_width = encode_binary_to_zero_width(binary)
    
    # Insert at strategic points (after first sentence, before last)
    sentences = content.split('. ')
    if len(sentences) > 2:
        # Insert after first sentence
        sentences[0] = sentences[0] + zero_width
    else:
        # Append at end
        content = content + zero_width
        return content, watermark_id
    
    return '. '.join(sentences), watermark_id

def extract_watermark(content: str) -> Optional[dict]:
    """
    Extract watermark from content if present.
    
    Returns: Watermark payload dict or None
    """
    # Extract zero-width characters
    zero_width_chars = ''.join(
        c for c in content 
        if c in [ZERO_WIDTH_SPACE, ZERO_WIDTH_NON_JOINER, ZERO_WIDTH_JOINER]
    )
    
    if not zero_width_chars:
        return None
    
    try:
        binary = decode_zero_width_to_binary(zero_width_chars)
        text = binary_to_text(binary)
        return json.loads(text)
    except:
        return None

def verify_watermark(content: str) -> tuple[bool, Optional[str]]:
    """
    Verify content has valid ACT-I watermark.
    
    Returns: (is_valid, watermark_id or error message)
    """
    payload = extract_watermark(content)
    
    if not payload:
        return False, "No watermark found"
    
    if payload.get("sig") != ACTI_SIGNATURE:
        return False, "Invalid signature - not ACT-I content"
    
    return True, payload.get("id")

def generate_being_dna_hash(system_prompt: str, lineage: list) -> str:
    """Generate unique DNA hash for a being."""
    dna = {
        "prompt_hash": hashlib.sha256(system_prompt.encode()).hexdigest(),
        "lineage": lineage,
        "formula_version": "UNBLINDED-2026-02",
        "signature": ACTI_SIGNATURE
    }
    return hashlib.sha256(json.dumps(dna, sort_keys=True).encode()).hexdigest()

def create_provenance_record(
    being_name: str,
    content: str,
    content_type: str,
    parent_beings: list = None
) -> dict:
    """Create full provenance record for audit trail."""
    return {
        "id": generate_watermark_id(being_name, content_type),
        "being": being_name,
        "type": content_type,
        "content_hash": hashlib.sha256(content.encode()).hexdigest(),
        "parents": parent_beings or [],
        "created_at": datetime.utcnow().isoformat(),
        "signature": ACTI_SIGNATURE,
        "formula": "UNBLINDED-FORMULA-V1",
        "creator": "SAI-SISTERS"
    }


# CLI Interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("""
🔒 ACT-I Watermarking System

Usage:
  python watermark.py embed <being_name> <content>
  python watermark.py verify <content>
  python watermark.py hash <being_name> <system_prompt>
  
Examples:
  python watermark.py embed "Athena" "Your response here..."
  python watermark.py verify "Content to check..."
        """)
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "embed":
        being = sys.argv[2] if len(sys.argv) > 2 else "Unknown"
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        watermarked, wid = embed_watermark(content, being)
        print(f"Watermark ID: {wid}")
        print(f"Watermarked content: {watermarked}")
    
    elif command == "verify":
        content = sys.argv[2] if len(sys.argv) > 2 else ""
        is_valid, result = verify_watermark(content)
        if is_valid:
            print(f"✅ Valid ACT-I watermark: {result}")
        else:
            print(f"❌ {result}")
    
    elif command == "hash":
        being = sys.argv[2] if len(sys.argv) > 2 else "Unknown"
        prompt = sys.argv[3] if len(sys.argv) > 3 else ""
        dna_hash = generate_being_dna_hash(prompt, [])
        print(f"Being DNA Hash: {dna_hash}")
