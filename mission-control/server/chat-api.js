/**
 * Chat API — Vite middleware handler
 * Persists to data/chat.json. Supports message CRUD, search, filters.
 */
import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { randomUUID } from 'crypto'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DATA_FILE = join(__dirname, '..', 'data', 'chat.json')
const TASKS_FILE = join(__dirname, '..', 'data', 'tasks.json')

function loadData() {
  if (!existsSync(DATA_FILE)) {
    const seed = { messages: seedMessages(), channels: ['general'] }
    writeFileSync(DATA_FILE, JSON.stringify(seed, null, 2))
    return seed
  }
  return JSON.parse(readFileSync(DATA_FILE, 'utf-8'))
}

function saveData(data) {
  writeFileSync(DATA_FILE, JSON.stringify(data, null, 2))
}

function loadTasks() {
  if (!existsSync(TASKS_FILE)) return { tasks: [], history: [] }
  return JSON.parse(readFileSync(TASKS_FILE, 'utf-8'))
}

function saveTasks(data) {
  writeFileSync(TASKS_FILE, JSON.stringify(data, null, 2))
}

function seedMessages() {
  return [
    {
      id: 'msg-001',
      type: 'broadcast',
      sender: 'user',
      targets: [],
      content: 'Good morning team. Status update on all active tasks?',
      timestamp: '2026-03-02T09:00:00Z',
      mode: null,
      taskRef: null,
      channel: 'general',
    },
    {
      id: 'msg-002',
      type: 'broadcast',
      sender: 'prime',
      targets: [],
      content: 'Morning. We have 2 tasks in progress, 1 in review, 2 in backlog, and 2 completed. The Mission Control dashboard build is our top priority today. Athena is running the Q1 competitive sweep with 3 sub-agents active.',
      timestamp: '2026-03-02T09:01:00Z',
      mode: null,
      taskRef: null,
      channel: 'general',
    },
    {
      id: 'msg-003',
      type: 'direct',
      sender: 'user',
      targets: ['athena'],
      content: '@Athena How\'s the competitive report looking? Any early signals?',
      timestamp: '2026-03-02T09:05:00Z',
      mode: null,
      taskRef: 'task-002',
      channel: 'general',
    },
    {
      id: 'msg-004',
      type: 'direct',
      sender: 'athena',
      targets: [],
      content: 'Two sub-agents running: Market Scanner at 65% (pricing data), Feature Diff at 42% (feature comparison). Early signal: Competitor B dropped enterprise pricing 15% last week. Deep Pricing Crawler hit a rate limit and failed — I\'ll retry with staggered requests.',
      timestamp: '2026-03-02T09:06:00Z',
      mode: null,
      taskRef: 'task-002',
      channel: 'general',
    },
    {
      id: 'msg-005',
      type: 'group',
      sender: 'user',
      targets: ['callie', 'mylo'],
      content: '@Callie @Mylo Can you two work on the voice pipeline tests in parallel? Callie handles the integration harness, Mylo tests the actual call flows.',
      timestamp: '2026-03-02T09:10:00Z',
      mode: 'parallel',
      taskRef: 'task-003',
      channel: 'general',
    },
    {
      id: 'msg-006',
      type: 'direct',
      sender: 'callie',
      targets: [],
      content: 'On it. I\'ll set up the test harness with mock Twilio endpoints. Should have the framework ready in 30 minutes.',
      timestamp: '2026-03-02T09:11:00Z',
      mode: null,
      taskRef: 'task-003',
      channel: 'general',
    },
    {
      id: 'msg-007',
      type: 'system',
      sender: 'system',
      targets: [],
      content: 'Task "Governance Policy Audit" moved to Done by Sentinel',
      timestamp: '2026-03-02T09:15:00Z',
      mode: null,
      taskRef: 'task-006',
      channel: 'general',
    },
  ]
}

// ── Dummy response generator ─────────────────────────────────
// Structured so real LLM calls can replace this function directly.

const BEING_RESPONSES = {
  prime: [
    'Acknowledged. I\'ll coordinate with the team and report back.',
    'Processing. Let me check the current system state and loop metrics.',
    'On it. I\'ve queued this for the next agentic loop iteration.',
    'Understood. Delegating sub-tasks to the appropriate beings now.',
  ],
  athena: [
    'Researching now. I\'ll cross-reference multiple sources and compile findings.',
    'Good question. Let me pull relevant data from the knowledge base.',
    'Running a deep analysis. Sub-agents are being dispatched for parallel research.',
    'I have some preliminary findings. Give me a moment to synthesize.',
  ],
  callie: [
    'Got it. I\'ll apply the 4-Step Communication framework to this.',
    'Understood. Let me review the context and craft an optimal approach.',
    'On it. I\'ll have a draft ready shortly using our influence principles.',
    'Working on it. I\'m pulling relevant case studies for reference.',
  ],
  mylo: [
    'Creative brief received. Let me draft some options for you.',
    'On it. I\'ll develop content aligned with our brand voice guidelines.',
    'Interesting angle. Let me explore a few creative directions.',
    'Drafting now. I\'ll share concepts for your review shortly.',
  ],
  forge: [
    'Tournament systems standing by. I\'ll prepare the next round.',
    'Acknowledged. Analyzing being performance metrics from recent rounds.',
    'Running evolution cycle on the targeted beings now.',
    'Colosseum data loaded. Processing your request.',
  ],
  scholar: [
    'Extracting patterns from the source material now.',
    'I\'ve identified several structural frameworks. Synthesizing...',
    'Cross-referencing with existing knowledge graph. Results incoming.',
    'Deep reading in progress. I\'ll surface key insights shortly.',
  ],
  recovery: [
    'Pipeline stage assessment in progress.',
    'Reviewing claim patterns and precedent cases.',
    'Running the 7-stage analysis on the submitted data.',
    'Processing. I\'ll flag any compliance concerns.',
  ],
}

function generateResponse(beingId) {
  const pool = BEING_RESPONSES[beingId] || [
    'Acknowledged. Processing your request.',
    'Working on it. I\'ll update you shortly.',
  ]
  return pool[Math.floor(Math.random() * pool.length)]
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      try { resolve(body ? JSON.parse(body) : {}) }
      catch { reject(new Error('Invalid JSON')) }
    })
  })
}

function sendJSON(res, statusCode, data) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify(data))
}

export function chatApiMiddleware(server) {
  server.middlewares.use(async (req, res, next) => {
    if (!req.url.startsWith('/api/chat')) return next()

    try {
      const data = loadData()
      const url = new URL(req.url, 'http://localhost')
      const pathParts = url.pathname.replace('/api/chat', '').split('/').filter(Boolean)

      // GET /api/chat/messages — list with filters + search
      if (req.method === 'GET' && (pathParts.length === 0 || pathParts[0] === 'messages')) {
        let messages = [...data.messages]

        const sender = url.searchParams.get('sender')
        const target = url.searchParams.get('target')
        const type = url.searchParams.get('type')
        const search = url.searchParams.get('search')
        const from = url.searchParams.get('from')
        const to = url.searchParams.get('to')
        const limit = parseInt(url.searchParams.get('limit') || '100')
        const offset = parseInt(url.searchParams.get('offset') || '0')

        if (sender) messages = messages.filter(m => m.sender === sender)
        if (target) messages = messages.filter(m => m.targets.includes(target))
        if (type) messages = messages.filter(m => m.type === type)
        if (search) {
          const q = search.toLowerCase()
          messages = messages.filter(m => m.content.toLowerCase().includes(q))
        }
        if (from) messages = messages.filter(m => m.timestamp >= from)
        if (to) messages = messages.filter(m => m.timestamp <= to)

        const total = messages.length
        messages = messages.slice(offset, offset + limit)

        return sendJSON(res, 200, { messages, total })
      }

      // POST /api/chat/messages — send a message
      if (req.method === 'POST' && (pathParts.length === 0 || pathParts[0] === 'messages')) {
        const body = await parseBody(req)
        const now = new Date().toISOString()

        // Determine message type
        let type = body.type || 'broadcast'
        if (body.targets && body.targets.length === 1) type = 'direct'
        else if (body.targets && body.targets.length > 1) type = 'group'
        else if (!body.targets || body.targets.length === 0) type = 'broadcast'

        const msg = {
          id: `msg-${randomUUID().slice(0, 8)}`,
          type,
          sender: body.sender || 'user',
          targets: body.targets || [],
          content: body.content || '',
          timestamp: now,
          mode: body.mode || null,
          taskRef: body.taskRef || null,
          channel: body.channel || 'general',
        }

        data.messages.push(msg)

        // Handle /task slash command
        let createdTask = null
        if (msg.content.startsWith('/task create ')) {
          const title = msg.content.replace('/task create ', '').trim()
          if (title) {
            const tasksData = loadTasks()
            const task = {
              id: `task-${randomUUID().slice(0, 8)}`,
              title,
              description: `Created from chat by ${msg.sender}`,
              status: 'backlog',
              priority: 'medium',
              assignees: msg.targets.length > 0 ? msg.targets : [],
              created: now,
              updated: now,
            }
            tasksData.tasks.push(task)
            tasksData.history.push({
              id: randomUUID().slice(0, 8),
              taskId: task.id,
              action: 'created',
              details: { title, source: 'chat', messageId: msg.id },
              timestamp: now,
            })
            saveTasks(tasksData)
            createdTask = task

            // Post system message about task creation
            const sysMsg = {
              id: `msg-${randomUUID().slice(0, 8)}`,
              type: 'system',
              sender: 'system',
              targets: [],
              content: `Task "${title}" created and added to backlog`,
              timestamp: new Date(Date.now() + 100).toISOString(),
              mode: null,
              taskRef: task.id,
              channel: msg.channel,
            }
            data.messages.push(sysMsg)
          }
        }

        saveData(data)

        // Generate stub responses from targeted beings
        const responses = []
        if (msg.sender === 'user' && msg.targets.length > 0 && !msg.content.startsWith('/')) {
          const delays = msg.mode === 'sequential'
            ? msg.targets.map((_, i) => 800 + i * 1200)
            : msg.targets.map((_, i) => 600 + i * 400)

          for (let i = 0; i < msg.targets.length; i++) {
            const beingId = msg.targets[i]
            const response = {
              id: `msg-${randomUUID().slice(0, 8)}`,
              type: msg.targets.length === 1 ? 'direct' : 'group',
              sender: beingId,
              targets: [],
              content: generateResponse(beingId),
              timestamp: new Date(Date.now() + delays[i]).toISOString(),
              mode: null,
              taskRef: msg.taskRef,
              channel: msg.channel,
            }
            responses.push(response)
            data.messages.push(response)
          }
          saveData(data)
        }

        return sendJSON(res, 201, { message: msg, responses, createdTask })
      }

      // DELETE /api/chat/messages/:id
      if (req.method === 'DELETE' && pathParts[0] === 'messages' && pathParts[1]) {
        const idx = data.messages.findIndex(m => m.id === pathParts[1])
        if (idx === -1) return sendJSON(res, 404, { error: 'Message not found' })
        data.messages.splice(idx, 1)
        saveData(data)
        return sendJSON(res, 200, { deleted: pathParts[1] })
      }

      // POST /api/chat/system — post a system message (for task updates etc.)
      if (req.method === 'POST' && pathParts[0] === 'system') {
        const body = await parseBody(req)
        const msg = {
          id: `msg-${randomUUID().slice(0, 8)}`,
          type: 'system',
          sender: 'system',
          targets: [],
          content: body.content || '',
          timestamp: new Date().toISOString(),
          mode: null,
          taskRef: body.taskRef || null,
          channel: body.channel || 'general',
        }
        data.messages.push(msg)
        saveData(data)
        return sendJSON(res, 201, { message: msg })
      }

      return sendJSON(res, 404, { error: 'Not found' })
    } catch (err) {
      console.error('[chat-api]', err)
      sendJSON(res, 500, { error: err.message })
    }
  })
}
