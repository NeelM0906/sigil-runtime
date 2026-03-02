// Sigil Dashboard — Team Manager Schedule Manager

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

/**
 * Format an ISO timestamp as a relative time string (e.g. "in 5 min", "3 hours ago").
 * Falls back to locale string for dates far in the past/future.
 */
function fmtRelativeTime(value) {
  if (!value) return '--';
  try {
    const date = new Date(value);
    const now = Date.now();
    const diffMs = date.getTime() - now;
    const absDiff = Math.abs(diffMs);
    const future = diffMs > 0;

    if (absDiff < 60_000) return future ? 'in <1 min' : 'just now';
    if (absDiff < 3_600_000) {
      const mins = Math.round(absDiff / 60_000);
      return future ? `in ${mins} min` : `${mins} min ago`;
    }
    if (absDiff < 86_400_000) {
      const hrs = Math.round(absDiff / 3_600_000);
      return future ? `in ${hrs}h` : `${hrs}h ago`;
    }
    if (absDiff < 604_800_000) {
      const days = Math.round(absDiff / 86_400_000);
      return future ? `in ${days}d` : `${days}d ago`;
    }
    return date.toLocaleDateString();
  } catch {
    return escapeHtml(String(value));
  }
}

const CRON_EXAMPLES = [
  { expr: '*/30 * * * *', label: 'Every 30 min' },
  { expr: '0 * * * *',    label: 'Every hour' },
  { expr: '0 9 * * *',    label: 'Daily at 9am' },
  { expr: '0 3 * * *',    label: 'Daily at 3am' },
  { expr: '0 9 * * 1',    label: 'Mon at 9am' },
];

function renderForm(onSubmit, onCancel) {
  const formHtml = `
    <div class="tm-schedule-form" data-tm-sched-form>
      <div class="tm-schedule-form-field">
        <label class="tm-schedule-form-label" for="tm-sched-name">Name</label>
        <input class="input input-sm" id="tm-sched-name" type="text" placeholder="Deploy nightly" required />
      </div>
      <div class="tm-schedule-form-field">
        <label class="tm-schedule-form-label" for="tm-sched-cron">Cron expression</label>
        <input class="input input-sm" id="tm-sched-cron" type="text" placeholder="*/30 * * * *" required />
        <span class="text-xs" style="opacity:.5">min hour day month weekday</span>
      </div>
      <div class="tm-schedule-form-field">
        <label class="tm-schedule-form-label" for="tm-sched-action">Action</label>
        <select class="input input-sm" id="tm-sched-action">
          <option value="deploy" selected>deploy</option>
        </select>
      </div>
      <div class="tm-schedule-form-field" style="align-self:end">
        <label class="tm-schedule-form-label tm-schedule-form-checkbox-label">
          <input type="checkbox" id="tm-sched-approval" />
          Requires approval
        </label>
      </div>
      <div class="tm-schedule-form-actions">
        <button class="btn btn-sm" data-tm-sched-submit>Create</button>
        <button class="btn btn-sm btn-ghost" data-tm-sched-cancel>Cancel</button>
      </div>
    </div>
    <div class="tm-schedule-cron-hints">
      ${CRON_EXAMPLES.map(e => `<button class="btn btn-xs btn-ghost tm-cron-hint" data-cron="${escapeHtml(e.expr)}" title="${escapeHtml(e.expr)}">${escapeHtml(e.label)}</button>`).join('')}
    </div>`;
  return formHtml;
}

function renderScheduleTable(schedules) {
  if (!schedules || schedules.length === 0) {
    return `
      <div class="tm-schedule-empty">
        <span class="text-xs" style="opacity:.5">No schedules yet. Click "+ New" to create one.</span>
      </div>`;
  }

  return `
    <div class="table-container" style="overflow-x:auto">
      <table class="table tm-schedule-table" role="table" aria-label="Graph schedules">
        <thead>
          <tr>
            <th>Name</th>
            <th>Cron</th>
            <th>Action</th>
            <th>Next run</th>
            <th>Last run</th>
            <th>On</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${schedules.map(s => `
            <tr class="tm-schedule-row" data-schedule-id="${escapeHtml(s.id)}">
              <td class="text-sm">${escapeHtml(s.name || 'Untitled')}</td>
              <td class="text-xs text-mono">${escapeHtml(s.cron_expression || '--')}</td>
              <td><span class="badge badge-outline text-xs">${escapeHtml(s.action || 'deploy')}</span></td>
              <td class="text-xs text-mono" style="opacity:.7">${fmtRelativeTime(s.next_run_at)}</td>
              <td class="text-xs text-mono" style="opacity:.7">${fmtRelativeTime(s.last_run_at)}</td>
              <td>
                <label class="tm-toggle-switch" title="${s.enabled !== false ? 'Enabled' : 'Disabled'}">
                  <input type="checkbox" class="tm-toggle-input" data-tm-sched-toggle="${escapeHtml(s.id)}" ${s.enabled !== false ? 'checked' : ''} />
                  <span class="tm-toggle-slider"></span>
                </label>
              </td>
              <td>
                <button class="btn btn-sm btn-ghost" data-tm-sched-delete="${escapeHtml(s.id)}" aria-label="Delete schedule" title="Delete schedule">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>`;
}

/**
 * Render the schedule manager panel into the given element.
 * @param {HTMLElement} el  Target container element
 * @param {object} store    TeamManagerStore instance
 * @param {object} api      SigilAPI instance
 */
export function renderScheduleManager(el, store, api) {
  const schedules = store.schedules || [];
  const showForm = el.dataset.tmSchedShowForm === 'true';

  el.innerHTML = `
    <div class="tm-schedules-header">
      <span class="text-sm font-semibold">Schedules</span>
      <div class="flex gap-1">
        <span class="badge badge-outline text-xs">${schedules.length}</span>
        <button class="btn btn-sm btn-outline" data-tm-sched-new title="New schedule">+ New</button>
        <button class="btn btn-sm btn-ghost" data-tm-sched-refresh title="Refresh schedules">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
        </button>
      </div>
    </div>
    <div data-tm-sched-form-container>${showForm ? renderForm() : ''}</div>
    ${renderScheduleTable(schedules)}
    <div data-tm-sched-feedback class="text-xs text-mono mt-1" style="opacity:.75;min-height:1rem"></div>`;

  // ── Bind events ──

  const feedbackEl = el.querySelector('[data-tm-sched-feedback]');
  const formContainer = el.querySelector('[data-tm-sched-form-container]');

  function showFeedback(msg) {
    if (feedbackEl) feedbackEl.textContent = msg;
  }

  // New schedule button
  el.querySelector('[data-tm-sched-new]')?.addEventListener('click', () => {
    if (formContainer.innerHTML.trim()) {
      // Already showing form -- collapse it
      formContainer.innerHTML = '';
      el.dataset.tmSchedShowForm = 'false';
      return;
    }
    el.dataset.tmSchedShowForm = 'true';
    formContainer.innerHTML = renderForm();
    bindFormEvents();
  });

  // Refresh
  el.querySelector('[data-tm-sched-refresh]')?.addEventListener('click', async () => {
    showFeedback('Refreshing...');
    await store.loadSchedules();
    renderScheduleManager(el, store, api);
  });

  // Toggle enable/disable
  el.querySelectorAll('[data-tm-sched-toggle]').forEach(input => {
    input.addEventListener('change', async () => {
      const scheduleId = input.getAttribute('data-tm-sched-toggle');
      const enabled = input.checked;
      showFeedback(enabled ? 'Enabling...' : 'Disabling...');
      await store.toggleSchedule(scheduleId, enabled);
      showFeedback(enabled ? 'Enabled' : 'Disabled');
      renderScheduleManager(el, store, api);
    });
  });

  // Delete
  el.querySelectorAll('[data-tm-sched-delete]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const scheduleId = btn.getAttribute('data-tm-sched-delete');
      if (!confirm('Delete this schedule?')) return;
      showFeedback('Deleting...');
      await store.deleteSchedule(scheduleId);
      showFeedback('Deleted');
      renderScheduleManager(el, store, api);
    });
  });

  // Form events (if form is already visible on re-render)
  if (showForm) bindFormEvents();

  function bindFormEvents() {
    // Cron hint buttons
    el.querySelectorAll('.tm-cron-hint').forEach(hint => {
      hint.addEventListener('click', () => {
        const cronInput = el.querySelector('#tm-sched-cron');
        if (cronInput) cronInput.value = hint.getAttribute('data-cron') || '';
      });
    });

    // Submit
    el.querySelector('[data-tm-sched-submit]')?.addEventListener('click', async () => {
      const nameInput = el.querySelector('#tm-sched-name');
      const cronInput = el.querySelector('#tm-sched-cron');
      const actionInput = el.querySelector('#tm-sched-action');
      const approvalInput = el.querySelector('#tm-sched-approval');

      const name = nameInput?.value?.trim();
      const cron = cronInput?.value?.trim();
      const action = actionInput?.value || 'deploy';
      const requiresApproval = approvalInput?.checked || false;

      if (!name) { nameInput?.focus(); showFeedback('Name is required'); return; }
      if (!cron) { cronInput?.focus(); showFeedback('Cron expression is required'); return; }

      showFeedback('Creating schedule...');
      const result = await store.createSchedule(name, cron, action, requiresApproval);
      if (result) {
        showFeedback('Schedule created');
        el.dataset.tmSchedShowForm = 'false';
        renderScheduleManager(el, store, api);
      } else {
        showFeedback(store.error || 'Failed to create schedule');
      }
    });

    // Cancel
    el.querySelector('[data-tm-sched-cancel]')?.addEventListener('click', () => {
      el.dataset.tmSchedShowForm = 'false';
      formContainer.innerHTML = '';
    });
  }
}
