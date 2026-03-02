// Sigil Dashboard — Team Manager Node Inspector

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

const NODE_COLORS = {
  human:    '#10b981',
  group:    '#8b5cf6',
  agent:    '#3b82f6',
  skill:    '#f59e0b',
  pipeline: '#ef4444',
  context:  '#06b6d4',
  note:     '#6b7280',
};

/** Field definitions per node kind */
const KIND_FIELDS = {
  human: [
    { key: 'user_id', label: 'User ID', type: 'text', placeholder: 'user-123' },
    { key: 'display_name', label: 'Display Name', type: 'text', placeholder: 'Jane Doe' },
    { key: 'role', label: 'Role', type: 'text', placeholder: 'operator' },
  ],
  group: [
    { key: 'group_name', label: 'Group Name', type: 'text', placeholder: 'engineering' },
    { key: 'member_ids', label: 'Member IDs', type: 'text', placeholder: 'user-1, user-2' },
    { key: 'role', label: 'Group Role', type: 'text', placeholder: 'reviewers' },
  ],
  agent: [
    { key: 'agent_id', label: 'Agent ID', type: 'text', placeholder: 'agent-alpha' },
    { key: 'model_id', label: 'Model ID', type: 'text', placeholder: 'anthropic/claude-opus-4.6' },
    { key: 'workspace_root', label: 'Workspace Root', type: 'text', placeholder: '/path/to/workspace' },
    { key: 'tool_profile', label: 'Tool Profile', type: 'select', options: ['full', 'minimal', 'readonly', 'none'] },
  ],
  skill: [
    { key: 'skill_id', label: 'Skill ID', type: 'text', placeholder: 'web_search' },
    { key: 'version', label: 'Version', type: 'text', placeholder: '1.0.0' },
  ],
  pipeline: [
    { key: 'pipeline_name', label: 'Pipeline Name', type: 'text', placeholder: 'data-ingest' },
    { key: 'trigger_type', label: 'Trigger', type: 'select', options: ['manual', 'cron', 'event', 'webhook'] },
  ],
  context: [
    { key: 'context_type', label: 'Context Type', type: 'select', options: ['memory', 'file', 'api', 'embedding'] },
    { key: 'source_ref', label: 'Source Reference', type: 'text', placeholder: '/path/or/url' },
  ],
  note: [
    { key: 'body', label: 'Note Content', type: 'textarea', placeholder: 'Enter notes...' },
  ],
};

function renderField(field, value) {
  const id = `tm-field-${field.key}`;
  const escapedVal = escapeHtml(value);

  if (field.type === 'textarea') {
    return `
      <div class="tm-inspector-field">
        <label class="tm-inspector-label" for="${id}">${escapeHtml(field.label)}</label>
        <textarea id="${id}" class="textarea tm-inspector-textarea" data-field="${escapeHtml(field.key)}" placeholder="${escapeHtml(field.placeholder || '')}">${escapedVal}</textarea>
      </div>`;
  }

  if (field.type === 'select') {
    const options = (field.options || []).map(opt => {
      const selected = opt === value ? ' selected' : '';
      return `<option value="${escapeHtml(opt)}"${selected}>${escapeHtml(opt)}</option>`;
    }).join('');
    return `
      <div class="tm-inspector-field">
        <label class="tm-inspector-label" for="${id}">${escapeHtml(field.label)}</label>
        <select id="${id}" class="select" data-field="${escapeHtml(field.key)}">
          <option value="">-- select --</option>
          ${options}
        </select>
      </div>`;
  }

  // Default: text input
  return `
    <div class="tm-inspector-field">
      <label class="tm-inspector-label" for="${id}">${escapeHtml(field.label)}</label>
      <input id="${id}" class="input" type="text" data-field="${escapeHtml(field.key)}" value="${escapedVal}" placeholder="${escapeHtml(field.placeholder || '')}"/>
    </div>`;
}

/**
 * Renders the node inspector into the given container.
 * @param {HTMLElement} el
 * @param {object} node
 * @param {import('./store.js').TeamManagerStore} store
 * @param {object} opts
 * @param {function} opts.onClose
 */
export function renderInspector(el, node, store, opts = {}) {
  if (!node) {
    el.innerHTML = '';
    el.classList.remove('tm-inspector--open');
    return;
  }

  el.classList.add('tm-inspector--open');
  const kind = node.kind || 'agent';
  const color = NODE_COLORS[kind] || '#6b7280';
  const fields = KIND_FIELDS[kind] || [];
  const config = node.config || {};

  el.innerHTML = `
    <div class="tm-inspector-panel">
      <div class="tm-inspector-header">
        <div class="flex items-center gap-2">
          <span class="tm-inspector-kind-dot" style="background:${color}"></span>
          <span class="tm-inspector-kind-label">${escapeHtml(kind)}</span>
        </div>
        <button class="btn btn-ghost btn-sm btn-icon" data-inspector-close aria-label="Close inspector">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>
      <div class="separator"></div>

      <div class="tm-inspector-field">
        <label class="tm-inspector-label" for="tm-field-label">Label</label>
        <input id="tm-field-label" class="input" type="text" data-field="label" value="${escapeHtml(node.label || '')}" placeholder="Node label"/>
      </div>

      ${fields.map(f => renderField(f, config[f.key] ?? '')).join('')}

      <div class="separator"></div>
      <div class="tm-inspector-meta">
        <div class="stat-row"><span class="stat-label">ID</span><span class="stat-value text-xs">${escapeHtml(node.id)}</span></div>
        <div class="stat-row"><span class="stat-label">Position</span><span class="stat-value text-xs">${Math.round(node.position_x)}, ${Math.round(node.position_y)}</span></div>
      </div>
      <div class="separator"></div>

      <div class="flex gap-2 mt-3">
        <button class="btn btn-sm flex-1" data-inspector-save>Save</button>
        <button class="btn btn-sm btn-outline flex-1" data-inspector-cancel>Cancel</button>
      </div>
      <button class="btn btn-sm btn-destructive w-full mt-2" data-inspector-delete>Delete Node</button>

      <div class="tm-inspector-feedback text-xs text-mono mt-2" style="opacity:.75"></div>
    </div>`;

  // ── Event bindings ──

  const feedbackEl = el.querySelector('.tm-inspector-feedback');

  function showFeedback(msg, isError = false) {
    if (!feedbackEl) return;
    feedbackEl.textContent = msg;
    feedbackEl.style.color = isError ? 'hsl(var(--destructive))' : 'hsl(var(--success))';
  }

  // Close
  el.querySelector('[data-inspector-close]').addEventListener('click', () => {
    if (opts.onClose) opts.onClose();
  });

  // Cancel
  el.querySelector('[data-inspector-cancel]').addEventListener('click', () => {
    if (opts.onClose) opts.onClose();
  });

  // Save
  el.querySelector('[data-inspector-save]').addEventListener('click', async () => {
    const changes = {};
    const labelInput = el.querySelector('[data-field="label"]');
    if (labelInput) changes.label = labelInput.value;

    const configChanges = {};
    for (const field of fields) {
      const input = el.querySelector(`[data-field="${field.key}"]`);
      if (input) {
        configChanges[field.key] = input.value;
      }
    }
    changes.config = { ...(node.config || {}), ...configChanges };

    showFeedback('Saving...');
    const result = await store.updateNode(node.id, changes);
    if (result) {
      showFeedback('Saved');
    } else {
      showFeedback(store.error || 'Save failed', true);
    }
  });

  // Delete
  el.querySelector('[data-inspector-delete]').addEventListener('click', async () => {
    if (!confirm(`Delete node "${node.label || node.id}"?`)) return;
    showFeedback('Deleting...');
    await store.deleteNode(node.id);
    showFeedback('Deleted');
    if (opts.onClose) opts.onClose();
  });
}
