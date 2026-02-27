// Sigil Dashboard — API Client

export class SigilAPI {
  constructor({ baseUrl = '', tenantId = 'tenant-local', userId = 'user-local', workspace = null } = {}) {
    this.baseUrl = baseUrl;
    this.tenantId = tenantId;
    this.userId = userId;
    this.workspace = workspace;
  }

  _qs(extra = {}) {
    const params = new URLSearchParams();
    params.set('tenant_id', this.tenantId);
    params.set('user_id', this.userId);
    if (this.workspace) params.set('workspace_root', this.workspace);
    for (const [k, v] of Object.entries(extra)) {
      if (v != null) params.set(k, String(v));
    }
    return params.toString();
  }

  async _get(path, extra = {}) {
    const url = `${this.baseUrl}${path}?${this._qs(extra)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
    return res.json();
  }

  async _post(path, body = {}) {
    const payload = {
      tenant_id: this.tenantId,
      user_id: this.userId,
      ...body,
    };
    if (this.workspace) payload.workspace_root = this.workspace;
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
    return res.json();
  }

  // Dashboard
  getDashboard() { return this._get('/api/dashboard'); }
  getActivity(limit = 50) { return this._get('/api/dashboard/activity', { limit }); }

  // Chat
  chat(sessionId, message) {
    return this._post('/chat', { session_id: sessionId, message });
  }

  // Autonomy controls
  heartbeatAction(action) { return this._post(`/api/dashboard/heartbeat/${action}`); }
  cronAction(action) { return this._post(`/api/dashboard/cron/${action}`); }

  // Approvals
  decideApproval(approvalId, approved) {
    return this._post('/approvals/decide', { approval_id: approvalId, approved });
  }

  // Commands
  executeCommand(sessionId, command) {
    return this._post('/commands/execute', { session_id: sessionId, command });
  }

  // Health check
  async health() {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      return res.ok;
    } catch {
      return false;
    }
  }
}
