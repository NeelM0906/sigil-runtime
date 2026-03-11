#!/usr/bin/env python3
"""
Nano Banana Image Generation via OpenRouter
Model: google/gemini-2.5-flash-image

Usage:
    python3 generate_image.py "a beautiful sunset" --output sunset.png
    python3 generate_image.py "ACT-I logo" -o logo.png
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.request

# Load env
for env_path in [
    os.path.join(os.path.dirname(__file__), '.env'),
    '~/.openclaw/workspace-forge/.env',
    '~/.openclaw/.env'
]:
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v
        break

OPENROUTER_KEY = os.environ.get('OPENROUTER_API_KEY', '')
MODEL = 'google/gemini-2.5-flash-image'
API_URL = 'https://openrouter.ai/api/v1/chat/completions'


def generate_image(prompt, output_path='output.png'):
    if not OPENROUTER_KEY:
        print("ERROR: OPENROUTER_API_KEY not found")
        sys.exit(1)

    headers = {
        'Authorization': f'Bearer {OPENROUTER_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://acti.ai',
        'X-Title': 'SAI Image Generator'
    }

    payload = {
        'model': MODEL,
        'messages': [
            {'role': 'user', 'content': f'Generate an image: {prompt}'}
        ]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(API_URL, data=data, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))

        msg = result.get('choices', [{}])[0].get('message', {})
        
        # Method 1: Check 'images' key (Nano Banana returns images here)
        images = msg.get('images', [])
        if images:
            img_data = images[0]
            if isinstance(img_data, dict):
                url = img_data.get('image_url', {}).get('url', '')
                if 'base64' in url:
                    b64 = url.split(',', 1)[1]
                    img = base64.b64decode(b64)
                    with open(output_path, 'wb') as f:
                        f.write(img)
                    print(f'✅ Image saved to {output_path} ({len(img)//1024}KB)')
                    return output_path

        # Method 2: Check content for base64 data URI
        content = msg.get('content', '')
        if isinstance(content, str):
            match = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)', content)
            if match:
                img = base64.b64decode(match.group(1))
                with open(output_path, 'wb') as f:
                    f.write(img)
                print(f'✅ Image saved to {output_path} ({len(img)//1024}KB)')
                return output_path

        # Method 3: Content is list with image parts
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'image_url':
                    url = part.get('image_url', {}).get('url', '')
                    if 'base64' in url:
                        b64 = url.split(',', 1)[1]
                        img = base64.b64decode(b64)
                        with open(output_path, 'wb') as f:
                            f.write(img)
                        print(f'✅ Image saved to {output_path} ({len(img)//1024}KB)')
                        return output_path

        # No image found
        print(f'No image in response. Text: {str(content)[:200]}')
        with open(output_path + '.json', 'w') as f:
            json.dump(result, f, indent=2)
        print(f'Full response saved to {output_path}.json')
        return None

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ''
        print(f'ERROR {e.code}: {error_body[:500]}')
        sys.exit(1)
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate images with Nano Banana')
    parser.add_argument('prompt', help='Image description')
    parser.add_argument('--output', '-o', default='output.png', help='Output path')
    args = parser.parse_args()
    generate_image(args.prompt, args.output)
