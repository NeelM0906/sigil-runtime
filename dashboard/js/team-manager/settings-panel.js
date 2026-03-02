// Sigil Dashboard — Team Manager Settings Panel
// 400px slide-in panel for API key, color themes, preferences, and data export/import.
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

const STORAGE_KEY = 'tm-settings';
const VERSION = '1.0';

const DEFAULT_SETTINGS = {
  apiKey: '',
  teamColor: '#4a9eff',
  agentColor: '#f0883e',
  accentColor: '#4a9eff',
  autoSave: true,
};

// ── Module state ──

let _el = null;
let _store = null;
let _api = null;
let _unsub = null;

let _settings = { ...DEFAULT_SETTINGS };
let _apiKeyVisible = false;
let _includeSkills = false;

// ── Persistence ──

function _loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      _settings = { ...DEFAULT_SETTINGS, ...parsed };
    } else {
      _settings = { ...DEFAULT_SETTINGS };
    }
  } catch {
    _settings = { ...DEFAULT_SETTINGS };
  }
}

function _saveSettings() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(_settings));
    // Apply accent color as CSS variable
    if (_settings.accentColor) {
      document.documentElement.style.setProperty('--tm-accent-color', _settings.accentColor);
      document.documentElement.style.setProperty('--accent-blue', _settings.accentColor);
    }
  } catch {
    // localStorage unavailable
  }
}

// ── Render ──

function _render() {
  if (!_el || !_store) return;

  const maskedKey = _apiKeyVisible
    ? escapeHtml(_settings.apiKey)
    : (_settings.apiKey ? '\u2022'.repeat(Math.min(_settings.apiKey.length, 20)) : '');

  _el.innerHTML = `
    <div class="tm-settings-panel" style="position:fixed;top:var(--toolbar-height,48px);right:0;bottom:0;width:400px;background:var(--bg-secondary,#161b22);border-left:1px solid var(--border-color,#21262d);box-shadow:-4px 0 24px rgba(0,0,0,0.4);display:flex;flex-direction:column;z-index:150;animation:slideInRight 0.2s ease">
      <!-- Header -->
      <div style="display:flex;justify-content:space-between;align-items:center;padding:14px 16px 12px;border-bottom:1px solid var(--border-color,#21262d);flex-shrink:0">
        <span style="font-weight:700;font-size:16px;color:var(--text-primary,#e6edf3)">Settings</span>
        <button data-settings-close style="background:transparent;border:none;color:var(--text-secondary,#8b949e);cursor:pointer;font-size:18px;padding:0 4px;line-height:1">&#xd7;</button>
      </div>

      <!-- Content -->
      <div style="flex:1;overflow:auto;padding:16px">
        <!-- Version info -->
        <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:rgba(74,158,255,0.06);border:1px solid var(--border-color,#21262d);border-radius:6px;margin-bottom:16px">
          <span style="font-size:12px;color:var(--text-secondary,#8b949e)">Version</span>
          <span style="font-size:13px;font-weight:600;color:var(--text-primary,#e6edf3)">ATM v${escapeHtml(VERSION)}</span>
        </div>

        <!-- Claude API section -->
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--text-secondary,#8b949e);border-bottom:1px solid var(--border-color,#21262d);padding-bottom:6px;margin-top:20px;margin-bottom:12px;font-weight:600">Claude API</div>
        <div style="margin-bottom:16px">
          <label style="font-size:12px;text-transform:uppercase;color:var(--text-secondary,#8b949e);margin-bottom:4px;display:block;letter-spacing:0.5px">API Key</label>
          <div style="display:flex;gap:6px">
            <input type="${_apiKeyVisible ? 'text' : 'password'}" data-settings-apikey value="${escapeHtml(_settings.apiKey)}" placeholder="sk-ant-..." style="background:var(--bg-primary,#0d1117);border:1px solid var(--border-color,#21262d);color:var(--text-primary,#e6edf3);padding:8px;border-radius:6px;flex:1;font-size:13px;outline:none;box-sizing:border-box;transition:border-color 0.15s" />
            <button data-settings-toggle-key style="background:transparent;border:1px solid var(--border-color,#21262d);color:var(--text-secondary,#8b949e);border-radius:4px;cursor:pointer;padding:4px 8px;font-size:11px;white-space:nowrap">${_apiKeyVisible ? 'Hide' : 'Show'}</button>
          </div>
          <div style="font-size:11px;color:var(--text-secondary,#8b949e);margin-top:4px">Used for AI generation features</div>
        </div>

        <!-- Colors section -->
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--text-secondary,#8b949e);border-bottom:1px solid var(--border-color,#21262d);padding-bottom:6px;margin-top:20px;margin-bottom:12px;font-weight:600">Colors</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
          <div>
            <label style="font-size:12px;text-transform:uppercase;color:var(--text-secondary,#8b949e);margin-bottom:4px;display:block;letter-spacing:0.5px">Team Color</label>
            <div style="display:flex;gap:6px;align-items:center">
              <input type="color" data-settings-team-color-picker value="${escapeHtml(_settings.teamColor)}" style="width:32px;height:32px;border:none;border-radius:4px;cursor:pointer;background:none;padding:0" />
              <input type="text" data-settings-team-color value="${escapeHtml(_settings.teamColor)}" style="background:var(--bg-primary,#0d1117);border:1px solid var(--border-color,#21262d);color:var(--text-primary,#e6edf3);padding:8px;border-radius:6px;flex:1;font-size:13px;outline:none;box-sizing:border-box;transition:border-color 0.15s" />
            </div>
          </div>
          <div>
            <label style="font-size:12px;text-transform:uppercase;color:var(--text-secondary,#8b949e);margin-bottom:4px;display:block;letter-spacing:0.5px">Agent Color</label>
            <div style="display:flex;gap:6px;align-items:center">
              <input type="color" data-settings-agent-color-picker value="${escapeHtml(_settings.agentColor)}" style="width:32px;height:32px;border:none;border-radius:4px;cursor:pointer;background:none;padding:0" />
              <input type="text" data-settings-agent-color value="${escapeHtml(_settings.agentColor)}" style="background:var(--bg-primary,#0d1117);border:1px solid var(--border-color,#21262d);color:var(--text-primary,#e6edf3);padding:8px;border-radius:6px;flex:1;font-size:13px;outline:none;box-sizing:border-box;transition:border-color 0.15s" />
            </div>
          </div>
        </div>
        <div style="margin-bottom:16px">
          <label style="font-size:12px;text-transform:uppercase;color:var(--text-secondary,#8b949e);margin-bottom:4px;display:block;letter-spacing:0.5px">Accent Color</label>
          <div style="display:flex;gap:6px;align-items:center">
            <input type="color" data-settings-accent-color-picker value="${escapeHtml(_settings.accentColor)}" style="width:32px;height:32px;border:none;border-radius:4px;cursor:pointer;background:none;padding:0" />
            <input type="text" data-settings-accent-color value="${escapeHtml(_settings.accentColor)}" style="background:var(--bg-primary,#0d1117);border:1px solid var(--border-color,#21262d);color:var(--text-primary,#e6edf3);padding:8px;border-radius:6px;flex:1;font-size:13px;outline:none;box-sizing:border-box;transition:border-color 0.15s" />
          </div>
        </div>

        <!-- Preferences section -->
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--text-secondary,#8b949e);border-bottom:1px solid var(--border-color,#21262d);padding-bottom:6px;margin-top:20px;margin-bottom:12px;font-weight:600">Preferences</div>
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;margin-bottom:12px">
          <input type="checkbox" data-settings-autosave ${_settings.autoSave ? 'checked' : ''} style="width:16px;height:16px;cursor:pointer" />
          <span style="font-size:13px;color:var(--text-primary,#e6edf3)">Auto-save on changes</span>
        </label>

        <!-- Save button -->
        <button data-settings-save style="width:100%;padding:10px 16px;margin-top:16px;background:var(--accent-blue,#4a9eff);color:white;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;transition:opacity 0.15s">Save Settings</button>

        <!-- Data section -->
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--text-secondary,#8b949e);border-bottom:1px solid var(--border-color,#21262d);padding-bottom:6px;margin-top:20px;margin-bottom:12px;font-weight:600">Data</div>
        <div style="display:flex;gap:8px;margin-bottom:8px">
          <button data-settings-export style="flex:1;padding:8px 12px;background:transparent;color:var(--accent-green,#3fb950);border:1px solid var(--accent-green,#3fb950);border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;transition:background 0.15s">Export</button>
          <button data-settings-import style="flex:1;padding:8px 12px;background:transparent;color:var(--accent-blue,#4a9eff);border:1px solid var(--accent-blue,#4a9eff);border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;transition:background 0.15s">Import</button>
        </div>
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;margin-bottom:8px;margin-top:4px">
          <input type="checkbox" data-settings-include-skills ${_includeSkills ? 'checked' : ''} style="width:14px;height:14px;cursor:pointer" />
          <span style="font-size:12px;color:var(--text-primary,#e6edf3)">Include skills (ZIP)</span>
        </label>
        <div style="font-size:11px;color:var(--text-secondary,#8b949e);margin-bottom:4px">Export saves your tree layout and metadata. Import supports .json files.</div>

        <!-- Advanced section -->
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--text-secondary,#8b949e);border-bottom:1px solid var(--border-color,#21262d);padding-bottom:6px;margin-top:20px;margin-bottom:12px;font-weight:600">Advanced</div>
        <div style="font-size:12px;color:var(--text-secondary,#8b949e);padding:8px 0">(reserved)</div>
      </div>
    </div>`;

  _bindEvents();
}

// ── Event binding ──

function _bindEvents() {
  if (!_el) return;

  // Close
  const closeBtn = _el.querySelector('[data-settings-close]');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      if (_store) {
        _store.settingsOpen = false;
        _store._notify();
      }
    });
  }

  // API key input
  const apiKeyInput = _el.querySelector('[data-settings-apikey]');
  if (apiKeyInput) {
    apiKeyInput.addEventListener('input', (e) => {
      _settings.apiKey = e.target.value;
    });
  }

  // Toggle API key visibility
  const toggleKeyBtn = _el.querySelector('[data-settings-toggle-key]');
  if (toggleKeyBtn) {
    toggleKeyBtn.addEventListener('click', () => {
      _apiKeyVisible = !_apiKeyVisible;
      _render();
      // Re-focus the API key input
      const newInput = _el.querySelector('[data-settings-apikey]');
      if (newInput) newInput.focus();
    });
  }

  // Color pickers: team
  _bindColorPair('team-color-picker', 'team-color', 'teamColor');
  // Color pickers: agent
  _bindColorPair('agent-color-picker', 'agent-color', 'agentColor');
  // Color pickers: accent
  _bindColorPair('accent-color-picker', 'accent-color', 'accentColor');

  // Auto-save checkbox
  const autosaveCheckbox = _el.querySelector('[data-settings-autosave]');
  if (autosaveCheckbox) {
    autosaveCheckbox.addEventListener('change', (e) => {
      _settings.autoSave = e.target.checked;
    });
  }

  // Save button
  const saveBtn = _el.querySelector('[data-settings-save]');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      _saveSettings();
      if (_store) _store.addToast('Settings saved', 'success');
    });
    saveBtn.addEventListener('mouseenter', () => { saveBtn.style.opacity = '0.85'; });
    saveBtn.addEventListener('mouseleave', () => { saveBtn.style.opacity = '1'; });
  }

  // Include skills checkbox
  const includeSkillsCheckbox = _el.querySelector('[data-settings-include-skills]');
  if (includeSkillsCheckbox) {
    includeSkillsCheckbox.addEventListener('change', (e) => {
      _includeSkills = e.target.checked;
    });
  }

  // Export button
  const exportBtn = _el.querySelector('[data-settings-export]');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      _handleExport();
    });
    exportBtn.addEventListener('mouseenter', () => { exportBtn.style.background = 'rgba(63,185,80,0.1)'; });
    exportBtn.addEventListener('mouseleave', () => { exportBtn.style.background = 'transparent'; });
  }

  // Import button
  const importBtn = _el.querySelector('[data-settings-import]');
  if (importBtn) {
    importBtn.addEventListener('click', () => {
      _handleImport();
    });
    importBtn.addEventListener('mouseenter', () => { importBtn.style.background = 'rgba(74,158,255,0.1)'; });
    importBtn.addEventListener('mouseleave', () => { importBtn.style.background = 'transparent'; });
  }
}

/**
 * Bind a color picker + text input pair so they stay in sync.
 */
function _bindColorPair(pickerAttr, textAttr, settingsKey) {
  const picker = _el.querySelector(`[data-settings-${pickerAttr}]`);
  const text = _el.querySelector(`[data-settings-${textAttr}]`);
  if (!picker || !text) return;

  picker.addEventListener('input', (e) => {
    _settings[settingsKey] = e.target.value;
    text.value = e.target.value;
  });

  text.addEventListener('input', (e) => {
    const val = e.target.value;
    _settings[settingsKey] = val;
    // Only update picker if value is a valid hex color
    if (/^#[0-9a-fA-F]{6}$/.test(val)) {
      picker.value = val;
    }
  });
}

// ── Export / Import handlers ──

function _handleExport() {
  if (!_store) return;

  const exportData = {
    version: VERSION,
    exportedAt: new Date().toISOString(),
    graph: _store.activeGraph || null,
    nodes: _store.nodes,
    edges: _store.edges,
    viewport: _store.viewport,
    settings: _settings,
  };

  const json = JSON.stringify(exportData, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `team-manager-export-${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  if (_store) _store.addToast('Tree exported successfully', 'success');
}

function _handleImport() {
  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = '.json';
  fileInput.style.display = 'none';
  document.body.appendChild(fileInput);

  fileInput.addEventListener('change', async () => {
    const file = fileInput.files?.[0];
    document.body.removeChild(fileInput);
    if (!file) return;

    try {
      const content = await file.text();
      const data = JSON.parse(content);

      if (!_store) return;

      // Import nodes if present
      if (Array.isArray(data.nodes)) {
        _store.nodes = data.nodes;
      }
      if (Array.isArray(data.edges)) {
        _store.edges = data.edges;
      }
      if (data.viewport) {
        _store.viewport = data.viewport;
      }

      _store._notify();
      _store.addToast('Tree imported successfully', 'success');
    } catch (err) {
      if (_store) _store.addToast(`Import failed: ${err.message}`, 'error');
    }
  });

  fileInput.click();
}

// ── Public API ──

/**
 * Render the Settings Panel into the given element.
 * @param {HTMLElement} el - Container element
 * @param {import('./store.js').TeamManagerStore} store
 * @param {import('../api.js').SigilAPI} api
 */
export function renderSettingsPanel(el, store, api) {
  _el = el;
  _store = store;
  _api = api;
  _apiKeyVisible = false;
  _includeSkills = false;

  // Load persisted settings
  _loadSettings();

  // Subscribe to store changes
  if (_unsub) _unsub();
  _unsub = store.subscribe(() => {
    if (store.settingsOpen) {
      _render();
    } else {
      el.innerHTML = '';
    }
  });

  _render();
}

/**
 * Tear down the Settings Panel and clean up listeners.
 */
export function destroySettingsPanel() {
  if (_unsub) {
    _unsub();
    _unsub = null;
  }
  if (_el) {
    _el.innerHTML = '';
    _el = null;
  }
  _store = null;
  _api = null;
  _apiKeyVisible = false;
  _includeSkills = false;
}
