// Sigil Dashboard — Sisters Panel

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function statusBadge(item) {
  const status = escapeHtml(item?.status || 'unknown');
  const running = Boolean(item?.running);
  if (running) return `<span class="badge badge-success">${status}</span>`;
  if (status === 'failed' || status === 'timed_out') return `<span class="badge badge-destructive">${status}</span>`;
  return `<span class="badge badge-outline">${status}</span>`;
}

function fmtTime(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return escapeHtml(String(value));
  }
}

export function renderSisters(el, state, api) {
  const sisters = state.get('sisters') || {};
  const items = Array.isArray(sisters.items) ? sisters.items : [];

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Sisters</span>
        <div class="flex gap-1">
          <span class="badge badge-outline">${sisters.total || 0} total</span>
          <span class="badge badge-success">${sisters.running || 0} running</span>
        </div>
      </div>
      ${items.length === 0 ? `
        <div class="empty-state">
          <div class="empty-state-text">No sisters configured</div>
        </div>
      ` : `
        <div class="table-container" style="max-height:280px;overflow-y:auto">
          <table class="table" role="table" aria-label="Sister status">
            <thead>
              <tr><th>Sister</th><th>Status</th><th>Last Activity</th><th>Actions</th></tr>
            </thead>
            <tbody>
              ${items.map(item => `
                <tr>
                  <td>
                    <div class="text-sm"><strong>${escapeHtml(item.display_name || item.sister_id)}</strong></div>
                    <div class="text-xs text-mono" style="opacity:.65">${escapeHtml(item.sister_id)}</div>
                  </td>
                  <td>${statusBadge(item)}</td>
                  <td class="text-xs text-mono" style="opacity:.7">${fmtTime(item.last_activity)}</td>
                  <td>
                    <div class="flex gap-1">
                      <button class="btn btn-sm btn-outline" data-sister-action="spawn" data-sister-id="${escapeHtml(item.sister_id)}" ${item.running ? 'disabled' : ''}>Start</button>
                      <button class="btn btn-sm btn-outline" data-sister-action="stop" data-sister-id="${escapeHtml(item.sister_id)}" ${item.running ? '' : 'disabled'}>Stop</button>
                    </div>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `}
      <div data-sister-feedback class="text-xs text-mono mt-2" style="opacity:.75"></div>
    </div>`;

  const feedbackEl = el.querySelector('[data-sister-feedback]');
  el.querySelectorAll('[data-sister-action]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const action = btn.getAttribute('data-sister-action');
      const sisterId = btn.getAttribute('data-sister-id');
      if (!action || !sisterId) return;
      btn.disabled = true;
      if (feedbackEl) feedbackEl.textContent = `${action} ${sisterId}...`;
      try {
        await api.sisterAction(action, sisterId);
        if (feedbackEl) feedbackEl.textContent = `${action} ${sisterId}: success`;
      } catch (err) {
        console.error(`sister ${action} failed`, err);
        if (feedbackEl) feedbackEl.textContent = `${action} ${sisterId}: failed`;
      } finally {
        btn.disabled = false;
      }
    });
  });
}
