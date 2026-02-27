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
        <div class="sub-card" style="flex:1;min-width:200px" role="region" aria-label="Heartbeat engine">
          <div class="flex items-center gap-2 mb-3">
            <span class="status-dot ${hbRunning ? 'online pulse' : 'offline'}"></span>
            <span class="sub-card-title" style="margin:0">Heartbeat</span>
            <span class="badge ${hbRunning ? 'badge-success' : 'badge-outline'}" style="font-size:9px">${hbRunning ? 'RUN' : 'OFF'}</span>
          </div>
          <div class="stat-row"><span class="stat-label">Interval</span><span class="stat-value">${hb.interval_seconds || '—'}s</span></div>
          <div class="stat-row"><span class="stat-label">Runs</span><span class="stat-value">${hb.total_runs || 0}</span></div>
          <div class="stat-row"><span class="stat-label">Errors</span><span class="stat-value">${hb.total_errors || 0}</span></div>
          ${hb.last_run ? `<div class="stat-row"><span class="stat-label">Last</span><span class="stat-value text-xs">${new Date(hb.last_run).toLocaleTimeString()}</span></div>` : ''}
          <div class="flex gap-2 mt-3">
            <button class="btn btn-sm btn-outline hb-start" aria-label="${hbRunning ? 'Restart' : 'Start'} heartbeat">${hbRunning ? 'Restart' : 'Start'}</button>
            <button class="btn btn-sm btn-outline hb-stop" ${!hbRunning ? 'disabled' : ''} aria-label="Stop heartbeat">Stop</button>
            <button class="btn btn-sm btn-ghost hb-tick" aria-label="Run heartbeat once">Tick</button>
          </div>
        </div>
        <!-- Cron -->
        <div class="sub-card" style="flex:1;min-width:200px" role="region" aria-label="Cron scheduler">
          <div class="flex items-center gap-2 mb-3">
            <span class="status-dot ${cronRunning ? 'online pulse' : 'offline'}"></span>
            <span class="sub-card-title" style="margin:0">Cron</span>
            <span class="badge ${cronRunning ? 'badge-success' : 'badge-outline'}" style="font-size:9px">${cronRunning ? 'RUN' : 'OFF'}</span>
          </div>
          ${schedules.length > 0 ? `
            <div class="table-container" style="max-height:140px;overflow-y:auto">
              <table class="table">
                <thead><tr><th>Expr</th><th>Goal</th><th></th></tr></thead>
                <tbody>
                  ${schedules.map(s => `
                    <tr>
                      <td class="text-mono text-xs">${s.cron_expression || '—'}</td>
                      <td class="text-xs truncate" style="max-width:120px">${s.task_goal || '—'}</td>
                      <td><span class="badge ${s.enabled ? 'badge-success' : 'badge-outline'}" style="font-size:9px">${s.enabled ? 'on' : 'off'}</span></td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          ` : '<div class="text-xs text-muted" style="opacity:0.5">No scheduled tasks</div>'}
          <div class="flex gap-2 mt-3">
            <button class="btn btn-sm btn-outline cron-start" aria-label="${cronRunning ? 'Restart' : 'Start'} cron">${cronRunning ? 'Restart' : 'Start'}</button>
            <button class="btn btn-sm btn-outline cron-stop" ${!cronRunning ? 'disabled' : ''} aria-label="Stop cron">Stop</button>
          </div>
        </div>
      </div>
    </div>`;

  el.querySelector('.hb-start')?.addEventListener('click', () => api.heartbeatAction('start'));
  el.querySelector('.hb-stop')?.addEventListener('click', () => api.heartbeatAction('stop'));
  el.querySelector('.hb-tick')?.addEventListener('click', () => api.heartbeatAction('tick'));
  el.querySelector('.cron-start')?.addEventListener('click', () => api.cronAction('start'));
  el.querySelector('.cron-stop')?.addEventListener('click', () => api.cronAction('stop'));
}
