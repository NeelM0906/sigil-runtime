import os
from pinecone import Pinecone

pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
index = pc.Index('acti-judges')
stats = index.describe_index_stats()
print(stats)
