// Sigil Dashboard — Team Manager Store

/** Generate a unique ID for cloned/pasted nodes. */
function _generateId() {
  return 'nd-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
}

export class TeamManagerStore {
  constructor(api) {
    this.api = api;
    this.graphs = [];
    this.activeGraph = null;
    this.nodes = [];
    this.edges = [];
    this.selectedNodes = new Set();
    this.deployments = [];
    this.variables = [];
    this.schedules = [];
    this.viewport = { x: 0, y: 0, zoom: 1 };
    this._listeners = new Set();
    this._loading = false;
    this._error = null;

    // Clipboard
    this.clipboard = null; // { nodes: [], sourceParentId }

    // Undo stack (position moves only)
    this._undoStack = []; // Array of Map<nodeId, {x, y}>, max 20

    // Collapse state
    this.collapsedGroups = new Set();

    // Autosave
    this._autosaveTimer = null;
    this._autosaveDirty = false;

    // UI state (matching reference ui-store)
    this.searchQuery = '';
    this.filterKind = null; // null = all, or 'agent'|'skill'|'group'|'pipeline'|'human'|'context'
    this.multiSelectedNodeIds = new Set();
    this.contextMenu = null; // { x, y, nodeId? }
    this.toasts = []; // { id, message, type: 'success'|'error'|'info' }
    this.settingsOpen = false;
    this.contextHubOpen = false;
    this.createDialogOpen = false;
    this.createDialogParentId = null;
    this.createDialogDefaultKind = null;
    this.deleteDialogNodeId = null;
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

  // ── Deployments ──

  async loadDeployments() {
    if (!this.activeGraph) return;
    try {
      const data = await this.api.tmListDeployments(this.activeGraph.id);
      this.deployments = Array.isArray(data.deployments) ? data.deployments : [];
      this._notify();
    } catch (err) {
      this._error = err.message;
      this._notify();
    }
  }

  async cancelDeployment(deploymentId) {
    try {
      await this.api.tmCancelDeployment(deploymentId);
      await this.loadDeployments();
    } catch (err) {
      this._error = err.message;
      this._notify();
    }
  }

  async getDeployment(deploymentId) {
    try {
      return await this.api.tmGetDeployment(deploymentId);
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  // ── Pipelines ──

  async loadPipeline(nodeId) {
    try {
      const data = await this.api.tmGetPipeline(nodeId);
      return data;
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  async savePipeline(graphId, nodeId, steps) {
    try {
      return await this.api.tmSavePipeline(graphId, nodeId, steps);
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  // ── Variables ──

  async loadVariables() {
    if (!this.activeGraph) return;
    try {
      const data = await this.api.tmListVariables(this.activeGraph.id);
      this.variables = Array.isArray(data.variables) ? data.variables : [];
      this._notify();
    } catch (err) {
      this._error = err.message;
      this._notify();
    }
  }

  async setVariable(key, value, varType = 'string') {
    if (!this.activeGraph) return null;
    try {
      const result = await this.api.tmSetVariable(this.activeGraph.id, key, value, varType);
      await this.loadVariables();
      return result;
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  async deleteVariable(key) {
    if (!this.activeGraph) return;
    try {
      await this.api.tmDeleteVariable(this.activeGraph.id, key);
      await this.loadVariables();
    } catch (err) {
      this._error = err.message;
      this._notify();
    }
  }

  // ── Schedules ──

  async loadSchedules() {
    if (!this.activeGraph) return;
    try {
      const data = await this.api.tmListSchedules(this.activeGraph.id);
      this.schedules = Array.isArray(data.schedules) ? data.schedules : [];
      this._notify();
    } catch (err) {
      this._error = err.message;
      this._notify();
    }
  }

  async createSchedule(name, cronExpr, action = 'deploy', requiresApproval = false) {
    if (!this.activeGraph) return null;
    try {
      const result = await this.api.tmCreateSchedule(
        this.activeGraph.id, name, cronExpr, action, {}, requiresApproval
      );
      await this.loadSchedules();
      return result;
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  async toggleSchedule(scheduleId, enabled) {
    try {
      await this.api.tmToggleSchedule(scheduleId, enabled);
      await this.loadSchedules();
    } catch (err) {
      this._error = err.message;
      this._notify();
    }
  }

  async deleteSchedule(scheduleId) {
    try {
      await this.api.tmDeleteSchedule(scheduleId);
      await this.loadSchedules();
    } catch (err) {
      this._error = err.message;
      this._notify();
    }
  }

  // ── Graph Meta ──

  async updateGraphMeta(changes) {
    if (!this.activeGraph) return null;
    try {
      const data = await this.api.tmUpdateGraph(this.activeGraph.id, changes);
      const updated = data.graph || data;
      this.activeGraph = { ...this.activeGraph, ...updated };
      this._notify();
      return updated;
    } catch (err) {
      this._error = err.message;
      this._notify();
      return null;
    }
  }

  // ── Selection ──

  selectNode(nodeId, multi = false) {
    if (!multi) {
      this._closeOverlays();
      this.clearMultiSelect();
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

  // ── Clipboard ──

  /**
   * Collect a node and all its descendants (via edges) into the clipboard.
   * Deep-clones all collected nodes so the clipboard is a snapshot.
   */
  copyNodes(nodeId) {
    const source = this.nodes.find(n => n.id === nodeId);
    if (!source) return;

    const descendants = this._collectDescendants(nodeId);
    const allNodes = [source, ...descendants].map(n => ({ ...n }));

    // Determine the parent of the source node from edges
    const parentEdge = this.edges.find(e => e.target_node_id === nodeId);
    const sourceParentId = parentEdge ? parentEdge.source_node_id : null;

    this.clipboard = { nodes: allNodes, sourceParentId };
  }

  /**
   * Paste clipboard nodes under a target parent. Generates new UUIDs,
   * remaps parent references in edges, appends "(copy)" to the root node name.
   * Persists each new node via the API. Returns the new root node ID.
   */
  async pasteNodes(targetParentId) {
    if (!this.clipboard || this.clipboard.nodes.length === 0) return null;
    if (!this.activeGraph) return null;

    const oldToNew = new Map();
    const clonedNodes = [];

    // First pass: assign new IDs and clone node data
    for (const node of this.clipboard.nodes) {
      const newId = _generateId();
      oldToNew.set(node.id, newId);
      clonedNodes.push({ ...node, id: newId });
    }

    // Second pass: rename root node with "(copy)" suffix
    if (clonedNodes.length > 0) {
      clonedNodes[0].label = (clonedNodes[0].label || clonedNodes[0].name || '') + ' (copy)';
      if (clonedNodes[0].name) {
        clonedNodes[0].name = clonedNodes[0].name + ' (copy)';
      }
    }

    // Persist each cloned node via API and collect results
    const newRootId = clonedNodes[0].id;
    for (const node of clonedNodes) {
      const x = node.position_x || 0;
      const y = node.position_y || 0;
      const config = node.config || {};
      await this.addNode(node.kind, node.label || node.name, x + 40, y + 40, config);
    }

    // Create edge from target parent to new root
    if (targetParentId) {
      await this.addEdge(targetParentId, newRootId, 'hierarchy');
    }

    // Recreate internal edges between cloned nodes (remap old IDs to new IDs)
    for (const edge of this.edges) {
      if (oldToNew.has(edge.source_node_id) && oldToNew.has(edge.target_node_id)) {
        await this.addEdge(
          oldToNew.get(edge.source_node_id),
          oldToNew.get(edge.target_node_id),
          edge.edge_type || 'default'
        );
      }
    }

    return newRootId;
  }

  /**
   * Convenience: copy a node then immediately paste it under the same parent.
   */
  async duplicateNodes(nodeId) {
    const parentEdge = this.edges.find(e => e.target_node_id === nodeId);
    const parentId = parentEdge ? parentEdge.source_node_id : null;
    this.copyNodes(nodeId);
    return await this.pasteNodes(parentId);
  }

  /**
   * Recursively collect all descendant nodes of a given nodeId via edges.
   */
  _collectDescendants(parentId) {
    const result = [];
    const childEdges = this.edges.filter(e => e.source_node_id === parentId);
    for (const edge of childEdges) {
      const child = this.nodes.find(n => n.id === edge.target_node_id);
      if (child) {
        result.push(child);
        result.push(...this._collectDescendants(child.id));
      }
    }
    return result;
  }

  // ── Undo (position moves only) ──

  /**
   * Push a position snapshot onto the undo stack.
   * @param {Map<string, {x: number, y: number}>} positionMap - Map of nodeId to {x, y}
   */
  pushUndo(positionMap) {
    this._undoStack.push(positionMap);
    if (this._undoStack.length > 20) {
      this._undoStack.shift();
    }
  }

  /**
   * Undo the last position change by popping the stack and restoring positions.
   */
  undo() {
    if (this._undoStack.length === 0) return;
    const positionMap = this._undoStack.pop();
    for (const [nodeId, pos] of positionMap) {
      this.moveNodeLocal(nodeId, pos.x, pos.y);
    }
    this._notify();
  }

  // ── Collapse ──

  /**
   * Toggle the collapsed state of a group node.
   */
  toggleCollapse(groupId) {
    if (this.collapsedGroups.has(groupId)) {
      this.collapsedGroups.delete(groupId);
    } else {
      this.collapsedGroups.add(groupId);
    }
    this._notify();
  }

  /**
   * Collapse all specified groups at once.
   * @param {string[]|Set<string>} groupIds
   */
  collapseAllGroups(groupIds) {
    this.collapsedGroups = new Set(groupIds);
    this._notify();
  }

  /**
   * Expand all groups (clear collapsed set).
   */
  expandAllGroups() {
    this.collapsedGroups = new Set();
    this._notify();
  }

  /**
   * Returns nodes filtered to exclude children of collapsed groups (recursive).
   * A node is hidden if any of its ancestor groups is collapsed.
   */
  getVisibleNodes() {
    if (this.collapsedGroups.size === 0) return [...this.nodes];

    // Build a set of all node IDs that are descendants of collapsed groups
    const hiddenIds = new Set();
    const collectHidden = (parentId) => {
      const childEdges = this.edges.filter(e => e.source_node_id === parentId);
      for (const edge of childEdges) {
        hiddenIds.add(edge.target_node_id);
        collectHidden(edge.target_node_id);
      }
    };

    for (const groupId of this.collapsedGroups) {
      collectHidden(groupId);
    }

    return this.nodes.filter(n => !hiddenIds.has(n.id));
  }

  // ── Autosave ──

  /**
   * Mark the current graph state as dirty. Starts an 800ms debounce timer
   * that triggers _autoSave() when it fires.
   */
  markDirty() {
    this._autosaveDirty = true;
    if (this._autosaveTimer) {
      clearTimeout(this._autosaveTimer);
    }
    this._autosaveTimer = setTimeout(() => {
      this._autoSave();
    }, 800);
  }

  /**
   * Persist the current graph state if dirty and a graph is active.
   */
  async _autoSave() {
    if (!this._autosaveDirty || !this.activeGraph) return;
    this._autosaveDirty = false;
    this._autosaveTimer = null;
    try {
      await this.updateGraphMeta({
        nodes: this.nodes,
        edges: this.edges,
        viewport: this.viewport,
      });
    } catch (err) {
      console.error('TeamManagerStore autosave failed:', err);
    }
  }

  // ── Sticky Notes ──

  /**
   * Create a sticky note node (kind='note') and persist via API.
   * @returns {object|null} The created note node, or null on failure.
   */
  async createStickyNote(text, color = '#fef08a', x = 100, y = 100) {
    const noteId = 'note-' + Date.now().toString(36);
    const noteNode = {
      id: noteId,
      kind: 'note',
      label: 'Note',
      name: 'Note',
      position_x: x,
      position_y: y,
      config: { text, color },
    };

    this.nodes = [...this.nodes, noteNode];
    this._notify();

    // Persist via API if graph is active
    if (this.activeGraph) {
      try {
        await this.api.tmAddNode(this.activeGraph.id, 'note', 'Note', x, y, { text, color });
      } catch (err) {
        console.error('TeamManagerStore createStickyNote persist failed:', err);
      }
    }

    return noteNode;
  }

  /**
   * Update an existing sticky note node.
   * @param {string} noteId
   * @param {object} changes - { text?, color? }
   */
  async updateStickyNote(noteId, changes) {
    const node = this.nodes.find(n => n.id === noteId);
    if (!node || node.kind !== 'note') return;

    const updatedConfig = { ...(node.config || {}), ...changes };
    this.nodes = this.nodes.map(n =>
      n.id === noteId ? { ...n, config: updatedConfig } : n
    );
    this._notify();

    try {
      await this.api.tmUpdateNode(noteId, { config: updatedConfig });
    } catch (err) {
      console.error('TeamManagerStore updateStickyNote persist failed:', err);
    }
  }

  /**
   * Delete a sticky note node.
   */
  async deleteStickyNote(noteId) {
    const node = this.nodes.find(n => n.id === noteId);
    if (!node || node.kind !== 'note') return;

    this.nodes = this.nodes.filter(n => n.id !== noteId);
    this.edges = this.edges.filter(e => e.source_node_id !== noteId && e.target_node_id !== noteId);
    this._notify();

    try {
      await this.api.tmDeleteNode(noteId);
    } catch (err) {
      console.error('TeamManagerStore deleteStickyNote persist failed:', err);
    }
  }

  // ── UI State ──

  /**
   * Set the search query filter string.
   */
  setSearchQuery(query) {
    this.searchQuery = query;
    this._notify();
  }

  /**
   * Set the kind filter. null = show all kinds.
   * @param {string|null} kind - 'agent'|'skill'|'group'|'pipeline'|'human'|'context' or null
   */
  setFilterKind(kind) {
    this.filterKind = kind;
    this._notify();
  }

  /**
   * Toggle a node in the multi-selection set (for shift-click / ctrl-click).
   */
  toggleMultiSelect(nodeId) {
    if (this.multiSelectedNodeIds.has(nodeId)) {
      this.multiSelectedNodeIds.delete(nodeId);
    } else {
      this.multiSelectedNodeIds.add(nodeId);
    }
    this._notify();
  }

  /**
   * Clear the multi-selection set.
   */
  clearMultiSelect() {
    if (this.multiSelectedNodeIds.size > 0) {
      this.multiSelectedNodeIds = new Set();
      this._notify();
    }
  }

  /**
   * Open a context menu at the given coordinates, optionally targeting a node.
   */
  openContextMenu(x, y, nodeId = null) {
    this.contextMenu = { x, y, nodeId };
    this._notify();
  }

  /**
   * Close the context menu.
   */
  closeContextMenu() {
    this.contextMenu = null;
    this._notify();
  }

  /**
   * Open the create-node dialog, optionally pre-selecting a parent and default kind.
   */
  openCreateDialog(parentId = null, defaultKind = null) {
    this.createDialogOpen = true;
    this.createDialogParentId = parentId;
    this.createDialogDefaultKind = defaultKind;
    this._notify();
  }

  /**
   * Close the create-node dialog and reset associated state.
   */
  closeCreateDialog() {
    this.createDialogOpen = false;
    this.createDialogParentId = null;
    this.createDialogDefaultKind = null;
    this._notify();
  }

  /**
   * Open the delete-confirmation dialog for a specific node.
   */
  openDeleteDialog(nodeId) {
    this.deleteDialogNodeId = nodeId;
    this._notify();
  }

  /**
   * Close the delete-confirmation dialog.
   */
  closeDeleteDialog() {
    this.deleteDialogNodeId = null;
    this._notify();
  }

  // ── Toast System ──

  /**
   * Show a toast notification. Auto-removes after 3 seconds.
   * @param {string} message
   * @param {'success'|'error'|'info'} type
   */
  addToast(message, type = 'info') {
    const id = Date.now();
    this.toasts = [...this.toasts, { id, message, type }];
    this._notify();
    setTimeout(() => this.removeToast(id), 3000);
  }

  /**
   * Remove a toast by its ID.
   */
  removeToast(id) {
    this.toasts = this.toasts.filter(t => t.id !== id);
    this._notify();
  }

  // ── Overlay Mutual Exclusion ──

  /**
   * Close all overlay panels (settings, contextHub, createDialog, deleteDialog).
   * Used internally when selecting a node without multi-select to ensure
   * the canvas/inspector area is unobstructed.
   */
  _closeOverlays() {
    let changed = false;
    if (this.settingsOpen) { this.settingsOpen = false; changed = true; }
    if (this.contextHubOpen) { this.contextHubOpen = false; changed = true; }
    if (this.createDialogOpen) {
      this.createDialogOpen = false;
      this.createDialogParentId = null;
      this.createDialogDefaultKind = null;
      changed = true;
    }
    if (this.deleteDialogNodeId !== null) {
      this.deleteDialogNodeId = null;
      changed = true;
    }
    if (changed) this._notify();
  }
}
