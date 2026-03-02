// Sigil Dashboard — Team Manager Deployment Tracker

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

const STATUS_BADGE_CLASS = {
  pending:   'badge-warning',
  running:   'badge-info',
  completed: 'badge-success',
  failed:    'badge-destructive',
  cancelled: 'badge-outline',
};

const ACTIVE_STATUSES = new Set(['pending', 'running']);

function fmtRelativeTime(value) {
  if (!value) return '--';
  try {
    const now = Date.now();
    const ts = new Date(value).getTime();
    const diff = now - ts;
    if (diff < 0) return 'just now';
    if (diff < 60_000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
    if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
    return `${Math.floor(diff / 86_400_000)}d ago`;
  } catch {
    return escapeHtml(String(value));
  }
}

function statusBadge(status) {
  const cls = STATUS_BADGE_CLASS[status] || 'badge-outline';
  return `<span class="badge ${cls}">${escapeHtml(status || 'unknown')}</span>`;
}

let _pollInterval = null;
let _expandedId = null;

function hasActiveDeployments(deployments) {
  return deployments.some(d => ACTIVE_STATUSES.has(d.status));
}

function startPolling(store) {
  stopPolling();
  _pollInterval = setInterval(() => {
    if (hasActiveDeployments(store.deployments)) {
      store.loadDeployments();
    } else {
      stopPolling();
    }
  }, 5000);
}

function stopPolling() {
  if (_pollInterval) {
    clearInterval(_pollInterval);
    _pollInterval = null;
  }
}

function renderDeployDetail(deployment) {
  if (!deployment) return '';
  const plan = deployment.plan || deployment.deploy_plan;
  const error = deployment.error || deployment.error_message;
  const nodes = deployment.nodes || [];

  let detailHtml = '<div class="tm-deploy-detail">';

  if (plan) {
    detailHtml += `
      <div class="tm-deploy-detail-section">
        <span class="tm-deploy-detail-label">Plan</span>
        <pre class="tm-deploy-detail-pre">${escapeHtml(typeof plan === 'string' ? plan : JSON.stringify(plan, null, 2))}</pre>
      </div>`;
  }

  if (error) {
    detailHtml += `
      <div class="tm-deploy-detail-section">
        <span class="tm-deploy-detail-label" style="color:hsl(var(--destructive))">Error</span>
        <pre class="tm-deploy-detail-pre">${escapeHtml(error)}</pre>
      </div>`;
  }

  if (nodes.length > 0) {
    detailHtml += `
      <div class="tm-deploy-detail-section">
        <span class="tm-deploy-detail-label">Nodes (${nodes.length})</span>
        <div class="tm-deploy-detail-nodes">
          ${nodes.map(n => `<span class="badge badge-outline text-xs">${escapeHtml(n.label || n.id || n)}</span>`).join(' ')}
        </div>
      </div>`;
  }

  if (!plan && !error && nodes.length === 0) {
    detailHtml += '<div class="text-xs text-muted" style="padding:var(--space-1) 0">No additional details available.</div>';
  }

  detailHtml += '</div>';
  return detailHtml;
}

/**
 * Renders the deployment tracker panel into the given container element.
 * @param {HTMLElement} el
 * @param {import('./store.js').TeamManagerStore} store
 * @param {import('../api.js').SigilAPI} api
 */
export function renderDeploymentTracker(el, store, api) {
  const deployments = store.deployments || [];

  el.innerHTML = `
    <div class="tm-deploy-tracker">
      <div class="tm-deploy-header">
        <span class="text-sm font-semibold">Deployments</span>
        <div class="flex items-center gap-1">
          ${hasActiveDeployments(deployments) ? '<span class="tm-deploy-pulse"></span>' : ''}
          <span class="badge badge-outline text-xs">${deployments.length}</span>
          <button class="btn btn-sm btn-ghost" data-deploy-action="refresh" aria-label="Refresh deployments">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
          </button>
        </div>
      </div>

      ${deployments.length === 0 ? `
        <div class="tm-deploy-empty text-xs text-muted">No deployments for this graph.</div>
      ` : `
        <table class="table tm-deploy-table" role="table" aria-label="Deployments">
          <thead>
            <tr>
              <th>Status</th>
              <th>Graph</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${deployments.map(d => {
              const isExpanded = _expandedId === d.id;
              return `
                <tr class="tm-deploy-row ${isExpanded ? 'tm-deploy-row--expanded' : ''}" data-deploy-id="${escapeHtml(d.id)}">
                  <td>${statusBadge(d.status)}</td>
                  <td class="text-xs text-mono truncate" style="max-width:120px">${escapeHtml(d.graph_name || d.graph_id || '--')}</td>
                  <td class="text-xs text-mono" style="opacity:.7">${fmtRelativeTime(d.created_at)}</td>
                  <td>
                    <div class="flex gap-1">
                      ${ACTIVE_STATUSES.has(d.status) ? `
                        <button class="btn btn-sm btn-outline btn-destructive" data-deploy-action="cancel" data-deploy-id="${escapeHtml(d.id)}" title="Cancel deployment">Cancel</button>
                      ` : ''}
                      ${d.status === 'completed' ? `
                        <button class="btn btn-sm btn-outline" data-deploy-action="primer" data-deploy-id="${escapeHtml(d.id)}" title="View primer">Primer</button>
                      ` : ''}
                      <button class="btn btn-sm btn-ghost" data-deploy-action="toggle" data-deploy-id="${escapeHtml(d.id)}" title="${isExpanded ? 'Collapse' : 'Expand'}" aria-label="${isExpanded ? 'Collapse details' : 'Expand details'}">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="transform:rotate(${isExpanded ? '180' : '0'}deg);transition:transform 150ms ease"><path d="m6 9 6 6 6-6"/></svg>
                      </button>
                    </div>
                  </td>
                </tr>
                ${isExpanded ? `<tr class="tm-deploy-detail-row"><td colspan="4">${renderDeployDetail(d)}</td></tr>` : ''}
              `;
            }).join('')}
          </tbody>
        </table>
      `}
      <div data-deploy-feedback class="text-xs text-mono mt-1" style="opacity:.75;min-height:1rem"></div>
    </div>`;

  // ── Bind events ──

  const feedbackEl = el.querySelector('[data-deploy-feedback]');

  function showFeedback(msg) {
    if (feedbackEl) feedbackEl.textContent = msg;
  }

  // Refresh
  el.querySelector('[data-deploy-action="refresh"]')?.addEventListener('click', async () => {
    showFeedback('Refreshing...');
    await store.loadDeployments();
    renderDeploymentTracker(el, store, api);
    showFeedback('');
  });

  // Cancel deployment
  el.querySelectorAll('[data-deploy-action="cancel"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const deployId = btn.getAttribute('data-deploy-id');
      if (!confirm('Cancel this deployment?')) return;
      btn.disabled = true;
      showFeedback('Cancelling...');
      await store.cancelDeployment(deployId);
      renderDeploymentTracker(el, store, api);
      showFeedback('Cancelled');
    });
  });

  // Primer (fetch primer for first node of a completed deployment)
  el.querySelectorAll('[data-deploy-action="primer"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const deployId = btn.getAttribute('data-deploy-id');
      btn.disabled = true;
      showFeedback('Fetching primer...');
      try {
        const detail = await store.getDeployment(deployId);
        const nodes = detail?.nodes || detail?.deployment?.nodes || [];
        if (nodes.length > 0) {
          const firstNodeId = typeof nodes[0] === 'string' ? nodes[0] : nodes[0].id;
          const primerResult = await api.tmGetPrimer(deployId, firstNodeId);
          showFeedback(primerResult?.primer ? 'Primer loaded -- expand row to view' : 'No primer available');
        } else {
          showFeedback('No nodes in deployment');
        }
      } catch (err) {
        showFeedback(err.message || 'Primer fetch failed');
      }
      btn.disabled = false;
    });
  });

  // Toggle expand/collapse
  el.querySelectorAll('[data-deploy-action="toggle"]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const deployId = btn.getAttribute('data-deploy-id');
      _expandedId = _expandedId === deployId ? null : deployId;
      renderDeploymentTracker(el, store, api);
    });
  });

  // Row click also toggles expand
  el.querySelectorAll('.tm-deploy-row').forEach(row => {
    row.addEventListener('click', () => {
      const deployId = row.getAttribute('data-deploy-id');
      _expandedId = _expandedId === deployId ? null : deployId;
      renderDeploymentTracker(el, store, api);
    });
  });

  // Start polling if there are active deployments
  if (hasActiveDeployments(deployments)) {
    startPolling(store);
  }
}

/**
 * Cleanup function -- call when the deployments panel is hidden or destroyed.
 */
export function destroyDeploymentTracker() {
  stopPolling();
  _expandedId = null;
}
