/**
 * Beings Registry API — Vite middleware handler
 * Persists to data/beings.json.
 */
import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { randomUUID } from 'crypto'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DATA_FILE = join(__dirname, '..', 'data', 'beings.json')

function loadData() {
  if (!existsSync(DATA_FILE)) {
    const seed = { beings: [] }
    writeFileSync(DATA_FILE, JSON.stringify(seed, null, 2))
    return seed
  }
  return JSON.parse(readFileSync(DATA_FILE, 'utf-8'))
}

function saveData(data) {
  writeFileSync(DATA_FILE, JSON.stringify(data, null, 2))
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

export function beingsApiMiddleware(server) {
  server.middlewares.use(async (req, res, next) => {
    if (!req.url.startsWith('/api/beings')) return next()

    try {
      const data = loadData()
      const url = new URL(req.url, 'http://localhost')
      const pathParts = url.pathname.replace('/api/beings', '').split('/').filter(Boolean)

      // GET /api/beings — list all
      if (req.method === 'GET' && pathParts.length === 0) {
        const type = url.searchParams.get('type')
        const status = url.searchParams.get('status')
        let beings = [...data.beings]
        if (type) beings = beings.filter(b => b.type === type)
        if (status) beings = beings.filter(b => b.status === status)
        return sendJSON(res, 200, { beings })
      }

      // GET /api/beings/:id
      if (req.method === 'GET' && pathParts.length === 1) {
        const being = data.beings.find(b => b.id === pathParts[0])
        if (!being) return sendJSON(res, 404, { error: 'Being not found' })
        return sendJSON(res, 200, { being })
      }

      // POST /api/beings — register a new being
      if (req.method === 'POST' && pathParts.length === 0) {
        const body = await parseBody(req)
        // Check for duplicate ID
        if (body.id && data.beings.some(b => b.id === body.id)) {
          return sendJSON(res, 409, { error: `Being '${body.id}' already exists` })
        }
        const being = {
          id: body.id || `being-${randomUUID().slice(0, 8)}`,
          name: body.name || 'Unknown Being',
          role: body.role || '',
          avatar: body.avatar || (body.name || 'U').charAt(0).toUpperCase(),
          status: body.status || 'offline',
          description: body.description || '',
          type: body.type || 'custom',
          tools: body.tools || [],
          skills: body.skills || [],
          color: body.color || '#6b7280',
          model_id: body.model_id || '',
          workspace: body.workspace || '',
          tenant_id: body.tenant_id || '',
          metrics: body.metrics || { tasksCompleted: 0, uptime: '0h', successRate: 0 },
        }
        data.beings.push(being)
        saveData(data)
        return sendJSON(res, 201, { being })
      }

      // PATCH /api/beings/:id — update being (status, metrics, etc.)
      if (req.method === 'PATCH' && pathParts.length === 1) {
        const idx = data.beings.findIndex(b => b.id === pathParts[0])
        if (idx === -1) return sendJSON(res, 404, { error: 'Being not found' })

        const body = await parseBody(req)
        const allowed = ['name', 'role', 'avatar', 'status', 'description', 'tools', 'skills', 'color', 'model_id', 'metrics']
        for (const key of allowed) {
          if (body[key] !== undefined) {
            data.beings[idx][key] = body[key]
          }
        }
        saveData(data)
        return sendJSON(res, 200, { being: data.beings[idx] })
      }

      // DELETE /api/beings/:id
      if (req.method === 'DELETE' && pathParts.length === 1) {
        const idx = data.beings.findIndex(b => b.id === pathParts[0])
        if (idx === -1) return sendJSON(res, 404, { error: 'Being not found' })
        const removed = data.beings.splice(idx, 1)[0]
        saveData(data)
        return sendJSON(res, 200, { deleted: removed.id })
      }

      return sendJSON(res, 404, { error: 'Not found' })
    } catch (err) {
      console.error('[beings-api]', err)
      sendJSON(res, 500, { error: err.message })
    }
  })
}
