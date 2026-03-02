// Sigil Dashboard — Team Manager Context Menu (vanilla JS, DOM overlay)
// Provides right-click context menus for the team manager canvas.
// No framework dependencies. Uses absolute-positioned DOM overlays (not SVG).

// ── State ──

let _menuOverlay = null;   // outermost overlay div (captures outside clicks)
let _menuEl = null;         // the visible menu container
let _escHandler = null;     // keydown listener reference
let _submenuTimeout = null; // delayed close for submenu hover grace period

// ── Styles ──

const MENU_BG = '#1e1e3a';
const MENU_BORDER = 'rgba(255, 255, 255, 0.08)';
const MENU_SHADOW = '0 4px 24px rgba(0, 0, 0, 0.5), 0 1px 4px rgba(0, 0, 0, 0.3)';
const ITEM_HOVER_BG = 'rgba(74, 158, 255, 0.12)';
const DANGER_COLOR = '#f85149';
const DANGER_HOVER_BG = 'rgba(248, 81, 73, 0.12)';
const DIVIDER_COLOR = 'rgba(255, 255, 255, 0.08)';
const TEXT_PRIMARY = '#e6edf3';
const TEXT_SECONDARY = '#8b949e';
const SUBMENU_INDICATOR_COLOR = 'rgba(255, 255, 255, 0.35)';

// ── Core: show / hide ──

/**
 * Removes any visible context menu and cleans up event listeners.
 */
function hideContextMenu() {
  if (_menuOverlay && _menuOverlay.parentNode) {
    _menuOverlay.parentNode.removeChild(_menuOverlay);
  }
  _menuOverlay = null;
  _menuEl = null;

  if (_escHandler) {
    document.removeEventListener('keydown', _escHandler);
    _escHandler = null;
  }
  if (_submenuTimeout) {
    clearTimeout(_submenuTimeout);
    _submenuTimeout = null;
  }
}

/**
 * Creates and shows a context menu at the given screen coordinates.
 *
 * @param {number} x - clientX of the right-click
 * @param {number} y - clientY of the right-click
 * @param {Array<{
 *   label?: string,
 *   icon?: string,
 *   action?: function,
 *   danger?: boolean,
 *   divider?: boolean,
 *   submenu?: Array<{label: string, icon?: string, action: function}>
 * }>} items - menu item descriptors
 */
function showContextMenu(x, y, items) {
  // Tear down any previous menu
  hideContextMenu();

  // -- Overlay: transparent full-screen click-catcher --
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;z-index:9998;';
  overlay.addEventListener('mousedown', (e) => {
    // Click on the overlay itself (not the menu) closes the menu
    if (e.target === overlay) {
      e.preventDefault();
      e.stopPropagation();
      hideContextMenu();
    }
  });

  // -- Menu container --
  const menu = _createMenuPanel(items, /* isSubmenu */ false);
  overlay.appendChild(menu);
  document.body.appendChild(overlay);

  _menuOverlay = overlay;
  _menuEl = menu;

  // Position after appending so we can measure dimensions
  _positionMenu(menu, x, y);

  // Escape key closes
  _escHandler = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      hideContextMenu();
    }
  };
  document.addEventListener('keydown', _escHandler);
}

// ── Menu panel builder ──

/**
 * Builds a single menu panel (top-level or submenu) from item descriptors.
 * @returns {HTMLDivElement}
 */
function _createMenuPanel(items, isSubmenu) {
  const panel = document.createElement('div');
  panel.style.cssText = [
    `background: ${MENU_BG}`,
    `border: 1px solid ${MENU_BORDER}`,
    'border-radius: 8px',
    `box-shadow: ${MENU_SHADOW}`,
    'padding: 4px 0',
    'min-width: 180px',
    'position: absolute',
    'z-index: 9999',
    'user-select: none',
    'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif',
    'font-size: 13px',
    isSubmenu ? 'max-height: 320px; overflow-y: auto' : '',
  ].filter(Boolean).join(';') + ';';

  for (const item of items) {
    if (item.divider) {
      const divider = document.createElement('div');
      divider.style.cssText = `height:1px;background:${DIVIDER_COLOR};margin:4px 8px;`;
      panel.appendChild(divider);
      continue;
    }

    if (item.submenu && item.submenu.length > 0) {
      panel.appendChild(_createSubmenuRow(item));
    } else {
      panel.appendChild(_createMenuItem(item));
    }
  }

  return panel;
}

/**
 * Creates a single clickable menu item row.
 * @returns {HTMLButtonElement}
 */
function _createMenuItem(item) {
  const btn = document.createElement('button');
  btn.type = 'button';
  const isDanger = !!item.danger;
  const textColor = isDanger ? DANGER_COLOR : TEXT_PRIMARY;
  const hoverBg = isDanger ? DANGER_HOVER_BG : ITEM_HOVER_BG;

  btn.style.cssText = [
    'display: flex',
    'align-items: center',
    'gap: 10px',
    'width: 100%',
    'padding: 8px 16px',
    'background: transparent',
    'border: none',
    `color: ${textColor}`,
    'font-size: 13px',
    'font-family: inherit',
    'text-align: left',
    'cursor: pointer',
    'white-space: nowrap',
    'line-height: 20px',
    'transition: background 0.1s ease',
    'outline: none',
  ].join(';') + ';';

  // Icon (emoji/unicode)
  if (item.icon) {
    const iconSpan = document.createElement('span');
    iconSpan.style.cssText = 'flex-shrink:0;width:18px;text-align:center;font-size:14px;';
    iconSpan.textContent = item.icon;
    btn.appendChild(iconSpan);
  }

  // Label
  const labelSpan = document.createElement('span');
  labelSpan.style.cssText = 'flex:1;';
  labelSpan.textContent = item.label || '';
  btn.appendChild(labelSpan);

  // Hover effects
  btn.addEventListener('mouseenter', () => {
    btn.style.background = hoverBg;
  });
  btn.addEventListener('mouseleave', () => {
    btn.style.background = 'transparent';
  });

  // Action
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    hideContextMenu();
    if (typeof item.action === 'function') {
      item.action();
    }
  });

  return btn;
}

/**
 * Creates a submenu row: a button with a ▸ indicator that opens a child panel on hover.
 * @returns {HTMLDivElement}
 */
function _createSubmenuRow(item) {
  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'position:relative;';

  // Trigger button
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.style.cssText = [
    'display: flex',
    'align-items: center',
    'gap: 10px',
    'width: 100%',
    'padding: 8px 16px',
    'background: transparent',
    'border: none',
    `color: ${TEXT_PRIMARY}`,
    'font-size: 13px',
    'font-family: inherit',
    'text-align: left',
    'cursor: pointer',
    'white-space: nowrap',
    'line-height: 20px',
    'transition: background 0.1s ease',
    'outline: none',
  ].join(';') + ';';

  // Icon
  if (item.icon) {
    const iconSpan = document.createElement('span');
    iconSpan.style.cssText = 'flex-shrink:0;width:18px;text-align:center;font-size:14px;';
    iconSpan.textContent = item.icon;
    btn.appendChild(iconSpan);
  }

  // Label
  const labelSpan = document.createElement('span');
  labelSpan.style.cssText = 'flex:1;';
  labelSpan.textContent = item.label || '';
  btn.appendChild(labelSpan);

  // ▸ indicator
  const arrow = document.createElement('span');
  arrow.style.cssText = `flex-shrink:0;font-size:10px;color:${SUBMENU_INDICATOR_COLOR};margin-left:8px;`;
  arrow.textContent = '\u25B8'; // ▸
  btn.appendChild(arrow);

  wrapper.appendChild(btn);

  // Submenu panel (created on demand)
  let subPanel = null;

  function openSubmenu() {
    if (_submenuTimeout) {
      clearTimeout(_submenuTimeout);
      _submenuTimeout = null;
    }
    if (subPanel) return; // already open

    subPanel = _createMenuPanel(item.submenu, /* isSubmenu */ true);
    wrapper.appendChild(subPanel);

    // Position the submenu to the right of the trigger row
    const wrapperRect = wrapper.getBoundingClientRect();
    const panelWidth = subPanel.offsetWidth || 180;
    const panelHeight = subPanel.offsetHeight || 200;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    // Default: open to the right
    let left = wrapperRect.width + 2;
    let top = 0;

    // If it would go offscreen right, flip to the left
    if (wrapperRect.right + panelWidth + 4 > vw) {
      left = -(panelWidth + 2);
    }

    // If it would go offscreen bottom, shift up
    if (wrapperRect.top + panelHeight > vh) {
      top = -(panelHeight - wrapperRect.height);
      if (wrapperRect.top + top < 4) top = -(wrapperRect.top - 4);
    }

    subPanel.style.left = left + 'px';
    subPanel.style.top = top + 'px';
  }

  function closeSubmenu() {
    _submenuTimeout = setTimeout(() => {
      if (subPanel && subPanel.parentNode) {
        subPanel.parentNode.removeChild(subPanel);
      }
      subPanel = null;
    }, 150); // grace period so cursor can travel to submenu
  }

  // Hover on the wrapper (includes both button and submenu)
  wrapper.addEventListener('mouseenter', openSubmenu);
  wrapper.addEventListener('mouseleave', closeSubmenu);

  // Keep submenu open while hovering inside it
  wrapper.addEventListener('mouseenter', () => {
    if (_submenuTimeout) {
      clearTimeout(_submenuTimeout);
      _submenuTimeout = null;
    }
  });

  // Button hover highlight
  btn.addEventListener('mouseenter', () => {
    btn.style.background = ITEM_HOVER_BG;
  });
  btn.addEventListener('mouseleave', () => {
    btn.style.background = 'transparent';
  });

  return wrapper;
}

// ── Positioning ──

/**
 * Positions a menu panel near (x, y), clamping to viewport edges.
 */
function _positionMenu(panel, x, y) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const pw = panel.offsetWidth || 180;
  const ph = panel.offsetHeight || 200;
  const margin = 8;

  // Prefer placing to the bottom-right of the click point
  let left = x;
  let top = y;

  // Clamp right edge
  if (left + pw + margin > vw) {
    left = vw - pw - margin;
  }
  // Clamp bottom edge
  if (top + ph + margin > vh) {
    top = vh - ph - margin;
  }
  // Clamp left/top edges
  if (left < margin) left = margin;
  if (top < margin) top = margin;

  panel.style.left = left + 'px';
  panel.style.top = top + 'px';
}

// ── High-level menu builders ──

/**
 * Shows the context menu for right-clicking on an empty canvas area.
 *
 * @param {number} x - clientX
 * @param {number} y - clientY
 * @param {{
 *   onNewTeam: function,
 *   onNewPipeline: function,
 *   onAddStickyNote: function
 * }} callbacks
 */
function showPaneContextMenu(x, y, callbacks) {
  const items = [
    {
      label: 'New Team',
      icon: '\u2295',       // ⊕
      action: callbacks.onNewTeam,
    },
    {
      label: 'New Project Manager',
      icon: '\u2295',       // ⊕
      action: callbacks.onNewPipeline,
    },
    { divider: true },
    {
      label: 'Add Sticky Note',
      icon: '\uD83D\uDCCC', // 📌
      action: callbacks.onAddStickyNote,
    },
  ];

  showContextMenu(x, y, items);
}

/**
 * Shows the context menu for right-clicking on a node.
 *
 * @param {number} x - clientX
 * @param {number} y - clientY
 * @param {string} nodeId - the ID of the right-clicked node
 * @param {{
 *   onEdit: function(nodeId: string),
 *   onAddChild: function(nodeId: string),
 *   onDuplicate: function(nodeId: string),
 *   onCopy: function(nodeId: string),
 *   onMoveTo: function(nodeId: string, targetId: string),
 *   onRemove: function(nodeId: string)
 * }} callbacks
 * @param {Array<{id: string, label: string}>} moveTargets
 *   Available parents to move this node into.
 *   Caller should already exclude self, descendants, and current parent.
 */
function showNodeContextMenu(x, y, nodeId, callbacks, moveTargets) {
  const items = [
    {
      label: 'Edit',
      icon: '\u270F\uFE0F',  // ✏️
      action: () => callbacks.onEdit(nodeId),
    },
    {
      label: 'Add Child Node',
      icon: '\u2295',         // ⊕
      action: () => callbacks.onAddChild(nodeId),
    },
    {
      label: 'Duplicate',
      icon: '\u2A01',         // ⊡  (using ⨁ as close match — see note below)
      action: () => callbacks.onDuplicate(nodeId),
    },
    {
      label: 'Copy',
      icon: '\uD83D\uDCCB',  // 📋
      action: () => callbacks.onCopy(nodeId),
    },
  ];

  // Move to... submenu (only if there are valid targets)
  if (moveTargets && moveTargets.length > 0) {
    const submenuItems = moveTargets.map((target) => ({
      label: target.label,
      icon: target.id === 'root' ? '\uD83C\uDFE0' : undefined, // 🏠 for root
      action: () => callbacks.onMoveTo(nodeId, target.id),
    }));

    items.push({
      label: 'Move to...',
      icon: '\u2192',          // →
      submenu: submenuItems,
    });
  }

  // Divider before danger zone
  items.push({ divider: true });

  // Danger: remove
  items.push({
    label: 'Remove from Canvas',
    icon: '\u2715',            // ✕
    danger: true,
    action: () => callbacks.onRemove(nodeId),
  });

  showContextMenu(x, y, items);
}

// ── Exports ──

export { showPaneContextMenu, showNodeContextMenu, hideContextMenu };
