// Sigil Dashboard — Team Manager Panel

import { TeamManagerStore } from '../team-manager/store.js';
import { TeamManagerCanvas } from '../team-manager/canvas.js';
import { renderInspector } from '../team-manager/inspector.js';
import { renderAgentEditor, renderGroupEditor, renderPipelineEditor, renderDefaultEditor } from '../team-manager/editors.js';
import { renderDeploymentTracker, destroyDeploymentTracker } from '../team-manager/deployments.js';
import { renderVariablesPanel } from '../team-manager/variables.js';
import { renderScheduleManager } from '../team-manager/schedules.js';

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function fmtTime(value) {
  if (!value) return '--';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return escapeHtml(String(value));
  }
}

const NODE_KIND_LABELS = {
  human: 'Human',
  group: 'Group',
  agent: 'Agent',
  skill: 'Skill',
  pipeline: 'Pipeline',
  context: 'Context',
  note: 'Note',
};

const NODE_KIND_COLORS = {
  human:    '#10b981',
  group:    '#8b5cf6',
  agent:    '#3b82f6',
  skill:    '#f59e0b',
  pipeline: '#ef4444',
  context:  '#06b6d4',
  note:     '#6b7280',
};

// Kinds available in the create-node dialog
const CREATE_NODE_KINDS = [
  { value: 'agent', label: 'Agent' },
  { value: 'group', label: 'Group / Team' },
  { value: 'pipeline', label: 'Pipeline' },
  { value: 'skill', label: 'Skill' },
  { value: 'human', label: 'Human' },
  { value: 'context', label: 'Context' },
  { value: 'settings', label: 'Settings' },
];

// Filter pill definitions
const FILTER_PILLS = [
  { kind: null,        label: 'All' },
  { kind: 'group',     label: 'Teams' },
  { kind: 'agent',     label: 'Agents' },
  { kind: 'skill',     label: 'Skills' },
  { kind: 'pipeline',  label: 'Pipelines' },
];

const TOAST_COLORS = {
  success: '#22c55e',
  error:   '#ef4444',
  info:    '#3b82f6',
};

// ── Module-level state (persists across re-renders) ──
let _store = null;
let _canvas = null;
let _mode = 'list';  // 'list' | 'canvas'
let _initialized = false;
let _deploymentsOpen = false;
let _variablesOpen = false;
let _schedulesOpen = false;

// Store subscription unsubscribers for cleanup
let _toastUnsub = null;
let _dialogUnsub = null;
let _multiSelectUnsub = null;

function getStore(api) {
  if (!_store) {
    _store = new TeamManagerStore(api);
  }
  return _store;
}

// ── List View ──

function renderListView(el, store, api) {
  const graphs = store.graphs;
  const loading = store.loading;
  const error = store.error;

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Team Manager</span>
        <div class="flex gap-2">
          <span class="badge badge-outline">${graphs.length} graph${graphs.length !== 1 ? 's' : ''}</span>
          <button class="btn btn-sm btn-outline" data-tm-action="new-graph">+ New Graph</button>
          <button class="btn btn-sm btn-ghost" data-tm-action="refresh" aria-label="Refresh">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
          </button>
        </div>
      </div>

      ${error ? `<div class="alert alert-destructive mb-3"><span>${escapeHtml(error)}</span></div>` : ''}
      ${loading ? '<div class="skeleton skeleton-card"></div>' : ''}

      ${!loading && graphs.length === 0 ? `
        <div class="empty-state">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.2;margin-bottom:var(--space-3)">
            <circle cx="5" cy="6" r="3"/><circle cx="19" cy="6" r="3"/><circle cx="12" cy="18" r="3"/>
            <line x1="5" y1="9" x2="12" y2="15" stroke-opacity="0.4"/>
            <line x1="19" y1="9" x2="12" y2="15" stroke-opacity="0.4"/>
          </svg>
          <div class="empty-state-text">No team graphs yet. Create one to get started.</div>
        </div>
      ` : ''}

      ${!loading && graphs.length > 0 ? `
        <div class="table-container" style="max-height:320px;overflow-y:auto">
          <table class="table" role="table" aria-label="Team graphs">
            <thead>
              <tr><th>Name</th><th>Nodes</th><th>Status</th><th>Updated</th><th>Actions</th></tr>
            </thead>
            <tbody>
              ${graphs.map(g => `
                <tr class="tm-graph-row" data-graph-id="${escapeHtml(g.id)}">
                  <td>
                    <div class="text-sm"><strong>${escapeHtml(g.name || 'Untitled')}</strong></div>
                    ${g.description ? `<div class="text-xs text-muted truncate" style="max-width:180px">${escapeHtml(g.description)}</div>` : ''}
                  </td>
                  <td class="text-mono text-xs tabular-nums">${g.node_count != null ? g.node_count : '--'}</td>
                  <td>${graphStatusBadge(g.status)}</td>
                  <td class="text-xs text-mono" style="opacity:.7">${fmtTime(g.updated_at)}</td>
                  <td>
                    <div class="flex gap-1">
                      <button class="btn btn-sm btn-outline" data-tm-action="open" data-graph-id="${escapeHtml(g.id)}">Open</button>
                      <button class="btn btn-sm btn-outline" data-tm-action="deploy" data-graph-id="${escapeHtml(g.id)}">Deploy</button>
                      <button class="btn btn-sm btn-ghost" data-tm-action="delete-graph" data-graph-id="${escapeHtml(g.id)}" aria-label="Delete graph">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                      </button>
                    </div>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      ` : ''}
      <div data-tm-feedback class="text-xs text-mono mt-2" style="opacity:.75"></div>
    </div>`;

  // ── Bind events ──

  const feedbackEl = el.querySelector('[data-tm-feedback]');

  function showFeedback(msg) {
    if (feedbackEl) feedbackEl.textContent = msg;
  }

  // New graph
  el.querySelector('[data-tm-action="new-graph"]')?.addEventListener('click', async () => {
    const name = prompt('Graph name:');
    if (!name) return;
    const desc = prompt('Description (optional):') || '';
    showFeedback('Creating...');
    const result = await store.createGraph(name, desc);
    if (result) {
      showFeedback('Created');
      renderListView(el, store, api);
    } else {
      showFeedback(store.error || 'Failed');
    }
  });

  // Refresh
  el.querySelector('[data-tm-action="refresh"]')?.addEventListener('click', async () => {
    showFeedback('Refreshing...');
    await store.loadGraphs();
    renderListView(el, store, api);
  });

  // Open graph -> canvas mode
  el.querySelectorAll('[data-tm-action="open"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const graphId = btn.getAttribute('data-graph-id');
      showFeedback('Loading graph...');
      await store.loadGraph(graphId);
      _mode = 'canvas';
      renderTeams(el, null, api);
    });
  });

  // Deploy
  el.querySelectorAll('[data-tm-action="deploy"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const graphId = btn.getAttribute('data-graph-id');
      btn.disabled = true;
      showFeedback(`Deploying ${graphId}...`);
      const result = await store.deployGraph(graphId);
      showFeedback(result ? 'Deployed' : (store.error || 'Deploy failed'));
      btn.disabled = false;
    });
  });

  // Delete graph
  el.querySelectorAll('[data-tm-action="delete-graph"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const graphId = btn.getAttribute('data-graph-id');
      if (!confirm(`Delete graph ${graphId}?`)) return;
      showFeedback('Deleting...');
      await store.deleteGraph(graphId);
      renderListView(el, store, api);
    });
  });
}

function graphStatusBadge(status) {
  const map = {
    draft:    'badge-outline',
    active:   'badge-success',
    deployed: 'badge-info',
    error:    'badge-destructive',
    archived: 'badge-warning',
  };
  const cls = map[status] || 'badge-outline';
  return `<span class="badge ${cls}">${escapeHtml(status || 'draft')}</span>`;
}

// ── Graph Name Inline Edit ──

function initGraphNameEdit(el, store, statusEl) {
  const nameSpan = el.querySelector('[data-tm-action="edit-name"]');
  const nameIcon = el.querySelector('[data-tm-action="edit-name-icon"]');
  if (!nameSpan) return;

  function startEdit() {
    const currentName = store.activeGraph?.name || 'Untitled';
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'tm-graph-name-input';
    input.value = currentName;
    nameSpan.replaceWith(input);
    input.focus();
    input.select();

    let committed = false;

    async function commit() {
      if (committed) return;
      committed = true;
      const newName = input.value.trim();
      if (!newName || newName === currentName) {
        restore(currentName);
        return;
      }
      if (statusEl) statusEl.textContent = 'Renaming...';
      const result = await store.updateGraphMeta({ name: newName });
      if (result) {
        if (statusEl) statusEl.textContent = `Renamed to "${newName}"`;
      } else {
        if (statusEl) statusEl.textContent = store.error || 'Rename failed';
      }
      restore(store.activeGraph?.name || newName);
    }

    function restore(name) {
      const span = document.createElement('span');
      span.className = 'text-sm font-semibold tm-graph-name-editable';
      span.setAttribute('data-tm-action', 'edit-name');
      span.title = 'Click to rename';
      span.textContent = name;
      input.replaceWith(span);
      initGraphNameEdit(el, store, statusEl);
    }

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        commit();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        committed = true;
        restore(currentName);
      }
    });

    input.addEventListener('blur', () => {
      commit();
    });
  }

  nameSpan.addEventListener('click', startEdit);
  if (nameIcon) nameIcon.addEventListener('click', startEdit);
}

// ── Toast Container ──

/**
 * Renders the toast notification container (fixed bottom-right).
 * Subscribes to store.toasts and re-renders on change.
 */
function mountToastContainer(parentEl, store) {
  // Create a fixed-position container outside the canvas flow
  let container = parentEl.querySelector('[data-tm-toast-container]');
  if (!container) {
    container = document.createElement('div');
    container.setAttribute('data-tm-toast-container', '');
    container.className = 'tm-toast-container';
    parentEl.appendChild(container);
  }

  function renderToasts() {
    container.innerHTML = '';
    for (const toast of store.toasts) {
      const color = TOAST_COLORS[toast.type] || TOAST_COLORS.info;
      const toastEl = document.createElement('div');
      toastEl.className = 'tm-toast tm-toast--slide-in';
      toastEl.innerHTML = `
        <div class="tm-toast-bar" style="background:${color}"></div>
        <span class="tm-toast-message">${escapeHtml(toast.message)}</span>
        <button class="tm-toast-dismiss" data-toast-id="${toast.id}" aria-label="Dismiss">&times;</button>
      `;
      toastEl.querySelector('.tm-toast-dismiss').addEventListener('click', () => {
        store.removeToast(toast.id);
      });
      container.appendChild(toastEl);
    }
  }

  renderToasts();

  // Subscribe to store changes for toast updates
  if (_toastUnsub) _toastUnsub();
  _toastUnsub = store.subscribe(() => {
    renderToasts();
  });

  return container;
}

// ── Multi-Select Toolbar ──

/**
 * Renders the floating multi-select toolbar above the canvas when 2+ nodes are selected.
 */
function mountMultiSelectToolbar(parentEl, store, api) {
  let toolbar = parentEl.querySelector('[data-tm-multiselect-toolbar]');
  if (!toolbar) {
    toolbar = document.createElement('div');
    toolbar.setAttribute('data-tm-multiselect-toolbar', '');
    toolbar.className = 'tm-multiselect-toolbar';
    parentEl.appendChild(toolbar);
  }

  function renderToolbar() {
    const count = store.multiSelectedNodeIds.size;
    if (count < 2) {
      toolbar.style.display = 'none';
      return;
    }

    toolbar.style.display = '';
    toolbar.innerHTML = `
      <span class="tm-multiselect-count">${count} selected</span>
      <button class="btn btn-sm tm-multiselect-generate" data-tm-action="generate-all-descriptions">Generate All Descriptions</button>
      <button class="btn btn-sm btn-ghost tm-multiselect-clear" data-tm-action="clear-multiselect">Clear</button>
    `;

    toolbar.querySelector('[data-tm-action="generate-all-descriptions"]')?.addEventListener('click', async () => {
      const btn = toolbar.querySelector('[data-tm-action="generate-all-descriptions"]');
      if (btn) { btn.disabled = true; btn.textContent = 'Generating...'; }

      const nodeIds = [...store.multiSelectedNodeIds];
      let successCount = 0;
      for (const nodeId of nodeIds) {
        const node = store.nodes.find(n => n.id === nodeId);
        if (!node) continue;
        const name = node.label || node.name || '';
        if (!name.trim()) continue;
        try {
          const result = await api.chat('tm-generate', `Generate a concise 1-2 sentence description for a ${node.kind || 'node'} named "${name}". Only output the description text, nothing else.`);
          const text = (result && (result.reply || result.response || result.message || '')).trim();
          if (text) {
            await store.updateNode(nodeId, { promptBody: text, config: { ...(node.config || {}), description: text } });
            successCount++;
          }
        } catch (err) {
          console.error(`Generate description failed for ${nodeId}:`, err);
        }
      }

      store.addToast(`Generated descriptions for ${successCount}/${nodeIds.length} nodes`, successCount > 0 ? 'success' : 'error');
      if (btn) { btn.disabled = false; btn.textContent = 'Generate All Descriptions'; }
    });

    toolbar.querySelector('[data-tm-action="clear-multiselect"]')?.addEventListener('click', () => {
      store.clearMultiSelect();
    });
  }

  renderToolbar();

  if (_multiSelectUnsub) _multiSelectUnsub();
  _multiSelectUnsub = store.subscribe(() => {
    renderToolbar();
  });

  return toolbar;
}

// ── Create Node Dialog ──

function renderCreateDialog(parentEl, store, api, canvasContainer) {
  let overlay = parentEl.querySelector('[data-tm-create-dialog]');

  function show() {
    if (overlay) overlay.remove();

    overlay = document.createElement('div');
    overlay.setAttribute('data-tm-create-dialog', '');
    overlay.className = 'tm-dialog-overlay';

    const defaultKind = store.createDialogDefaultKind || 'agent';

    overlay.innerHTML = `
      <div class="tm-dialog">
        <div class="tm-dialog-header">
          <span class="tm-dialog-title">Create Node</span>
          <button class="tm-dialog-close" data-action="cancel" aria-label="Close">&times;</button>
        </div>
        <div class="tm-dialog-body">
          <div class="tm-dialog-field">
            <label class="tm-dialog-label">Name</label>
            <input type="text" class="tm-dialog-input" data-field="name" placeholder="Node name" autofocus />
          </div>
          <div class="tm-dialog-field">
            <label class="tm-dialog-label">Kind</label>
            <select class="tm-dialog-select" data-field="kind">
              ${CREATE_NODE_KINDS.map(k => `<option value="${k.value}" ${k.value === defaultKind ? 'selected' : ''}>${escapeHtml(k.label)}</option>`).join('')}
            </select>
          </div>
          <div class="tm-dialog-field">
            <label class="tm-dialog-label">Description</label>
            <textarea class="tm-dialog-textarea" data-field="description" rows="3" placeholder="Optional description"></textarea>
          </div>
        </div>
        <div class="tm-dialog-footer">
          <button class="btn btn-sm btn-ghost" data-action="cancel">Cancel</button>
          <button class="btn btn-sm" data-action="create">Create</button>
        </div>
      </div>
    `;

    parentEl.appendChild(overlay);

    // Focus name input
    const nameInput = overlay.querySelector('[data-field="name"]');
    if (nameInput) setTimeout(() => nameInput.focus(), 50);

    // Cancel
    overlay.querySelectorAll('[data-action="cancel"]').forEach(btn => {
      btn.addEventListener('click', () => {
        store.closeCreateDialog();
      });
    });

    // Click outside dialog to cancel
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) store.closeCreateDialog();
    });

    // Create
    overlay.querySelector('[data-action="create"]')?.addEventListener('click', async () => {
      const name = overlay.querySelector('[data-field="name"]')?.value?.trim();
      const kind = overlay.querySelector('[data-field="kind"]')?.value || 'agent';
      const description = overlay.querySelector('[data-field="description"]')?.value?.trim() || '';

      if (!name) {
        const nameField = overlay.querySelector('[data-field="name"]');
        if (nameField) { nameField.style.borderColor = '#ef4444'; nameField.focus(); }
        return;
      }

      // Calculate center of canvas viewport for placement
      let cx = 300, cy = 200;
      if (canvasContainer) {
        const vp = store.viewport;
        const rect = canvasContainer.getBoundingClientRect();
        cx = (rect.width / 2 - vp.x) / vp.zoom;
        cy = (rect.height / 2 - vp.y) / vp.zoom;
      }
      const ox = (Math.random() - 0.5) * 100;
      const oy = (Math.random() - 0.5) * 100;

      const config = {};
      if (description) config.description = description;
      if (store.createDialogParentId) config.parentId = store.createDialogParentId;

      const node = await store.addNode(kind, name, Math.round(cx + ox), Math.round(cy + oy), config);
      if (node) {
        store.addToast(`Created ${kind}: ${name}`, 'success');

        // If there is a parent, create an edge
        if (store.createDialogParentId) {
          await store.addEdge(store.createDialogParentId, node.id, 'hierarchy');
        }
      } else {
        store.addToast(store.error || 'Failed to create node', 'error');
      }

      store.closeCreateDialog();
    });

    // Enter key submits
    overlay.querySelector('[data-field="name"]')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        overlay.querySelector('[data-action="create"]')?.click();
      }
    });
  }

  function hide() {
    if (overlay) {
      overlay.remove();
      overlay = null;
    }
  }

  return { show, hide };
}

// ── Delete Confirmation Dialog ──

function renderDeleteDialog(parentEl, store) {
  let overlay = parentEl.querySelector('[data-tm-delete-dialog]');

  function show(nodeId) {
    if (overlay) overlay.remove();

    const node = store.nodes.find(n => n.id === nodeId);
    const nodeName = node ? (node.label || node.name || nodeId) : nodeId;

    overlay = document.createElement('div');
    overlay.setAttribute('data-tm-delete-dialog', '');
    overlay.className = 'tm-dialog-overlay';
    overlay.innerHTML = `
      <div class="tm-dialog tm-dialog--delete">
        <div class="tm-dialog-header">
          <span class="tm-dialog-title">Delete ${escapeHtml(nodeName)}?</span>
          <button class="tm-dialog-close" data-action="cancel" aria-label="Close">&times;</button>
        </div>
        <div class="tm-dialog-body">
          <p class="tm-dialog-warning">This action cannot be undone. The node and all its connections will be permanently removed.</p>
        </div>
        <div class="tm-dialog-footer">
          <button class="btn btn-sm btn-ghost" data-action="cancel">Cancel</button>
          <button class="btn btn-sm btn-destructive" data-action="delete">Delete</button>
        </div>
      </div>
    `;

    parentEl.appendChild(overlay);

    // Cancel
    overlay.querySelectorAll('[data-action="cancel"]').forEach(btn => {
      btn.addEventListener('click', () => {
        store.closeDeleteDialog();
      });
    });

    // Click outside to cancel
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) store.closeDeleteDialog();
    });

    // Delete
    overlay.querySelector('[data-action="delete"]')?.addEventListener('click', async () => {
      await store.deleteNode(nodeId);
      store.addToast(`Deleted ${nodeName}`, 'info');
      store.closeDeleteDialog();
    });
  }

  function hide() {
    if (overlay) {
      overlay.remove();
      overlay = null;
    }
  }

  return { show, hide };
}

// ── Welcome Screen ──

function renderWelcomeScreen(containerEl, store) {
  // Check if graph has no meaningful nodes (empty or only root)
  const meaningfulNodes = store.nodes.filter(n => n.kind !== 'root' && n.kind !== 'settings');
  if (meaningfulNodes.length > 0) return null;

  const welcome = document.createElement('div');
  welcome.className = 'tm-welcome-overlay';
  welcome.innerHTML = `
    <div class="tm-welcome-card">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.25;margin-bottom:16px">
        <circle cx="5" cy="6" r="3"/><circle cx="19" cy="6" r="3"/><circle cx="12" cy="18" r="3"/>
        <line x1="5" y1="9" x2="12" y2="15" stroke-opacity="0.4"/>
        <line x1="19" y1="9" x2="12" y2="15" stroke-opacity="0.4"/>
      </svg>
      <div class="tm-welcome-title">No nodes yet</div>
      <div class="tm-welcome-desc">Start building your agent team by creating a group node.</div>
      <button class="btn btn-sm tm-welcome-create-btn" data-tm-action="welcome-create">Create Your First Team</button>
    </div>
  `;

  welcome.querySelector('[data-tm-action="welcome-create"]')?.addEventListener('click', () => {
    store.openCreateDialog(null, 'group');
  });

  containerEl.appendChild(welcome);
  return welcome;
}

// ── Per-Kind Editor Dispatch ──

function renderNodeEditor(inspectorEl, node, store, api) {
  if (!node) {
    inspectorEl.innerHTML = '';
    inspectorEl.classList.remove('tm-inspector--open');
    return;
  }

  inspectorEl.classList.add('tm-inspector--open');

  // Wrap in a panel container with close button and kind badge header
  inspectorEl.innerHTML = `
    <div class="tm-inspector-panel">
      <div class="tm-inspector-header">
        <div class="flex items-center gap-2">
          <span class="tm-inspector-kind-dot" style="background:${NODE_KIND_COLORS[node.kind] || '#6b7280'}"></span>
          <span class="tm-inspector-kind-label">${escapeHtml(node.kind || 'unknown')}</span>
        </div>
        <button class="btn btn-ghost btn-sm btn-icon" data-inspector-close aria-label="Close inspector">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>
      <div class="separator"></div>
      <div data-tm-editor-content></div>
      <div class="separator" style="margin-top:12px"></div>
      <div class="tm-inspector-meta">
        <div class="stat-row"><span class="stat-label">ID</span><span class="stat-value text-xs">${escapeHtml(node.id)}</span></div>
        <div class="stat-row"><span class="stat-label">Position</span><span class="stat-value text-xs">${Math.round(node.position_x || 0)}, ${Math.round(node.position_y || 0)}</span></div>
      </div>
      <div class="separator"></div>
      <button class="btn btn-sm btn-destructive w-full mt-2" data-inspector-delete>Delete Node</button>
    </div>
  `;

  const editorContent = inspectorEl.querySelector('[data-tm-editor-content]');

  // Dispatch to per-kind editor
  if (node.kind === 'agent') {
    renderAgentEditor(editorContent, node, store, api);
  } else if (node.kind === 'group') {
    renderGroupEditor(editorContent, node, store, api);
  } else if (node.kind === 'pipeline') {
    renderPipelineEditor(editorContent, node, store, api);
  } else {
    renderDefaultEditor(editorContent, node, store, api);
  }

  // Close button
  inspectorEl.querySelector('[data-inspector-close]')?.addEventListener('click', () => {
    store.clearSelection();
    renderNodeEditor(inspectorEl, null, store, api);
  });

  // Delete button
  inspectorEl.querySelector('[data-inspector-delete]')?.addEventListener('click', () => {
    store.openDeleteDialog(node.id);
  });
}

// ── Canvas View ──

function renderCanvasView(el, store, api) {
  const graph = store.activeGraph;
  const graphName = graph ? (graph.name || 'Untitled') : 'Graph';

  el.innerHTML = `
    <div class="tm-canvas-wrapper">
      <div class="tm-canvas-toolbar">
        <div class="flex items-center gap-2">
          <button class="btn btn-sm btn-ghost" data-tm-action="back" aria-label="Back to list">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          </button>
          <span class="text-sm font-semibold tm-graph-name-editable" data-tm-action="edit-name" title="Click to rename">${escapeHtml(graphName)}</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity:.35;flex-shrink:0;cursor:pointer" data-tm-action="edit-name-icon"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>
          ${graph ? `<span class="badge badge-outline text-xs">${store.nodes.length} nodes</span>` : ''}

          <!-- Search bar -->
          <div class="tm-search-bar">
            <input type="text" class="tm-search-input" data-tm-action="search" placeholder="Search nodes..." value="${escapeHtml(store.searchQuery)}" />
            <button class="tm-search-clear ${store.searchQuery ? '' : 'tm-search-clear--hidden'}" data-tm-action="search-clear" aria-label="Clear search">&times;</button>
          </div>

          <!-- Kind filter pills -->
          <div class="tm-filter-pills">
            ${FILTER_PILLS.map(pill => `
              <button class="tm-filter-pill ${store.filterKind === pill.kind ? 'tm-filter-pill--active' : ''}" data-tm-filter-kind="${pill.kind === null ? '' : pill.kind}">${pill.label}</button>
            `).join('')}
          </div>

          <!-- Collapse/Expand all -->
          <button class="btn btn-sm btn-ghost tm-collapse-btn" data-tm-action="collapse-all" title="Collapse all groups">&#9662;</button>
          <button class="btn btn-sm btn-ghost tm-collapse-btn" data-tm-action="expand-all" title="Expand all groups">&#9656;</button>
        </div>
        <div class="flex items-center gap-1">
          <div class="tm-node-palette flex gap-1">
            ${Object.entries(NODE_KIND_LABELS).map(([kind, label]) => `
              <button class="btn btn-sm btn-outline tm-palette-btn" data-tm-add-kind="${kind}" title="Add ${label}" style="border-color:${NODE_KIND_COLORS[kind]}40;color:${NODE_KIND_COLORS[kind]}">
                ${label}
              </button>
            `).join('')}
          </div>
          <div class="separator" style="width:1px;height:20px;margin:0 var(--space-2)"></div>
          <button class="btn btn-sm btn-outline" data-tm-action="validate" title="Validate graph">Validate</button>
          <button class="btn btn-sm" data-tm-action="deploy-canvas" title="Deploy graph">Deploy</button>
          <button class="btn btn-sm btn-ghost ${_variablesOpen ? 'tm-deploy-toggle--active' : ''}" data-tm-action="toggle-variables" title="Graph variables">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
          <button class="btn btn-sm btn-ghost tm-deploy-toggle-btn ${_deploymentsOpen ? 'tm-deploy-toggle--active' : ''}" data-tm-action="toggle-deployments" title="Deployment history">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          </button>
          <button class="btn btn-sm btn-ghost ${_schedulesOpen ? 'tm-deploy-toggle--active' : ''}" data-tm-action="toggle-schedules" title="Schedule manager">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </button>
          <!-- Context Hub trigger -->
          <button class="btn btn-sm btn-ghost ${store.contextHubOpen ? 'tm-deploy-toggle--active' : ''}" data-tm-action="toggle-context-hub" title="Context Hub">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          </button>
          <!-- Settings trigger -->
          <button class="btn btn-sm btn-ghost ${store.settingsOpen ? 'tm-deploy-toggle--active' : ''}" data-tm-action="toggle-settings" title="Settings">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          </button>
          <button class="btn btn-sm btn-ghost" data-tm-action="reset-zoom" title="Reset zoom">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </button>
        </div>
      </div>
      <div class="tm-canvas-body">
        <div class="tm-canvas-area" data-tm-canvas></div>
        <div class="tm-inspector-sidebar" data-tm-inspector></div>
        <!-- Context Hub overlay panel (right side, content rendered by context-hub.js) -->
        <div class="tm-overlay-panel tm-overlay-panel--context-hub" data-tm-context-hub style="${store.contextHubOpen ? '' : 'display:none'}">
          <div class="tm-overlay-panel-header">
            <span class="tm-overlay-panel-title">Context Hub</span>
            <button class="btn btn-ghost btn-sm btn-icon" data-tm-action="close-context-hub" aria-label="Close Context Hub">&times;</button>
          </div>
          <div class="tm-overlay-panel-content" data-tm-context-hub-content></div>
        </div>
        <!-- Settings overlay panel (right side, content rendered by settings-panel.js) -->
        <div class="tm-overlay-panel tm-overlay-panel--settings" data-tm-settings style="${store.settingsOpen ? '' : 'display:none'}">
          <div class="tm-overlay-panel-header">
            <span class="tm-overlay-panel-title">Settings</span>
            <button class="btn btn-ghost btn-sm btn-icon" data-tm-action="close-settings" aria-label="Close Settings">&times;</button>
          </div>
          <div class="tm-overlay-panel-content" data-tm-settings-content></div>
        </div>
      </div>
      <div class="tm-variables-panel" data-tm-variables style="${_variablesOpen ? '' : 'display:none'}"></div>
      <div class="tm-deployments-panel" data-tm-deployments style="${_deploymentsOpen ? '' : 'display:none'}"></div>
      <div class="tm-schedules-panel" data-tm-schedules style="${_schedulesOpen ? '' : 'display:none'}"></div>
      <div class="tm-canvas-statusbar">
        <span class="text-xs text-mono" style="opacity:.6" data-tm-status>Ready</span>
        <span class="text-xs text-mono" style="opacity:.6" data-tm-zoom>100%</span>
      </div>
    </div>`;

  // ── Init canvas ──
  const canvasContainer = el.querySelector('[data-tm-canvas]');
  const inspectorEl = el.querySelector('[data-tm-inspector]');
  const statusEl = el.querySelector('[data-tm-status]');
  const zoomEl = el.querySelector('[data-tm-zoom]');
  const wrapperEl = el.querySelector('.tm-canvas-wrapper');

  // Destroy old canvas if exists
  if (_canvas) _canvas.destroy();

  _canvas = new TeamManagerCanvas(canvasContainer, store, {
    onNodeDblClick: (nodeId) => {
      const node = store.nodes.find(n => n.id === nodeId);
      if (node) {
        renderNodeEditor(inspectorEl, node, store, api);
      }
    },
  });

  // Update zoom display on store change
  store.subscribe(() => {
    if (zoomEl) zoomEl.textContent = `${Math.round(store.viewport.zoom * 100)}%`;
  });

  // ── Mount toast container ──
  mountToastContainer(wrapperEl, store);

  // ── Mount multi-select toolbar ──
  mountMultiSelectToolbar(wrapperEl, store, api);

  // ── Welcome screen ──
  renderWelcomeScreen(canvasContainer, store);

  // ── Create & Delete Dialogs (reactive to store state) ──
  const createDialog = renderCreateDialog(wrapperEl, store, api, canvasContainer);
  const deleteDialog = renderDeleteDialog(wrapperEl, store);

  if (_dialogUnsub) _dialogUnsub();
  _dialogUnsub = store.subscribe(() => {
    // Create dialog
    if (store.createDialogOpen) {
      createDialog.show();
    } else {
      createDialog.hide();
    }

    // Delete dialog
    if (store.deleteDialogNodeId) {
      deleteDialog.show(store.deleteDialogNodeId);
    } else {
      deleteDialog.hide();
    }

    // Context Hub panel visibility
    const contextHubEl = el.querySelector('[data-tm-context-hub]');
    if (contextHubEl) {
      contextHubEl.style.display = store.contextHubOpen ? '' : 'none';
    }
    const contextHubBtn = el.querySelector('[data-tm-action="toggle-context-hub"]');
    if (contextHubBtn) {
      contextHubBtn.classList.toggle('tm-deploy-toggle--active', store.contextHubOpen);
    }

    // Settings panel visibility
    const settingsEl = el.querySelector('[data-tm-settings]');
    if (settingsEl) {
      settingsEl.style.display = store.settingsOpen ? '' : 'none';
    }
    const settingsBtn = el.querySelector('[data-tm-action="toggle-settings"]');
    if (settingsBtn) {
      settingsBtn.classList.toggle('tm-deploy-toggle--active', store.settingsOpen);
    }
  });

  // ── Search bar events ──
  const searchInput = el.querySelector('[data-tm-action="search"]');
  const searchClear = el.querySelector('[data-tm-action="search-clear"]');

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      store.setSearchQuery(searchInput.value);
      if (searchClear) {
        searchClear.classList.toggle('tm-search-clear--hidden', !searchInput.value);
      }
    });
  }

  if (searchClear) {
    searchClear.addEventListener('click', () => {
      store.setSearchQuery('');
      if (searchInput) searchInput.value = '';
      searchClear.classList.add('tm-search-clear--hidden');
      if (searchInput) searchInput.focus();
    });
  }

  // ── Filter pill events ──
  el.querySelectorAll('.tm-filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const kind = pill.getAttribute('data-tm-filter-kind');
      store.setFilterKind(kind === '' ? null : kind);
      // Update active state
      el.querySelectorAll('.tm-filter-pill').forEach(p => p.classList.remove('tm-filter-pill--active'));
      pill.classList.add('tm-filter-pill--active');
    });
  });

  // ── Collapse/Expand all ──
  el.querySelector('[data-tm-action="collapse-all"]')?.addEventListener('click', () => {
    const allGroupIds = store.nodes.filter(n => n.kind === 'group').map(n => n.id);
    store.collapseAllGroups(allGroupIds);
  });

  el.querySelector('[data-tm-action="expand-all"]')?.addEventListener('click', () => {
    store.expandAllGroups();
  });

  // ── Context Hub toggle ──
  el.querySelector('[data-tm-action="toggle-context-hub"]')?.addEventListener('click', () => {
    store.contextHubOpen = !store.contextHubOpen;
    if (store.contextHubOpen) {
      store.settingsOpen = false;
    }
    store._notify();
  });

  el.querySelector('[data-tm-action="close-context-hub"]')?.addEventListener('click', () => {
    store.contextHubOpen = false;
    store._notify();
  });

  // ── Settings toggle ──
  el.querySelector('[data-tm-action="toggle-settings"]')?.addEventListener('click', () => {
    store.settingsOpen = !store.settingsOpen;
    if (store.settingsOpen) {
      store.contextHubOpen = false;
    }
    store._notify();
  });

  el.querySelector('[data-tm-action="close-settings"]')?.addEventListener('click', () => {
    store.settingsOpen = false;
    store._notify();
  });

  // ── Toolbar events ──

  // Back to list
  el.querySelector('[data-tm-action="back"]').addEventListener('click', () => {
    if (_canvas) { _canvas.destroy(); _canvas = null; }
    destroyDeploymentTracker();
    _deploymentsOpen = false;
    _variablesOpen = false;
    _schedulesOpen = false;
    // Cleanup subscriptions
    if (_toastUnsub) { _toastUnsub(); _toastUnsub = null; }
    if (_dialogUnsub) { _dialogUnsub(); _dialogUnsub = null; }
    if (_multiSelectUnsub) { _multiSelectUnsub(); _multiSelectUnsub = null; }
    _mode = 'list';
    renderTeams(el, null, api);
  });

  // Graph name inline edit
  initGraphNameEdit(el, store, statusEl);

  // Add node from palette
  el.querySelectorAll('[data-tm-add-kind]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const kind = btn.getAttribute('data-tm-add-kind');
      store.openCreateDialog(null, kind);
    });
  });

  // Validate
  el.querySelector('[data-tm-action="validate"]')?.addEventListener('click', async () => {
    if (!graph) return;
    if (statusEl) statusEl.textContent = 'Validating...';
    const result = await store.validateGraph(graph.id);
    if (result) {
      const valid = result.valid !== false;
      if (statusEl) statusEl.textContent = valid ? 'Validation passed' : `Validation: ${(result.errors || []).join(', ') || 'issues found'}`;
      store.addToast(valid ? 'Validation passed' : 'Validation issues found', valid ? 'success' : 'error');
    } else {
      if (statusEl) statusEl.textContent = store.error || 'Validation failed';
      store.addToast(store.error || 'Validation failed', 'error');
    }
  });

  // Deploy
  const deploymentsEl = el.querySelector('[data-tm-deployments]');
  el.querySelector('[data-tm-action="deploy-canvas"]')?.addEventListener('click', async () => {
    if (!graph) return;
    if (!confirm(`Deploy graph "${graph.name}"?`)) return;
    if (statusEl) statusEl.textContent = 'Deploying...';
    const result = await store.deployGraph(graph.id);
    if (statusEl) statusEl.textContent = result ? 'Deployed successfully' : (store.error || 'Deploy failed');
    store.addToast(result ? 'Deployed successfully' : (store.error || 'Deploy failed'), result ? 'success' : 'error');
    // Auto-refresh deployments panel if open
    if (_deploymentsOpen && deploymentsEl) {
      await store.loadDeployments();
      renderDeploymentTracker(deploymentsEl, store, api);
    }
  });

  // Toggle variables panel
  const variablesEl = el.querySelector('[data-tm-variables]');
  el.querySelector('[data-tm-action="toggle-variables"]')?.addEventListener('click', async () => {
    _variablesOpen = !_variablesOpen;
    const toggleBtn = el.querySelector('[data-tm-action="toggle-variables"]');
    if (variablesEl) {
      if (_variablesOpen) {
        variablesEl.style.display = '';
        if (toggleBtn) toggleBtn.classList.add('tm-deploy-toggle--active');
        if (statusEl) statusEl.textContent = 'Loading variables...';
        await store.loadVariables();
        renderVariablesPanel(variablesEl, store, api);
        if (statusEl) statusEl.textContent = `${store.variables.length} variable(s)`;
      } else {
        variablesEl.style.display = 'none';
        variablesEl.innerHTML = '';
        if (toggleBtn) toggleBtn.classList.remove('tm-deploy-toggle--active');
        if (statusEl) statusEl.textContent = 'Ready';
      }
    }
  });

  // If variables panel was previously open, re-render it
  if (_variablesOpen && variablesEl) {
    store.loadVariables().then(() => {
      renderVariablesPanel(variablesEl, store, api);
    });
  }

  // Toggle deployments panel
  el.querySelector('[data-tm-action="toggle-deployments"]')?.addEventListener('click', async () => {
    _deploymentsOpen = !_deploymentsOpen;
    const toggleBtn = el.querySelector('[data-tm-action="toggle-deployments"]');
    if (deploymentsEl) {
      if (_deploymentsOpen) {
        deploymentsEl.style.display = '';
        if (toggleBtn) toggleBtn.classList.add('tm-deploy-toggle--active');
        if (statusEl) statusEl.textContent = 'Loading deployments...';
        await store.loadDeployments();
        renderDeploymentTracker(deploymentsEl, store, api);
        if (statusEl) statusEl.textContent = `${store.deployments.length} deployment(s)`;
      } else {
        deploymentsEl.style.display = 'none';
        deploymentsEl.innerHTML = '';
        if (toggleBtn) toggleBtn.classList.remove('tm-deploy-toggle--active');
        destroyDeploymentTracker();
        if (statusEl) statusEl.textContent = 'Ready';
      }
    }
  });

  // If deployments panel was previously open, re-render it
  if (_deploymentsOpen && deploymentsEl) {
    store.loadDeployments().then(() => {
      renderDeploymentTracker(deploymentsEl, store, api);
    });
  }

  // Toggle schedules panel
  const schedulesEl = el.querySelector('[data-tm-schedules]');
  el.querySelector('[data-tm-action="toggle-schedules"]')?.addEventListener('click', async () => {
    _schedulesOpen = !_schedulesOpen;
    const toggleBtn = el.querySelector('[data-tm-action="toggle-schedules"]');
    if (schedulesEl) {
      if (_schedulesOpen) {
        schedulesEl.style.display = '';
        if (toggleBtn) toggleBtn.classList.add('tm-deploy-toggle--active');
        if (statusEl) statusEl.textContent = 'Loading schedules...';
        await store.loadSchedules();
        renderScheduleManager(schedulesEl, store, api);
        if (statusEl) statusEl.textContent = `${store.schedules.length} schedule(s)`;
      } else {
        schedulesEl.style.display = 'none';
        schedulesEl.innerHTML = '';
        if (toggleBtn) toggleBtn.classList.remove('tm-deploy-toggle--active');
        if (statusEl) statusEl.textContent = 'Ready';
      }
    }
  });

  // If schedules panel was previously open, re-render it
  if (_schedulesOpen && schedulesEl) {
    store.loadSchedules().then(() => {
      renderScheduleManager(schedulesEl, store, api);
    });
  }

  // Reset zoom
  el.querySelector('[data-tm-action="reset-zoom"]')?.addEventListener('click', () => {
    store.resetViewport();
    if (_canvas) _canvas.render();
  });
}

// ── Main export ──

export function renderTeams(el, state, api) {
  const store = getStore(api);

  if (!_initialized) {
    _initialized = true;
    store.loadGraphs();
  }

  if (_mode === 'canvas' && store.activeGraph) {
    renderCanvasView(el, store, api);
  } else {
    _mode = 'list';
    renderListView(el, store, api);
  }
}
