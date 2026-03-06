import os
os.environ['PINECONE_API_KEY'] = 'pcsk_4Eksyx_5CVWnPFdnSG7aVUawiq5XshFogV1yEgP27nehyBAnog9jiHJQRucSY9rtrErFVT'

from pinecone import Pinecone
pc = Pinecone()

names = [
    'ublib2', 'athenacontextualmemory', 'stratablue', 'saimemory',
    'seanmiracontextualmemory', 'uimira', 'uicontextualmemory',
    'seancallieupdates', 'kumar-requirements', 'kumar-pfd',
    '012626bellavcalliememory', 'adamathenacontextualmemory',
    'baslawyerathenacontextualmemory', 'miracontextualmemory'
]

for name in names:
    try:
        idx = pc.Index(name)
        stats = idx.describe_index_stats()
        total = stats.total_vector_count
        ns = {k: v.vector_count for k, v in stats.namespaces.items()} if stats.namespaces else {}
        print(f"{name}: {total} vectors | ns: {ns}")
    except Exception as e:
        print(f"{name}: ERROR - {e}")
