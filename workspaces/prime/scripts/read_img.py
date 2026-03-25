import base64, os
from openai import OpenAI

client = OpenAI()
with open('uploads/IMG_0255.png', 'rb') as f:
    img_b64 = base64.b64encode(f.read()).decode()

resp = client.chat.completions.create(
    model='gpt-4o',
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': 'Read ALL text in this screenshot exactly. It looks like a Pinecone console. Extract every API key name, key value, environment, project name, and any details visible.'},
            {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_b64}'}}
        ]
    }],
    max_tokens=2000
)
print(resp.choices[0].message.content)
