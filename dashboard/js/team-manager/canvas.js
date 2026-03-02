// Sigil Dashboard — Team Manager Canvas (SVG-based)
// Major overhaul: integrates layout.js, node-renderer.js, context-menu.js,
// and enhanced store features (clipboard, undo, collapse, multi-select).

import { layoutNodes, NODE_WIDTH, NODE_HEIGHT } from './layout.js';
import { createNodeSVG, createStickyNoteSVG, NODE_COLORS, getNodeColor } from './node-renderer.js';
import { showPaneContextMenu, showNodeContextMenu, hideContextMenu } from './context-menu.js';

// ── Helpers ──

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

// ── Edge rendering ──

const EDGE_COLORS = {
  reports_to:   '#10b981',
  delegates_to: '#8b5cf6',
  feeds:        '#3b82f6',
  uses:         '#f59e0b',
  triggers:     '#ef4444',
  annotates:    '#6b7280',
};

const EDGE_LABELS = {
  reports_to:   'reports to',
  delegates_to: 'delegates to',
  feeds:        'feeds',
  uses:         'uses',
  triggers:     'triggers',
  annotates:    'annotates',
};

function edgeColorFor(edgeType) {
  return EDGE_COLORS[edgeType] || '#3a3a6a';
}

function computeEdgePath(source, target) {
  if (!source || !target) return '';
  const sx = source.position_x;
  const sy = source.position_y;
  const tx = target.position_x;
  const ty = target.position_y;
  const dx = tx - sx;
  const dy = ty - sy;
  const cx1 = sx + dx * 0.4;
  const cy1 = sy;
  const cx2 = tx - dx * 0.4;
  const cy2 = ty;
  return `M ${sx} ${sy} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${tx} ${ty}`;
}

function svgEdge(edge, nodesById, selected, animated = false) {
  const source = nodesById[edge.source_node_id];
  const target = nodesById[edge.target_node_id];
  if (!source || !target) return '';
  const d = computeEdgePath(source, target);
  const edgeType = edge.edge_type || edge.type || 'default';
  const hasTypeColor = !!EDGE_COLORS[edgeType];
  const color = hasTypeColor ? edgeColorFor(edgeType) : '#3a3a6a';
  const isDashed = edgeType === 'annotates';
  const strokeWidth = selected ? 3 : 1.5;
  const strokeOpacity = selected ? 1 : 0.6;
  let dashAttr = isDashed ? ' stroke-dasharray="6 3"' : '';

  // Animated dashed stroke for first-level edges (root -> direct children)
  if (animated && !isDashed) {
    dashAttr = ' stroke-dasharray="8 4"';
  }

  const selectedClass = selected ? ' tm-edge--selected' : '';
  const label = hasTypeColor ? (EDGE_LABELS[edgeType] || edgeType) : '';

  const mx = (source.position_x + target.position_x) / 2;
  const my = (source.position_y + target.position_y) / 2;

  const animateTag = animated
    ? `<animate attributeName="stroke-dashoffset" from="24" to="0" dur="1.2s" repeatCount="indefinite"/>`
    : '';

  const labelTag = label
    ? `<text x="${mx}" y="${my - 6}" text-anchor="middle" class="tm-edge-label" fill="${color}" fill-opacity="0.85">${escapeHtml(label)}</text>`
    : '';

  return `
    <g class="tm-edge${selectedClass}" data-edge-id="${escapeHtml(edge.id)}">
      <path d="${d}" fill="none" stroke="transparent" stroke-width="12" class="tm-edge-hitarea"/>
      <path d="${d}" fill="none" stroke="${color}" stroke-width="${strokeWidth}" stroke-opacity="${strokeOpacity}"${dashAttr} marker-end="url(#tm-arrowhead-${escapeHtml(edgeType)})">${animateTag}</path>
      ${labelTag}
    </g>`;
}

/** Build an arrowhead marker def for a given edge type color */
function svgArrowheadMarker(edgeType) {
  const color = edgeColorFor(edgeType);
  return `<marker id="tm-arrowhead-${escapeHtml(edgeType)}" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto" markerUnits="strokeWidth">
      <polygon points="0 0, 10 3.5, 0 7" fill="${color}" fill-opacity="0.7"/>
    </marker>`;
}

/** Show the edge type picker popup at the given screen coordinates. */
function showEdgeTypePicker(x, y, callback) {
  const existing = document.querySelector('.tm-edge-type-picker');
  if (existing) existing.remove();

  const picker = document.createElement('div');
  picker.className = 'tm-edge-type-picker';
  picker.style.left = `${x}px`;
  picker.style.top = `${y}px`;

  const types = Object.keys(EDGE_COLORS);
  for (const t of types) {
    const btn = document.createElement('button');
    btn.className = 'tm-edge-type-btn';
    btn.type = 'button';
    btn.setAttribute('data-edge-type', t);
    btn.innerHTML = `<span class="tm-edge-type-dot" style="background:${EDGE_COLORS[t]}"></span>${escapeHtml(EDGE_LABELS[t] || t)}`;
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      picker.remove();
      outsideHandler && document.removeEventListener('pointerdown', outsideHandler, true);
      callback(t);
    });
    picker.appendChild(btn);
  }

  document.body.appendChild(picker);

  let outsideHandler = null;
  requestAnimationFrame(() => {
    outsideHandler = (e) => {
      if (!picker.contains(e.target)) {
        picker.remove();
        document.removeEventListener('pointerdown', outsideHandler, true);
      }
    };
    document.addEventListener('pointerdown', outsideHandler, true);
  });
}

// ── Canvas class ──

export class TeamManagerCanvas {
  /**
   * @param {HTMLElement} container - DOM element to mount into
   * @param {import('./store.js').TeamManagerStore} store
   * @param {object} opts
   * @param {function} opts.onNodeDblClick - callback(nodeId)
   * @param {function} opts.onEdgeCreate - callback(sourceId, targetId, edgeType)
   */
  constructor(container, store, opts = {}) {
    this.container = container;
    this.store = store;
    this.onNodeDblClick = opts.onNodeDblClick || null;
    this.onEdgeCreate = opts.onEdgeCreate || null;

    this._svg = null;
    this._viewGroup = null;
    this._minimapCanvas = null;
    this._welcomeOverlay = null;
    this._multiSelectBanner = null;

    this._dragState = null;        // { nodeId, startX, startY, origX, origY, descendants: [{id, origX, origY}] }
    this._panState = null;         // { startMX, startMY, startVX, startVY }
    this._edgeDrawState = null;    // { sourceNodeId, tempLine }
    this._selectedEdge = null;     // edge id
    this._hoveredNodeId = null;    // currently hovered node id
    this._unsub = null;
    this._initialFitDone = false;

    // Layout cache: mapping of animated edge source IDs from last layout
    this._animatedEdgePairs = new Set();

    this._init();
  }

  _init() {
    this.container.innerHTML = '';
    this.container.classList.add('tm-canvas-container');
    this.container.style.position = 'relative';

    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('class', 'tm-canvas-svg');
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');

    // Defs: arrowhead markers + dot grid pattern + default arrowhead
    const edgeMarkers = Object.keys(EDGE_COLORS).map(t => svgArrowheadMarker(t)).join('\n        ');
    // Also add a default arrowhead for untyped edges
    const defaultArrowhead = `<marker id="tm-arrowhead-default" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto" markerUnits="strokeWidth">
          <polygon points="0 0, 10 3.5, 0 7" fill="#3a3a6a" fill-opacity="0.7"/>
        </marker>`;

    svg.innerHTML = `
      <defs>
        <marker id="tm-arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto" markerUnits="strokeWidth">
          <polygon points="0 0, 10 3.5, 0 7" fill="hsl(var(--muted-foreground))" fill-opacity="0.5"/>
        </marker>
        ${edgeMarkers}
        ${defaultArrowhead}
        <pattern id="tm-dot-grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <circle cx="10" cy="10" r="1" fill="#2a2a4e"/>
        </pattern>
      </defs>
      <rect class="tm-canvas-bg" width="10000" height="10000" x="-5000" y="-5000" fill="url(#tm-dot-grid)"/>
      <g class="tm-view-group"></g>
    `;

    this._svg = svg;
    this._viewGroup = svg.querySelector('.tm-view-group');
    this.container.appendChild(svg);

    // Create the minimap canvas (DOM overlay, bottom-right)
    this._createMinimap();

    // Create the welcome overlay (hidden by default)
    this._createWelcomeOverlay();

    // Create the multi-select banner (hidden by default)
    this._createMultiSelectBanner();

    this._bindEvents();
    this._unsub = this.store.subscribe(() => this.render());
    this.render();
  }

  destroy() {
    if (this._unsub) this._unsub();
    this._unbindEvents();
    hideContextMenu();
    this.container.innerHTML = '';
  }

  // ── Minimap ──

  _createMinimap() {
    const wrapper = document.createElement('div');
    wrapper.className = 'tm-minimap';
    wrapper.style.cssText = [
      'position: absolute',
      'bottom: 12px',
      'right: 12px',
      'width: 200px',
      'height: 150px',
      'background: linear-gradient(135deg, rgba(21, 27, 35, 0.95) 0%, rgba(13, 17, 23, 0.95) 100%)',
      'border: 1px solid rgba(255,255,255,0.08)',
      'border-radius: 12px',
      'overflow: hidden',
      'pointer-events: none',
      'z-index: 10',
      'box-shadow: 0 4px 24px rgba(0,0,0,0.4)',
    ].join(';') + ';';

    const canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 150;
    canvas.style.cssText = 'width:200px;height:150px;';
    wrapper.appendChild(canvas);
    this.container.appendChild(wrapper);
    this._minimapCanvas = canvas;
  }

  _renderMinimap(nodesById) {
    const canvas = this._minimapCanvas;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, 200, 150);

    const nodes = Object.values(nodesById);
    if (nodes.length === 0) return;

    // Compute bounding box
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of nodes) {
      const px = Number(n.position_x) || 0;
      const py = Number(n.position_y) || 0;
      if (px < minX) minX = px;
      if (py < minY) minY = py;
      if (px + NODE_WIDTH > maxX) maxX = px + NODE_WIDTH;
      if (py + NODE_HEIGHT > maxY) maxY = py + NODE_HEIGHT;
    }

    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const padding = 20;
    const scaleX = (200 - padding * 2) / rangeX;
    const scaleY = (150 - padding * 2) / rangeY;
    const scale = Math.min(scaleX, scaleY);

    // Center within minimap
    const usedW = rangeX * scale;
    const usedH = rangeY * scale;
    const offsetX = (200 - usedW) / 2;
    const offsetY = (150 - usedH) / 2;

    for (const n of nodes) {
      const px = Number(n.position_x) || 0;
      const py = Number(n.position_y) || 0;
      const mx = offsetX + (px - minX) * scale;
      const my = offsetY + (py - minY) * scale;
      const color = NODE_COLORS[n.kind] || '#4a9eff';

      ctx.beginPath();
      const dotSize = Math.max(3, Math.min(6, 4 * scale));
      ctx.arc(mx + (NODE_WIDTH * scale) / 2, my + (NODE_HEIGHT * scale) / 2, dotSize, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
    }

    // Draw viewport rectangle
    const { x, y, zoom } = this.store.viewport;
    const svgRect = this._svg.getBoundingClientRect();
    const vpLeft = (-x / zoom);
    const vpTop = (-y / zoom);
    const vpWidth = svgRect.width / zoom;
    const vpHeight = svgRect.height / zoom;

    const vrx = offsetX + (vpLeft - minX) * scale;
    const vry = offsetY + (vpTop - minY) * scale;
    const vrw = vpWidth * scale;
    const vrh = vpHeight * scale;

    ctx.strokeStyle = 'rgba(74, 158, 255, 0.5)';
    ctx.lineWidth = 1;
    ctx.strokeRect(vrx, vry, vrw, vrh);
  }

  // ── Welcome Overlay ──

  _createWelcomeOverlay() {
    const overlay = document.createElement('div');
    overlay.className = 'tm-welcome-overlay';
    overlay.style.cssText = [
      'position: absolute',
      'inset: 0',
      'display: none',
      'flex-direction: column',
      'align-items: center',
      'justify-content: center',
      'pointer-events: none',
      'z-index: 5',
    ].join(';') + ';';

    overlay.innerHTML = `
      <div style="
        background: rgba(13, 17, 23, 0.9);
        border-radius: 16px;
        padding: 48px 56px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        backdrop-filter: blur(12px);
      ">
        <div style="font-size:28px;font-weight:700;color:#e6edf3;margin-bottom:8px;letter-spacing:-0.01em;">
          Create your first team
        </div>
        <div style="font-size:13px;color:#8b949e;margin-bottom:24px;">
          Right-click the canvas or double-click to get started
        </div>
        <button class="tm-welcome-create-btn" style="
          pointer-events: auto;
          padding: 10px 24px;
          background: #4a9eff;
          color: #ffffff;
          border: none;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.15s ease;
        ">Create</button>
      </div>
    `;

    const createBtn = overlay.querySelector('.tm-welcome-create-btn');
    createBtn.addEventListener('click', () => {
      this.store.openCreateDialog();
    });
    createBtn.addEventListener('mouseenter', () => {
      createBtn.style.background = '#3a8eef';
    });
    createBtn.addEventListener('mouseleave', () => {
      createBtn.style.background = '#4a9eff';
    });

    this.container.appendChild(overlay);
    this._welcomeOverlay = overlay;
  }

  _updateWelcomeOverlay() {
    if (!this._welcomeOverlay) return;
    const showWelcome = this.store.nodes.length <= 1;
    this._welcomeOverlay.style.display = showWelcome ? 'flex' : 'none';
  }

  // ── Multi-select banner ──

  _createMultiSelectBanner() {
    const banner = document.createElement('div');
    banner.className = 'tm-multiselect-banner';
    banner.style.cssText = [
      'position: absolute',
      'top: 12px',
      'left: 50%',
      'transform: translateX(-50%)',
      'z-index: 20',
      'display: none',
      'gap: 8px',
      'align-items: center',
      'background: rgba(13, 17, 23, 0.95)',
      'border: 1px solid #8b5cf6',
      'border-radius: 10px',
      'padding: 8px 16px',
      'box-shadow: 0 4px 20px rgba(139, 92, 246, 0.25)',
      'backdrop-filter: blur(12px)',
      'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif',
    ].join(';') + ';';

    banner.innerHTML = `
      <span class="tm-multiselect-count" style="font-size:12px;color:#8b5cf6;font-weight:600;"></span>
      <button class="tm-multiselect-clear" style="
        padding: 4px 8px;
        background: transparent;
        color: #8b949e;
        border: none;
        cursor: pointer;
        font-size: 14px;
      " title="Clear selection">x</button>
    `;

    banner.querySelector('.tm-multiselect-clear').addEventListener('click', () => {
      this.store.clearMultiSelect();
    });

    this.container.appendChild(banner);
    this._multiSelectBanner = banner;
  }

  _updateMultiSelectBanner() {
    if (!this._multiSelectBanner) return;
    const count = this.store.multiSelectedNodeIds.size;
    if (count > 1) {
      this._multiSelectBanner.style.display = 'flex';
      this._multiSelectBanner.querySelector('.tm-multiselect-count').textContent = `${count} selected`;
    } else {
      this._multiSelectBanner.style.display = 'none';
    }
  }

  // ── Layout helpers ──

  /**
   * Collect all descendant node IDs via edges.
   * @param {string} parentId
   * @returns {string[]}
   */
  _getDescendantIds(parentId) {
    const result = [];
    const childEdges = this.store.edges.filter(e => e.source_node_id === parentId);
    for (const edge of childEdges) {
      result.push(edge.target_node_id);
      result.push(...this._getDescendantIds(edge.target_node_id));
    }
    return result;
  }

  /**
   * Count direct children of a node from edges.
   */
  _childCount(nodeId) {
    return this.store.edges.filter(e => e.source_node_id === nodeId).length;
  }

  /**
   * Get the parent node kind for a given node.
   */
  _parentKindOf(nodeId) {
    const parentEdge = this.store.edges.find(e => e.target_node_id === nodeId);
    if (!parentEdge) return null;
    const parentNode = this.store.nodes.find(n => n.id === parentEdge.source_node_id);
    return parentNode ? parentNode.kind : null;
  }

  // ── Rendering ──

  render() {
    const { nodes, edges } = this.store;
    const { x, y, zoom } = this.store.viewport;

    // Update view transform
    this._viewGroup.setAttribute('transform', `translate(${x}, ${y}) scale(${zoom})`);

    // Compute layout positions
    const savedPositions = {};
    for (const n of nodes) {
      const px = Number(n.position_x);
      const py = Number(n.position_y);
      if (isFinite(px) && isFinite(py) && (px !== 0 || py !== 0)) {
        savedPositions[n.id] = { x: px, y: py };
      }
    }

    const layoutResult = layoutNodes(nodes, edges, this.store.collapsedGroups, savedPositions);
    const { positions, visibleNodeIds, visibleEdges } = layoutResult;

    // Build animated edge pairs set
    this._animatedEdgePairs = new Set();
    for (const ve of visibleEdges) {
      if (ve.animated) {
        this._animatedEdgePairs.add(`${ve.source}:${ve.target}`);
      }
    }

    // Apply computed positions back to node objects for edge rendering
    const nodesById = {};
    for (const n of nodes) {
      const pos = positions.get(n.id);
      if (pos) {
        n.position_x = pos.x;
        n.position_y = pos.y;
      } else {
        n.position_x = Number(n.position_x) || 0;
        n.position_y = Number(n.position_y) || 0;
      }
      nodesById[n.id] = n;
    }

    // Clear old content (keeping the container so we can append DOM nodes)
    // Use innerHTML for edge SVG markup, then append rich node DOM elements
    let edgeHtml = '';
    for (const edge of edges) {
      if (!visibleNodeIds.has(edge.source_node_id) || !visibleNodeIds.has(edge.target_node_id)) continue;
      const pairKey = `${edge.source_node_id}:${edge.target_node_id}`;
      const isAnimated = this._animatedEdgePairs.has(pairKey);
      edgeHtml += svgEdge(edge, nodesById, edge.id === this._selectedEdge, isAnimated);
    }

    // Set edge HTML first
    this._viewGroup.innerHTML = edgeHtml;

    // Now append rich SVG node elements (DOM-based, from node-renderer.js)
    for (const node of nodes) {
      if (!visibleNodeIds.has(node.id)) continue;

      const isSelected = this.store.selectedNodes.has(node.id);
      const isMultiSelected = this.store.multiSelectedNodeIds.has(node.id);
      const isHovered = this._hoveredNodeId === node.id;
      const isCollapsed = this.store.collapsedGroups.has(node.id);
      const parentKind = this._parentKindOf(node.id);
      const childCount = this._childCount(node.id);

      let nodeEl;
      if (node.kind === 'note') {
        nodeEl = createStickyNoteSVG(node, {
          selected: isSelected,
          hovered: isHovered,
        });
      } else {
        nodeEl = createNodeSVG(node, {
          selected: isSelected,
          multiSelected: isMultiSelected,
          hovered: isHovered,
          collapsed: isCollapsed,
          childCount,
          skills: node.assignedSkills || (node.config && node.config.skills) || [],
          parentKind,
          onRemove: (id) => { this.store.deleteNode(id); },
          onAddChild: (id) => { this.store.openCreateDialog(id); },
          onCollapse: (id) => { this.store.toggleCollapse(id); this.render(); },
        });
      }

      // Position the node group via transform
      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.setAttribute('transform', `translate(${node.position_x}, ${node.position_y})`);
      g.setAttribute('class', 'tm-node-wrapper');
      g.setAttribute('data-node-id', node.id);
      g.appendChild(nodeEl);
      this._viewGroup.appendChild(g);
    }

    // Re-attach temporary edge line if actively drawing
    if (this._edgeDrawState && this._edgeDrawState.tempLine) {
      this._viewGroup.appendChild(this._edgeDrawState.tempLine);
    }

    // Update overlays
    this._updateWelcomeOverlay();
    this._updateMultiSelectBanner();
    this._renderMinimap(nodesById);

    // Fit view on first render
    if (!this._initialFitDone && nodes.length > 0) {
      this._initialFitDone = true;
      requestAnimationFrame(() => this._fitView());
    }
  }

  // ── Fit View ──

  _fitView() {
    const nodes = this.store.nodes;
    if (nodes.length === 0) return;

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of nodes) {
      const px = Number(n.position_x) || 0;
      const py = Number(n.position_y) || 0;
      if (px < minX) minX = px;
      if (py < minY) minY = py;
      if (px + NODE_WIDTH > maxX) maxX = px + NODE_WIDTH;
      if (py + NODE_HEIGHT > maxY) maxY = py + NODE_HEIGHT;
    }

    const svgRect = this._svg.getBoundingClientRect();
    const svgW = svgRect.width;
    const svgH = svgRect.height;
    const rangeX = maxX - minX;
    const rangeY = maxY - minY;

    if (rangeX <= 0 || rangeY <= 0) return;

    const padding = 80;
    const scaleX = (svgW - padding * 2) / rangeX;
    const scaleY = (svgH - padding * 2) / rangeY;
    const zoom = Math.max(0.1, Math.min(1.5, Math.min(scaleX, scaleY)));

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const vpX = svgW / 2 - centerX * zoom;
    const vpY = svgH / 2 - centerY * zoom;

    this.store.setViewport(vpX, vpY, zoom);
    this.render();
  }

  // ── Events ──

  _bindEvents() {
    this._onMouseDown = this._handleMouseDown.bind(this);
    this._onMouseMove = this._handleMouseMove.bind(this);
    this._onMouseUp = this._handleMouseUp.bind(this);
    this._onWheel = this._handleWheel.bind(this);
    this._onDblClick = this._handleDblClick.bind(this);
    this._onClick = this._handleClick.bind(this);
    this._onKeyDown = this._handleKeyDown.bind(this);
    this._onContextMenu = this._handleContextMenu.bind(this);
    this._onMouseOver = this._handleMouseOver.bind(this);
    this._onMouseOut = this._handleMouseOut.bind(this);

    this._svg.addEventListener('mousedown', this._onMouseDown);
    window.addEventListener('mousemove', this._onMouseMove);
    window.addEventListener('mouseup', this._onMouseUp);
    this._svg.addEventListener('wheel', this._onWheel, { passive: false });
    this._svg.addEventListener('dblclick', this._onDblClick);
    this._svg.addEventListener('click', this._onClick);
    this._svg.addEventListener('contextmenu', this._onContextMenu);
    this._svg.addEventListener('mouseover', this._onMouseOver);
    this._svg.addEventListener('mouseout', this._onMouseOut);
    window.addEventListener('keydown', this._onKeyDown);
  }

  _unbindEvents() {
    if (!this._svg) return;
    this._svg.removeEventListener('mousedown', this._onMouseDown);
    window.removeEventListener('mousemove', this._onMouseMove);
    window.removeEventListener('mouseup', this._onMouseUp);
    this._svg.removeEventListener('wheel', this._onWheel);
    this._svg.removeEventListener('dblclick', this._onDblClick);
    this._svg.removeEventListener('click', this._onClick);
    this._svg.removeEventListener('contextmenu', this._onContextMenu);
    this._svg.removeEventListener('mouseover', this._onMouseOver);
    this._svg.removeEventListener('mouseout', this._onMouseOut);
    window.removeEventListener('keydown', this._onKeyDown);
  }

  _findNodeId(target) {
    // Check for rich node wrapper or legacy node group
    const wrapper = target.closest('.tm-node-wrapper');
    if (wrapper) return wrapper.getAttribute('data-node-id');
    const nodeGroup = target.closest('[data-node-id]');
    return nodeGroup ? nodeGroup.getAttribute('data-node-id') : null;
  }

  _findEdgeId(target) {
    const edgeGroup = target.closest('.tm-edge');
    return edgeGroup ? edgeGroup.getAttribute('data-edge-id') : null;
  }

  _svgPoint(clientX, clientY) {
    const { x, y, zoom } = this.store.viewport;
    const rect = this._svg.getBoundingClientRect();
    return {
      x: (clientX - rect.left - x) / zoom,
      y: (clientY - rect.top - y) / zoom,
    };
  }

  // ── Mouse over/out for hover state ──

  _handleMouseOver(e) {
    const nodeId = this._findNodeId(e.target);
    if (nodeId && nodeId !== this._hoveredNodeId) {
      this._hoveredNodeId = nodeId;
      this.render();
    }
  }

  _handleMouseOut(e) {
    const nodeId = this._findNodeId(e.relatedTarget);
    if (this._hoveredNodeId && nodeId !== this._hoveredNodeId) {
      this._hoveredNodeId = null;
      this.render();
    }
  }

  // ── Click ──

  _handleClick(e) {
    const nodeId = this._findNodeId(e.target);
    const edgeId = this._findEdgeId(e.target);

    if (nodeId) {
      this._selectedEdge = null;
      // Ctrl/Cmd + click toggles multi-select
      if (e.ctrlKey || e.metaKey) {
        this.store.toggleMultiSelect(nodeId);
      } else {
        this.store.clearMultiSelect();
        this.store.selectNode(nodeId, e.shiftKey);
      }
      this.render();
    } else if (edgeId) {
      this._selectedEdge = (this._selectedEdge === edgeId) ? null : edgeId;
      this.store.clearSelection();
      this.store.clearMultiSelect();
      this.render();
    } else if (!e.shiftKey && !e.ctrlKey && !e.metaKey) {
      this._selectedEdge = null;
      this.store.clearSelection();
      this.store.clearMultiSelect();
      this.render();
    }
  }

  // ── Double click ──

  _handleDblClick(e) {
    const nodeId = this._findNodeId(e.target);
    if (nodeId) {
      // Double-click on node: open edit/inspector
      if (this.onNodeDblClick) {
        this.onNodeDblClick(nodeId);
      }
    } else {
      // Double-click on empty canvas: open create dialog
      this.store.openCreateDialog();
    }
  }

  // ── Context menu (right-click) ──

  _handleContextMenu(e) {
    e.preventDefault();
    const nodeId = this._findNodeId(e.target);

    if (nodeId) {
      // Node context menu
      const node = this.store.nodes.find(n => n.id === nodeId);
      if (!node) return;

      // Build move targets: all groups/pipelines excluding self, descendants, and current parent
      const descendantIds = new Set(this._getDescendantIds(nodeId));
      const parentEdge = this.store.edges.find(ed => ed.target_node_id === nodeId);
      const currentParentId = parentEdge ? parentEdge.source_node_id : null;

      const moveTargets = [];

      // Offer "Root" as a target if not already at root
      if (currentParentId !== null) {
        moveTargets.push({ id: 'root', label: 'Root' });
      }

      for (const n of this.store.nodes) {
        if (n.id === nodeId) continue;
        if (n.id === currentParentId) continue;
        if (descendantIds.has(n.id)) continue;
        if (n.kind === 'group' || n.kind === 'pipeline') {
          const prefix = n.kind === 'pipeline' ? '[Pipeline] ' : '';
          moveTargets.push({ id: n.id, label: `${prefix}${n.name || n.label || n.id}` });
        }
      }

      const callbacks = {
        onEdit: (id) => {
          this.store.selectNode(id);
          if (this.onNodeDblClick) this.onNodeDblClick(id);
        },
        onAddChild: (id) => {
          this.store.openCreateDialog(id);
        },
        onDuplicate: (id) => {
          this.store.duplicateNodes(id);
        },
        onCopy: (id) => {
          this.store.copyNodes(id);
        },
        onMoveTo: (fromId, toId) => {
          // Reparent: remove old edge, add new edge
          const oldEdge = this.store.edges.find(ed => ed.target_node_id === fromId);
          if (oldEdge) {
            this.store.deleteEdge(oldEdge.id);
          }
          if (toId !== 'root') {
            this.store.addEdge(toId, fromId, 'reports_to');
          }
        },
        onRemove: (id) => {
          this.store.deleteNode(id);
        },
      };

      showNodeContextMenu(e.clientX, e.clientY, nodeId, callbacks, moveTargets);
    } else {
      // Pane context menu
      const canvasPoint = this._svgPoint(e.clientX, e.clientY);

      showPaneContextMenu(e.clientX, e.clientY, {
        onNewTeam: () => {
          this.store.openCreateDialog(null, 'group');
        },
        onNewPipeline: () => {
          this.store.openCreateDialog(null, 'pipeline');
        },
        onAddStickyNote: () => {
          this.store.createStickyNote('', 'yellow', canvasPoint.x, canvasPoint.y);
        },
      });
    }
  }

  // ── Mouse down ──

  _handleMouseDown(e) {
    if (e.button !== 0) return;
    const nodeId = this._findNodeId(e.target);

    if (nodeId && e.shiftKey) {
      // Shift+drag on a node = start edge draw
      const node = this.store.nodes.find(n => n.id === nodeId);
      if (!node) return;
      const svgNS = 'http://www.w3.org/2000/svg';
      const tempLine = document.createElementNS(svgNS, 'line');
      tempLine.setAttribute('class', 'tm-edge-temp');
      tempLine.setAttribute('x1', node.position_x);
      tempLine.setAttribute('y1', node.position_y);
      tempLine.setAttribute('x2', node.position_x);
      tempLine.setAttribute('y2', node.position_y);
      tempLine.setAttribute('stroke', '#4a9eff');
      tempLine.setAttribute('stroke-width', '2');
      tempLine.setAttribute('stroke-opacity', '0.6');
      tempLine.setAttribute('stroke-dasharray', '6 4');
      tempLine.setAttribute('pointer-events', 'none');
      this._viewGroup.appendChild(tempLine);
      this._edgeDrawState = { sourceNodeId: nodeId, tempLine };
      this._svg.style.cursor = 'crosshair';
      e.preventDefault();
    } else if (nodeId) {
      // Start node drag
      const node = this.store.nodes.find(n => n.id === nodeId);
      if (!node) return;

      // Check if this is a group/pipeline -- if so, capture descendant positions for group drag
      const isGroupLike = node.kind === 'group' || node.kind === 'pipeline';
      const descendants = [];
      const undoPositions = new Map();

      // Always capture the dragged node's position for undo
      undoPositions.set(nodeId, { x: node.position_x, y: node.position_y });

      if (isGroupLike) {
        const descIds = this._getDescendantIds(nodeId);
        for (const descId of descIds) {
          const descNode = this.store.nodes.find(n => n.id === descId);
          if (descNode) {
            descendants.push({
              id: descId,
              origX: Number(descNode.position_x) || 0,
              origY: Number(descNode.position_y) || 0,
            });
            undoPositions.set(descId, {
              x: Number(descNode.position_x) || 0,
              y: Number(descNode.position_y) || 0,
            });
          }
        }
      }

      // Push undo snapshot
      this.store.pushUndo(undoPositions);

      this._dragState = {
        nodeId,
        startX: e.clientX,
        startY: e.clientY,
        origX: Number(node.position_x) || 0,
        origY: Number(node.position_y) || 0,
        descendants,
      };
      e.preventDefault();
    } else {
      // Start pan
      const { x, y } = this.store.viewport;
      this._panState = {
        startMX: e.clientX,
        startMY: e.clientY,
        startVX: x,
        startVY: y,
      };
      this._svg.style.cursor = 'grabbing';
      e.preventDefault();
    }
  }

  // ── Mouse move ──

  _handleMouseMove(e) {
    if (this._edgeDrawState) {
      const pt = this._svgPoint(e.clientX, e.clientY);
      this._edgeDrawState.tempLine.setAttribute('x2', pt.x);
      this._edgeDrawState.tempLine.setAttribute('y2', pt.y);
    } else if (this._dragState) {
      const { nodeId, startX, startY, origX, origY, descendants } = this._dragState;
      const zoom = this.store.viewport.zoom;
      const dx = (e.clientX - startX) / zoom;
      const dy = (e.clientY - startY) / zoom;

      // Move the primary node
      this.store.moveNodeLocal(nodeId, origX + dx, origY + dy);

      // Move all descendants (group drag)
      for (const desc of descendants) {
        this.store.moveNodeLocal(desc.id, desc.origX + dx, desc.origY + dy);
      }

      this.render();
    } else if (this._panState) {
      const { startMX, startMY, startVX, startVY } = this._panState;
      const dx = e.clientX - startMX;
      const dy = e.clientY - startMY;
      this.store.setViewport(startVX + dx, startVY + dy, this.store.viewport.zoom);
      this.render();
    }
  }

  // ── Mouse up ──

  _handleMouseUp(e) {
    if (this._edgeDrawState) {
      const { sourceNodeId, tempLine } = this._edgeDrawState;
      if (tempLine.parentNode) tempLine.remove();
      this._svg.style.cursor = '';

      const targetNodeId = this._findNodeId(e.target);
      this._edgeDrawState = null;

      if (targetNodeId && targetNodeId !== sourceNodeId) {
        showEdgeTypePicker(e.clientX, e.clientY, (edgeType) => {
          this.store.addEdge(sourceNodeId, targetNodeId, edgeType);
          if (this.onEdgeCreate) {
            this.onEdgeCreate(sourceNodeId, targetNodeId, edgeType);
          }
        });
      }
      return;
    }

    if (this._dragState) {
      const { nodeId, descendants } = this._dragState;
      const node = this.store.nodes.find(n => n.id === nodeId);

      if (node) {
        // Proximity reparenting: if within 60px of another node, reparent
        const PROXIMITY = 60;
        let reparented = false;

        // Only do proximity reparenting for single-node (non-multi-select) drags
        if (this.store.multiSelectedNodeIds.size <= 1 && descendants.length === 0) {
          for (const otherNode of this.store.nodes) {
            if (otherNode.id === nodeId) continue;
            if (otherNode.kind === 'note') continue;
            const dx = Math.abs(node.position_x - otherNode.position_x);
            const dy = Math.abs(node.position_y - otherNode.position_y);
            if (dx < PROXIMITY && dy < PROXIMITY) {
              // Reparent: remove old parent edge, add new parent edge
              const oldEdge = this.store.edges.find(ed => ed.target_node_id === nodeId);
              if (oldEdge) {
                this.store.deleteEdge(oldEdge.id);
              }
              this.store.addEdge(otherNode.id, nodeId, 'reports_to');
              reparented = true;
              break;
            }
          }
        }

        if (!reparented) {
          // Commit positions to server
          this.store.updateNode(nodeId, {
            position_x: node.position_x,
            position_y: node.position_y,
          });

          // Also commit descendant positions
          for (const desc of descendants) {
            const descNode = this.store.nodes.find(n => n.id === desc.id);
            if (descNode) {
              this.store.updateNode(desc.id, {
                position_x: descNode.position_x,
                position_y: descNode.position_y,
              });
            }
          }
        }
      }

      this._dragState = null;
    }

    if (this._panState) {
      this._panState = null;
      this._svg.style.cursor = '';
    }
  }

  // ── Wheel (zoom) ──

  _handleWheel(e) {
    e.preventDefault();
    const { x, y, zoom } = this.store.viewport;
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.1, Math.min(5, zoom * delta));

    const rect = this._svg.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const newX = mx - (mx - x) * (newZoom / zoom);
    const newY = my - (my - y) * (newZoom / zoom);

    this.store.setViewport(newX, newY, newZoom);
    this.render();
  }

  // ── Keyboard shortcuts ──

  _handleKeyDown(e) {
    const tag = document.activeElement?.tagName;
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    const isMod = e.ctrlKey || e.metaKey;

    // Delete/Backspace: remove selected node or edge
    if (e.key === 'Delete' || e.key === 'Backspace') {
      if (isInput) return;

      if (this._selectedEdge) {
        const edgeId = this._selectedEdge;
        this._selectedEdge = null;
        this.store.deleteEdge(edgeId);
        e.preventDefault();
        return;
      }

      const selectedId = this._getFirstSelectedNodeId();
      if (selectedId && selectedId !== 'root') {
        this.store.deleteNode(selectedId);
        e.preventDefault();
      }
    }

    // Escape: cancel edge draw, deselect, clear multi-select
    if (e.key === 'Escape') {
      if (this._edgeDrawState) {
        const { tempLine } = this._edgeDrawState;
        if (tempLine.parentNode) tempLine.remove();
        this._edgeDrawState = null;
        this._svg.style.cursor = '';
        e.preventDefault();
      } else {
        this._selectedEdge = null;
        this.store.clearSelection();
        this.store.clearMultiSelect();
        hideContextMenu();
        this.render();
        e.preventDefault();
      }
    }

    // Ctrl/Cmd + Z: undo
    if (isMod && e.key === 'z') {
      if (isInput) return;
      e.preventDefault();
      this.store.undo();
    }

    // Ctrl/Cmd + C: copy
    if (isMod && e.key === 'c') {
      if (isInput) return;
      const selectedId = this._getFirstSelectedNodeId();
      if (selectedId && selectedId !== 'root') {
        e.preventDefault();
        this.store.copyNodes(selectedId);
      }
    }

    // Ctrl/Cmd + V: paste
    if (isMod && e.key === 'v') {
      if (isInput) return;
      e.preventDefault();
      const selectedId = this._getFirstSelectedNodeId();
      this.store.pasteNodes(selectedId || null);
    }

    // Ctrl/Cmd + D: duplicate
    if (isMod && e.key === 'd') {
      if (isInput) return;
      const selectedId = this._getFirstSelectedNodeId();
      if (selectedId && selectedId !== 'root') {
        e.preventDefault();
        this.store.duplicateNodes(selectedId);
      }
    }
  }

  /** Get the first (or only) selected node ID. */
  _getFirstSelectedNodeId() {
    if (this.store.selectedNodes.size > 0) {
      return this.store.selectedNodes.values().next().value;
    }
    return null;
  }

  /** Get SVG coordinates for a canvas position (for adding nodes at click). */
  getCanvasPoint(clientX, clientY) {
    return this._svgPoint(clientX, clientY);
  }
}
