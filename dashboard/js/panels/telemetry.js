// Sigil Dashboard — Loop Telemetry Panel

function svgBarChart(values, opts = {}) {
  const { width = 300, height = 80, color = 'var(--chart-1)', label = '' } = opts;
  if (!values || values.length === 0) {
    return `<div class="empty-state" style="padding:var(--space-4)"><div class="empty-state-text">No data</div></div>`;
  }
  const max = Math.max(...values, 1);
  const barW = Math.max(4, Math.floor((width - 40) / values.length) - 2);
  const chartW = values.length * (barW + 2);
  const bars = values.map((v, i) => {
    const h = Math.max(2, (v / max) * (height - 20));
    const x = i * (barW + 2);
    const y = height - 16 - h;
    return `<rect x="${x}" y="${y}" width="${barW}" height="${h}" rx="1" fill="hsl(${color})" opacity="${0.5 + 0.5 * (v / max)}"/>`;
  }).join('');

  // X-axis labels: first, mid, last
  const xLabels = [];
  if (values.length > 0) {
    xLabels.push(`<text x="0" y="${height - 2}" fill="hsl(var(--muted-foreground))" font-size="9" font-family="var(--font-mono)">1</text>`);
    if (values.length > 2) {
      const mid = Math.floor(values.length / 2);
      xLabels.push(`<text x="${mid * (barW + 2)}" y="${height - 2}" fill="hsl(var(--muted-foreground))" font-size="9" font-family="var(--font-mono)">${mid + 1}</text>`);
    }
    xLabels.push(`<text x="${(values.length - 1) * (barW + 2)}" y="${height - 2}" fill="hsl(var(--muted-foreground))" font-size="9" font-family="var(--font-mono)">${values.length}</text>`);
  }

  return `<svg width="${chartW}" height="${height}" viewBox="0 0 ${chartW} ${height}" style="max-width:100%">${bars}${xLabels.join('')}</svg>`;
}

function stoppedReasonBadge(reason) {
  const map = {
    complete: 'badge-success',
    max_iterations: 'badge-warning',
    budget_exhausted: 'badge-destructive',
    loop_detected: 'badge-warning',
    no_tool_calls: 'badge-info',
  };
  return map[reason] || '';
}

export function renderTelemetry(el, state, api) {
  const telemetry = state.get('loop_telemetry') || [];
  const reversed = telemetry.slice().reverse();

  const iterations = reversed.map(t => t.iterations || 0);
  const toolCounts = reversed.map(t => {
    try {
      const calls = JSON.parse(t.tool_calls_json || '[]');
      return Array.isArray(calls) ? calls.length : 0;
    } catch { return 0; }
  });

  // Stopped reason counts
  const reasonCounts = {};
  for (const t of telemetry) {
    const r = t.stopped_reason || 'unknown';
    reasonCounts[r] = (reasonCounts[r] || 0) + 1;
  }

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Loop Telemetry</span>
        <span class="badge badge-outline">Last ${telemetry.length}</span>
      </div>
      ${telemetry.length === 0 ? `
        <div class="empty-state">
          <div class="empty-state-icon">&#128202;</div>
          <div class="empty-state-text">No loop executions yet</div>
        </div>
      ` : `
        <div class="flex gap-4 flex-wrap">
          <div style="flex:1;min-width:200px">
            <div class="text-xs text-muted mb-2">Iterations per turn</div>
            ${svgBarChart(iterations, { color: 'var(--chart-1)' })}
          </div>
          <div style="flex:1;min-width:200px">
            <div class="text-xs text-muted mb-2">Tool calls per turn</div>
            ${svgBarChart(toolCounts, { color: 'var(--chart-2)' })}
          </div>
        </div>
        <div class="separator"></div>
        <div class="flex gap-2 flex-wrap">
          ${Object.entries(reasonCounts).map(([reason, count]) => `
            <span class="badge ${stoppedReasonBadge(reason)}">${reason}: ${count}</span>
          `).join('')}
        </div>
      `}
    </div>`;
}
