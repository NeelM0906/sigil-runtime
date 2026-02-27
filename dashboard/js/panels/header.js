// Sigil Dashboard — Header Panel

const SIGIL_LOGO = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.9">
  <path d="M12 2L2 7l10 5 10-5-10-5z"/>
  <path d="M2 17l10 5 10-5"/>
  <path d="M2 12l10 5 10-5"/>
</svg>`;

const ICON_REFRESH = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>`;

const ICON_SUN = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>`;

const ICON_MOON = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;

const ICON_CHAT = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`;

export function renderHeader(el, opts) {
  if (!el) return;
  const { tenant, user, online, countdown, refreshInterval, onRefresh, onToggleTheme, onToggleChat, theme } = opts;

  const statusClass = online ? 'online pulse' : 'offline';
  const statusText = online ? 'Connected' : 'Offline';
  const themeIcon = theme === 'dark' ? ICON_SUN : ICON_MOON;

  // Countdown arc (mini SVG)
  const pct = countdown / refreshInterval;
  const r = 6, cx = 7, cy = 7;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - pct);
  const countdownArc = `<svg width="14" height="14" viewBox="0 0 14 14" style="transform:rotate(-90deg)">
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="hsl(var(--border))" stroke-width="1.5"/>
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="hsl(var(--muted-foreground)/0.5)" stroke-width="1.5"
      stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" stroke-linecap="round"
      style="transition:stroke-dashoffset 1s linear"/>
  </svg>`;

  el.innerHTML = `
    <div class="flex items-center justify-between" role="toolbar" aria-label="Dashboard controls">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2" style="color:hsl(var(--foreground))">
          ${SIGIL_LOGO}
          <span style="font-size:var(--font-size-sm);font-weight:700;letter-spacing:0.06em">SIGIL</span>
          <span class="badge badge-outline" style="font-size:9px;letter-spacing:0.12em;padding:1px 6px">CONTROL</span>
        </div>
        <div style="width:1px;height:20px;background:hsl(var(--border)/0.4);margin:0 var(--space-1)"></div>
        <div class="flex items-center gap-2">
          <span class="status-dot ${statusClass}" role="status" aria-label="${statusText}"></span>
          <span class="text-xs text-muted">${statusText}</span>
        </div>
        <span class="text-xs text-muted text-mono" style="opacity:0.6">${tenant} / ${user}</span>
      </div>
      <div class="flex items-center gap-1">
        <div class="flex items-center gap-1 text-muted" style="margin-right:var(--space-1)" title="Auto-refresh in ${countdown}s">
          ${countdownArc}
          <span class="text-xs tabular-nums text-mono" style="opacity:0.5;min-width:18px">${countdown}s</span>
        </div>
        <button class="btn btn-ghost btn-icon btn-sm" title="Refresh now" aria-label="Refresh dashboard" id="header-refresh-btn">${ICON_REFRESH}</button>
        <button class="btn btn-ghost btn-icon btn-sm" title="Toggle theme" aria-label="Toggle theme" id="header-theme-btn">${themeIcon}</button>
        <button class="btn btn-ghost btn-icon btn-sm" title="Toggle chat" aria-label="Toggle chat panel" id="header-chat-btn">${ICON_CHAT}</button>
      </div>
    </div>`;

  el.querySelector('#header-refresh-btn')?.addEventListener('click', onRefresh);
  el.querySelector('#header-theme-btn')?.addEventListener('click', onToggleTheme);
  el.querySelector('#header-chat-btn')?.addEventListener('click', onToggleChat);
}
