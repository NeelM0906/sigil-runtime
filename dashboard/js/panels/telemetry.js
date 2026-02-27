// Sigil Dashboard — Loop Telemetry Panel

function barChart(values, opts = {}) {
  const { w = 280, h = 70, color = 'var(--chart-1)' } = opts;
  if (!values || values.length === 0) return '';
  const max = Math.max(...values, 1);
  const gap = 1;
  const barW = Math.max(3, Math.floor((w - values.length * gap) / values.length));
  const chartW = values.length * (barW + gap);

  const bars = values.map((v, i) => {
    const bh = Math.max(1, (v / max) * (h - 14));
    const x = i * (barW + gap);
    const y = h - 12 - bh;
    const opacity = 0.3 + 0.7 * (v / max);
    return `<rect x="${x}" y="${y}" width="${barW}" height="${bh}" rx="1.5" fill="hsl(${color})" opacity="${opacity.toFixed(2)}">
      <title>Turn ${i + 1}: ${v}</title>
    </rect>`;
  }).join('');

  // X-axis markers
  const labels = [];
  if (values.length > 0) {
    labels.push(`<text x="0" y="${h - 1}" fill="hsl(var(--muted-foreground))" font-size="8" font-family="var(--font-mono)" opacity="0.5">1</text>`);
    if (values.length > 4) {
      const mid = Math.floor(values.length / 2);
      labels.push(`<text x="${mid * (barW + gap)}" y="${h - 1}" fill="hsl(var(--muted-foreground))" font-size="8" font-family="var(--font-mono)" opacity="0.5">${mid + 1}</text>`);
    }
    labels.push(`<text x="${(values.length - 1) * (barW + gap)}" y="${h - 1}" fill="hsl(var(--muted-foreground))" font-size="8" font-family="var(--font-mono)" opacity="0.5">${values.length}</text>`);
  }

  return `<svg width="${chartW}" height="${h}" viewBox="0 0 ${chartW} ${h}" role="img" aria-label="Bar chart" style="display:block;max-width:100%">${bars}${labels.join('')}</svg>`;
}

function reasonBadgeClass(reason) {
  const map = {
    complete: 'badge-success',
    max_iterations: 'badge-warning',
    budget_exhausted: 'badge-destructive',
    loop_detected: 'badge-warning',
    no_tool_calls: 'badge-info',
  };
  return map[reason] || 'badge-outline';
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

  const reasonCounts = {};
  for (const t of telemetry) {
    const r = t.stopped_reason || 'unknown';
    reasonCounts[r] = (reasonCounts[r] || 0) + 1;
  }

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Loop Telemetry</span>
        <span class="badge badge-outline">${telemetry.length} runs</span>
      </div>
      ${telemetry.length === 0 ? `
        <div class="empty-state">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.2;margin-bottom:var(--space-3)">
            <path d="M3 3v18h18"/><path d="m7 16 4-8 4 5 5-6"/>
          </svg>
          <div class="empty-state-text">Telemetry data appears after loop executions</div>
        </div>
      ` : `
        <div class="flex gap-4 flex-wrap">
          <div style="flex:1;min-width:180px">
            <div class="text-xs text-muted mb-2" style="opacity:0.6">Iterations / turn</div>
            ${barChart(iterations, { color: 'var(--chart-1)' })}
          </div>
          <div style="flex:1;min-width:180px">
            <div class="text-xs text-muted mb-2" style="opacity:0.6">Tool calls / turn</div>
            ${barChart(toolCounts, { color: 'var(--chart-2)' })}
          </div>
        </div>
        <div class="separator"></div>
        <div class="flex gap-2 flex-wrap" role="group" aria-label="Stop reason counts">
          ${Object.entries(reasonCounts).map(([reason, count]) => `
            <span class="badge ${reasonBadgeClass(reason)}">${reason} ${count}</span>
          `).join('')}
        </div>
      `}
    </div>`;
}
