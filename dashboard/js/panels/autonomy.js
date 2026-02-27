// Sigil Dashboard — Autonomy (Heartbeat + Cron) Panel

export function renderAutonomy(el, state, api) {
  const auto = state.get('autonomy') || {};
  const hb = auto.heartbeat || {};
  const cron = auto.cron || {};
  const schedules = auto.schedules || [];

  const hbRunning = hb.running === true;
  const cronRunning = cron.running === true;

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Autonomy</span>
      </div>
      <div class="flex gap-3 flex-wrap">
        <!-- Heartbeat -->
        <div style="flex:1;min-width:200px;border:1px solid hsl(var(--border)/0.5);border-radius:var(--radius);padding:var(--space-3)">
          <div class="flex items-center gap-2 mb-3">
            <span class="status-dot ${hbRunning ? 'online pulse' : 'offline'}"></span>
            <span class="text-sm font-medium">Heartbeat</span>
            <span class="badge ${hbRunning ? 'badge-success' : 'badge-outline'}">${hbRunning ? 'Running' : 'Stopped'}</span>
          </div>
          <div class="stat-row"><span class="stat-label">Interval</span><span class="stat-value">${hb.interval_seconds || '—'}s</span></div>
          <div class="stat-row"><span class="stat-label">Total runs</span><span class="stat-value">${hb.total_runs || 0}</span></div>
          <div class="stat-row"><span class="stat-label">Errors</span><span class="stat-value">${hb.total_errors || 0}</span></div>
          ${hb.last_run ? `<div class="stat-row"><span class="stat-label">Last run</span><span class="stat-value text-xs">${new Date(hb.last_run).toLocaleTimeString()}</span></div>` : ''}
          <div class="flex gap-2 mt-3">
            <button class="btn btn-sm btn-outline hb-start">${hbRunning ? 'Restart' : 'Start'}</button>
            <button class="btn btn-sm btn-outline hb-stop" ${!hbRunning ? 'disabled' : ''}>Stop</button>
            <button class="btn btn-sm btn-ghost hb-tick">Run Once</button>
          </div>
        </div>
        <!-- Cron -->
        <div style="flex:1;min-width:200px;border:1px solid hsl(var(--border)/0.5);border-radius:var(--radius);padding:var(--space-3)">
          <div class="flex items-center gap-2 mb-3">
            <span class="status-dot ${cronRunning ? 'online pulse' : 'offline'}"></span>
            <span class="text-sm font-medium">Cron Scheduler</span>
            <span class="badge ${cronRunning ? 'badge-success' : 'badge-outline'}">${cronRunning ? 'Running' : 'Stopped'}</span>
          </div>
          ${schedules.length > 0 ? `
            <div class="table-container" style="max-height:160px;overflow-y:auto">
              <table class="table">
                <thead><tr><th>Cron</th><th>Goal</th><th>Status</th></tr></thead>
                <tbody>
                  ${schedules.map(s => `
                    <tr>
                      <td class="text-mono text-xs">${s.cron_expression || '—'}</td>
                      <td class="text-sm truncate" style="max-width:150px">${s.task_goal || '—'}</td>
                      <td><span class="badge ${s.enabled ? 'badge-success' : 'badge-outline'}">${s.enabled ? 'on' : 'off'}</span></td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          ` : '<div class="text-xs text-muted">No scheduled tasks</div>'}
          <div class="flex gap-2 mt-3">
            <button class="btn btn-sm btn-outline cron-start">${cronRunning ? 'Restart' : 'Start'}</button>
            <button class="btn btn-sm btn-outline cron-stop" ${!cronRunning ? 'disabled' : ''}>Stop</button>
          </div>
        </div>
      </div>
    </div>`;

  // Wire buttons
  el.querySelector('.hb-start')?.addEventListener('click', () => api.heartbeatAction('start'));
  el.querySelector('.hb-stop')?.addEventListener('click', () => api.heartbeatAction('stop'));
  el.querySelector('.hb-tick')?.addEventListener('click', () => api.heartbeatAction('tick'));
  el.querySelector('.cron-start')?.addEventListener('click', () => api.cronAction('start'));
  el.querySelector('.cron-stop')?.addEventListener('click', () => api.cronAction('stop'));
}
