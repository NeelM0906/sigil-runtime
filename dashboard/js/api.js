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
    return this._post(`/api/team-manager/graphs/${encodeURIComponent(graphId)}/delete`, {});
  }

  async tmAddNode(graphId, kind, label, posX, posY, config = {}) {
    return this._post('/api/team-manager/nodes', {
      graph_id: graphId, kind, label, position_x: posX, position_y: posY, config,
    });
  }

  async tmUpdateNode(nodeId, changes) {
    return this._post(`/api/team-manager/nodes/${encodeURIComponent(nodeId)}/update`, changes);
  }

  async tmDeleteNode(nodeId) {
    return this._post(`/api/team-manager/nodes/${encodeURIComponent(nodeId)}/delete`, {});
  }

  async tmAddEdge(graphId, sourceId, targetId, edgeType) {
    return this._post('/api/team-manager/edges', {
      graph_id: graphId, source_node_id: sourceId, target_node_id: targetId, edge_type: edgeType,
    });
  }

  async tmDeleteEdge(edgeId) {
    return this._post(`/api/team-manager/edges/${encodeURIComponent(edgeId)}/delete`, {});
  }

  async tmDeployGraph(graphId) {
    return this._post('/api/team-manager/deploy', { graph_id: graphId });
  }

  async tmValidateGraph(graphId) {
    return this._post('/api/team-manager/validate', { graph_id: graphId });
  }

  // Graph updates
  async tmUpdateGraph(graphId, changes) {
    return this._post(`/api/team-manager/graphs/${encodeURIComponent(graphId)}/update`, changes);
  }

  // Deployments
  async tmListDeployments(graphId) {
    return this._get('/api/team-manager/deployments', graphId ? { graph_id: graphId } : {});
  }

  async tmGetDeployment(deploymentId) {
    return this._get(`/api/team-manager/deployments/${encodeURIComponent(deploymentId)}`);
  }

  async tmCancelDeployment(deploymentId) {
    return this._post(`/api/team-manager/deployments/${encodeURIComponent(deploymentId)}/cancel`, {});
  }

  async tmGetPrimer(deploymentId, nodeId) {
    return this._post(`/api/team-manager/deployments/${encodeURIComponent(deploymentId)}/primer`, { node_id: nodeId });
  }

  // Schedules
  async tmListSchedules(graphId) {
    return this._get('/api/team-manager/schedules', graphId ? { graph_id: graphId } : {});
  }

  async tmCreateSchedule(graphId, name, cronExpression, action = 'deploy', actionParams = {}, requiresApproval = false) {
    return this._post('/api/team-manager/schedules', {
      graph_id: graphId, name, cron_expression: cronExpression, action, action_params: actionParams, requires_approval: requiresApproval,
    });
  }

  async tmUpdateSchedule(scheduleId, changes) {
    return this._post(`/api/team-manager/schedules/${encodeURIComponent(scheduleId)}/update`, changes);
  }

  async tmDeleteSchedule(scheduleId) {
    return this._post(`/api/team-manager/schedules/${encodeURIComponent(scheduleId)}/delete`, {});
  }

  async tmToggleSchedule(scheduleId, enabled) {
    return this._post(`/api/team-manager/schedules/${encodeURIComponent(scheduleId)}/toggle`, { enabled });
  }

  // Variables
  async tmSetVariable(graphId, key, value = '', varType = 'string') {
    return this._post('/api/team-manager/variables', { graph_id: graphId, key, value, var_type: varType });
  }

  async tmListVariables(graphId) {
    return this._get('/api/team-manager/variables', { graph_id: graphId });
  }

  async tmDeleteVariable(graphId, key) {
    return this._post(`/api/team-manager/variables/${encodeURIComponent(graphId)}/delete`, { key });
  }

  // Pipelines
  async tmSavePipeline(graphId, nodeId, steps = []) {
    return this._post('/api/team-manager/pipelines', { graph_id: graphId, node_id: nodeId, steps });
  }

  async tmGetPipeline(nodeId) {
    return this._get('/api/team-manager/pipelines', { node_id: nodeId });
  }

  // Layouts
  async tmSaveLayout(graphId, layout = {}, isDefault = false) {
    return this._post('/api/team-manager/layouts', { graph_id: graphId, layout, is_default: isDefault });
  }

  async tmListLayouts(graphId) {
    return this._get('/api/team-manager/layouts', { graph_id: graphId });
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
