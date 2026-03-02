// Sigil Dashboard — Team Manager Variables Panel

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function maskSecret(value) {
  const str = String(value ?? '');
  if (str.length <= 3) return '***';
  return escapeHtml(str.slice(0, 3)) + '***';
}

function displayValue(variable) {
  if (variable.var_type === 'secret') return maskSecret(variable.value);
  return escapeHtml(String(variable.value ?? ''));
}

const VAR_TYPES = ['string', 'number', 'boolean', 'json', 'secret'];

/**
 * Render the variables panel inside the given element.
 * @param {HTMLElement} el - Container element
 * @param {import('./store.js').TeamManagerStore} store
 * @param {import('../api.js').SigilAPI} api
 */
export function renderVariablesPanel(el, store, api) {
  const variables = store.variables || [];
  const hasVars = variables.length > 0;

  el.innerHTML = `
    <div class="tm-var-header">
      <span class="text-xs font-semibold" style="text-transform:uppercase;letter-spacing:.06em;color:hsl(var(--muted-foreground))">Variables</span>
      <div class="flex gap-1">
        <button class="btn btn-sm btn-outline" data-var-action="add" style="height:1.375rem;font-size:var(--font-size-xs);padding:0 6px">+ Add</button>
        <button class="btn btn-sm btn-ghost" data-var-action="refresh" aria-label="Refresh variables" style="height:1.375rem;padding:0 4px">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
        </button>
      </div>
    </div>
    <div data-var-form-container></div>
    ${!hasVars ? `
      <div class="text-xs text-muted" style="padding:var(--space-2) 0;opacity:.6">No variables defined for this graph.</div>
    ` : `
      <table class="table" role="table" aria-label="Graph variables" style="font-size:var(--font-size-xs)">
        <thead>
          <tr>
            <th style="padding:var(--space-1)">Key</th>
            <th style="padding:var(--space-1)">Value</th>
            <th style="padding:var(--space-1)">Type</th>
            <th style="padding:var(--space-1)">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${variables.map(v => `
            <tr data-var-key="${escapeHtml(v.key)}">
              <td class="text-mono" style="padding:var(--space-1)">${escapeHtml(v.key)}</td>
              <td class="text-mono" style="padding:var(--space-1);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" data-var-value-cell>${displayValue(v)}</td>
              <td style="padding:var(--space-1)"><span class="badge badge-outline" style="font-size:10px">${escapeHtml(v.var_type || 'string')}</span></td>
              <td style="padding:var(--space-1)">
                <div class="flex gap-1">
                  <button class="btn btn-sm btn-ghost" data-var-action="edit" data-var-key="${escapeHtml(v.key)}" title="Edit variable" style="height:1.25rem;padding:0 3px;font-size:10px">Edit</button>
                  <button class="btn btn-sm btn-ghost" data-var-action="delete" data-var-key="${escapeHtml(v.key)}" title="Delete variable" style="height:1.25rem;padding:0 3px">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                  </button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `}
    <div data-var-feedback class="text-xs text-mono" style="opacity:.75;min-height:.875rem;margin-top:var(--space-1)"></div>
  `;

  // ── References ──
  const formContainer = el.querySelector('[data-var-form-container]');
  const feedbackEl = el.querySelector('[data-var-feedback]');

  function showFeedback(msg) {
    if (feedbackEl) feedbackEl.textContent = msg;
  }

  // ── Add variable form ──
  function showAddForm(prefill = null) {
    const isEdit = prefill !== null;
    const typeOptions = VAR_TYPES.map(t =>
      `<option value="${t}" ${(prefill?.var_type || 'string') === t ? 'selected' : ''}>${t}</option>`
    ).join('');

    formContainer.innerHTML = `
      <div class="tm-var-form">
        <input type="text" class="input" data-var-input="key" placeholder="Key" value="${escapeHtml(prefill?.key || '')}" style="width:100px;font-size:var(--font-size-xs);height:1.5rem;padding:0 6px" ${isEdit ? 'readonly' : ''}>
        <input type="${prefill?.var_type === 'secret' ? 'password' : 'text'}" class="input" data-var-input="value" placeholder="Value" value="${isEdit && prefill?.var_type !== 'secret' ? escapeHtml(String(prefill?.value ?? '')) : ''}" style="flex:1;font-size:var(--font-size-xs);height:1.5rem;padding:0 6px">
        <select class="input" data-var-input="type" style="width:80px;font-size:var(--font-size-xs);height:1.5rem;padding:0 4px">${typeOptions}</select>
        <button class="btn btn-sm" data-var-action="save" style="height:1.5rem;font-size:var(--font-size-xs);padding:0 8px">${isEdit ? 'Update' : 'Save'}</button>
        <button class="btn btn-sm btn-ghost" data-var-action="cancel" style="height:1.5rem;font-size:var(--font-size-xs);padding:0 6px">Cancel</button>
      </div>
    `;

    // Toggle password field when type changes
    const typeSelect = formContainer.querySelector('[data-var-input="type"]');
    const valueInput = formContainer.querySelector('[data-var-input="value"]');
    typeSelect.addEventListener('change', () => {
      valueInput.type = typeSelect.value === 'secret' ? 'password' : 'text';
    });

    // Save handler
    formContainer.querySelector('[data-var-action="save"]').addEventListener('click', async () => {
      const key = formContainer.querySelector('[data-var-input="key"]').value.trim();
      const value = formContainer.querySelector('[data-var-input="value"]').value;
      const varType = formContainer.querySelector('[data-var-input="type"]').value;

      if (!key) {
        showFeedback('Key is required');
        return;
      }

      // JSON validation
      if (varType === 'json') {
        try {
          JSON.parse(value);
        } catch {
          showFeedback('Invalid JSON value');
          return;
        }
      }

      // Number validation
      if (varType === 'number' && value !== '' && isNaN(Number(value))) {
        showFeedback('Invalid number value');
        return;
      }

      showFeedback('Saving...');
      const result = await store.setVariable(key, value, varType);
      if (result) {
        formContainer.innerHTML = '';
        showFeedback('Saved');
        renderVariablesPanel(el, store, api);
      } else {
        showFeedback(store.error || 'Save failed');
      }
    });

    // Cancel handler
    formContainer.querySelector('[data-var-action="cancel"]').addEventListener('click', () => {
      formContainer.innerHTML = '';
      showFeedback('');
    });

    // Focus the appropriate input
    const focusTarget = isEdit
      ? formContainer.querySelector('[data-var-input="value"]')
      : formContainer.querySelector('[data-var-input="key"]');
    focusTarget?.focus();
  }

  // ── Add button ──
  el.querySelector('[data-var-action="add"]')?.addEventListener('click', () => {
    showAddForm();
  });

  // ── Refresh button ──
  el.querySelector('[data-var-action="refresh"]')?.addEventListener('click', async () => {
    showFeedback('Refreshing...');
    await store.loadVariables();
    renderVariablesPanel(el, store, api);
  });

  // ── Edit buttons ──
  el.querySelectorAll('[data-var-action="edit"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.getAttribute('data-var-key');
      const variable = variables.find(v => v.key === key);
      if (variable) showAddForm(variable);
    });
  });

  // ── Delete buttons ──
  el.querySelectorAll('[data-var-action="delete"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const key = btn.getAttribute('data-var-key');
      if (!confirm(`Delete variable "${key}"?`)) return;
      showFeedback('Deleting...');
      await store.deleteVariable(key);
      renderVariablesPanel(el, store, api);
    });
  });
}
