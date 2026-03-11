import os
from pinecone import Pinecone

pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
if 'acti-judges' in pc.list_indexes().names():
    index = pc.Index('acti-judges')
    stats = index.describe_index_stats()
    print(f"Total Vectors in acti-judges: {stats.total_vector_count}")
    namespaces = len(stats.namespaces)
    print(f"Total Namespaces: {namespaces}")
else:
    print("Index 'acti-judges' not found.")
