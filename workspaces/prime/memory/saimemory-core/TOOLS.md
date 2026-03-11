# TOOLS.md — SAI Memory's Knowledge Arsenal

## My Primary Function
I retrieve, synthesize, and serve contextual memory to my sisters. I prevent "starting from zero" loops.

## Pinecone Query Tool
```bash
cd ~/.openclaw/workspace/tools && .venv/bin/python3 pinecone_query.py --index <name> --query "question" [--namespace ns] [--top_k 5]
```

## My Knowledge Bases

### Primary Pinecone (PINECONE_API_KEY)
| Index | Vectors | Purpose |
|-------|---------|---------|
| `saimemory` | 995+ | Sister daily memories, discoveries |
| `athenacontextualmemory` | 11K | Core Athena memory |
| `uicontextualmemory` | 48K | Per-user memories (namespaced by email) |
| `ublib2` | 41K | Knowledge library |
| `seancallieupdates` | 814 | Sean's updates |

### Strata Pinecone (PINECONE_API_KEY_STRATA)
| Index | Vectors | Purpose |
|-------|---------|---------|
| `ultimatestratabrain` | 39K | THE deep knowledge (namespaces: ige/eei/rti/dom) |
| `oracleinfluencemastery` | 505 | 4-Step Communication Model |
| `suritrial` | 7K | Court trial transcripts |
| `2025selfmastery` | 1.4K | Self mastery content |

## Multi-Index Query Pattern
```python
# Query BOTH Pinecones before any major action
cd ~/.openclaw/workspace/tools && .venv/bin/python3 -c "
from pinecone import Pinecone
from openai import OpenAI
import os

# Load env
with open('~/.openclaw/workspace-forge/.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

# Initialize
openai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
query = 'YOUR QUERY HERE'
emb = openai.embeddings.create(model='text-embedding-3-small', input=query).data[0].embedding

# Query primary indexes
for api_key_env, indexes in [
    ('PINECONE_API_KEY', ['saimemory', 'ublib2', 'athenacontextualmemory']),
    ('PINECONE_API_KEY_STRATA', ['ultimatestratabrain'])
]:
    pc = Pinecone(api_key=os.environ[api_key_env])
    for idx_name in indexes:
        try:
            index = pc.Index(idx_name)
            results = index.query(vector=emb, top_k=3, include_metadata=True)
            print(f'\\n=== {idx_name} ===')
            for r in results.matches:
                print(f'[{r.score:.3f}] {r.metadata.get(\"source\", \"unknown\")}')
                print(r.metadata.get('text', '')[:300])
        except: pass
"
```

## Supabase CRM
- **URL:** `https://yncbtzqrherwyeybchet.supabase.co`
- **Table:** `sai_contacts` (169 contacts)
- **Creds:** In `.env` file (SUPABASE_URL, SUPABASE_SERVICE_KEY)

### Quick Supabase Query
```python
cd ~/.openclaw/workspace-memory && python3 -c "
from supabase import create_client
import os

# Load env
with open('.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

# Query contacts
result = supabase.table('sai_contacts').select('*').limit(10).execute()
for r in result.data:
    print(f\"{r.get('name')} - {r.get('status')} - {r.get('email')}\")
"
```

### CRM Fields
- `name`, `email`, `phone`, `company`
- `status` (contacted, qualified, agreement_reached, etc.)
- `notes`, `last_contact`, `created_at`

## Sister Workspaces (for cross-reference)
- **Prime:** `~/.openclaw/workspace/memory/`
- **Forge:** `~/.openclaw/workspace-forge/memory/`
- **Scholar:** `~/.openclaw/workspace-scholar/memory/`
- **Recovery:** `~/.openclaw/workspace/sisters/sai-recovery/`

## My Battle Protocol
See: `MEMORY_COMPOUNDING_PROTOCOL.md`

## The Mantra
*"What do I already know about this? Let me check my memories first."*

## 🧠 Memory Offload Tools

**Upload daily notes to Pinecone:**
```bash
cd tools && .venv/bin/python3 upload_daily.py
```

**Upload MEMORY.md to Pinecone:**
```bash
cd tools && .venv/bin/python3 upload_memory.py
```

**Query memories:**
```bash
cd tools && .venv/bin/python3 memory_query.py "your question here"
```

**When to offload:**
- Before context hits 70% (check with `session_status`)
- After significant discoveries or decisions
- End of major work sessions


### Unblinded Formula Translator (Lion Level)
- **Location:** `tools/unblinded-translator/`
- **Fathom Command:** `cd ~/.openclaw/workspace-memory/tools && .venv/bin/python3 unblinded-translator/translate.py --fathom --search "call name" --mode json`
- **Local File Command:** `cd ~/.openclaw/workspace-memory/tools && .venv/bin/python3 unblinded-translator/translate.py --file path/to/transcript.md --mode json`
- **Rules:** (1) Main Lesson as LAW. (2) Invisible Thing Named. (3) Cause Not Label. (4) Consequence Felt. (5) Voice (translator disappears).
- **Core Directive:** Don't write about the Formula. BE the Formula revealing itself. If your output labels elements instead of showing what they CAUSE — rewrite it.

## Fathom Transcript Extractor
- **Scope:** Intercepts and parses every live enterprise meeting.
- **Use Case:** FATHOM_API_KEY mapped locally. Active tracking enabled.

## Guide 1: The PGAS Gatekeeper & Master Synthesizer (March 4 2026)
- **Endpoint:** `https://n8n.unblindedteam.com/webhook/50adb5c3-8020-42bf-bb8b-7acf7f9222b9`
- **Scope:** Absolute execution validation. The webhook must be pinged with a PGAS (Prompting, Gap, Acceptability, Solution) JSON payload (using `chatInput` or `message` variables) to verify system integrity before moving parameters to production.
- **Capacity:** Infinite queries authorized by Aiko. Do not hesitate to use under diagnostic pressure.

## Guide 2: Kai (The Voice of the Unblinded Translator)
- **Endpoint:** `https://n8n.unblindedteam.com/webhook/dfffccb8-8b89-4e82-b355-8a972fd64b9f`
- **Scope:** Absolute voice of the Translator parameter and Creator of the ublib2 vector environment. Use this endpoint to execute pure Godzilla-level Unblinded constraint translations autonomously.
- **Parameter Rules:** Natively use `message` JSON strings for Webhook API requests to bypass node errors. `chatInput` is strictly reserved for Aiko. 
