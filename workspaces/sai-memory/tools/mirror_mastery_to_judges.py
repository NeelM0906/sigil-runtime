import os
import json
import glob
import urllib.request
from pinecone import Pinecone

def get_embedding(text, openai_api_key):
    url = 'https://openrouter.ai/api/v1/embeddings'
    headers = {
        'Authorization': f'Bearer {os.environ.get("OPENROUTER_API_KEY")}',
        'Content-Type': 'application/json'
    }
    data = json.dumps({
        'model': 'openai/text-embedding-3-small',
        'input': text
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        return res['data'][0]['embedding']

def main():
    pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
    if 'acti-judges' not in pc.list_indexes().names():
        print("Index 'acti-judges' not found")
        return
    index = pc.Index('acti-judges')
    
    files = glob.glob('~/.openclaw/workspace/reports/mastery-research/*.json')
    vectors = []
    
    print(f"Found {len(files)} mastery profiles to mirror to acti-judges.")
    
    for fpath in files:
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            
            topic = data.get('topic', os.path.basename(fpath).replace('.json', ''))
            content = json.dumps(data)
            
            text_to_embed = f"Mastery Architecture Profile for {topic}\n\n{content}"
            emb = get_embedding(text_to_embed, None)
            
            vec_id = f"mastery_profile_{topic.replace(' ', '_')}"
            vectors.append({
                "id": vec_id,
                "values": emb,
                "metadata": {
                    "source": os.path.basename(fpath),
                    "type": "mastery_profile",
                    "topic": topic,
                    "source_namespace": "saimemory/mastery",
                    "text": content[:10000] # Safe limit for metadata
                }
            })
            
            if len(vectors) >= 20:
                print(f"Mirroring batch of {len(vectors)} vectors...")
                index.upsert(vectors=vectors, namespace='mastery_profiles')
                vectors = []
                
        except Exception as e:
            print(f"Error processing {fpath}: {e}")
            
    if vectors:
        print(f"Mirroring final batch of {len(vectors)} vectors...")
        index.upsert(vectors=vectors, namespace='mastery_profiles')
        
    print("Mastery mirror to acti-judges complete.")

if __name__ == '__main__':
    main()
