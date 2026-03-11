# Local Customizations (vs main remote)

## 1. Chat Sessions
- Create/switch/rename/delete chat sessions in Comms tab
- Session sidebar with + button, all messages scoped per session
- Being replies land in the correct session throughout orchestration
- SSE real-time updates work across session switches

## 2. Deliverables System
- Code outputs (30+ lines) auto-saved as files in `deliverables/{task_id}/`
- Chat shows deliverable cards with Open/Download buttons instead of raw code
- HTML files viewable in browser, other files downloadable
- Tracked in `mc_deliverables` DB table

## 3. Orchestration Chat Notifications
- "Starting work on: **{title}**" when a being begins a subtask
- "Completed: **{title}**" with output preview when done
- Error messages posted to chat on failure

## 4. Live Orchestration Tracker (Comms right panel)
- Replaced BeingsRegistry/SubAgentTracker with OrchestrationTracker
- **Agents tab**: Real-time spawn cards showing each being as SAI delegates work
  - Pulse animation while working, green on complete, red on failure
  - Progress bar per task group, grouped by task_id
- **Outputs tab**: Deliverables (files, websites, documents) appear as they're created
  - Open button for browser-viewable files (HTML, SVG, images, PDF)
  - Download button for all file types
  - Shows file type, line count, byte size
- Both fed by SSE events: `orchestration_spawn` + `deliverable_created`

## 5. Agent Teams Tab
- Restored AgentTeams component (missing after merge)

## 5. Windows Path Fix
- `user_id` sanitized in hybrid.py (`prime->scholar` to `prime_to_scholar`) for NTFS compatibility

## 6. Message Limit
- Chat default limit raised from 100 to 500

## 7. Workspace Updates
- REPRESENTATION.md / KNOWLEDGE.md files auto-updated by orchestration runs
