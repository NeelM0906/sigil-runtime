// Sigil Dashboard — Activity Feed Panel

const TYPE_COLORS = {
  TURN: 'badge-info',
  TOOL: 'badge-success',
  MEMORY: 'badge',
  ADAPT: 'badge-warning',
  SUBAGT: 'badge-info',
  CRON: 'badge-warning',
  HBEAT: 'badge',
};

let currentFilter = 'ALL';

export function renderActivity(el, events, opts = {}) {
  const { paused = false, onTogglePause } = opts;
  const types = ['ALL', ...new Set(events.map(e => e.type))];

  const filtered = currentFilter === 'ALL'
    ? events
    : events.filter(e => e.type === currentFilter);

  el.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="flex items-center gap-3">
          <span class="card-title">Activity Feed</span>
          <span class="badge badge-outline">${events.length} events</span>
        </div>
        <div class="flex items-center gap-2">
          <select class="select" style="width:auto;height:1.75rem;font-size:var(--font-size-xs)" id="activity-filter">
            ${types.map(t => `<option value="${t}" ${t === currentFilter ? 'selected' : ''}>${t}</option>`).join('')}
          </select>
          <button class="btn btn-sm btn-ghost" id="activity-pause">${paused ? '&#9654; Resume' : '&#9646;&#9646; Pause'}</button>
        </div>
      </div>
      <div style="max-height:300px;overflow-y:auto">
        ${filtered.length === 0 ? `
          <div class="empty-state" style="padding:var(--space-4)">
            <div class="empty-state-text">No activity events</div>
          </div>
        ` : `
          <div style="display:flex;flex-direction:column;gap:2px">
            ${filtered.map(ev => `
              <div class="flex items-center gap-3" style="padding:var(--space-2) var(--space-1);border-bottom:1px solid hsl(var(--border)/0.3)">
                <span class="text-mono text-xs text-muted" style="min-width:70px;flex-shrink:0">${ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '—'}</span>
                <span class="badge ${TYPE_COLORS[ev.type] || 'badge-outline'}" style="min-width:55px;text-align:center">${ev.type}</span>
                <span class="text-mono text-xs text-muted truncate" style="min-width:60px;max-width:80px">${ev.session ? ev.session.slice(0, 8) : '—'}</span>
                <span class="text-sm truncate flex-1">${ev.description || '—'}</span>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    </div>`;

  el.querySelector('#activity-filter')?.addEventListener('change', (e) => {
    currentFilter = e.target.value;
    renderActivity(el, events, opts);
  });
  el.querySelector('#activity-pause')?.addEventListener('click', () => {
    if (onTogglePause) onTogglePause();
  });
}
