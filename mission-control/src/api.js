/**
 * Mission Control API client — routes through BOMBA SR runtime via /api/mc/*
 */

async function request(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || 'Request failed')
  }
  return res.json()
}

// ── Tasks API ────────────────────────────────────────────────

export const tasksApi = {
  list(filters = {}) {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(filters)) {
      if (v) params.set(k, v)
    }
    const qs = params.toString()
    return request(`/api/mc/tasks${qs ? `?${qs}` : ''}`)
  },
  get(id) {
    return request(`/api/mc/tasks/${id}`)
  },
  create(task) {
    return request('/api/mc/tasks', { method: 'POST', body: JSON.stringify(task) })
  },
  update(id, changes) {
    return request(`/api/mc/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })
  },
  delete(id) {
    return request(`/api/mc/tasks/${id}`, { method: 'DELETE' })
  },
  history(taskId) {
    return request(`/api/mc/tasks/history${taskId ? `?taskId=${taskId}` : ''}`)
  },
}

// ── Beings API ───────────────────────────────────────────────

export const beingsApi = {
  list(filters = {}) {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(filters)) {
      if (v) params.set(k, v)
    }
    const qs = params.toString()
    return request(`/api/mc/beings${qs ? `?${qs}` : ''}`)
  },
  get(id) {
    return request(`/api/mc/beings/${id}`)
  },
  update(id, changes) {
    return request(`/api/mc/beings/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })
  },
}

// ── Chat API ─────────────────────────────────────────────────

export const chatApi = {
  list(filters = {}) {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(filters)) {
      if (v) params.set(k, String(v))
    }
    const qs = params.toString()
    return request(`/api/mc/chat/messages${qs ? `?${qs}` : ''}`)
  },
  send(message) {
    return request('/api/mc/chat/messages', { method: 'POST', body: JSON.stringify(message) })
  },
  delete(id) {
    return request(`/api/mc/chat/messages/${id}`, { method: 'DELETE' })
  },
  postSystem(content, taskRef = null) {
    return request('/api/mc/chat/system', {
      method: 'POST',
      body: JSON.stringify({ content, taskRef }),
    })
  },
}

// ── Sub-Agents API ───────────────────────────────────────────

export const subagentsApi = {
  list() {
    return request('/api/mc/subagents')
  },
}
