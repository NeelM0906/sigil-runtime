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

  // On 401 force re-login
  if (res.status === 401) {
    localStorage.removeItem('mc_auth')
    window.location.reload()
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
  sessions(userId) {
    const qs = userId ? `?user_id=${userId}` : ''
    return request(`/api/mc/chat/sessions${qs}`)
  },
  createSession(name, userId) {
    return request('/api/mc/chat/sessions', { method: 'POST', body: JSON.stringify({ name, user_id: userId }) })
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

// ── ACT-I Architecture API ──────────────────────────────────

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

// ── Code Agent API (Pi Bridge) ─────────────────────────────

export const codeApi = {
  health() {
    return request('/api/mc/code/health')
  },
  sessions() {
    return request('/api/mc/code/sessions')
  },
  createSession(title = 'New session') {
    return request('/api/mc/code/sessions', { method: 'POST', body: JSON.stringify({ title }) })
  },
  deleteSession(id) {
    return request(`/api/mc/code/sessions/${id}`, { method: 'DELETE' })
  },
  prompt(sessionId, message) {
    return request(`/api/mc/code/sessions/${sessionId}/prompt`, {
      method: 'POST', body: JSON.stringify({ message }),
    })
  },
  abort(sessionId) {
    return request(`/api/mc/code/sessions/${sessionId}/abort`, { method: 'POST' })
  },
  messages(sessionId) {
    return request(`/api/mc/code/sessions/${sessionId}/messages`)
  },
  state() {
    return request('/api/mc/code/state')
  },
  respondUi(sessionId, requestId, response) {
    return request(`/api/mc/code/sessions/${sessionId}/respond-ui`, {
      method: 'POST', body: JSON.stringify({ request_id: requestId, response }),
    })
  },
  files(depth = 3) {
    return request(`/api/mc/code/files?depth=${depth}`)
  },
  readFile(filePath) {
    return request(`/api/mc/code/files/read?path=${encodeURIComponent(filePath)}`)
  },
}
