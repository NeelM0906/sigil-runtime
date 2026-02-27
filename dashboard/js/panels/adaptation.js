// Sigil Dashboard — Adaptation + Self-Eval Panel

function delta(curr, prev) {
  if (curr == null || prev == null) return '<span class="delta-flat">—</span>';
  const d = curr - prev;
  if (Math.abs(d) < 0.001) return '<span class="delta-flat">—</span>';
  const arrow = d > 0 ? '&#9650;' : '&#9660;';
  const cls = d > 0 ? 'delta-up' : 'delta-down';
  return `<span class="${cls}">${arrow} ${Math.abs(d).toFixed(3)}</span>`;
}

export function renderAdaptation(el, state, api) {
  const adapt = state.get('adaptation') || {};
  const policy = adapt.policy || {};
  const metrics = adapt.recent_metrics || [];
  const latest = metrics[0] || {};
  const prior = metrics[1] || {};

  const metricRows = [
    ['Retrieval P@K', latest.retrieval_precision, prior.retrieval_precision],
    ['Escalation Rate', latest.search_escalation_rate, prior.search_escalation_rate],
    ['Sub-agent Success', latest.subagent_success_rate, prior.subagent_success_rate],
    ['Loop Incidents', latest.loop_incident_count, prior.loop_incident_count],
    ['Brier Score', latest.brier_score, prior.brier_score],
  ];

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Adaptation Engine</span>
        <span class="badge badge-outline">${policy.name || 'default'} v${policy.version || '?'}</span>
      </div>
      <div class="table-container">
        <table class="table">
          <thead>
            <tr><th>Metric</th><th class="text-right">Latest</th><th class="text-right">Prior</th><th class="text-right">Delta</th></tr>
          </thead>
          <tbody>
            ${metricRows.map(([name, curr, prev]) => `
              <tr>
                <td>${name}</td>
                <td class="text-right text-mono">${curr != null ? Number(curr).toFixed(3) : '—'}</td>
                <td class="text-right text-mono">${prev != null ? Number(prev).toFixed(3) : '—'}</td>
                <td class="text-right">${delta(curr, prev)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      <div class="separator"></div>
      <div class="stat-row">
        <span class="stat-label">Turns tracked</span>
        <span class="stat-value">${adapt.turn_count || 0}</span>
      </div>
      ${policy.reason ? `<div class="text-xs text-muted mt-2">Reason: ${policy.reason}</div>` : ''}
    </div>`;
}
