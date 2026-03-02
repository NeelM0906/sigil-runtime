// Sigil Dashboard — Team Manager Panel

import { TeamManagerStore } from '../team-manager/store.js';
import { TeamManagerCanvas } from '../team-manager/canvas.js';
import { renderInspector } from '../team-manager/inspector.js';

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
          <span class="text-sm font-semibold">${escapeHtml(graphName)}</span>
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
          <button class="btn btn-sm btn-ghost" data-tm-action="reset-zoom" title="Reset zoom">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </button>
        </div>
      </div>
      <div class="tm-canvas-body">
        <div class="tm-canvas-area" data-tm-canvas></div>
        <div class="tm-inspector-sidebar" data-tm-inspector></div>
      </div>
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
    _mode = 'list';
    renderTeams(el, null, api);
  });

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
  el.querySelector('[data-tm-action="deploy-canvas"]')?.addEventListener('click', async () => {
    if (!graph) return;
    if (!confirm(`Deploy graph "${graph.name}"?`)) return;
    if (statusEl) statusEl.textContent = 'Deploying...';
    const result = await store.deployGraph(graph.id);
    if (statusEl) statusEl.textContent = result ? 'Deployed successfully' : (store.error || 'Deploy failed');
  });

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
