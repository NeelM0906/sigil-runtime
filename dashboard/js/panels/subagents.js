// Sigil Dashboard — Sub-Agents Panel

function statusBadge(status) {
  const map = {
    running: 'badge-info',
    completed: 'badge-success',
    failed: 'badge-destructive',
    cancelled: 'badge-warning',
  };
  return `<span class="badge ${map[status] || 'badge-outline'}">${status || 'unknown'}</span>`;
}

function truncate(str, len = 60) {
  if (!str) return '—';
  return str.length > len ? str.slice(0, len) + '...' : str;
}

export function renderSubagents(el, state, api) {
  const sa = state.get('subagents') || {};
  const runs = sa.runs || [];

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Sub-Agents</span>
        <div class="flex gap-2">
          <span class="badge badge-info">${sa.active || 0} active</span>
          <span class="badge badge-success">${sa.completed || 0} done</span>
          <span class="badge badge-destructive">${sa.failed || 0} failed</span>
        </div>
      </div>
      ${runs.length === 0 ? `
        <div class="empty-state">
          <div class="empty-state-icon">&#128301;</div>
          <div class="empty-state-text">No sub-agent runs yet</div>
        </div>
      ` : `
        <div class="table-container" style="max-height:280px;overflow-y:auto">
          <table class="table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Goal</th>
                <th>Depth</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              ${runs.map(r => `
                <tr>
                  <td>${statusBadge(r.status)}</td>
                  <td class="text-sm truncate" style="max-width:200px" title="${(r.goal || '').replace(/"/g, '&quot;')}">${truncate(r.goal)}</td>
                  <td class="text-mono text-xs">${r.depth != null ? r.depth : '—'}</td>
                  <td class="text-mono text-xs">${r.created_at ? new Date(r.created_at).toLocaleTimeString() : '—'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `}
    </div>`;
}
