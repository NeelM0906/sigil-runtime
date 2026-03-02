// Sigil Dashboard — Team Manager Store

export class TeamManagerStore {
  constructor(api) {
    this.api = api;
    this.graphs = [];
    this.activeGraph = null;
    this.nodes = [];
    this.edges = [];
    this.selectedNodes = new Set();
    this.viewport = { x: 0, y: 0, zoom: 1 };
    this._listeners = new Set();
    this._loading = false;
    this._error = null;
  }

  /** Subscribe to state changes. Returns unsubscribe function. */
  subscribe(fn) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  }

  _notify() {
    for (const fn of this._listeners) {
      try { fn(); } catch (e) { console.error('TeamManagerStore listener error:', e); }
    }
  }

  get loading() { return this._loading; }
  get error() { return this._error; }

  // ── Graph list ──

  async loadGraphs() {
    this._loading = true;
    this._error = null;
    this._notify();
    try {
      const data = await this.api.tmListGraphs();
      this.graphs = Array.isArray(data.graphs) ? data.graphs : [];
    } catch (err) {
      this._error = err.message;
      this.graphs = [];
    } finally {
      this._loading = false;
      this._notify();
    }
  }

  async loadGraph(graphId) {
    this._loading = true;
    this._error = null;
    this._notify();
    try {
      const data = await this.api.tmGetGraph(graphId);
      this.activeGraph = data.graph || data;
      this.nodes = Array.isArray(data.nodes) ? data.nodes : [];
      this.edges = Array.isArray(data.edges) ? data.edges : [];
      this.selectedNodes.clear();
    } catch (err) {
      this._error = err.message;
      this.activeGraph = null;
      this.nodes = [];
      this.edges = [];
    } finally {
      this._loading = false;
      this._notify();
    }
  }

  async createGraph(name, description) {
    this._error = null;
    try {
      const data = await this.api.tmCreateGraph(name, description);
      await this.loadGraphs();
      return data;
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  async deleteGraph(graphId) {
    this._error = null;
    try {
      await this.api.tmDeleteGraph(graphId);
      if (this.activeGraph && this.activeGraph.id === graphId) {
        this.activeGraph = null;
        this.nodes = [];
        this.edges = [];
        this.selectedNodes.clear();
      }
      await this.loadGraphs();
    } catch (err) {
      this._error = err.message;
      this._notify();
    }
  }

  // ── Nodes ──

  async addNode(kind, label, x, y, config = {}) {
    if (!this.activeGraph) return null;
    this._error = null;
    try {
      const data = await this.api.tmAddNode(this.activeGraph.id, kind, label, x, y, config);
      const node = data.node || data;
      this.nodes = [...this.nodes, node];
      this._notify();
      return node;
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  async updateNode(nodeId, changes) {
    this._error = null;
    try {
      const data = await this.api.tmUpdateNode(nodeId, changes);
      const updated = data.node || data;
      this.nodes = this.nodes.map(n => n.id === nodeId ? { ...n, ...updated } : n);
      this._notify();
      return updated;
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  async deleteNode(nodeId) {
    this._error = null;
    try {
      await this.api.tmDeleteNode(nodeId);
      this.nodes = this.nodes.filter(n => n.id !== nodeId);
      this.edges = this.edges.filter(e => e.source_node_id !== nodeId && e.target_node_id !== nodeId);
      this.selectedNodes.delete(nodeId);
      this._notify();
    } catch (err) {
      this._error = err.message;
      this._notify();
    }
  }

  // ── Edges ──

  async addEdge(sourceId, targetId, edgeType = 'default') {
    if (!this.activeGraph) return null;
    this._error = null;
    try {
      const data = await this.api.tmAddEdge(this.activeGraph.id, sourceId, targetId, edgeType);
      const edge = data.edge || data;
      this.edges = [...this.edges, edge];
      this._notify();
      return edge;
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  async deleteEdge(edgeId) {
    this._error = null;
    try {
      await this.api.tmDeleteEdge(edgeId);
      this.edges = this.edges.filter(e => e.id !== edgeId);
      this._notify();
    } catch (err) {
      this._error = err.message;
      this._notify();
    }
  }

  // ── Deploy ──

  async deployGraph(graphId) {
    this._error = null;
    try {
      const data = await this.api.tmDeployGraph(graphId);
      await this.loadGraphs();
      return data;
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  async validateGraph(graphId) {
    this._error = null;
    try {
      return await this.api.tmValidateGraph(graphId);
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  // ── Selection ──

  selectNode(nodeId, multi = false) {
    if (!multi) {
      this.selectedNodes.clear();
    }
    if (this.selectedNodes.has(nodeId)) {
      this.selectedNodes.delete(nodeId);
    } else {
      this.selectedNodes.add(nodeId);
    }
    this._notify();
  }

  clearSelection() {
    if (this.selectedNodes.size > 0) {
      this.selectedNodes.clear();
      this._notify();
    }
  }

  // ── Viewport ──

  setViewport(x, y, zoom) {
    this.viewport = { x, y, zoom: Math.max(0.1, Math.min(5, zoom)) };
    // No notify -- viewport updates are high-frequency; canvas reads directly
  }

  resetViewport() {
    this.viewport = { x: 0, y: 0, zoom: 1 };
    this._notify();
  }

  // ── Local node move (optimistic, no API call) ──

  moveNodeLocal(nodeId, x, y) {
    this.nodes = this.nodes.map(n =>
      n.id === nodeId ? { ...n, position_x: x, position_y: y } : n
    );
    // No notify -- drag updates are high-frequency; canvas handles its own render
  }
}
