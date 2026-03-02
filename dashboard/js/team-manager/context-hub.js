// Sigil Dashboard — Team Manager Context Hub (Catalog Panel)
// 480px slide-in panel for browsing, searching, and importing catalog items.
// Vanilla JS ES6 module — no React, no npm.

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

// ── Constants ──

const KIND_COLORS = {
  agent: '#f0883e',
  skill: '#3fb950',
  group: '#4a9eff',
};

const FILTERS = ['All', 'Skills', 'Teams', 'Agents'];

// ── Module state ──

let _el = null;
let _store = null;
let _api = null;
let _unsub = null;

let _searchQuery = '';
let _activeFilter = 'All';
let _expandedCards = new Set();
let _importDropdownOpen = false;
let _importMode = 'menu'; // 'menu' | 'url'
let _importUrlValue = '';
let _outsideClickHandler = null;

// ── Helpers ──

function _generateNodeId(path) {
  let hash = 0;
  for (let i = 0; i < path.length; i++) {
    hash = ((hash << 5) - hash + path.charCodeAt(i)) | 0;
  }
  return 'nd-' + Math.abs(hash).toString(36) + '-' + Date.now().toString(36).slice(-4);
}

/** Convert a GitHub blob URL to raw content URL. */
function toRawGitHubUrl(url) {
  try {
    const u = new URL(url);
    if (u.hostname === 'raw.githubusercontent.com') return url;
    if (u.hostname === 'github.com') {
      const parts = u.pathname.split('/').filter(Boolean);
      if (parts.length >= 4 && parts[2] === 'blob') {
        const [user, repo, , branch, ...rest] = parts;
        return `https://raw.githubusercontent.com/${user}/${repo}/${branch}/${rest.join('/')}`;
      }
    }
  } catch {
    // not a valid URL
  }
  return url;
}

/** Check if a node ID exists in the current graph tree. */
function _isOnTree(nodeId) {
  if (!_store) return false;
  return _store.nodes.some(n => n.id === nodeId);
}

/** Build catalog items from the store's current nodes. */
function _buildCatalogItems() {
  if (!_store) return { teams: [], skills: [], agents: [] };

  const teams = [];
  const skills = [];
  const agents = [];

  for (const node of _store.nodes) {
    const kind = node.kind || 'agent';
    const item = {
      id: node.id,
      name: node.label || node.name || node.id,
      description: node.config?.description || node.config?.prompt_body || '',
      kind,
      team: node.config?.team || null,
      sourcePath: node.config?.source_path || '',
      model: node.config?.model_id || null,
      agentCount: 0,
      skillCount: 0,
    };

    if (kind === 'group') {
      // Count children
      const childEdges = _store.edges.filter(e => e.source_node_id === node.id);
      item.agentCount = childEdges.length;
      teams.push(item);
    } else if (kind === 'skill') {
      skills.push(item);
    } else if (kind === 'agent' || kind === 'human') {
      agents.push(item);
    }
  }

  return { teams, skills, agents };
}

/** Filter items by search query and active filter. */
function _filterItems(items, kind) {
  const filterMap = { Skills: 'skill', Teams: 'group', Agents: 'agent' };
  if (_activeFilter !== 'All') {
    const wanted = filterMap[_activeFilter];
    if (kind !== wanted) return [];
  }

  if (!_searchQuery) return items;
  const q = _searchQuery.toLowerCase();
  return items.filter(item =>
    item.name.toLowerCase().includes(q) ||
    item.description.toLowerCase().includes(q) ||
    (item.team || '').toLowerCase().includes(q)
  );
}

// ── Render helpers ──

function _renderBadge(text, bg, color, border) {
  const borderStyle = border ? `border:1px solid ${border};` : '';
  return `<span style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;background:${bg};color:${color};padding:1px 8px;border-radius:10px;${borderStyle}display:inline-block">${escapeHtml(text)}</span>`;
}

function _renderBentoCard(item) {
  const expanded = _expandedCards.has(item.id);
  const onTree = _isOnTree(item.id);
  const color = KIND_COLORS[item.kind] || '#4a9eff';
  const kindLabel = item.kind === 'group' ? 'team' : item.kind;

  let badges = _renderBadge(kindLabel, color, '#fff');
  if (item.team) {
    badges += _renderBadge(item.team, `${color}22`, color, `${color}44`);
  }
  if (onTree) {
    badges += _renderBadge('On Tree', 'rgba(76,175,80,0.15)', '#3fb950', 'rgba(76,175,80,0.3)');
  }
  if (item.kind === 'group' && item.agentCount > 0) {
    badges += _renderBadge(
      `${item.agentCount} agent${item.agentCount > 1 ? 's' : ''}`,
      'rgba(255,152,0,0.15)', '#f0883e', 'rgba(255,152,0,0.3)'
    );
  }
  if (item.kind === 'group' && item.skillCount > 0) {
    badges += _renderBadge(
      `${item.skillCount} skill${item.skillCount > 1 ? 's' : ''}`,
      'rgba(76,175,80,0.15)', '#3fb950', 'rgba(76,175,80,0.3)'
    );
  }

  const chevron = expanded ? '&#x25B4;' : '&#x25BE;';
  const descClamp = expanded
    ? 'display:-webkit-box;-webkit-line-clamp:10;-webkit-box-orient:vertical;overflow:hidden'
    : 'display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden';

  let expandedPanel = '';
  if (expanded) {
    let detailRows = '';
    if (item.kind === 'agent' || item.kind === 'human') {
      if (item.model) {
        detailRows += `<div style="display:flex;gap:8px;margin-bottom:3px"><span style="font-size:11px;color:var(--text-secondary,#8b949e);min-width:50px">Model:</span><span style="font-size:11px;color:var(--text-primary,#e6edf3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(item.model)}</span></div>`;
      }
    }
    if (item.sourcePath) {
      detailRows += `<div style="font-size:10px;color:var(--text-secondary,#8b949e);margin-bottom:10px;word-break:break-all;opacity:0.7">${escapeHtml(item.sourcePath)}</div>`;
    }

    let actions = '';
    if (!onTree && item.kind !== 'group') {
      actions += `<button data-hub-action="add" data-hub-item-id="${escapeHtml(item.id)}" style="padding:5px 12px;font-size:11px;font-weight:600;background:transparent;border:1px solid #3fb950;color:#3fb950;border-radius:6px;cursor:pointer;transition:background 0.15s">Add to Tree</button>`;
    } else {
      actions += `<button data-hub-action="view" data-hub-item-id="${escapeHtml(item.id)}" style="padding:5px 12px;font-size:11px;font-weight:600;background:transparent;border:1px solid var(--accent-blue,#4a9eff);color:var(--accent-blue,#4a9eff);border-radius:6px;cursor:pointer;transition:background 0.15s">View on Tree</button>`;
    }
    if (item.kind !== 'group') {
      actions += `<button data-hub-action="edit" data-hub-item-id="${escapeHtml(item.id)}" style="padding:5px 12px;font-size:11px;font-weight:600;background:transparent;border:1px solid var(--accent-blue,#4a9eff);color:var(--accent-blue,#4a9eff);border-radius:6px;cursor:pointer;transition:background 0.15s">Edit</button>`;
    }

    expandedPanel = `
      <div style="border-top:1px solid var(--border-color,#21262d);padding:10px 14px;animation:fadeIn 0.15s ease">
        ${detailRows ? `<div style="margin-bottom:10px">${detailRows}</div>` : ''}
        <div style="display:flex;gap:6px;flex-wrap:wrap">${actions}</div>
      </div>`;
  }

  return `
    <div class="tm-hub-card" data-hub-card="${escapeHtml(item.id)}" style="background:var(--bg-surface,#1c2333);border:1px solid ${expanded ? color : 'var(--border-color,#21262d)'};border-radius:10px;overflow:hidden;transition:border-color 0.2s ease,box-shadow 0.2s ease;cursor:pointer;${expanded ? 'box-shadow:0 4px 20px rgba(0,0,0,0.3)' : ''}">
      <div data-hub-toggle="${escapeHtml(item.id)}" style="padding:12px 14px;display:flex;align-items:flex-start;gap:10px">
        <div style="width:10px;height:10px;border-radius:50%;background:${color};flex-shrink:0;margin-top:4px"></div>
        <div style="flex:1;min-width:0">
          <div style="font-weight:600;font-size:14px;color:var(--text-primary,#e6edf3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(item.name)}</div>
          ${item.description ? `<div style="font-size:12px;color:var(--text-secondary,#8b949e);margin-top:2px;line-height:1.3;${descClamp}">${escapeHtml(item.description)}</div>` : ''}
          <div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap">${badges}</div>
        </div>
        <div style="color:var(--text-secondary,#8b949e);font-size:14px;flex-shrink:0;transition:transform 0.2s;transform:rotate(${expanded ? '180deg' : '0deg'});margin-top:2px">${chevron}</div>
      </div>
      ${expandedPanel}
    </div>`;
}

function _renderSectionHeader(label, count) {
  return `<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-secondary,#8b949e);padding:12px 0 6px;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:8px">${escapeHtml(label)} (${count})</div>`;
}

function _renderImportDropdown() {
  if (!_importDropdownOpen) return '';

  if (_importMode === 'url') {
    return `
      <div class="tm-hub-import-dropdown" data-hub-import-dropdown style="position:absolute;top:100%;right:0;margin-top:4px;width:260px;background:var(--bg-surface,#1c2333);border:1px solid var(--border-color,#21262d);border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,0.5);z-index:200;padding:6px">
        <div style="padding:4px">
          <div style="font-size:11px;font-weight:600;color:var(--text-secondary,#8b949e);margin-bottom:6px">GitHub URL</div>
          <input type="text" data-hub-url-input value="${escapeHtml(_importUrlValue)}" placeholder="https://github.com/user/repo/blob/main/skill.md" style="width:100%;box-sizing:border-box;padding:7px 10px;font-size:12px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.12);border-radius:6px;color:var(--text-primary,#e6edf3);outline:none;margin-bottom:8px" />
          <div style="display:flex;gap:6px;justify-content:flex-end">
            <button data-hub-import-back style="padding:5px 10px;font-size:11px;font-weight:600;background:transparent;border:1px solid var(--border-color,#21262d);color:var(--text-secondary,#8b949e);border-radius:6px;cursor:pointer">Back</button>
            <button data-hub-import-fetch style="padding:5px 14px;font-size:11px;font-weight:600;background:var(--accent-blue,#4a9eff);border:none;color:#fff;border-radius:6px;cursor:pointer;opacity:${_importUrlValue.trim() ? '1' : '0.5'}">Import</button>
          </div>
        </div>
      </div>`;
  }

  return `
    <div class="tm-hub-import-dropdown" data-hub-import-dropdown style="position:absolute;top:100%;right:0;margin-top:4px;width:260px;background:var(--bg-surface,#1c2333);border:1px solid var(--border-color,#21262d);border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,0.5);z-index:200;padding:6px">
      <button data-hub-import-file style="display:block;width:100%;padding:8px 12px;font-size:12px;font-weight:500;color:var(--text-primary,#e6edf3);background:transparent;border:none;border-radius:4px;cursor:pointer;text-align:left;transition:background 0.12s">From File...</button>
      <button data-hub-import-url style="display:block;width:100%;padding:8px 12px;font-size:12px;font-weight:500;color:var(--text-primary,#e6edf3);background:transparent;border:none;border-radius:4px;cursor:pointer;text-align:left;transition:background 0.12s">From GitHub URL</button>
    </div>`;
}

function _renderFilterPills() {
  return FILTERS.map(chip => {
    const isActive = _activeFilter === chip;
    return `<button data-hub-filter="${escapeHtml(chip)}" style="padding:4px 14px;font-size:12px;font-weight:600;border-radius:20px;border:${isActive ? '1px solid transparent' : '1px solid rgba(255,255,255,0.12)'};background:${isActive ? 'var(--accent-blue,#4a9eff)' : 'transparent'};color:${isActive ? '#fff' : 'var(--text-secondary,#8b949e)'};cursor:pointer;transition:all 0.15s ease;letter-spacing:0.02em">${escapeHtml(chip)}</button>`;
  }).join('');
}

// ── Main render ──

function _render() {
  if (!_el || !_store) return;

  const { teams, skills, agents } = _buildCatalogItems();
  const filteredTeams = _filterItems(teams, 'group');
  const filteredSkills = _filterItems(skills, 'skill');
  const filteredAgents = _filterItems(agents, 'agent');

  const sections = [];
  if (filteredTeams.length > 0) sections.push({ label: 'Teams', items: filteredTeams });
  if (filteredSkills.length > 0) sections.push({ label: 'Skills', items: filteredSkills });
  if (filteredAgents.length > 0) sections.push({ label: 'Agents', items: filteredAgents });

  const totalCount = filteredTeams.length + filteredSkills.length + filteredAgents.length;

  let contentHtml;
  if (totalCount === 0) {
    contentHtml = `<div style="color:var(--text-secondary,#8b949e);font-size:13px;padding:40px 0;text-align:center">${_searchQuery ? 'No matches found' : 'No items found'}</div>`;
  } else {
    contentHtml = sections.map(section =>
      _renderSectionHeader(section.label, section.items.length) +
      `<div style="display:flex;flex-direction:column;gap:8px;margin-bottom:4px">${section.items.map(item => _renderBentoCard(item)).join('')}</div>`
    ).join('');
  }

  _el.innerHTML = `
    <div class="tm-context-hub" style="position:fixed;top:var(--toolbar-height,48px);right:0;bottom:0;width:480px;background:var(--bg-secondary,#161b22);border-left:1px solid var(--border-color,#21262d);box-shadow:-4px 0 24px rgba(0,0,0,0.4);display:flex;flex-direction:column;z-index:100;animation:slideInRight 0.2s ease">
      <!-- Header -->
      <div style="flex-shrink:0;background:linear-gradient(180deg,rgba(21,27,35,0.95) 0%,rgba(21,27,35,0.85) 100%);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,0.06);padding:14px 16px 12px">
        <!-- Title row -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <span style="font-weight:700;font-size:16px;color:var(--text-primary,#e6edf3)">Catalog</span>
          <div style="display:flex;gap:8px;align-items:center">
            <div style="position:relative">
              <button data-hub-import-toggle style="padding:5px 14px;font-size:12px;font-weight:600;background:transparent;border:1px solid var(--border-color,#21262d);color:var(--text-primary,#e6edf3);border-radius:8px;cursor:pointer;transition:border-color 0.15s">Import</button>
              ${_renderImportDropdown()}
            </div>
            <button data-hub-new style="padding:5px 14px;font-size:12px;font-weight:600;background:var(--accent-blue,#4a9eff);border:none;color:#fff;border-radius:8px;cursor:pointer;transition:opacity 0.15s">+ New</button>
            <button data-hub-close style="background:transparent;border:none;color:var(--text-secondary,#8b949e);cursor:pointer;font-size:18px;padding:0 4px;line-height:1">&#xd7;</button>
          </div>
        </div>

        <!-- Utility row -->
        <div style="display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap">
          <button data-hub-refresh style="padding:4px 12px;font-size:11px;font-weight:600;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);color:var(--text-secondary,#8b949e);border-radius:6px;cursor:pointer;transition:all 0.15s">Refresh</button>
          <button data-hub-save-plan style="padding:4px 12px;font-size:11px;font-weight:600;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);color:var(--text-secondary,#8b949e);border-radius:6px;cursor:pointer;transition:all 0.15s">Save Plan</button>
        </div>

        <!-- Search input -->
        <div style="position:relative;margin-bottom:10px">
          <input type="text" data-hub-search value="${escapeHtml(_searchQuery)}" placeholder="Search skills, agents, teams..." style="width:100%;box-sizing:border-box;padding:8px 30px 8px 12px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:var(--text-primary,#e6edf3);font-size:13px;outline:none;transition:border-color 0.2s" />
          ${_searchQuery ? '<button data-hub-search-clear style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--text-secondary,#8b949e);cursor:pointer;font-size:14px;padding:0">&#xd7;</button>' : ''}
        </div>

        <!-- Filter pills -->
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          ${_renderFilterPills()}
        </div>
      </div>

      <!-- Content area -->
      <div style="flex:1;overflow:auto;padding:16px">
        ${contentHtml}
      </div>
    </div>`;

  _bindEvents();
}

// ── Event binding ──

function _bindEvents() {
  if (!_el) return;

  // Close button
  const closeBtn = _el.querySelector('[data-hub-close]');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      if (_store) {
        _store.contextHubOpen = false;
        _store._notify();
      }
    });
  }

  // New button
  const newBtn = _el.querySelector('[data-hub-new]');
  if (newBtn) {
    newBtn.addEventListener('click', () => {
      if (_store) {
        _store.openCreateDialog();
        _store.contextHubOpen = false;
        _store._notify();
      }
    });
  }

  // Refresh button
  const refreshBtn = _el.querySelector('[data-hub-refresh]');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      if (_store && _store.activeGraph) {
        _store.loadGraph(_store.activeGraph.id);
      }
    });
  }

  // Save Plan button
  const savePlanBtn = _el.querySelector('[data-hub-save-plan]');
  if (savePlanBtn) {
    savePlanBtn.addEventListener('click', async () => {
      if (_store && _store.activeGraph) {
        try {
          await _store.updateGraphMeta({
            nodes: _store.nodes,
            edges: _store.edges,
            viewport: _store.viewport,
          });
          _store.addToast('Plan saved', 'success');
        } catch (err) {
          _store.addToast(err.message || 'Failed to save plan', 'error');
        }
      }
    });
  }

  // Search input
  const searchInput = _el.querySelector('[data-hub-search]');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      _searchQuery = e.target.value;
      _render();
      // Refocus the search input and restore cursor position
      const newInput = _el.querySelector('[data-hub-search]');
      if (newInput) {
        newInput.focus();
        newInput.setSelectionRange(newInput.value.length, newInput.value.length);
      }
    });
    searchInput.addEventListener('focus', (e) => {
      e.target.style.borderColor = 'rgba(74,158,255,0.4)';
    });
    searchInput.addEventListener('blur', (e) => {
      e.target.style.borderColor = 'rgba(255,255,255,0.1)';
    });
  }

  // Search clear
  const searchClear = _el.querySelector('[data-hub-search-clear]');
  if (searchClear) {
    searchClear.addEventListener('click', () => {
      _searchQuery = '';
      _render();
    });
  }

  // Filter pills
  _el.querySelectorAll('[data-hub-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      _activeFilter = btn.getAttribute('data-hub-filter') || 'All';
      _render();
    });
  });

  // Card toggle (expand/collapse)
  _el.querySelectorAll('[data-hub-toggle]').forEach(toggleEl => {
    toggleEl.addEventListener('click', () => {
      const itemId = toggleEl.getAttribute('data-hub-toggle');
      if (_expandedCards.has(itemId)) {
        _expandedCards.delete(itemId);
      } else {
        _expandedCards.add(itemId);
      }
      _render();
    });
  });

  // Card action buttons
  _el.querySelectorAll('[data-hub-action]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const action = btn.getAttribute('data-hub-action');
      const itemId = btn.getAttribute('data-hub-item-id');
      if (!itemId || !_store) return;

      if (action === 'add') {
        _handleAddToTree(itemId);
      } else if (action === 'view' || action === 'edit') {
        _store.selectNode(itemId);
        _store.contextHubOpen = false;
        _store._notify();
      }
    });
  });

  // Import toggle
  const importToggle = _el.querySelector('[data-hub-import-toggle]');
  if (importToggle) {
    importToggle.addEventListener('click', () => {
      _importDropdownOpen = !_importDropdownOpen;
      _importMode = 'menu';
      _importUrlValue = '';
      _render();
    });
  }

  // Import dropdown items
  const importFileBtn = _el.querySelector('[data-hub-import-file]');
  if (importFileBtn) {
    importFileBtn.addEventListener('click', () => {
      // No Tauri FS available in browser context -- show a file input fallback
      _handleFileImport();
    });
    importFileBtn.addEventListener('mouseenter', (e) => {
      e.target.style.background = 'rgba(255,255,255,0.06)';
    });
    importFileBtn.addEventListener('mouseleave', (e) => {
      e.target.style.background = 'transparent';
    });
  }

  const importUrlBtn = _el.querySelector('[data-hub-import-url]');
  if (importUrlBtn) {
    importUrlBtn.addEventListener('click', () => {
      _importMode = 'url';
      _render();
      const urlInput = _el.querySelector('[data-hub-url-input]');
      if (urlInput) urlInput.focus();
    });
    importUrlBtn.addEventListener('mouseenter', (e) => {
      e.target.style.background = 'rgba(255,255,255,0.06)';
    });
    importUrlBtn.addEventListener('mouseleave', (e) => {
      e.target.style.background = 'transparent';
    });
  }

  // Import URL mode: back / fetch
  const importBack = _el.querySelector('[data-hub-import-back]');
  if (importBack) {
    importBack.addEventListener('click', () => {
      _importMode = 'menu';
      _render();
    });
  }

  const urlInput = _el.querySelector('[data-hub-url-input]');
  if (urlInput) {
    urlInput.addEventListener('input', (e) => {
      _importUrlValue = e.target.value;
    });
    urlInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') _handleUrlImport();
    });
  }

  const importFetch = _el.querySelector('[data-hub-import-fetch]');
  if (importFetch) {
    importFetch.addEventListener('click', () => {
      _handleUrlImport();
    });
  }

  // Click-outside handler for import dropdown
  _setupOutsideClickHandler();

  // Hover effects on utility buttons
  _el.querySelectorAll('[data-hub-refresh],[data-hub-save-plan]').forEach(btn => {
    btn.addEventListener('mouseenter', () => {
      btn.style.borderColor = 'rgba(255,255,255,0.25)';
      btn.style.color = 'var(--text-primary,#e6edf3)';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.borderColor = 'rgba(255,255,255,0.1)';
      btn.style.color = 'var(--text-secondary,#8b949e)';
    });
  });

  // Hover effects on action buttons inside expanded cards
  _el.querySelectorAll('[data-hub-action]').forEach(btn => {
    const origBorder = btn.style.borderColor;
    btn.addEventListener('mouseenter', () => {
      const borderColor = btn.style.borderColor || btn.style.border;
      btn.style.background = btn.style.color ? `${btn.style.color}18` : 'rgba(255,255,255,0.06)';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.background = 'transparent';
    });
  });
}

function _setupOutsideClickHandler() {
  if (_outsideClickHandler) {
    document.removeEventListener('mousedown', _outsideClickHandler);
  }
  if (_importDropdownOpen) {
    _outsideClickHandler = (e) => {
      const dropdown = _el.querySelector('[data-hub-import-dropdown]');
      const toggle = _el.querySelector('[data-hub-import-toggle]');
      if (dropdown && !dropdown.contains(e.target) && toggle && !toggle.contains(e.target)) {
        _importDropdownOpen = false;
        _importMode = 'menu';
        _importUrlValue = '';
        _render();
      }
    };
    // Delay to avoid catching the current click
    setTimeout(() => {
      document.addEventListener('mousedown', _outsideClickHandler);
    }, 0);
  }
}

// ── Action handlers ──

function _handleAddToTree(itemId) {
  if (!_store) return;
  const existing = _store.nodes.find(n => n.id === itemId);
  if (!existing) return;

  // Node already exists in graph; toast and done
  _store.addToast(`"${existing.label || existing.name}" is already on the tree`, 'info');
}

function _handleFileImport() {
  // Create a temporary file input since we have no Tauri FS
  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = '.md,.json';
  fileInput.style.display = 'none';
  document.body.appendChild(fileInput);

  fileInput.addEventListener('change', async () => {
    const file = fileInput.files?.[0];
    document.body.removeChild(fileInput);
    if (!file) return;

    try {
      const content = await file.text();
      // Try to add as a skill node
      if (_store && _store.activeGraph) {
        const name = file.name.replace(/\.(md|json)$/, '');
        const node = await _store.addNode('skill', name, 100, 100, {
          description: `Imported from ${file.name}`,
          source_path: file.name,
          content,
        });
        if (node) {
          _store.addToast(`Imported "${name}"`, 'success');
          _importDropdownOpen = false;
          _render();
        }
      }
    } catch (err) {
      if (_store) _store.addToast(`Import failed: ${err.message}`, 'error');
    }
  });

  fileInput.click();
}

async function _handleUrlImport() {
  if (!_importUrlValue.trim() || !_store || !_store.activeGraph) return;

  try {
    const rawUrl = toRawGitHubUrl(_importUrlValue.trim());
    const response = await fetch(rawUrl);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const content = await response.text();
    if (!content || content.trim().length === 0) throw new Error('Empty response from URL');

    // Extract a name from the URL path
    const urlParts = rawUrl.split('/');
    const fileName = urlParts[urlParts.length - 1] || 'imported-skill';
    const name = fileName.replace(/\.(md|json)$/, '');

    const node = await _store.addNode('skill', name, 100, 100, {
      description: `Imported from ${_importUrlValue.trim()}`,
      source_path: rawUrl,
      content,
    });

    if (node) {
      _store.addToast(`Imported "${name}" from URL`, 'success');
    }
    _importDropdownOpen = false;
    _importUrlValue = '';
    _importMode = 'menu';
    _render();
  } catch (err) {
    if (_store) _store.addToast(`Import failed: ${err.message}`, 'error');
  }
}

// ── Public API ──

/**
 * Render the Context Hub catalog panel into the given element.
 * @param {HTMLElement} el - Container element
 * @param {import('./store.js').TeamManagerStore} store
 * @param {import('../api.js').SigilAPI} api
 */
export function renderContextHub(el, store, api) {
  _el = el;
  _store = store;
  _api = api;

  // Reset local state on open
  _searchQuery = '';
  _activeFilter = 'All';
  _expandedCards.clear();
  _importDropdownOpen = false;
  _importMode = 'menu';
  _importUrlValue = '';

  // Subscribe to store changes for re-render
  if (_unsub) _unsub();
  _unsub = store.subscribe(() => {
    if (store.contextHubOpen) {
      _render();
    } else {
      el.innerHTML = '';
    }
  });

  _render();
}

/**
 * Tear down the Context Hub and clean up listeners.
 */
export function destroyContextHub() {
  if (_unsub) {
    _unsub();
    _unsub = null;
  }
  if (_outsideClickHandler) {
    document.removeEventListener('mousedown', _outsideClickHandler);
    _outsideClickHandler = null;
  }
  if (_el) {
    _el.innerHTML = '';
    _el = null;
  }
  _store = null;
  _api = null;
  _searchQuery = '';
  _activeFilter = 'All';
  _expandedCards.clear();
  _importDropdownOpen = false;
}
