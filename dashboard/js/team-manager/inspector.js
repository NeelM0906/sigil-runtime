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

/** Action types available for pipeline steps */
const STEP_ACTION_TYPES = ['process', 'validate', 'transform', 'filter', 'aggregate', 'notify', 'custom'];

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
 * Renders pipeline steps into a container and wires up reorder/delete/add controls.
 * @param {HTMLElement} containerEl - The DOM element to render into
 * @param {Array} steps - Current steps array [{name, action, config}, ...]
 * @param {function} onUpdate - Callback receiving the updated steps array after any change
 */
function renderPipelineSteps(containerEl, steps, onUpdate) {
  let html = '<div class="tm-pipeline-steps-header">' +
    '<span class="tm-inspector-label" style="margin-bottom:0">Pipeline Steps</span>' +
    '<span class="tm-pipeline-step-count text-xs" style="color:hsl(var(--muted-foreground))">' +
    steps.length + (steps.length === 1 ? ' step' : ' steps') +
    '</span></div>';

  if (steps.length === 0) {
    html += '<div class="tm-pipeline-empty text-xs" style="color:hsl(var(--muted-foreground));padding:var(--space-2) 0">No steps defined. Add a step to get started.</div>';
  } else {
    html += '<div class="tm-pipeline-step-list">';
    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      html += `<div class="tm-pipeline-step" data-step-index="${i}">` +
        `<span class="tm-pipeline-step-num">${i + 1}.</span>` +
        `<span class="tm-pipeline-step-name" title="${escapeHtml(step.action || 'process')}">${escapeHtml(step.name || 'Untitled')}</span>` +
        '<span class="tm-pipeline-step-actions">' +
          `<button data-step-up="${i}" title="Move up"${i === 0 ? ' disabled' : ''}>&#9650;</button>` +
          `<button data-step-down="${i}" title="Move down"${i === steps.length - 1 ? ' disabled' : ''}>&#9660;</button>` +
          `<button data-step-delete="${i}" title="Delete step">&#10005;</button>` +
        '</span>' +
      '</div>';
    }
    html += '</div>';
  }

  html += '<button class="btn btn-sm btn-outline w-full mt-2" data-step-add>+ Add Step</button>';
  containerEl.innerHTML = html;

  // Bind move-up buttons
  containerEl.querySelectorAll('[data-step-up]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.getAttribute('data-step-up'), 10);
      if (idx <= 0) return;
      const updated = [...steps];
      [updated[idx - 1], updated[idx]] = [updated[idx], updated[idx - 1]];
      onUpdate(updated);
    });
  });

  // Bind move-down buttons
  containerEl.querySelectorAll('[data-step-down]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.getAttribute('data-step-down'), 10);
      if (idx >= steps.length - 1) return;
      const updated = [...steps];
      [updated[idx], updated[idx + 1]] = [updated[idx + 1], updated[idx]];
      onUpdate(updated);
    });
  });

  // Bind delete buttons
  containerEl.querySelectorAll('[data-step-delete]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.getAttribute('data-step-delete'), 10);
      const updated = steps.filter((_, i) => i !== idx);
      onUpdate(updated);
    });
  });

  // Bind add button
  const addBtn = containerEl.querySelector('[data-step-add]');
  if (addBtn) {
    addBtn.addEventListener('click', () => {
      const name = prompt('Step name:');
      if (!name || !name.trim()) return;
      const actionOptions = STEP_ACTION_TYPES.join(', ');
      const action = prompt(`Action type (${actionOptions}):`, 'process');
      if (!action || !action.trim()) return;
      const updated = [...steps, { name: name.trim(), action: action.trim(), config: {} }];
      onUpdate(updated);
    });
  }
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
  const isPipeline = kind === 'pipeline';

  // Pipeline steps state -- held in closure, survives re-renders of the step list
  let pipelineSteps = [];

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

      ${isPipeline ? '<div class="separator"></div><div class="tm-pipeline-steps" data-pipeline-steps></div>' : ''}

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

  // ── Pipeline steps: async load + render ──
  if (isPipeline) {
    const stepsContainer = el.querySelector('[data-pipeline-steps]');
    if (stepsContainer) {
      // Show loading state
      stepsContainer.innerHTML = '<span class="text-xs" style="color:hsl(var(--muted-foreground))">Loading steps...</span>';

      // Updater re-renders the step list and keeps local state in sync
      function updateSteps(newSteps) {
        pipelineSteps = newSteps;
        renderPipelineSteps(stepsContainer, pipelineSteps, updateSteps);
      }

      // Load existing pipeline data from the API
      store.loadPipeline(node.id).then(data => {
        if (data && Array.isArray(data.steps)) {
          pipelineSteps = data.steps;
        } else {
          pipelineSteps = [];
        }
        renderPipelineSteps(stepsContainer, pipelineSteps, updateSteps);
      }).catch(() => {
        pipelineSteps = [];
        renderPipelineSteps(stepsContainer, pipelineSteps, updateSteps);
      });
    }
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

    // Save node properties
    const result = await store.updateNode(node.id, changes);

    // If pipeline node, also persist the steps
    if (isPipeline && store.activeGraph) {
      const pipelineResult = await store.savePipeline(store.activeGraph.id, node.id, pipelineSteps);
      if (result && pipelineResult) {
        showFeedback('Saved');
      } else if (result && !pipelineResult) {
        showFeedback('Node saved, but pipeline steps failed', true);
      } else {
        showFeedback(store.error || 'Save failed', true);
      }
    } else {
      if (result) {
        showFeedback('Saved');
      } else {
        showFeedback(store.error || 'Save failed', true);
      }
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
