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
  sisterAction(action, sisterId) { return this._post(`/api/dashboard/sisters/${action}`, { sister_id: sisterId }); }

  // Approvals
  decideApproval(approvalId, approved) {
    return this._post('/approvals/decide', { approval_id: approvalId, approved });
  }

  // Commands
  executeCommand(sessionId, command) {
    return this._post('/commands/execute', { session_id: sessionId, command });
  }

  listCommands() {
    return this._get('/commands');
  }

  // Team Manager
  async tmListGraphs() { return this._get('/api/team-manager/graphs'); }

  async tmCreateGraph(name, description) {
    return this._post('/api/team-manager/graphs', { name, description });
  }

  async tmGetGraph(graphId) {
    return this._get(`/api/team-manager/graphs/${encodeURIComponent(graphId)}`);
  }

  async tmDeleteGraph(graphId) {
    const url = `${this.baseUrl}/api/team-manager/graphs/${encodeURIComponent(graphId)}?${this._qs()}`;
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error(`DELETE /api/team-manager/graphs/${graphId}: ${res.status}`);
    return res.json();
  }

  async tmAddNode(graphId, kind, label, posX, posY, config = {}) {
    return this._post('/api/team-manager/nodes', {
      graph_id: graphId, kind, label, position_x: posX, position_y: posY, config,
    });
  }

  async tmUpdateNode(nodeId, changes) {
    const url = `${this.baseUrl}/api/team-manager/nodes/${encodeURIComponent(nodeId)}?${this._qs()}`;
    const payload = { tenant_id: this.tenantId, user_id: this.userId, ...changes };
    if (this.workspace) payload.workspace_root = this.workspace;
    const res = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`PUT /api/team-manager/nodes/${nodeId}: ${res.status}`);
    return res.json();
  }

  async tmDeleteNode(nodeId) {
    const url = `${this.baseUrl}/api/team-manager/nodes/${encodeURIComponent(nodeId)}?${this._qs()}`;
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error(`DELETE /api/team-manager/nodes/${nodeId}: ${res.status}`);
    return res.json();
  }

  async tmAddEdge(graphId, sourceId, targetId, edgeType) {
    return this._post('/api/team-manager/edges', {
      graph_id: graphId, source_node_id: sourceId, target_node_id: targetId, edge_type: edgeType,
    });
  }

  async tmDeleteEdge(edgeId) {
    const url = `${this.baseUrl}/api/team-manager/edges/${encodeURIComponent(edgeId)}?${this._qs()}`;
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error(`DELETE /api/team-manager/edges/${edgeId}: ${res.status}`);
    return res.json();
  }

  async tmDeployGraph(graphId) {
    return this._post('/api/team-manager/deploy', { graph_id: graphId });
  }

  async tmValidateGraph(graphId) {
    return this._post('/api/team-manager/validate', { graph_id: graphId });
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
