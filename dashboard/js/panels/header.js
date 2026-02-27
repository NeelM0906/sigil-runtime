// Sigil Dashboard — Header Panel

export function renderHeader(el, opts) {
  if (!el) return;
  const { tenant, user, online, countdown, refreshInterval, onRefresh, onToggleTheme, onToggleChat, theme } = opts;

  const statusClass = online ? 'online pulse' : 'offline';
  const statusText = online ? 'Connected' : 'Disconnected';
  const themeIcon = theme === 'dark'
    ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>'
    : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';

  el.innerHTML = `
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: hsl(var(--primary))">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
          </svg>
          <span class="font-semibold" style="font-size:var(--font-size-lg)">SIGIL</span>
          <span class="badge badge-outline" style="font-size:10px;letter-spacing:0.1em">CONTROL</span>
        </div>
        <div class="separator" style="width:1px;height:24px;margin:0 var(--space-2)"></div>
        <div class="flex items-center gap-2">
          <span class="status-dot ${statusClass}"></span>
          <span class="text-sm text-muted">${statusText}</span>
        </div>
        <div class="text-xs text-muted text-mono">${tenant} / ${user}</div>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xs text-muted tabular-nums" title="Auto-refresh countdown">${countdown}s</span>
        <button class="btn btn-ghost btn-icon btn-sm" onclick="this.blur()" title="Refresh now" id="header-refresh-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
        </button>
        <button class="btn btn-ghost btn-icon btn-sm" onclick="this.blur()" title="Toggle theme" id="header-theme-btn">
          ${themeIcon}
        </button>
        <button class="btn btn-ghost btn-icon btn-sm" onclick="this.blur()" title="Toggle chat" id="header-chat-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        </button>
      </div>
    </div>`;

  el.querySelector('#header-refresh-btn')?.addEventListener('click', onRefresh);
  el.querySelector('#header-theme-btn')?.addEventListener('click', onToggleTheme);
  el.querySelector('#header-chat-btn')?.addEventListener('click', onToggleChat);
}
