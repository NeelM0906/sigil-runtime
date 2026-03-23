/**
 * Mission Control API client — routes through SAI runtime via /api/mc/*
 */

async function request(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json' }

  // Attach auth token if available
  try {
    const stored = localStorage.getItem('mc_auth')
    if (stored) {
      const { token } = JSON.parse(stored)
      if (token) headers['Authorization'] = `Bearer ${token}`
    }
  } catch { /* ignore parse errors */ }

  const res = await fetch(path, {
    headers,
    ...opts,
  })

  // On 401 force re-login (debounced to avoid reload loops)
  if (res.status === 401) {
    if (!window._mc_reloading) {
      window._mc_reloading = true
      localStorage.removeItem('mc_auth')
      window.location.reload()
    }
    throw new Error('Session expired')
  }

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
  cancel(id) {
    return request(`/api/mc/tasks/${id}/cancel`, { method: 'POST' })
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
  getDetail(id) {
    return request(`/api/mc/beings/${id}/detail`)
  },
  getFile(id, filePath) {
    return request(`/api/mc/beings/${id}/file?path=${encodeURIComponent(filePath)}`)
  },
  update(id, changes) {
    return request(`/api/mc/beings/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })
  },
}

// ── Projects API ─────────────────────────────────────────────

export const projectsApi = {
  list() {
    return request('/api/mc/projects')
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
  // Sessions
  sessions() {
    return request('/api/mc/chat/sessions')
  },
  createSession(name) {
    return request('/api/mc/chat/sessions', { method: 'POST', body: JSON.stringify({ name }) })
  },
  renameSession(id, name) {
    return request(`/api/mc/chat/sessions/${id}`, { method: 'PATCH', body: JSON.stringify({ name }) })
  },
  deleteSession(id) {
    return request(`/api/mc/chat/sessions/${id}`, { method: 'DELETE' })
  },
}

// ── Deliverables API ─────────────────────────────────────────

export const deliverablesApi = {
  list(taskId = null) {
    const qs = taskId ? `?task_id=${taskId}` : ''
    return request(`/api/mc/deliverables${qs}`)
  },
}

// ── Sub-Agents API ───────────────────────────────────────────

export const subagentsApi = {
  list() {
    return request('/api/mc/subagents')
  },
}

// ── Skills API ──────────────────────────────────────────────

export const skillsApi = {
  list(status) {
    const qs = status ? `?status=${status}` : ''
    return request(`/api/mc/skills${qs}`)
  },
  get(id) {
    return request(`/api/mc/skills/${id}`)
  },
  catalog(source) {
    const qs = source ? `?source=${source}` : ''
    return request(`/api/mc/skills/catalog${qs}`)
  },
  searchCatalog(q) {
    return request(`/api/mc/skills/catalog/search?q=${encodeURIComponent(q)}`)
  },
  install(source, skillId, reason) {
    return request('/api/mc/skills/install', {
      method: 'POST',
      body: JSON.stringify({ source, skill_id: skillId, reason }),
    })
  },
  applyInstall(requestId) {
    return request(`/api/mc/skills/install/${requestId}/apply`, { method: 'POST' })
  },
  installRequests(status) {
    const qs = status ? `?status=${status}` : ''
    return request(`/api/mc/skills/install${qs}`)
  },
  executions(limit = 50) {
    return request(`/api/mc/skills/executions?limit=${limit}`)
  },
}

// ── Auth API ────────────────────────────────────────────────

export const authApi = {
  login: (email, password) => request('/api/mc/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password })
  }),
  register: (email, password, name) => request('/api/mc/auth/register', {
    method: 'POST', body: JSON.stringify({ email, password, name })
  }),
  logout: () => request('/api/mc/auth/logout', { method: 'POST' }),
  me: () => request('/api/mc/auth/me'),
  updateProfile: (data) => request('/api/mc/auth/me', {
    method: 'PATCH', body: JSON.stringify(data)
  }),
  changePassword: (old_password, new_password) => request('/api/mc/auth/change-password', {
    method: 'POST', body: JSON.stringify({ old_password, new_password })
  }),
}

// ── ACT-I Architecture API ──────────────────────────────────

export const actiApi = {
  architecture() {
    return request('/api/mc/acti/architecture')
  },
  beings() {
    return request('/api/mc/acti/beings')
  },
  being(id) {
    return request(`/api/mc/acti/beings/${id}`)
  },
  clusters(filters = {}) {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(filters)) {
      if (v) params.set(k, v)
    }
    const qs = params.toString()
    return request(`/api/mc/acti/clusters${qs ? `?${qs}` : ''}`)
  },
  skillFamilies() {
    return request('/api/mc/acti/skill-families')
  },
  levers() {
    return request('/api/mc/acti/levers')
  },
  sisterProfile(id) {
    return request(`/api/mc/acti/sisters/${id}`)
  },
}
