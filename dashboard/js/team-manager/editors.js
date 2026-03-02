// Sigil Dashboard -- Team Manager Rich Node Editors
// Vanilla ES6 module. No React, no npm. Renders to DOM elements.

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

/** Returns a debounced version of `fn`. Calling `.cancel()` on the result clears the pending timer. */
function debounce(fn, ms) {
  let timer = null;
  const wrapper = (...args) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { timer = null; fn(...args); }, ms);
  };
  wrapper.cancel = () => { if (timer) { clearTimeout(timer); timer = null; } };
  return wrapper;
}

/** Create a standard DOM element with optional attributes and children. */
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'style' && typeof v === 'object') {
      Object.assign(el.style, v);
    } else if (k.startsWith('on') && typeof v === 'function') {
      el.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (k === 'className') {
      el.className = v;
    } else if (k === 'htmlFor') {
      el.setAttribute('for', v);
    } else if (v === true) {
      el.setAttribute(k, '');
    } else if (v !== false && v != null) {
      el.setAttribute(k, String(v));
    }
  }
  for (const child of children) {
    if (child == null) continue;
    if (typeof child === 'string') {
      el.appendChild(document.createTextNode(child));
    } else if (Array.isArray(child)) {
      child.forEach(c => { if (c) el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    } else {
      el.appendChild(child);
    }
  }
  return el;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MODEL_OPTIONS = [
  { value: '', label: '(Default)' },
  { value: 'claude-sonnet-4-5-20250929', label: 'claude-sonnet-4-5-20250929' },
  { value: 'claude-opus-4-6', label: 'claude-opus-4-6' },
  { value: 'claude-haiku-4-5-20251001', label: 'claude-haiku-4-5-20251001' },
];

const PERMISSION_OPTIONS = [
  { value: '', label: '(Default)' },
  { value: 'default', label: 'default' },
  { value: 'acceptEdits', label: 'acceptEdits' },
  { value: 'bypassPermissions', label: 'bypassPermissions' },
  { value: 'plan', label: 'plan' },
  { value: 'dontAsk', label: 'dontAsk' },
];

const KIND_BADGE_COLORS = {
  agent: 'var(--accent-orange, #f97316)',
  skill: 'var(--accent-green, #22c55e)',
  group: 'var(--accent-blue, #3b82f6)',
  context: 'var(--accent-purple, #a855f7)',
  pipeline: '#d946ef',
  human: 'var(--accent-gold, #eab308)',
  settings: 'var(--accent-gray, #6b7280)',
};

const PIPELINE_ACCENT = '#d946ef';

const AUTOSAVE_DELAY = 800;

// ---------------------------------------------------------------------------
// createTagInput
// ---------------------------------------------------------------------------

/**
 * Renders a tag-input component into `containerEl`.
 * @param {HTMLElement} containerEl - parent element to render into (cleared first)
 * @param {string[]} tags - current tags
 * @param {(newTags: string[]) => void} onUpdate - called when tags change
 */
function createTagInput(containerEl, tags, onUpdate) {
  containerEl.innerHTML = '';
  containerEl.className = 'tm-editor-tag-input';

  // Render existing pills
  tags.forEach(tag => {
    const pill = h('span', { className: 'tm-tag' },
      tag,
      h('button', {
        className: 'tm-tag-remove',
        type: 'button',
        onClick: () => {
          const next = tags.filter(t => t !== tag);
          onUpdate(next);
        },
      }, '\u00d7'),
    );
    containerEl.appendChild(pill);
  });

  // Input field
  const input = h('input', {
    type: 'text',
    className: 'tm-tag-input-field',
    placeholder: tags.length === 0 ? 'Type and press Enter' : '',
    'data-field': 'tag-input',
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const val = input.value.trim();
      if (val && !tags.includes(val)) {
        onUpdate([...tags, val]);
      } else {
        // Re-render to clear input even if duplicate
        createTagInput(containerEl, tags, onUpdate);
      }
      return;
    }
    if (e.key === 'Backspace' && input.value === '' && tags.length > 0) {
      onUpdate(tags.slice(0, -1));
    }
  });

  containerEl.appendChild(input);
  return containerEl;
}

// ---------------------------------------------------------------------------
// Shared UI builders
// ---------------------------------------------------------------------------

function makeLabel(text) {
  return h('label', { className: 'tm-editor-label' }, text);
}

function makeField(...children) {
  return h('div', { className: 'tm-editor-field' }, ...children);
}

function makeSectionHeader(text, opts = {}) {
  const { count, collapsed, onToggle } = opts;
  const arrow = collapsed ? '\u25b8' : '\u25be';
  const countBadge = count != null
    ? h('span', { className: 'tm-editor-section-count' }, String(count))
    : null;

  const header = h('div', {
    className: 'tm-editor-section-header',
    style: onToggle ? { cursor: 'pointer', userSelect: 'none' } : {},
    onClick: onToggle || null,
  },
    onToggle ? h('span', { className: 'tm-editor-section-arrow' }, arrow) : null,
    h('span', {}, text),
    countBadge,
  );
  return header;
}

function makeTextInput(value, attrs = {}) {
  return h('input', {
    type: 'text',
    className: 'tm-editor-input',
    value: value ?? '',
    ...attrs,
  });
}

function makeNumberInput(value, attrs = {}) {
  return h('input', {
    type: 'number',
    className: 'tm-editor-input',
    value: value ?? 0,
    ...attrs,
  });
}

function makeTextarea(value, attrs = {}) {
  return h('textarea', {
    className: 'tm-editor-textarea',
    ...attrs,
  }, value ?? '');
}

function makeSelect(value, options, attrs = {}) {
  const sel = h('select', { className: 'tm-editor-select', ...attrs },
    ...options.map(opt => {
      const optEl = h('option', { value: opt.value }, opt.label);
      if (opt.value === value) optEl.selected = true;
      return optEl;
    }),
  );
  return sel;
}

function makeButton(text, attrs = {}) {
  return h('button', {
    type: 'button',
    className: 'tm-editor-btn',
    ...attrs,
  }, text);
}

// ---------------------------------------------------------------------------
// renderAgentEditor
// ---------------------------------------------------------------------------

/**
 * Renders the full agent editor into `el`.
 * @param {HTMLElement} el
 * @param {object} node
 * @param {import('./store.js').TeamManagerStore} store
 * @param {import('../api.js').SigilAPI} api
 */
function renderAgentEditor(el, node, store, api) {
  el.innerHTML = '';

  const config = node.config || {};

  // Local mutable state
  const state = {
    name: config.name ?? node.label ?? node.name ?? '',
    description: config.description ?? '',
    model: config.model ?? '',
    permissionMode: config.permissionMode ?? '',
    maxTurns: config.maxTurns ?? 0,
    tools: Array.isArray(config.tools) ? [...config.tools] : [],
    disallowedTools: Array.isArray(config.disallowedTools) ? [...config.disallowedTools] : [],
    skills: Array.isArray(config.skills) ? [...config.skills] : [],
    color: config.color ?? '',
    promptBody: node.promptBody ?? config.promptBody ?? '',
  };

  // Snapshot for discard
  const snapshot = JSON.parse(JSON.stringify(state));

  // Autosave debounced
  const autosave = debounce(() => {
    const updatedConfig = { name: state.name };
    if (state.description) updatedConfig.description = state.description;
    if (state.model) updatedConfig.model = state.model;
    if (state.permissionMode) updatedConfig.permissionMode = state.permissionMode;
    if (state.maxTurns) updatedConfig.maxTurns = state.maxTurns;
    if (state.tools.length) updatedConfig.tools = state.tools;
    if (state.disallowedTools.length) updatedConfig.disallowedTools = state.disallowedTools;
    if (state.skills.length) updatedConfig.skills = state.skills;
    if (state.color) updatedConfig.color = state.color;

    store.updateNode(node.id, {
      label: state.name,
      config: { ...(node.config || {}), ...updatedConfig },
      promptBody: state.promptBody,
    });
  }, AUTOSAVE_DELAY);

  function triggerSave() { autosave(); }

  // --- Identity Section ---
  el.appendChild(makeSectionHeader('Identity'));

  // Name
  const nameInput = makeTextInput(state.name, { 'data-field': 'name' });
  nameInput.addEventListener('input', () => { state.name = nameInput.value; triggerSave(); });
  el.appendChild(makeField(makeLabel('Name'), nameInput));

  // Description + Generate button
  const descRow = h('div', { className: 'tm-editor-label-row' },
    makeLabel('Description'),
  );
  const generateBtn = makeButton('Generate', {
    className: 'tm-editor-btn tm-editor-btn--generate',
    disabled: !state.name.trim(),
  });
  let generating = false;
  generateBtn.addEventListener('click', async () => {
    if (generating || !state.name.trim()) return;
    generating = true;
    generateBtn.textContent = 'Generating...';
    generateBtn.disabled = true;
    try {
      const result = await api.chat('tm-generate', `Generate a concise 1-2 sentence description for a Claude Code agent named "${state.name}". Only output the description text, nothing else.`);
      const text = (result && (result.reply || result.response || result.message || '')).trim();
      if (text) {
        state.description = text;
        descTextarea.value = text;
        triggerSave();
      }
    } catch (err) {
      console.error('Generate description failed:', err);
    }
    generating = false;
    generateBtn.textContent = 'Generate';
    generateBtn.disabled = !state.name.trim();
  });
  descRow.appendChild(generateBtn);

  const descTextarea = makeTextarea(state.description, { rows: '3', 'data-field': 'description' });
  descTextarea.addEventListener('input', () => { state.description = descTextarea.value; triggerSave(); });
  el.appendChild(makeField(descRow, descTextarea));

  // --- Behavior Section ---
  el.appendChild(makeSectionHeader('Behavior'));

  // Model
  const modelSelect = makeSelect(state.model, MODEL_OPTIONS, { 'data-field': 'model' });
  modelSelect.addEventListener('change', () => { state.model = modelSelect.value; triggerSave(); });
  el.appendChild(makeField(makeLabel('Model'), modelSelect));

  // Permission Mode
  const permSelect = makeSelect(state.permissionMode, PERMISSION_OPTIONS, { 'data-field': 'permissionMode' });
  permSelect.addEventListener('change', () => { state.permissionMode = permSelect.value; triggerSave(); });
  el.appendChild(makeField(makeLabel('Permission Mode'), permSelect));

  // Max Turns
  const maxTurnsInput = makeNumberInput(state.maxTurns, { min: '0', 'data-field': 'maxTurns' });
  maxTurnsInput.addEventListener('input', () => { state.maxTurns = Number(maxTurnsInput.value) || 0; triggerSave(); });
  el.appendChild(makeField(makeLabel('Max Turns'), maxTurnsInput));

  // --- Capabilities Section ---
  el.appendChild(makeSectionHeader('Capabilities'));

  // Tools
  const toolsContainer = h('div', { 'data-field': 'tools' });
  function renderTools() {
    createTagInput(toolsContainer, state.tools, (next) => {
      state.tools = next;
      triggerSave();
      renderTools();
    });
  }
  renderTools();
  el.appendChild(makeField(makeLabel('Tools'), toolsContainer));

  // Disallowed Tools
  const disallowedContainer = h('div', { 'data-field': 'disallowedTools' });
  function renderDisallowed() {
    createTagInput(disallowedContainer, state.disallowedTools, (next) => {
      state.disallowedTools = next;
      triggerSave();
      renderDisallowed();
    });
  }
  renderDisallowed();
  el.appendChild(makeField(makeLabel('Disallowed Tools'), disallowedContainer));

  // Skills
  const skillsContainer = h('div', { 'data-field': 'skills' });
  function renderSkills() {
    createTagInput(skillsContainer, state.skills, (next) => {
      state.skills = next;
      triggerSave();
      renderSkills();
    });
  }
  renderSkills();
  el.appendChild(makeField(makeLabel('Skills'), skillsContainer));

  // --- Appearance Section ---
  el.appendChild(makeSectionHeader('Appearance'));

  // Color
  const colorRow = h('div', { className: 'tm-editor-color-row' });
  const colorInput = makeTextInput(state.color, { 'data-field': 'color', placeholder: '#4a9eff' });
  const colorSwatch = h('div', {
    className: 'tm-editor-color-swatch',
    style: { background: state.color || '#4a9eff' },
  });
  colorInput.addEventListener('input', () => {
    state.color = colorInput.value;
    colorSwatch.style.background = colorInput.value || '#4a9eff';
    triggerSave();
  });
  colorRow.appendChild(colorInput);
  colorRow.appendChild(colorSwatch);
  el.appendChild(makeField(makeLabel('Color'), colorRow));

  // --- Prompt Body ---
  el.appendChild(makeSectionHeader('Prompt'));

  const promptTextarea = makeTextarea(state.promptBody, {
    'data-field': 'promptBody',
    className: 'tm-editor-textarea tm-editor-textarea--prompt',
  });
  promptTextarea.addEventListener('input', () => { state.promptBody = promptTextarea.value; triggerSave(); });
  el.appendChild(makeField(promptTextarea));

  // --- Discard button ---
  const discardBtn = makeButton('Discard', { className: 'tm-editor-btn tm-editor-btn--discard' });
  discardBtn.addEventListener('click', () => {
    autosave.cancel();
    Object.assign(state, JSON.parse(JSON.stringify(snapshot)));
    // Re-render
    renderAgentEditor(el, node, store, api);
  });
  el.appendChild(h('div', { className: 'tm-editor-actions' }, discardBtn));
}

// ---------------------------------------------------------------------------
// renderGroupEditor
// ---------------------------------------------------------------------------

/**
 * Renders the group/team editor into `el`.
 * @param {HTMLElement} el
 * @param {object} node
 * @param {import('./store.js').TeamManagerStore} store
 * @param {import('../api.js').SigilAPI} api
 */
function renderGroupEditor(el, node, store, api) {
  el.innerHTML = '';

  const config = node.config || {};

  // Determine if this is a nested member or a top-level team
  const parentNode = node.parentId ? store.nodes.find(n => n.id === node.parentId) : null;
  const isMember = parentNode && parentNode.kind === 'group';

  const state = {
    name: node.label ?? node.name ?? config.name ?? '',
    description: node.promptBody ?? config.description ?? '',
  };
  const snapshot = JSON.parse(JSON.stringify(state));

  const autosave = debounce(() => {
    store.updateNode(node.id, {
      label: state.name,
      promptBody: state.description,
    });
  }, AUTOSAVE_DELAY);

  function triggerSave() { autosave(); }

  // --- Name ---
  const nameInput = makeTextInput(state.name, { 'data-field': 'name' });
  nameInput.addEventListener('input', () => { state.name = nameInput.value; triggerSave(); });
  el.appendChild(makeField(makeLabel('Name'), nameInput));

  // --- Description + Generate ---
  const descLabelRow = h('div', { className: 'tm-editor-label-row' }, makeLabel('Description'));
  const genBtn = makeButton('Generate', { className: 'tm-editor-btn tm-editor-btn--generate' });
  let generating = false;
  genBtn.addEventListener('click', async () => {
    if (generating || !state.name.trim()) return;
    generating = true;
    genBtn.textContent = 'Generating...';
    genBtn.disabled = true;
    try {
      const context = isMember
        ? `This is an agent named "${state.name}" that is part of the team "${parentNode.label || parentNode.name || 'unknown'}".`
        : `This is a team named "${state.name}" that manages AI agents.`;
      const result = await api.chat('tm-generate', `${context}\n\nWrite a concise 1-2 sentence description for this ${isMember ? 'agent' : 'team'} based on its name. Be specific. Only output the description text, nothing else.`);
      const text = (result && (result.reply || result.response || result.message || '')).trim();
      if (text) {
        state.description = text;
        descTextarea.value = text;
        triggerSave();
      }
    } catch (err) {
      console.error('Generate description failed:', err);
    }
    generating = false;
    genBtn.textContent = 'Generate';
    genBtn.disabled = false;
  });
  descLabelRow.appendChild(genBtn);

  const descTextarea = makeTextarea(state.description, { rows: '3', 'data-field': 'description' });
  descTextarea.addEventListener('input', () => { state.description = descTextarea.value; triggerSave(); });
  el.appendChild(makeField(descLabelRow, descTextarea));

  // --- Deploy section (top-level teams only) ---
  if (!isMember) {
    el.appendChild(makeSectionHeader('Deploy'));

    const deployPromptTextarea = makeTextarea('', {
      rows: '2',
      placeholder: 'What should this team accomplish?',
      'data-field': 'deployPrompt',
    });
    el.appendChild(makeField(
      h('label', { className: 'tm-editor-label', style: { fontSize: '10px' } }, 'Deploy Prompt'),
      deployPromptTextarea,
    ));

    const deployBtnRow = h('div', { className: 'tm-editor-deploy-row' });

    const deployBtn = makeButton('Deploy Team', {
      className: 'tm-editor-btn tm-editor-btn--deploy',
    });
    let deploying = false;
    deployBtn.addEventListener('click', async () => {
      if (deploying || !store.activeGraph) return;
      deploying = true;
      deployBtn.textContent = 'Deploying...';
      deployBtn.disabled = true;
      try {
        await store.deployGraph(store.activeGraph.id);
      } catch (err) {
        console.error('Deploy failed:', err);
      }
      deploying = false;
      deployBtn.textContent = 'Deploy Team';
      deployBtn.disabled = false;
    });

    const scheduleBtn = makeButton('Schedule', {
      className: 'tm-editor-btn tm-editor-btn--schedule',
    });
    scheduleBtn.addEventListener('click', () => {
      // Placeholder -- integrates with schedule panel
      console.log('Schedule requested for team', node.id);
    });

    deployBtnRow.appendChild(deployBtn);
    deployBtnRow.appendChild(scheduleBtn);
    el.appendChild(deployBtnRow);
  }

  // --- Skills & Variables (collapsible) ---
  const assignedSkills = Array.isArray(node.assignedSkills) ? node.assignedSkills : [];
  const availableSkillNodes = store.nodes.filter(n => n.kind === 'skill');
  let skillsSectionOpen = assignedSkills.length > 0 || availableSkillNodes.length > 0;

  const skillsBody = h('div', { className: 'tm-editor-collapsible-body' });

  function renderSkillsSection() {
    const header = makeSectionHeader('Skills & Variables', {
      count: assignedSkills.length,
      collapsed: !skillsSectionOpen,
      onToggle: () => {
        skillsSectionOpen = !skillsSectionOpen;
        skillsBody.style.display = skillsSectionOpen ? '' : 'none';
        renderSkillsSection();
      },
    });

    // Replace the previous header if it exists
    const existingHeader = el.querySelector('[data-section="skills-header"]');
    if (existingHeader) {
      existingHeader.replaceWith(header);
    } else {
      el.appendChild(header);
    }
    header.setAttribute('data-section', 'skills-header');
  }

  function renderSkillsBody() {
    skillsBody.innerHTML = '';
    skillsBody.style.display = skillsSectionOpen ? '' : 'none';

    // Assigned skills list
    if (assignedSkills.length === 0) {
      skillsBody.appendChild(h('div', { className: 'tm-editor-empty' }, 'No skills assigned'));
    } else {
      assignedSkills.forEach((skillId, idx) => {
        const skillNode = store.nodes.find(n => n.id === skillId);
        const skillName = skillNode ? (skillNode.label || skillNode.name) : skillId;
        const skillDesc = skillNode ? (skillNode.promptBody || '') : '';

        const row = h('div', { className: 'tm-editor-skill-row' },
          h('div', { className: 'tm-editor-skill-info' },
            h('div', { className: 'tm-editor-skill-name' }, skillName),
            skillDesc ? h('div', { className: 'tm-editor-skill-desc' }, skillDesc.slice(0, 120)) : null,
          ),
          h('button', {
            type: 'button',
            className: 'tm-editor-btn-icon',
            title: 'Remove skill',
            onClick: () => {
              assignedSkills.splice(idx, 1);
              store.updateNode(node.id, { assignedSkills: [...assignedSkills] });
              renderSkillsBody();
            },
          }, '\u00d7'),
        );
        skillsBody.appendChild(row);
      });
    }

    // Add skill dropdown
    const unassigned = availableSkillNodes.filter(s => !assignedSkills.includes(s.id));
    if (unassigned.length > 0) {
      const addRow = h('div', { className: 'tm-editor-add-skill-row' });
      const skillSelect = makeSelect('', [
        { value: '', label: 'Select a skill...' },
        ...unassigned.map(s => ({ value: s.id, label: s.label || s.name || s.id })),
      ]);
      const addBtn = makeButton('Add Skill', { className: 'tm-editor-btn tm-editor-btn--small', disabled: true });
      skillSelect.addEventListener('change', () => { addBtn.disabled = !skillSelect.value; });
      addBtn.addEventListener('click', () => {
        if (!skillSelect.value) return;
        assignedSkills.push(skillSelect.value);
        store.updateNode(node.id, { assignedSkills: [...assignedSkills] });
        renderSkillsBody();
      });
      addRow.appendChild(skillSelect);
      addRow.appendChild(addBtn);
      skillsBody.appendChild(addRow);
    }

    // Inline create skill form
    const createToggle = makeButton('Create & Assign', { className: 'tm-editor-btn tm-editor-btn--outline tm-editor-btn--small' });
    let showCreateForm = false;
    const createFormContainer = h('div', {});

    createToggle.addEventListener('click', () => {
      showCreateForm = !showCreateForm;
      if (showCreateForm) {
        createFormContainer.innerHTML = '';
        const form = h('div', { className: 'tm-editor-create-skill-form' },
          h('div', { className: 'tm-editor-create-skill-title' }, 'Create New Skill'),
          makeTextInput('', { placeholder: 'Skill name (e.g. deploy-app)', 'data-field': 'newSkillName' }),
          makeTextarea('', { rows: '2', placeholder: 'Short description...', 'data-field': 'newSkillDesc' }),
          h('div', { className: 'tm-editor-create-skill-actions' },
            makeButton('Create & Assign', {
              className: 'tm-editor-btn tm-editor-btn--create',
              onClick: async () => {
                const nameEl = createFormContainer.querySelector('[data-field="newSkillName"]');
                const descEl = createFormContainer.querySelector('[data-field="newSkillDesc"]');
                const skillName = (nameEl?.value || '').trim();
                const skillDesc = (descEl?.value || '').trim();
                if (!skillName) return;
                const newNode = await store.addNode('skill', skillName, 0, 0, { description: skillDesc });
                if (newNode) {
                  assignedSkills.push(newNode.id);
                  store.updateNode(node.id, { assignedSkills: [...assignedSkills] });
                }
                showCreateForm = false;
                renderSkillsBody();
              },
            }),
            makeButton('Cancel', {
              className: 'tm-editor-btn tm-editor-btn--outline tm-editor-btn--small',
              onClick: () => { showCreateForm = false; createFormContainer.innerHTML = ''; },
            }),
          ),
        );
        createFormContainer.appendChild(form);
      } else {
        createFormContainer.innerHTML = '';
      }
    });

    skillsBody.appendChild(createToggle);
    skillsBody.appendChild(createFormContainer);
  }

  renderSkillsSection();
  renderSkillsBody();
  el.appendChild(skillsBody);

  // --- Agents section (collapsible) ---
  const children = store.nodes.filter(n => n.parentId === node.id);
  let agentsSectionOpen = true;

  const agentsBody = h('div', { className: 'tm-editor-collapsible-body' });

  function renderAgentsSection() {
    const header = makeSectionHeader('Agents', {
      count: children.length,
      collapsed: !agentsSectionOpen,
      onToggle: () => {
        agentsSectionOpen = !agentsSectionOpen;
        agentsBody.style.display = agentsSectionOpen ? '' : 'none';
        // Re-render header to update arrow
        const newHeader = makeSectionHeader('Agents', {
          count: children.length,
          collapsed: !agentsSectionOpen,
          onToggle: () => {
            agentsSectionOpen = !agentsSectionOpen;
            agentsBody.style.display = agentsSectionOpen ? '' : 'none';
            renderAgentsSection();
          },
        });
        newHeader.setAttribute('data-section', 'agents-header');
        const current = el.querySelector('[data-section="agents-header"]');
        if (current) current.replaceWith(newHeader);
      },
    });
    header.setAttribute('data-section', 'agents-header');

    const existing = el.querySelector('[data-section="agents-header"]');
    if (existing) {
      existing.replaceWith(header);
    } else {
      el.appendChild(header);
    }
  }

  function renderAgentsBody() {
    agentsBody.innerHTML = '';
    agentsBody.style.display = agentsSectionOpen ? '' : 'none';

    // Generate Agents row
    const genRow = h('div', { className: 'tm-editor-generate-agents-row' });
    const countInput = makeNumberInput(3, { min: '1', max: '10', style: { width: '70px', textAlign: 'center' } });
    const genAgentsBtn = makeButton('Generate Agents', { className: 'tm-editor-btn tm-editor-btn--generate' });
    let autoFilling = false;
    genAgentsBtn.addEventListener('click', async () => {
      if (autoFilling || !state.name.trim()) return;
      autoFilling = true;
      genAgentsBtn.textContent = 'Generating...';
      genAgentsBtn.disabled = true;
      try {
        const count = Math.max(1, Math.min(10, Number(countInput.value) || 3));
        const context = isMember
          ? `an agent named "${state.name}" in team "${parentNode?.label || parentNode?.name || 'unknown'}"`
          : `a team named "${state.name}" with description: "${state.description}"`;
        const result = await api.chat('tm-generate', `Generate exactly ${count} AI agent team members for ${context}.\n\nReturn ONLY valid JSON:\n{"agents":[{"name":"Agent Name","description":"What this agent does"}]}\n\nMake names descriptive.`);
        const text = (result && (result.reply || result.response || result.message || '')).trim();
        const jsonMatch = text.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          if (Array.isArray(parsed.agents)) {
            for (const agent of parsed.agents) {
              await store.addNode('agent', agent.name, 0, 0, { description: agent.description, parentId: node.id });
            }
            // Re-render agents body
            const updatedChildren = store.nodes.filter(n => n.parentId === node.id);
            children.length = 0;
            children.push(...updatedChildren);
            renderAgentsBody();
          }
        }
      } catch (err) {
        console.error('Auto-fill agents failed:', err);
      }
      autoFilling = false;
      genAgentsBtn.textContent = 'Generate Agents';
      genAgentsBtn.disabled = false;
    });
    genRow.appendChild(h('div', {}, h('label', { className: 'tm-editor-label', style: { fontSize: '10px' } }, 'Count'), countInput));
    genRow.appendChild(genAgentsBtn);
    agentsBody.appendChild(genRow);

    // Agent list
    if (children.length === 0) {
      agentsBody.appendChild(h('div', { className: 'tm-editor-empty' }, 'No agents yet'));
    } else {
      children.forEach(child => {
        const badgeColor = KIND_BADGE_COLORS[child.kind] || 'var(--text-secondary, #6b7280)';
        const row = h('div', {
          className: 'tm-editor-agent-row',
          onClick: () => { store.selectNode(child.id); },
        },
          h('span', {
            className: 'tm-editor-kind-badge',
            style: { background: badgeColor },
          }, child.kind),
          h('span', { className: 'tm-editor-agent-name' }, child.label || child.name || child.id),
        );
        agentsBody.appendChild(row);
      });
    }

    // Add Agent button
    const addAgentBtn = makeButton('+ Add Agent', { className: 'tm-editor-btn tm-editor-btn--dashed' });
    addAgentBtn.addEventListener('click', async () => {
      const label = prompt('Agent name:');
      if (!label || !label.trim()) return;
      await store.addNode('agent', label.trim(), 0, 0, { parentId: node.id });
      const updatedChildren = store.nodes.filter(n => n.parentId === node.id);
      children.length = 0;
      children.push(...updatedChildren);
      renderAgentsBody();
    });
    agentsBody.appendChild(addAgentBtn);
  }

  renderAgentsSection();
  renderAgentsBody();
  el.appendChild(agentsBody);

  // --- Discard ---
  const discardBtn = makeButton('Discard', { className: 'tm-editor-btn tm-editor-btn--discard' });
  discardBtn.addEventListener('click', () => {
    autosave.cancel();
    Object.assign(state, JSON.parse(JSON.stringify(snapshot)));
    renderGroupEditor(el, node, store, api);
  });
  el.appendChild(h('div', { className: 'tm-editor-actions', style: { marginTop: '24px' } }, discardBtn));
}

// ---------------------------------------------------------------------------
// renderPipelineEditor
// ---------------------------------------------------------------------------

/**
 * Renders the pipeline editor into `el`.
 * @param {HTMLElement} el
 * @param {object} node
 * @param {import('./store.js').TeamManagerStore} store
 * @param {import('../api.js').SigilAPI} api
 */
function renderPipelineEditor(el, node, store, api) {
  el.innerHTML = '';

  const config = node.config || {};

  const state = {
    name: node.label ?? node.name ?? config.name ?? '',
    description: node.promptBody ?? config.description ?? '',
    steps: Array.isArray(node.pipelineSteps) ? node.pipelineSteps.map(s => ({ ...s })) : [],
  };
  const snapshot = JSON.parse(JSON.stringify(state));

  const autosave = debounce(() => {
    store.updateNode(node.id, {
      label: state.name,
      promptBody: state.description,
    });
  }, AUTOSAVE_DELAY);

  function triggerSave() { autosave(); }

  function saveSteps() {
    if (store.activeGraph) {
      store.savePipeline(store.activeGraph.id, node.id, state.steps);
    }
  }

  // Available teams: root-level group nodes
  const availableTeams = store.nodes
    .filter(n => n.kind === 'group' && (!n.parentId || n.parentId === 'root'))
    .sort((a, b) => (a.label || a.name || '').localeCompare(b.label || b.name || ''));

  // --- Name ---
  const nameInput = makeTextInput(state.name, { 'data-field': 'name' });
  nameInput.addEventListener('input', () => { state.name = nameInput.value; triggerSave(); });
  el.appendChild(makeField(makeLabel('Name'), nameInput));

  // --- Description ---
  const descTextarea = makeTextarea(state.description, { rows: '3', 'data-field': 'description' });
  descTextarea.addEventListener('input', () => { state.description = descTextarea.value; triggerSave(); });
  el.appendChild(makeField(makeLabel('Description'), descTextarea));

  // --- Pipeline Steps ---
  el.appendChild(makeSectionHeader('Pipeline Steps'));

  const stepsContainer = h('div', { className: 'tm-editor-steps-container' });

  function renderSteps() {
    stepsContainer.innerHTML = '';

    if (state.steps.length === 0) {
      stepsContainer.appendChild(h('div', { className: 'tm-editor-empty' }, 'No steps yet. Add a step to get started.'));
    }

    state.steps.forEach((step, index) => {
      const card = h('div', { className: 'tm-editor-step-card' });

      // Header: number badge + team dropdown
      const headerRow = h('div', { className: 'tm-editor-step-header' });

      // Number badge
      const badge = h('span', { className: 'tm-editor-step-badge' }, String(index + 1));
      headerRow.appendChild(badge);

      // Team dropdown
      const teamSelect = makeSelect(step.teamId || '', [
        { value: '', label: 'Select a team...' },
        ...availableTeams.map(t => ({ value: t.id, label: t.label || t.name || t.id })),
      ], { style: { flex: '1' } });
      teamSelect.addEventListener('change', () => {
        state.steps[index].teamId = teamSelect.value;
        saveSteps();
      });
      headerRow.appendChild(teamSelect);
      card.appendChild(headerRow);

      // Prompt textarea
      const promptTA = makeTextarea(step.prompt || '', {
        rows: '2',
        placeholder: 'What should this team do?',
      });
      promptTA.addEventListener('input', () => {
        state.steps[index].prompt = promptTA.value;
        saveSteps();
      });
      card.appendChild(promptTA);

      // Action buttons
      const actions = h('div', { className: 'tm-editor-step-actions' });

      const upBtn = makeButton('\u2191 Up', { className: 'tm-editor-btn tm-editor-btn--step-action', disabled: index === 0 });
      upBtn.addEventListener('click', () => {
        if (index <= 0) return;
        [state.steps[index - 1], state.steps[index]] = [state.steps[index], state.steps[index - 1]];
        saveSteps();
        renderSteps();
      });

      const downBtn = makeButton('\u2193 Down', { className: 'tm-editor-btn tm-editor-btn--step-action', disabled: index === state.steps.length - 1 });
      downBtn.addEventListener('click', () => {
        if (index >= state.steps.length - 1) return;
        [state.steps[index], state.steps[index + 1]] = [state.steps[index + 1], state.steps[index]];
        saveSteps();
        renderSteps();
      });

      const dupBtn = makeButton('\u229e Duplicate', { className: 'tm-editor-btn tm-editor-btn--step-action' });
      dupBtn.addEventListener('click', () => {
        const copy = { id: 'step-' + Date.now(), teamId: step.teamId, prompt: step.prompt };
        state.steps.splice(index + 1, 0, copy);
        saveSteps();
        renderSteps();
      });

      const delBtn = makeButton('\u00d7 Delete', { className: 'tm-editor-btn tm-editor-btn--step-action tm-editor-btn--danger' });
      delBtn.addEventListener('click', () => {
        state.steps.splice(index, 1);
        saveSteps();
        renderSteps();
      });

      actions.appendChild(upBtn);
      actions.appendChild(downBtn);
      actions.appendChild(dupBtn);
      actions.appendChild(h('span', { style: { flex: '1' } }));
      actions.appendChild(delBtn);
      card.appendChild(actions);

      stepsContainer.appendChild(card);
    });

    // Add Step button
    const addStepBtn = makeButton('+ Add Step', { className: 'tm-editor-btn tm-editor-btn--dashed tm-editor-btn--pipeline' });
    addStepBtn.addEventListener('click', () => {
      state.steps.push({ id: 'step-' + Date.now(), teamId: '', prompt: '' });
      saveSteps();
      renderSteps();
    });
    stepsContainer.appendChild(addStepBtn);
  }

  renderSteps();
  el.appendChild(stepsContainer);

  // Load existing pipeline data if available
  store.loadPipeline(node.id).then(data => {
    if (data && Array.isArray(data.steps) && data.steps.length > 0) {
      state.steps = data.steps.map(s => ({ ...s }));
      renderSteps();
    }
  }).catch(() => { /* keep current state */ });

  // --- Variables section ---
  el.appendChild(makeSectionHeader('Variables'));

  const varsNote = h('div', { className: 'tm-editor-note' }, 'API keys, passwords, and config values passed to each step in this pipeline.');
  el.appendChild(varsNote);

  const variables = Array.isArray(node.variables) ? [...node.variables] : [];
  const varsContainer = h('div', { className: 'tm-editor-variables-container' });

  function renderVariables() {
    varsContainer.innerHTML = '';
    variables.forEach((v, idx) => {
      const row = h('div', { className: 'tm-editor-variable-row' },
        makeTextInput(v.name || '', { placeholder: 'Key', style: { flex: '1' } }),
        makeTextInput(v.value || '', { placeholder: 'Value', style: { flex: '2' } }),
        h('button', {
          type: 'button',
          className: 'tm-editor-btn-icon',
          onClick: () => { variables.splice(idx, 1); renderVariables(); },
        }, '\u00d7'),
      );
      const nameInput = row.querySelector('input:first-of-type');
      const valueInput = row.querySelector('input:nth-of-type(2)');
      nameInput.addEventListener('input', () => { variables[idx].name = nameInput.value; });
      valueInput.addEventListener('input', () => { variables[idx].value = valueInput.value; });
      varsContainer.appendChild(row);
    });

    const addVarBtn = makeButton('+ Add Variable', { className: 'tm-editor-btn tm-editor-btn--outline tm-editor-btn--small' });
    addVarBtn.addEventListener('click', () => {
      variables.push({ name: '', value: '', type: 'text' });
      renderVariables();
    });
    varsContainer.appendChild(addVarBtn);
  }

  renderVariables();
  el.appendChild(varsContainer);

  // --- Deploy section ---
  el.appendChild(makeSectionHeader('Deploy'));

  const deployRow = h('div', { className: 'tm-editor-deploy-row' });

  const playAllBtn = makeButton('Play All', {
    className: 'tm-editor-btn tm-editor-btn--pipeline-deploy',
    disabled: state.steps.length === 0,
  });
  let deploying = false;
  playAllBtn.addEventListener('click', async () => {
    if (deploying || state.steps.length === 0) return;
    deploying = true;
    playAllBtn.textContent = 'Deploying...';
    playAllBtn.disabled = true;
    try {
      if (store.activeGraph) {
        await store.deployGraph(store.activeGraph.id);
      }
    } catch (err) {
      console.error('Pipeline deploy failed:', err);
    }
    deploying = false;
    playAllBtn.textContent = 'Play All';
    playAllBtn.disabled = state.steps.length === 0;
  });

  const scheduleBtn = makeButton('Schedule', { className: 'tm-editor-btn tm-editor-btn--schedule' });
  scheduleBtn.addEventListener('click', () => {
    console.log('Schedule requested for pipeline', node.id);
  });

  deployRow.appendChild(playAllBtn);
  deployRow.appendChild(scheduleBtn);
  el.appendChild(deployRow);

  // Step count
  el.appendChild(h('div', { className: 'tm-editor-step-count' }, `${state.steps.length} step${state.steps.length !== 1 ? 's' : ''}`));
}

// ---------------------------------------------------------------------------
// renderDefaultEditor
// ---------------------------------------------------------------------------

/**
 * Fallback editor for node kinds without a dedicated editor.
 * @param {HTMLElement} el
 * @param {object} node
 * @param {import('./store.js').TeamManagerStore} store
 * @param {import('../api.js').SigilAPI} api
 */
function renderDefaultEditor(el, node, store, api) {
  el.innerHTML = '';

  const config = node.config || {};
  const kind = node.kind || 'unknown';
  const badgeColor = KIND_BADGE_COLORS[kind] || '#6b7280';

  const state = {
    name: node.label ?? node.name ?? config.name ?? '',
    description: node.promptBody ?? config.description ?? '',
  };
  const snapshot = JSON.parse(JSON.stringify(state));

  const autosave = debounce(() => {
    store.updateNode(node.id, {
      label: state.name,
      promptBody: state.description,
    });
  }, AUTOSAVE_DELAY);

  function triggerSave() { autosave(); }

  // Kind badge
  el.appendChild(h('div', { className: 'tm-editor-kind-badge-row' },
    h('span', {
      className: 'tm-editor-kind-badge',
      style: { background: badgeColor },
    }, kind),
  ));

  // Name
  const nameInput = makeTextInput(state.name, { 'data-field': 'name' });
  nameInput.addEventListener('input', () => { state.name = nameInput.value; triggerSave(); });
  el.appendChild(makeField(makeLabel('Name'), nameInput));

  // Description
  const descTextarea = makeTextarea(state.description, { rows: '4', 'data-field': 'description' });
  descTextarea.addEventListener('input', () => { state.description = descTextarea.value; triggerSave(); });
  el.appendChild(makeField(makeLabel('Description'), descTextarea));

  // Save + Discard
  const actionsRow = h('div', { className: 'tm-editor-actions' });

  const saveBtn = makeButton('Save', { className: 'tm-editor-btn tm-editor-btn--save' });
  saveBtn.addEventListener('click', () => {
    autosave.cancel();
    store.updateNode(node.id, {
      label: state.name,
      promptBody: state.description,
    });
  });

  const discardBtn = makeButton('Discard', { className: 'tm-editor-btn tm-editor-btn--discard' });
  discardBtn.addEventListener('click', () => {
    autosave.cancel();
    Object.assign(state, JSON.parse(JSON.stringify(snapshot)));
    renderDefaultEditor(el, node, store, api);
  });

  actionsRow.appendChild(saveBtn);
  actionsRow.appendChild(discardBtn);
  el.appendChild(actionsRow);
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

export { renderAgentEditor, renderGroupEditor, renderPipelineEditor, renderDefaultEditor, createTagInput };
