// Sigil Dashboard — Health / Cost / Tokens / Sessions Panel

function fmtUptime(seconds) {
  if (!seconds || seconds < 0) return '0s';
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function fmtNumber(n) {
  if (n == null || n === 0) return '0';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function sparklineSVG(values, opts = {}) {
  const { w = 180, h = 28, color = 'var(--chart-1)', fill = true } = opts;
  if (!values || values.length < 2) return '';
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const padY = 2;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - padY - ((v - min) / range) * (h - padY * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const line = `<polyline points="${points.join(' ')}" fill="none" stroke="hsl(${color})" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`;
  let area = '';
  if (fill) {
    area = `<polygon points="${points[0].split(',')[0]},${h} ${points.join(' ')} ${points[points.length-1].split(',')[0]},${h}" fill="url(#sparkGrad)" opacity="0.15"/>`;
  }
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="display:block;max-width:100%">
    <defs><linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="hsl(${color})"/>
      <stop offset="100%" stop-color="hsl(${color})" stop-opacity="0"/>
    </linearGradient></defs>
    ${area}${line}
  </svg>`;
}

function miniBarSVG(values, opts = {}) {
  const { h = 30, color = 'var(--chart-1)' } = opts;
  if (!values || values.length === 0) return '';
  const max = Math.max(...values, 1);
  const barW = Math.max(3, Math.floor(180 / values.length) - 1);
  const w = values.length * (barW + 1);
  const bars = values.map((v, i) => {
    const bh = Math.max(1, (v / max) * (h - 2));
    const opacity = 0.35 + 0.65 * (v / max);
    return `<rect x="${i * (barW + 1)}" y="${h - bh}" width="${barW}" height="${bh}" rx="1" fill="hsl(${color})" opacity="${opacity.toFixed(2)}"/>`;
  }).join('');
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="display:block;max-width:100%">${bars}</svg>`;
}

export function renderHealth(el, state, api) {
  const rt = state.get('runtime') || {};
  const sessions = state.get('sessions') || {};
  const tokens = state.get('tokens') || {};
  const telemetry = state.get('loop_telemetry') || [];
  const pinecone = state.get('pinecone') || {};
  const cfg = rt.config || {};

  const budgetUsd = cfg.budget_limit_usd || 2.0;
  const estCost = ((tokens.input_all || 0) * 3 + (tokens.output_all || 0) * 15) / 1_000_000;
  const costPct = Math.min(100, (estCost / budgetUsd) * 100);

  const tokenHistory = telemetry.slice().reverse().map(t => (t.total_input_tokens || 0) + (t.total_output_tokens || 0));
  const iterHistory = telemetry.slice().reverse().map(t => t.iterations || 0);

  const costBarClass = costPct > 80 ? 'destructive' : costPct > 50 ? 'warning' : 'success';

  el.innerHTML = `
    <div class="flex gap-4 flex-wrap" role="group" aria-label="Key metrics">
      <!-- Runtime -->
      <div class="card flex-1" style="min-width:200px">
        <div class="card-header">
          <span class="card-title">Runtime</span>
          <span class="badge ${rt.uptime_seconds ? 'badge-success' : 'badge-destructive'}" role="status">${rt.uptime_seconds ? 'Online' : 'Offline'}</span>
        </div>
        <div class="card-value">${fmtUptime(rt.uptime_seconds || 0)}</div>
        <div class="card-subtitle">uptime</div>
        <div class="separator"></div>
        <div class="stat-row"><span class="stat-label">Tenants</span><span class="stat-value">${rt.tenant_count || 0}</span></div>
        <div class="stat-row"><span class="stat-label">Threads</span><span class="stat-value">${rt.active_threads || 0}</span></div>
        <div class="stat-row"><span class="stat-label">Provider</span><span class="stat-value">${cfg.provider || '—'}</span></div>
        <div class="stat-row"><span class="stat-label">Model</span><span class="stat-value truncate" style="max-width:110px" title="${cfg.model_id || ''}">${(cfg.model_id || '—').split('/').pop()}</span></div>
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
        <div class="mt-2" role="progressbar" aria-valuenow="${costPct.toFixed(0)}" aria-valuemin="0" aria-valuemax="100" aria-label="Budget usage">
          <div class="progress">
            <div class="progress-fill ${costBarClass}" style="width:${costPct}%"></div>
          </div>
          <div class="text-xs text-muted mt-2 text-mono" style="opacity:0.7">${costPct.toFixed(1)}% used</div>
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
        <div class="stat-row"><span class="stat-label">In 24h</span><span class="stat-value">${fmtNumber(tokens.input_24h)}</span></div>
        <div class="stat-row"><span class="stat-label">Out 24h</span><span class="stat-value">${fmtNumber(tokens.output_24h)}</span></div>
        <div class="stat-row"><span class="stat-label">7d total</span><span class="stat-value">${fmtNumber((tokens.input_7d || 0) + (tokens.output_7d || 0))}</span></div>
        <div class="mt-2">${sparklineSVG(tokenHistory, { color: 'var(--chart-1)' })}</div>
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
        <div class="stat-row"><span class="stat-label">Avg iters</span><span class="stat-value">${sessions.avg_iterations || 0}</span></div>
        <div class="stat-row"><span class="stat-label">Max/turn</span><span class="stat-value">${cfg.max_iterations || 25}</span></div>
        <div class="mt-2">${miniBarSVG(iterHistory, { color: 'var(--chart-2)' })}</div>
      </div>

      <!-- Pinecone -->
      <div class="card flex-1" style="min-width:200px">
        <div class="card-header">
          <span class="card-title">Pinecone</span>
          <span class="badge ${pinecone.connected ? 'badge-success' : 'badge-outline'}">${pinecone.connected ? 'Connected' : 'Disconnected'}</span>
        </div>
        <div class="card-value">${fmtNumber(pinecone.index_count || 0)}</div>
        <div class="card-subtitle">indexes accessible</div>
        <div class="separator"></div>
        <div class="stat-row"><span class="stat-label">Enabled</span><span class="stat-value">${pinecone.enabled ? 'yes' : 'no'}</span></div>
        <div class="stat-row"><span class="stat-label">Vectors</span><span class="stat-value">${fmtNumber(pinecone.total_vector_count || 0)}</span></div>
        <div class="text-xs text-mono mt-2" style="opacity:.65">${pinecone.error ? `error: ${pinecone.error}` : 'status OK'}</div>
      </div>
    </div>`;
}
