// Sigil Dashboard — Activity Feed Panel

const TYPE_BADGE = {
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
  const types = ['ALL', ...new Set(events.map(e => e.type).filter(Boolean))];

  const filtered = currentFilter === 'ALL'
    ? events
    : events.filter(e => e.type === currentFilter);

  el.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="flex items-center gap-2">
          <span class="card-title">Activity</span>
          <span class="badge badge-outline">${events.length}</span>
        </div>
        <div class="flex items-center gap-2">
          <select class="select" style="width:auto;height:1.5rem;font-size:var(--font-size-xs);padding:0 1.75rem 0 0.5rem" id="activity-filter" aria-label="Filter activity by type">
            ${types.map(t => `<option value="${t}" ${t === currentFilter ? 'selected' : ''}>${t}</option>`).join('')}
          </select>
          <button class="btn btn-sm btn-ghost" id="activity-pause" aria-label="${paused ? 'Resume' : 'Pause'} activity feed">
            ${paused ? '&#9654;' : '&#10074;&#10074;'}
          </button>
        </div>
      </div>
      <div style="max-height:280px;overflow-y:auto" role="log" aria-label="Activity events" aria-live="${paused ? 'off' : 'polite'}">
        ${filtered.length === 0 ? `
          <div class="empty-state" style="padding:var(--space-6)">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.2;margin-bottom:var(--space-2)">
              <path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="10"/>
            </svg>
            <div class="empty-state-text">No activity events</div>
          </div>
        ` : `
          <div style="display:flex;flex-direction:column">
            ${filtered.map(ev => `
              <div class="flex items-center gap-3" style="padding:5px var(--space-2);border-bottom:1px solid hsl(var(--border)/0.15);transition:background var(--transition-fast)">
                <span class="text-mono text-xs" style="min-width:62px;flex-shrink:0;opacity:0.4">${ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : ''}</span>
                <span class="badge ${TYPE_BADGE[ev.type] || 'badge-outline'}" style="min-width:48px;text-align:center;font-size:9px">${ev.type}</span>
                <span class="text-mono text-xs truncate" style="min-width:56px;max-width:70px;opacity:0.3">${ev.session ? ev.session.slice(0, 8) : ''}</span>
                <span class="text-sm truncate flex-1" style="opacity:0.8">${ev.description || '—'}</span>
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
