// Sigil Dashboard — Team Manager Panel

import { TeamManagerStore } from '../team-manager/store.js';
import { TeamManagerCanvas } from '../team-manager/canvas.js';
import { renderInspector } from '../team-manager/inspector.js';
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

// ── Module-level state (persists across re-renders) ──
let _store = null;
let _canvas = null;
let _mode = 'list';  // 'list' | 'canvas'
let _initialized = false;
let _deploymentsOpen = false;
let _variablesOpen = false;
let _schedulesOpen = false;

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
          <button class="btn btn-sm btn-ghost" data-tm-action="reset-zoom" title="Reset zoom">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </button>
        </div>
      </div>
      <div class="tm-canvas-body">
        <div class="tm-canvas-area" data-tm-canvas></div>
        <div class="tm-inspector-sidebar" data-tm-inspector></div>
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

  // Destroy old canvas if exists
  if (_canvas) _canvas.destroy();

  _canvas = new TeamManagerCanvas(canvasContainer, store, {
    onNodeDblClick: (nodeId) => {
      const node = store.nodes.find(n => n.id === nodeId);
      if (node) {
        renderInspector(inspectorEl, node, store, {
          onClose: () => renderInspector(inspectorEl, null, store),
        });
      }
    },
  });

  // Update zoom display on store change
  store.subscribe(() => {
    if (zoomEl) zoomEl.textContent = `${Math.round(store.viewport.zoom * 100)}%`;
  });

  // ── Toolbar events ──

  // Back to list
  el.querySelector('[data-tm-action="back"]').addEventListener('click', () => {
    if (_canvas) { _canvas.destroy(); _canvas = null; }
    destroyDeploymentTracker();
    _deploymentsOpen = false;
    _variablesOpen = false;
    _schedulesOpen = false;
    _mode = 'list';
    renderTeams(el, null, api);
  });

  // Graph name inline edit
  initGraphNameEdit(el, store, statusEl);

  // Add node from palette
  el.querySelectorAll('[data-tm-add-kind]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const kind = btn.getAttribute('data-tm-add-kind');
      const label = prompt(`${NODE_KIND_LABELS[kind] || kind} label:`);
      if (!label) return;
      // Place at center of current viewport
      const vp = store.viewport;
      const rect = canvasContainer.getBoundingClientRect();
      const cx = (rect.width / 2 - vp.x) / vp.zoom;
      const cy = (rect.height / 2 - vp.y) / vp.zoom;
      // Offset slightly randomly to avoid stacking
      const ox = (Math.random() - 0.5) * 100;
      const oy = (Math.random() - 0.5) * 100;
      if (statusEl) statusEl.textContent = 'Adding node...';
      const node = await store.addNode(kind, label, Math.round(cx + ox), Math.round(cy + oy));
      if (statusEl) statusEl.textContent = node ? `Added ${kind}: ${label}` : (store.error || 'Failed');
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
    } else {
      if (statusEl) statusEl.textContent = store.error || 'Validation failed';
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
