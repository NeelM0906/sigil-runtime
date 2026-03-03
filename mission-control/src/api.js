/**
 * Task Board API client
 */
const BASE = '/api/tasks'

async function request(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || 'Request failed')
  }
  return res.json()
}

export const tasksApi = {
  list(filters = {}) {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(filters)) {
      if (v) params.set(k, v)
    }
    const qs = params.toString()
    return request(qs ? `?${qs}` : '')
  },

  get(id) {
    return request(`/${id}`)
  },

  create(task) {
    return request('', { method: 'POST', body: JSON.stringify(task) })
  },

  update(id, changes) {
    return request(`/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })
  },

  delete(id) {
    return request(`/${id}`, { method: 'DELETE' })
  },

  history(taskId) {
    return request(`/history${taskId ? `?taskId=${taskId}` : ''}`)
  },
}
