// Sigil Dashboard — Health / Cost / Tokens / Sessions Panel

function fmtUptime(seconds) {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function fmtNumber(n) {
  if (n == null) return '0';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function miniBar(values, maxH = 32) {
  if (!values || values.length === 0) return '';
  const max = Math.max(...values, 1);
  const barW = Math.max(4, Math.floor(200 / values.length) - 1);
  const bars = values.map((v, i) => {
    const h = Math.max(2, (v / max) * maxH);
    return `<rect x="${i * (barW + 1)}" y="${maxH - h}" width="${barW}" height="${h}" rx="1" fill="hsl(var(--chart-1))" opacity="${0.5 + 0.5 * (v / max)}"/>`;
  }).join('');
  const w = values.length * (barW + 1);
  return `<svg width="${w}" height="${maxH}" viewBox="0 0 ${w} ${maxH}">${bars}</svg>`;
}

export function renderHealth(el, state, api) {
  const rt = state.get('runtime') || {};
  const sessions = state.get('sessions') || {};
  const tokens = state.get('tokens') || {};
  const telemetry = state.get('loop_telemetry') || [];
  const cfg = rt.config || {};

  const budgetUsd = cfg.budget_limit_usd || 2.0;
  const totalTokens = (tokens.input_all || 0) + (tokens.output_all || 0);
  // Rough cost estimate: $3/M input, $15/M output (approx)
  const estCost = ((tokens.input_all || 0) * 3 + (tokens.output_all || 0) * 15) / 1_000_000;
  const costPct = Math.min(100, (estCost / budgetUsd) * 100);

  // Token sparkline from telemetry
  const tokenHistory = telemetry.slice().reverse().map(t => (t.total_input_tokens || 0) + (t.total_output_tokens || 0));
  const iterHistory = telemetry.slice().reverse().map(t => t.iterations || 0);

  el.innerHTML = `
    <div class="flex gap-4 flex-wrap">
      <!-- Runtime Status -->
      <div class="card flex-1" style="min-width:200px">
        <div class="card-header">
          <span class="card-title">Runtime</span>
          <span class="badge ${rt.uptime_seconds ? 'badge-success' : 'badge-destructive'}">${rt.uptime_seconds ? 'Online' : 'Offline'}</span>
        </div>
        <div class="card-value">${fmtUptime(rt.uptime_seconds || 0)}</div>
        <div class="card-subtitle">uptime</div>
        <div class="separator"></div>
        <div class="stat-row"><span class="stat-label">Tenants</span><span class="stat-value">${rt.tenant_count || 0}</span></div>
        <div class="stat-row"><span class="stat-label">Threads</span><span class="stat-value">${rt.active_threads || 0}</span></div>
        <div class="stat-row"><span class="stat-label">Provider</span><span class="stat-value">${cfg.provider || '—'}</span></div>
        <div class="stat-row"><span class="stat-label">Model</span><span class="stat-value text-xs truncate" style="max-width:120px">${cfg.model_id || '—'}</span></div>
      </div>

      <!-- Cost -->
      <div class="card flex-1" style="min-width:200px">
        <div class="card-header">
          <span class="card-title">Cost</span>
          <span class="badge badge-outline">est.</span>
        </div>
        <div class="card-value">$${estCost.toFixed(4)}</div>
        <div class="card-subtitle">estimated total</div>
        <div class="separator"></div>
        <div class="stat-row"><span class="stat-label">Budget</span><span class="stat-value">$${budgetUsd.toFixed(2)}</span></div>
        <div class="mt-2">
          <div class="progress">
            <div class="progress-fill ${costPct > 80 ? 'destructive' : costPct > 50 ? 'warning' : 'success'}" style="width:${costPct}%"></div>
          </div>
          <div class="text-xs text-muted mt-2">${costPct.toFixed(1)}% of budget</div>
        </div>
      </div>

      <!-- Tokens -->
      <div class="card flex-1" style="min-width:200px">
        <div class="card-header">
          <span class="card-title">Tokens</span>
        </div>
        <div class="card-value">${fmtNumber((tokens.input_24h || 0) + (tokens.output_24h || 0))}</div>
        <div class="card-subtitle">24h total</div>
        <div class="separator"></div>
        <div class="stat-row"><span class="stat-label">In (24h)</span><span class="stat-value">${fmtNumber(tokens.input_24h)}</span></div>
        <div class="stat-row"><span class="stat-label">Out (24h)</span><span class="stat-value">${fmtNumber(tokens.output_24h)}</span></div>
        <div class="stat-row"><span class="stat-label">7d total</span><span class="stat-value">${fmtNumber((tokens.input_7d || 0) + (tokens.output_7d || 0))}</span></div>
        <div class="mt-2">${miniBar(tokenHistory)}</div>
      </div>

      <!-- Sessions -->
      <div class="card flex-1" style="min-width:200px">
        <div class="card-header">
          <span class="card-title">Sessions</span>
        </div>
        <div class="card-value">${sessions.total_sessions || 0}</div>
        <div class="card-subtitle">total sessions</div>
        <div class="separator"></div>
        <div class="stat-row"><span class="stat-label">Total turns</span><span class="stat-value">${fmtNumber(sessions.total_turns)}</span></div>
        <div class="stat-row"><span class="stat-label">Avg iterations</span><span class="stat-value">${sessions.avg_iterations || 0}</span></div>
        <div class="stat-row"><span class="stat-label">Max iter/turn</span><span class="stat-value">${cfg.max_iterations || 25}</span></div>
        <div class="mt-2">${miniBar(iterHistory)}</div>
      </div>
    </div>`;
}
