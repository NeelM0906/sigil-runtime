import sys
import json
from supabase_memory import SaiMemory

mem = SaiMemory(sister="forge")
state = mem.wake_up()
print(f"Active tasks across network: {len(state['active_tasks'])}")
print(f"Recent convos: {len(state['recent_conversations'])}")
