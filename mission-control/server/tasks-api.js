/**
 * Task Board API — Vite middleware handler
 * Persists to data/tasks.json. Zero dependencies beyond Node stdlib.
 */
import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { randomUUID } from 'crypto'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DATA_FILE = join(__dirname, '..', 'data', 'tasks.json')

// ── Persistence ──────────────────────────────────────────────

function loadData() {
  if (!existsSync(DATA_FILE)) {
    const seed = { tasks: seedTasks(), history: [] }
    writeFileSync(DATA_FILE, JSON.stringify(seed, null, 2))
    return seed
  }
  return JSON.parse(readFileSync(DATA_FILE, 'utf-8'))
}

function saveData(data) {
  writeFileSync(DATA_FILE, JSON.stringify(data, null, 2))
}

// ── History Logger ───────────────────────────────────────────

function logHistory(data, taskId, action, details = {}) {
  data.history.push({
    id: randomUUID().slice(0, 8),
    taskId,
    action,
    details,
    timestamp: new Date().toISOString(),
  })
  // Keep last 500 entries
  if (data.history.length > 500) {
    data.history = data.history.slice(-500)
  }
}

// ── Seed Data ────────────────────────────────────────────────

function seedTasks() {
  return [
    {
      id: 'task-001',
      title: 'Implement Mission Control Dashboard',
      description: 'Build a React + Tailwind mission control dashboard with beings registry, task board, chat, and sub-agent tracker.',
      status: 'in_progress',
      priority: 'critical',
      assignees: ['prime', 'callie'],
      created: '2026-03-02T10:00:00Z',
      updated: '2026-03-02T14:30:00Z',
    },
    {
      id: 'task-002',
      title: 'Prove-Ahead Q1 Competitive Report',
      description: 'Run full competitive intelligence sweep for Q1 2026. Analyze top 5 competitors, pricing shifts, and feature launches.',
      status: 'in_progress',
      priority: 'high',
      assignees: ['athena'],
      created: '2026-02-28T09:00:00Z',
      updated: '2026-03-01T16:00:00Z',
    },
    {
      id: 'task-003',
      title: 'Voice Pipeline Integration Tests',
      description: 'Write and run integration tests for the ElevenLabs + Twilio voice pipeline. Cover inbound/outbound call flows.',
      status: 'in_review',
      priority: 'medium',
      assignees: ['callie', 'mylo'],
      created: '2026-02-27T11:00:00Z',
      updated: '2026-03-01T10:00:00Z',
    },
    {
      id: 'task-004',
      title: 'Memory Consolidation Optimization',
      description: 'Optimize semantic memory consolidation to reduce contradiction detection latency from 200ms to under 50ms.',
      status: 'backlog',
      priority: 'medium',
      assignees: ['prime'],
      created: '2026-03-01T08:00:00Z',
      updated: '2026-03-01T08:00:00Z',
    },
    {
      id: 'task-005',
      title: 'Brand Voice Guidelines v2',
      description: 'Update brand voice guidelines based on Q4 feedback. Include new tone variants for technical vs casual contexts.',
      status: 'backlog',
      priority: 'low',
      assignees: ['mylo'],
      created: '2026-02-25T14:00:00Z',
      updated: '2026-02-25T14:00:00Z',
    },
    {
      id: 'task-006',
      title: 'Governance Policy Audit',
      description: 'Audit all tool governance policies. Verify risk thresholds, approval flows, and logging compliance.',
      status: 'done',
      priority: 'high',
      assignees: ['sentinel', 'prime'],
      created: '2026-02-20T10:00:00Z',
      updated: '2026-02-26T17:00:00Z',
    },
    {
      id: 'task-007',
      title: 'Colosseum Tournament Results Analysis',
      description: 'Analyze results from Colosseum v2 tournament run. Extract being performance rankings and judge calibration data.',
      status: 'done',
      priority: 'medium',
      assignees: ['athena'],
      created: '2026-02-22T09:00:00Z',
      updated: '2026-02-24T15:00:00Z',
    },
  ]
}

// ── Request body parser ──────────────────────────────────────

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

// ── API Route Handler ────────────────────────────────────────

export function tasksApiMiddleware(server) {
  server.middlewares.use(async (req, res, next) => {
    // Only handle /api/tasks routes
    if (!req.url.startsWith('/api/tasks')) return next()

    try {
      const data = loadData()
      const url = new URL(req.url, 'http://localhost')
      const pathParts = url.pathname.replace('/api/tasks', '').split('/').filter(Boolean)

      // GET /api/tasks — list all (with optional filters)
      if (req.method === 'GET' && pathParts.length === 0) {
        let tasks = [...data.tasks]

        const assignee = url.searchParams.get('assignee')
        const priority = url.searchParams.get('priority')
        const status = url.searchParams.get('status')
        const dateFrom = url.searchParams.get('from')
        const dateTo = url.searchParams.get('to')

        if (assignee) tasks = tasks.filter(t => t.assignees.includes(assignee))
        if (priority) tasks = tasks.filter(t => t.priority === priority)
        if (status) tasks = tasks.filter(t => t.status === status)
        if (dateFrom) tasks = tasks.filter(t => t.created >= dateFrom)
        if (dateTo) tasks = tasks.filter(t => t.created <= dateTo)

        return sendJSON(res, 200, { tasks })
      }

      // GET /api/tasks/history?taskId=xxx — get history for a task (or all)
      if (req.method === 'GET' && pathParts[0] === 'history') {
        const taskId = url.searchParams.get('taskId')
        let history = data.history || []
        if (taskId) history = history.filter(h => h.taskId === taskId)
        return sendJSON(res, 200, { history: history.slice(-50) })
      }

      // GET /api/tasks/:id — single task + its history
      if (req.method === 'GET' && pathParts.length === 1) {
        const task = data.tasks.find(t => t.id === pathParts[0])
        if (!task) return sendJSON(res, 404, { error: 'Task not found' })
        const history = (data.history || []).filter(h => h.taskId === task.id)
        return sendJSON(res, 200, { task, history })
      }

      // POST /api/tasks — create task
      if (req.method === 'POST' && pathParts.length === 0) {
        const body = await parseBody(req)
        const now = new Date().toISOString()
        const task = {
          id: `task-${randomUUID().slice(0, 8)}`,
          title: body.title || 'Untitled Task',
          description: body.description || '',
          status: body.status || 'backlog',
          priority: body.priority || 'medium',
          assignees: body.assignees || [],
          created: now,
          updated: now,
        }
        data.tasks.push(task)
        logHistory(data, task.id, 'created', { title: task.title, priority: task.priority })
        saveData(data)
        return sendJSON(res, 201, { task })
      }

      // PATCH /api/tasks/:id — update task
      if (req.method === 'PATCH' && pathParts.length === 1) {
        const idx = data.tasks.findIndex(t => t.id === pathParts[0])
        if (idx === -1) return sendJSON(res, 404, { error: 'Task not found' })

        const body = await parseBody(req)
        const old = { ...data.tasks[idx] }
        const now = new Date().toISOString()

        // Track what changed for history
        const changes = {}
        for (const key of ['title', 'description', 'status', 'priority', 'assignees']) {
          if (body[key] !== undefined && JSON.stringify(body[key]) !== JSON.stringify(old[key])) {
            changes[key] = { from: old[key], to: body[key] }
            data.tasks[idx][key] = body[key]
          }
        }
        data.tasks[idx].updated = now

        if (Object.keys(changes).length > 0) {
          const action = changes.status ? 'status_change' : 'updated'
          logHistory(data, old.id, action, changes)
        }

        saveData(data)
        return sendJSON(res, 200, { task: data.tasks[idx] })
      }

      // DELETE /api/tasks/:id — delete task
      if (req.method === 'DELETE' && pathParts.length === 1) {
        const idx = data.tasks.findIndex(t => t.id === pathParts[0])
        if (idx === -1) return sendJSON(res, 404, { error: 'Task not found' })

        const removed = data.tasks.splice(idx, 1)[0]
        logHistory(data, removed.id, 'deleted', { title: removed.title })
        saveData(data)
        return sendJSON(res, 200, { deleted: removed.id })
      }

      return sendJSON(res, 404, { error: 'Not found' })
    } catch (err) {
      console.error('[tasks-api]', err)
      sendJSON(res, 500, { error: err.message })
    }
  })
}
