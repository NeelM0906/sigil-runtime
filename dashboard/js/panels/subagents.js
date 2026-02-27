// Sigil Dashboard — Sub-Agents Panel

function statusBadge(status) {
  const map = {
    running: 'badge-info',
    completed: 'badge-success',
    failed: 'badge-destructive',
    cancelled: 'badge-warning',
  };
  return `<span class="badge ${map[status] || 'badge-outline'}">${status || '?'}</span>`;
}

export function renderSubagents(el, state, api) {
  const sa = state.get('subagents') || {};
  const runs = sa.runs || [];

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Sub-Agents</span>
        <div class="flex gap-1">
          <span class="badge badge-info">${sa.active || 0}</span>
          <span class="badge badge-success">${sa.completed || 0}</span>
          <span class="badge badge-destructive">${sa.failed || 0}</span>
        </div>
      </div>
      ${runs.length === 0 ? `
        <div class="empty-state">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.2;margin-bottom:var(--space-3)">
            <circle cx="12" cy="12" r="10"/><path d="M8 12h8m-4-4v8"/>
          </svg>
          <div class="empty-state-text">No sub-agent runs yet</div>
        </div>
      ` : `
        <div class="table-container" style="max-height:260px;overflow-y:auto">
          <table class="table" role="table" aria-label="Sub-agent runs">
            <thead>
              <tr><th>Status</th><th>Goal</th><th>Depth</th><th>Time</th></tr>
            </thead>
            <tbody>
              ${runs.map(r => `
                <tr>
                  <td>${statusBadge(r.status)}</td>
                  <td class="text-sm truncate" style="max-width:180px" title="${(r.goal || '').replace(/"/g, '&quot;')}">${r.goal ? (r.goal.length > 55 ? r.goal.slice(0, 55) + '...' : r.goal) : '—'}</td>
                  <td class="text-mono text-xs" style="opacity:0.6">${r.depth != null ? r.depth : '—'}</td>
                  <td class="text-mono text-xs" style="opacity:0.6">${r.created_at ? new Date(r.created_at).toLocaleTimeString() : '—'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `}
    </div>`;
}
