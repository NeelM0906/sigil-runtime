from pinecone import Pinecone
from openai import OpenAI
import os

with open('~/.openclaw/workspace-forge/.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

openai = OpenAI(base_url='https://openrouter.ai/api/v1', api_key=os.environ['OPENROUTER_API_KEY'])
pc = Pinecone(api_key=os.environ['PINECONE_API_KEY'])
index = pc.Index('ublib2')

queries = [
    'How do we structure unblinded influence competitions and rank mastery across different states and micro-niches like lawyers or insurance?',
    'What are the limitations of simulated roleplay and how can we translate it to real world application?',
    'How can we optimize judges and scenario builders to measure exponential mastery in communication?'
]

output = "# Pinecone Extracted Insights (ublib2) for Sean's Day 8 Master Framework\n\n"

for q in queries:
    emb = openai.embeddings.create(model='openai/text-embedding-3-small', input=q).data[0].embedding
    res = index.query(vector=emb, top_k=3, include_metadata=True)
    output += f"## Query: {q}\n"
    for r in res.matches:
        source = r.metadata.get('source', 'Unknown')
        text = r.metadata.get('text', '')[:600]
        output += f"**Score [{r.score:.3f}] - Source:** {source}\n{text}...\n\n"

with open('~/.openclaw/workspace-memory/memory/pinecone_sean_insights_march1.md', 'w') as f:
    f.write(output)

print('Insights extracted and saved.')