/**
 * Mission Control API client
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
    return request(`/api/tasks${qs ? `?${qs}` : ''}`)
  },
  get(id) {
    return request(`/api/tasks/${id}`)
  },
  create(task) {
    return request('/api/tasks', { method: 'POST', body: JSON.stringify(task) })
  },
  update(id, changes) {
    return request(`/api/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })
  },
  delete(id) {
    return request(`/api/tasks/${id}`, { method: 'DELETE' })
  },
  history(taskId) {
    return request(`/api/tasks/history${taskId ? `?taskId=${taskId}` : ''}`)
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
    return request(`/api/beings${qs ? `?${qs}` : ''}`)
  },
  get(id) {
    return request(`/api/beings/${id}`)
  },
  register(being) {
    return request('/api/beings', { method: 'POST', body: JSON.stringify(being) })
  },
  update(id, changes) {
    return request(`/api/beings/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })
  },
  delete(id) {
    return request(`/api/beings/${id}`, { method: 'DELETE' })
  },
}
