// Sigil Dashboard — App Entry Point

import { SigilAPI } from './api.js';
import { DashboardState } from './state.js';
import { renderHeader } from './panels/header.js';
import { renderHealth } from './panels/health.js';
import { renderAdaptation } from './panels/adaptation.js';
import { renderMemory } from './panels/memory.js';
import { renderSubagents } from './panels/subagents.js';
import { renderSisters } from './panels/sisters.js';
import { renderAutonomy } from './panels/autonomy.js';
import { renderSkills } from './panels/skills.js';
import { renderTelemetry } from './panels/telemetry.js';
import { renderActivity } from './panels/activity.js';
import { initChat, updateSistersForAutocomplete } from './panels/chat.js';

// ── Config from URL params ──
const params = new URLSearchParams(window.location.search);
const config = {
  tenant: params.get('tenant') || 'tenant-local',
  user: params.get('user') || 'user-local',
  workspace: params.get('workspace') || null,
  port: params.get('port') || window.location.port || '8787',
};

const baseUrl = `${window.location.protocol}//${window.location.hostname}:${config.port}`;

const api = new SigilAPI({
  baseUrl: baseUrl === `${window.location.protocol}//${window.location.host}` ? '' : baseUrl,
  tenantId: config.tenant,
  userId: config.user,
  workspace: config.workspace,
});

const state = new DashboardState();
let refreshInterval = 10;
let refreshCountdown = refreshInterval;
let refreshTimer = null;
let online = false;
let activityPaused = false;

// ── Theme ──
function initTheme() {
  const saved = localStorage.getItem('sigil-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  document.body.setAttribute('data-theme', saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  document.body.setAttribute('data-theme', next);
  localStorage.setItem('sigil-theme', next);
}

// ── Render loop ──
const panels = [
  { id: 'panel-health', key: null, render: renderHealth },
  { id: 'panel-adaptation', key: 'adaptation', render: renderAdaptation },
  { id: 'panel-memory', key: 'memory', render: renderMemory },
  { id: 'panel-subagents', key: 'subagents', render: renderSubagents },
  { id: 'panel-sisters', key: 'sisters', render: renderSisters },
  { id: 'panel-autonomy', key: 'autonomy', render: renderAutonomy },
  { id: 'panel-skills', key: 'skills', render: renderSkills },
  { id: 'panel-telemetry', key: 'loop_telemetry', render: renderTelemetry },
  { id: 'panel-activity', key: null, render: null },
];

function renderAllPanels() {
  for (const panel of panels) {
    if (!panel.render) continue;
    const el = document.getElementById(panel.id);
    if (!el) continue;
    if (panel.key && !state.isDirty(panel.key)) continue;
    panel.render(el, state, api);
  }
}

async function fetchDashboardData() {
  try {
    const [dashboard, activityData] = await Promise.all([
      api.getDashboard(),
      activityPaused ? Promise.resolve(null) : api.getActivity(50),
    ]);
    online = true;
    state.update(dashboard);
    renderAllPanels();

    // Keep autocomplete sister mentions in sync with dashboard state
    updateSistersForAutocomplete(dashboard.sisters);

    if (activityData) {
      const el = document.getElementById('panel-activity');
      if (el) renderActivity(el, activityData.events || [], { paused: activityPaused, onTogglePause });
    }
  } catch (err) {
    online = false;
    console.error('Dashboard fetch error:', err);
  }
  renderHeader(document.getElementById('header'), {
    tenant: config.tenant,
    user: config.user,
    online,
    countdown: refreshCountdown,
    refreshInterval,
    onRefresh: () => { refreshCountdown = 0; tick(); },
    onToggleTheme: toggleTheme,
    onToggleChat,
    theme: document.documentElement.getAttribute('data-theme'),
  });
}

function onTogglePause() {
  activityPaused = !activityPaused;
}

function onToggleChat() {
  const sidebar = document.getElementById('chat-sidebar');
  if (sidebar) sidebar.classList.toggle('collapsed');
}

function tick() {
  refreshCountdown--;
  if (refreshCountdown <= 0) {
    refreshCountdown = refreshInterval;
    fetchDashboardData();
  } else {
    renderHeader(document.getElementById('header'), {
      tenant: config.tenant,
      user: config.user,
      online,
      countdown: refreshCountdown,
      refreshInterval,
      onRefresh: () => { refreshCountdown = 0; tick(); },
      onToggleTheme: toggleTheme,
      onToggleChat,
      theme: document.documentElement.getAttribute('data-theme'),
    });
  }
}

// ── Boot ──
async function boot() {
  initTheme();
  document.body.classList.add('loaded');

  // Show loading skeletons
  for (const panel of panels) {
    const el = document.getElementById(panel.id);
    if (el && panel.render) {
      el.innerHTML = '<div class="card"><div class="skeleton skeleton-card"></div></div>';
    }
  }

  // Initial fetch
  await fetchDashboardData();

  // Init chat
  initChat(document.getElementById('chat-sidebar'), api, config);

  // Start refresh timer
  refreshTimer = setInterval(tick, 1000);
}

boot();

// Expose for debugging
window.__sigil = { api, state, config };
