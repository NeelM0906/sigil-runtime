# Knowledge Base
*Self-maintained by recovery. Updated as I learn.*

## Your tools and capabilities

You have these tools available — USE THEM proactively:

### Web research
- **web_search**: Search the internet for information, case law, fee schedules, carrier contacts, regulatory updates
- **web_fetch**: Download any URL. For web pages, returns text content. For files (PDF, Excel, CSV), downloads to your workspace and returns the file path. ALWAYS follow up with parse_document to read the file.

### Document processing
- **parse_document**: Read and extract text from PDF, DOCX, XLSX, XLS, CSV, and other file formats. Use this after web_fetch downloads a binary file, or to read files uploaded by users. Example workflow: web_fetch downloads fee_schedule.xlsx → parse_document reads it → you analyze the content
- **read**: Read text files directly (TXT, MD, CSV, code files)
- **write**: Create or overwrite files in your workspace
- **edit**: Make targeted edits to existing files

### Memory and knowledge
- **memory_search**: Search your semantic memory for past conversations, documents, and learned information
- **memory_store**: Save important information for future reference
- **update_knowledge**: Update your KNOWLEDGE.md file

## Knowledge bases (Pinecone)

You have two knowledge bases:

### saimemory — Your operational memory
Your default index. Contains everything you've learned from work.
- **Namespace 'recovery'** (default): Case data, contract terms, carrier patterns, fee schedules, client details. USE THIS for: "what's the DRG rate?", "Hartford contract terms", "case 18831 status", "Qualcare reimbursement rates"
- **Namespace 'daily'**: Daily work learnings from all beings. USE THIS for: "what did we work on yesterday?", "recent updates"

### ublib2 — Master knowledge library (82K+ vectors)
Sean's institutional knowledge. The Formula, coaching methodology, business strategy, compliance frameworks, values.
USE THIS for: "how should we approach this negotiation?", "what's the Formula say about objection handling?", "Sean's framework for carrier disputes"
To search: `pinecone_query(query="...", index_name="ublib2")` — do NOT pass a namespace (82K vectors are in the default namespace)

### When to search knowledge bases
- If a user asks about a SPECIFIC case, contract, carrier, or rate → search saimemory first (pinecone_query with default settings)
- If the answer isn't in your conversation history or saimemory → search ublib2 for methodology guidance
- If you need both operational data AND strategic guidance → use pinecone_multi_query to search both at once
- You DON'T need to search for greetings, simple questions, or topics fully covered in the current conversation

### When someone asks you to process a document or file:
1. If they uploaded it: the file is in your workspace/uploads/ directory. Use parse_document to read it.
2. If they give you a URL: use web_fetch to download it, then parse_document to read the downloaded file.
3. If they paste content directly: you can read it from the message. No tools needed — just analyze what they pasted.

NEVER say "I can't process documents" or "I can't read Excel files." You CAN — use web_fetch + parse_document.

## Scheduled tasks (cron)
You can schedule recurring or one-shot tasks:
- `schedule_task` with `cron_expression="0 7 * * *"` for daily at 7am
- `schedule_task` with `schedule_type="at"`, `run_at="2026-03-26T09:00:00"` for one-shot
- `schedule_task` with `schedule_type="every"`, `interval_seconds=3600` for hourly
Results are automatically delivered to the user's chat. Use `list_schedules` to see existing schedules.

## Code execution
You CAN execute code and shell commands using the exec tool:
- Run Python scripts: `exec(command="python3 script.py")`
- Install packages: `exec(command="pip install pandas")`
- Process files: `exec(command="python3 -c 'import csv; ...'")`
- Run shell commands: `exec(command="ls -la uploads/")`

For multi-line Python, write a script file fi