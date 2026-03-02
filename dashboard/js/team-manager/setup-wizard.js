// Sigil Dashboard — Team Manager Setup Wizard
// Full-screen modal for first-run setup: API key, configuration check, summary.
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

const SETUP_KEY = 'tm-setup-completed';
const SETTINGS_KEY = 'tm-settings';

// ── Module state ──

let _el = null;
let _store = null;
let _api = null;
let _onComplete = null;

let _step = 1; // 1 | 2 | 3
let _apiKey = '';
let _showKey = false;
let _apiKeySaved = false;

// ── Helpers ──

function _isSetupCompleted() {
  try {
    return localStorage.getItem(SETUP_KEY) === 'true';
  } catch {
    return false;
  }
}

function _markSetupCompleted() {
  try {
    localStorage.setItem(SETUP_KEY, 'true');
  } catch {
    // localStorage unavailable
  }
}

function _saveApiKeyToSettings(key) {
  try {
    let settings = {};
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (raw) settings = JSON.parse(raw);
    settings.apiKey = key;
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    // localStorage unavailable
  }
}

// ── Styles (inline, scoped to the wizard) ──

const overlayStyle = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;z-index:20000';

const cardStyle = 'max-width:480px;width:90%;background:var(--bg-secondary,#161b22);border:1px solid var(--border-color,#21262d);border-radius:12px;padding:32px 28px 24px;color:var(--text-primary,#e6edf3);position:relative';

const primaryBtnStyle = 'background:var(--accent-blue,#4a9eff);color:#fff;border:none;border-radius:6px;padding:8px 20px;font-size:14px;font-weight:600;cursor:pointer;transition:opacity 0.15s';

const secondaryBtnStyle = 'background:transparent;color:var(--text-secondary,#8b949e);border:1px solid var(--border-color,#21262d);border-radius:6px;padding:8px 20px;font-size:14px;font-weight:500;cursor:pointer;transition:border-color 0.15s';

const inputStyle = 'width:100%;padding:8px 12px;background:var(--bg-primary,#0d1117);border:1px solid var(--border-color,#21262d);border-radius:6px;color:var(--text-primary,#e6edf3);font-size:14px;outline:none;box-sizing:border-box';

// ── Step renderers ──

function _renderStepDots() {
  return `<div style="display:flex;justify-content:center;gap:8px;margin-bottom:24px">
    ${[1, 2, 3].map(s =>
      `<div style="width:8px;height:8px;border-radius:50%;background:${s === _step ? 'var(--accent-blue,#4a9eff)' : 'var(--border-color,#21262d)'};transition:background 0.2s"></div>`
    ).join('')}
  </div>`;
}

function _renderStep1() {
  return `
    <h2 style="margin:0 0 8px;font-size:22px;font-weight:700">Agent Team Manager</h2>
    <p style="margin:0 0 4px;font-size:13px;color:var(--text-secondary,#8b949e)">Organize your agents into super teams that work in parallel.</p>
    <p style="margin:0 0 20px;font-size:14px;color:var(--text-secondary,#8b949e);line-height:1.5">Set up your API key to enable AI generation features, or skip this step.</p>

    <label style="display:block;font-size:13px;font-weight:600;margin-bottom:6px">API Key (optional):</label>
    <div style="position:relative;margin-bottom:20px">
      <input type="${_showKey ? 'text' : 'password'}" data-wizard-apikey value="${escapeHtml(_apiKey)}" placeholder="sk-ant-..." style="${inputStyle};padding-right:50px" />
      <button data-wizard-toggle-key style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--text-secondary,#8b949e);cursor:pointer;font-size:12px;padding:2px 4px">${_showKey ? 'Hide' : 'Show'}</button>
    </div>

    <div style="display:flex;justify-content:space-between">
      <button data-wizard-skip style="${secondaryBtnStyle}">Skip</button>
      <button data-wizard-next style="${primaryBtnStyle}">Next &rarr;</button>
    </div>`;
}

function _renderStep2() {
  const keyStatus = _apiKeySaved
    ? '<span style="color:var(--accent-green,#3fb950);font-size:16px">&#10003;</span> <span style="font-size:14px;font-weight:600">API key saved</span>'
    : '<span style="color:var(--text-secondary,#8b949e);font-size:16px">&#8211;</span> <span style="font-size:14px">API key skipped</span>';

  return `
    <h2 style="margin:0 0 8px;font-size:20px;font-weight:700">Configuration Check</h2>
    <p style="margin:0 0 20px;font-size:14px;color:var(--text-secondary,#8b949e);line-height:1.5">Review your setup before continuing.</p>

    <div style="padding:14px 16px;border-radius:8px;border:1px solid var(--border-color,#21262d);background:var(--bg-primary,#0d1117);margin-bottom:20px">
      <div style="display:flex;align-items:center;gap:10px">${keyStatus}</div>
    </div>

    <div style="display:flex;justify-content:space-between">
      <button data-wizard-back style="${secondaryBtnStyle}">Back</button>
      <button data-wizard-next style="${primaryBtnStyle}">Next &rarr;</button>
    </div>`;
}

function _renderStep3() {
  const keyCheck = _apiKeySaved
    ? '<span style="color:var(--accent-green,#3fb950);font-size:16px">&#10003;</span> <span>API key saved</span>'
    : '<span style="color:var(--text-secondary,#8b949e);font-size:16px">&#8211;</span> <span>API key skipped</span>';

  return `
    <h2 style="margin:0 0 8px;font-size:20px;font-weight:700">You're all set!</h2>
    <p style="margin:0 0 20px;font-size:14px;color:var(--text-secondary,#8b949e);line-height:1.5">Agent Team Manager is ready to help you organize your AI agent teams.</p>

    <div style="padding:14px 16px;border-radius:8px;border:1px solid var(--border-color,#21262d);background:var(--bg-primary,#0d1117);margin-bottom:24px;display:flex;flex-direction:column;gap:10px">
      <div style="display:flex;align-items:center;gap:10px;font-size:14px">${keyCheck}</div>
      <div style="display:flex;align-items:center;gap:10px;font-size:14px">
        <span style="color:var(--accent-green,#3fb950);font-size:16px">&#10003;</span>
        <span>Dashboard ready</span>
      </div>
      <div style="display:flex;align-items:center;gap:10px;font-size:14px">
        <span style="color:var(--accent-green,#3fb950);font-size:16px">&#10003;</span>
        <span>Team canvas initialized</span>
      </div>
    </div>

    <div style="display:flex;justify-content:space-between">
      <button data-wizard-back style="${secondaryBtnStyle}">Back</button>
      <button data-wizard-finish style="${primaryBtnStyle}">Get Started</button>
    </div>`;
}

// ── Main render ──

function _render() {
  if (!_el) return;

  let stepContent;
  if (_step === 1) stepContent = _renderStep1();
  else if (_step === 2) stepContent = _renderStep2();
  else stepContent = _renderStep3();

  _el.innerHTML = `
    <div style="${overlayStyle}">
      <div style="${cardStyle}">
        ${_renderStepDots()}
        ${stepContent}
      </div>
    </div>`;

  _bindEvents();
}

// ── Event binding ──

function _bindEvents() {
  if (!_el) return;

  // Step 1: API key input
  const apiKeyInput = _el.querySelector('[data-wizard-apikey]');
  if (apiKeyInput) {
    apiKeyInput.addEventListener('input', (e) => {
      _apiKey = e.target.value;
    });
    apiKeyInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') _handleNext();
    });
  }

  // Toggle key visibility
  const toggleKeyBtn = _el.querySelector('[data-wizard-toggle-key]');
  if (toggleKeyBtn) {
    toggleKeyBtn.addEventListener('click', () => {
      _showKey = !_showKey;
      _render();
      const newInput = _el.querySelector('[data-wizard-apikey]');
      if (newInput) {
        newInput.focus();
        newInput.setSelectionRange(newInput.value.length, newInput.value.length);
      }
    });
  }

  // Skip button (step 1 only)
  const skipBtn = _el.querySelector('[data-wizard-skip]');
  if (skipBtn) {
    skipBtn.addEventListener('click', () => {
      _apiKeySaved = false;
      _step = 2;
      _render();
    });
  }

  // Next button
  const nextBtn = _el.querySelector('[data-wizard-next]');
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      _handleNext();
    });
    nextBtn.addEventListener('mouseenter', () => { nextBtn.style.opacity = '0.85'; });
    nextBtn.addEventListener('mouseleave', () => { nextBtn.style.opacity = '1'; });
  }

  // Back button
  const backBtn = _el.querySelector('[data-wizard-back]');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      if (_step > 1) {
        _step -= 1;
        _render();
      }
    });
    backBtn.addEventListener('mouseenter', () => { backBtn.style.borderColor = 'rgba(255,255,255,0.25)'; });
    backBtn.addEventListener('mouseleave', () => { backBtn.style.borderColor = 'var(--border-color,#21262d)'; });
  }

  // Finish button (step 3)
  const finishBtn = _el.querySelector('[data-wizard-finish]');
  if (finishBtn) {
    finishBtn.addEventListener('click', () => {
      _handleFinish();
    });
    finishBtn.addEventListener('mouseenter', () => { finishBtn.style.opacity = '0.85'; });
    finishBtn.addEventListener('mouseleave', () => { finishBtn.style.opacity = '1'; });
  }
}

// ── Action handlers ──

function _handleNext() {
  if (_step === 1) {
    if (_apiKey.trim()) {
      _saveApiKeyToSettings(_apiKey.trim());
      _apiKeySaved = true;
      if (_store) _store.addToast('API key saved', 'success');
    } else {
      _apiKeySaved = false;
    }
    _step = 2;
    _render();
  } else if (_step === 2) {
    _step = 3;
    _render();
  }
}

function _handleFinish() {
  _markSetupCompleted();
  if (_el) {
    _el.innerHTML = '';
  }
  if (_onComplete) {
    _onComplete();
  }
}

// ── Public API ──

/**
 * Render the Setup Wizard modal into the given element.
 * Shows only if setup has not been completed (localStorage check).
 *
 * @param {HTMLElement} el - Container element (should be a full-screen overlay container)
 * @param {import('./store.js').TeamManagerStore} store
 * @param {import('../api.js').SigilAPI} api
 * @param {function} onComplete - Callback when wizard is completed
 */
export function renderSetupWizard(el, store, api, onComplete) {
  // Check if setup already completed
  if (_isSetupCompleted()) {
    el.innerHTML = '';
    if (onComplete) onComplete();
    return;
  }

  _el = el;
  _store = store;
  _api = api;
  _onComplete = onComplete;

  // Reset state
  _step = 1;
  _apiKey = '';
  _showKey = false;
  _apiKeySaved = false;

  _render();
}

/**
 * Tear down the Setup Wizard and clean up.
 */
export function destroySetupWizard() {
  if (_el) {
    _el.innerHTML = '';
    _el = null;
  }
  _store = null;
  _api = null;
  _onComplete = null;
  _step = 1;
  _apiKey = '';
  _showKey = false;
  _apiKeySaved = false;
}
