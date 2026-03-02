// Sigil Dashboard — Team Manager Canvas (SVG-based)

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

// ── Node shape SVG generators ──

const NODE_COLORS = {
  human:    '#10b981',
  group:    '#8b5cf6',
  agent:    '#3b82f6',
  skill:    '#f59e0b',
  pipeline: '#ef4444',
  context:  '#06b6d4',
  note:     '#6b7280',
};

function nodeColorFor(kind) {
  return NODE_COLORS[kind] || '#6b7280';
}

/** Human node: circle with person icon */
function svgHumanNode(node, selected) {
  const c = nodeColorFor('human');
  return `
    <g class="tm-node${selected ? ' tm-node--selected' : ''}" data-node-id="${escapeHtml(node.id)}" transform="translate(${node.position_x}, ${node.position_y})">
      <circle r="30" fill="${c}" fill-opacity="0.15" stroke="${c}" stroke-width="${selected ? 2.5 : 1.5}" class="tm-node-shape"/>
      <svg x="-10" y="-14" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
      <text y="24" text-anchor="middle" class="tm-node-label">${escapeHtml(node.label || 'Human')}</text>
    </g>`;
}

/** Group node: rounded rect with multi-person icon */
function svgGroupNode(node, selected) {
  const c = nodeColorFor('group');
  return `
    <g class="tm-node${selected ? ' tm-node--selected' : ''}" data-node-id="${escapeHtml(node.id)}" transform="translate(${node.position_x}, ${node.position_y})">
      <rect x="-40" y="-25" width="80" height="50" rx="10" fill="${c}" fill-opacity="0.15" stroke="${c}" stroke-width="${selected ? 2.5 : 1.5}" class="tm-node-shape"/>
      <svg x="-10" y="-14" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
      <text y="24" text-anchor="middle" class="tm-node-label">${escapeHtml(node.label || 'Group')}</text>
    </g>`;
}

/** Agent node: hexagon */
function svgAgentNode(node, selected) {
  const c = nodeColorFor('agent');
  // Regular hexagon inscribed in r=30
  const r = 30;
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    pts.push(`${(Math.cos(angle) * r).toFixed(1)},${(Math.sin(angle) * r).toFixed(1)}`);
  }
  return `
    <g class="tm-node${selected ? ' tm-node--selected' : ''}" data-node-id="${escapeHtml(node.id)}" transform="translate(${node.position_x}, ${node.position_y})">
      <polygon points="${pts.join(' ')}" fill="${c}" fill-opacity="0.15" stroke="${c}" stroke-width="${selected ? 2.5 : 1.5}" class="tm-node-shape"/>
      <svg x="-8" y="-12" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <path d="M9 9h6v6H9z"/>
      </svg>
      <text y="26" text-anchor="middle" class="tm-node-label">${escapeHtml(node.label || 'Agent')}</text>
    </g>`;
}

/** Skill node: diamond/rhombus */
function svgSkillNode(node, selected) {
  const c = nodeColorFor('skill');
  const s = 28;
  const pts = `0,${-s} ${s},0 0,${s} ${-s},0`;
  return `
    <g class="tm-node${selected ? ' tm-node--selected' : ''}" data-node-id="${escapeHtml(node.id)}" transform="translate(${node.position_x}, ${node.position_y})">
      <polygon points="${pts}" fill="${c}" fill-opacity="0.15" stroke="${c}" stroke-width="${selected ? 2.5 : 1.5}" class="tm-node-shape"/>
      <svg x="-7" y="-10" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
      <text y="24" text-anchor="middle" class="tm-node-label">${escapeHtml(node.label || 'Skill')}</text>
    </g>`;
}

/** Pipeline node: rectangle with step indicators */
function svgPipelineNode(node, selected) {
  const c = nodeColorFor('pipeline');
  return `
    <g class="tm-node${selected ? ' tm-node--selected' : ''}" data-node-id="${escapeHtml(node.id)}" transform="translate(${node.position_x}, ${node.position_y})">
      <rect x="-45" y="-22" width="90" height="44" rx="4" fill="${c}" fill-opacity="0.15" stroke="${c}" stroke-width="${selected ? 2.5 : 1.5}" class="tm-node-shape"/>
      <line x1="-15" y1="-10" x2="-15" y2="10" stroke="${c}" stroke-opacity="0.3" stroke-width="1"/>
      <line x1="15" y1="-10" x2="15" y2="10" stroke="${c}" stroke-opacity="0.3" stroke-width="1"/>
      <circle cx="-30" cy="0" r="3" fill="${c}" fill-opacity="0.6"/>
      <circle cx="0" cy="0" r="3" fill="${c}" fill-opacity="0.6"/>
      <circle cx="30" cy="0" r="3" fill="${c}" fill-opacity="0.6"/>
      <text y="18" text-anchor="middle" class="tm-node-label">${escapeHtml(node.label || 'Pipeline')}</text>
    </g>`;
}

/** Context node: cylinder (two ellipses + rect) */
function svgContextNode(node, selected) {
  const c = nodeColorFor('context');
  const w = 50, h = 40, ry = 8;
  return `
    <g class="tm-node${selected ? ' tm-node--selected' : ''}" data-node-id="${escapeHtml(node.id)}" transform="translate(${node.position_x}, ${node.position_y})">
      <rect x="${-w/2}" y="${-h/2 + ry}" width="${w}" height="${h - ry}" fill="${c}" fill-opacity="0.15" stroke="none" class="tm-node-shape-fill"/>
      <line x1="${-w/2}" y1="${-h/2 + ry}" x2="${-w/2}" y2="${h/2}" stroke="${c}" stroke-width="${selected ? 2.5 : 1.5}"/>
      <line x1="${w/2}" y1="${-h/2 + ry}" x2="${w/2}" y2="${h/2}" stroke="${c}" stroke-width="${selected ? 2.5 : 1.5}"/>
      <ellipse cx="0" cy="${-h/2 + ry}" rx="${w/2}" ry="${ry}" fill="${c}" fill-opacity="0.25" stroke="${c}" stroke-width="${selected ? 2.5 : 1.5}" class="tm-node-shape"/>
      <ellipse cx="0" cy="${h/2}" rx="${w/2}" ry="${ry}" fill="${c}" fill-opacity="0.15" stroke="${c}" stroke-width="${selected ? 2.5 : 1.5}"/>
      <text y="${h/2 + 18}" text-anchor="middle" class="tm-node-label">${escapeHtml(node.label || 'Context')}</text>
    </g>`;
}

/** Note node: tilted sticky rectangle */
function svgNoteNode(node, selected) {
  const c = nodeColorFor('note');
  return `
    <g class="tm-node${selected ? ' tm-node--selected' : ''}" data-node-id="${escapeHtml(node.id)}" transform="translate(${node.position_x}, ${node.position_y})">
      <g transform="rotate(-3)">
        <rect x="-35" y="-25" width="70" height="50" rx="2" fill="${c}" fill-opacity="0.15" stroke="${c}" stroke-width="${selected ? 2.5 : 1.5}" class="tm-node-shape"/>
        <path d="M 25,-25 L 35,-25 L 35,-15 Z" fill="${c}" fill-opacity="0.3"/>
      </g>
      <text y="2" text-anchor="middle" class="tm-node-label" style="font-size:10px">${escapeHtml((node.label || 'Note').slice(0, 30))}</text>
    </g>`;
}

const NODE_RENDERERS = {
  human: svgHumanNode,
  group: svgGroupNode,
  agent: svgAgentNode,
  skill: svgSkillNode,
  pipeline: svgPipelineNode,
  context: svgContextNode,
  note: svgNoteNode,
};

// ── Edge rendering ──

const EDGE_COLORS = {
  reports_to:   '#10b981',  // green  — hierarchy
  delegates_to: '#8b5cf6',  // purple — delegation
  feeds:        '#3b82f6',  // blue   — data flow
  uses:         '#f59e0b',  // amber  — dependency
  triggers:     '#ef4444',  // red    — triggers
  annotates:    '#6b7280',  // gray   — annotations
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
  return EDGE_COLORS[edgeType] || 'hsl(var(--muted-foreground))';
}

function computeEdgePath(source, target) {
  if (!source || !target) return '';
  const sx = source.position_x;
  const sy = source.position_y;
  const tx = target.position_x;
  const ty = target.position_y;
  const dx = tx - sx;
  const dy = ty - sy;
  // Cubic bezier with gentle curve
  const cx1 = sx + dx * 0.4;
  const cy1 = sy;
  const cx2 = tx - dx * 0.4;
  const cy2 = ty;
  return `M ${sx} ${sy} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${tx} ${ty}`;
}

function svgEdge(edge, nodesById, selected) {
  const source = nodesById[edge.source_node_id];
  const target = nodesById[edge.target_node_id];
  if (!source || !target) return '';
  const d = computeEdgePath(source, target);
  const edgeType = edge.edge_type || edge.type || 'default';
  const color = edgeColorFor(edgeType);
  const isDashed = edgeType === 'annotates';
  const strokeWidth = selected ? 3 : 1.5;
  const strokeOpacity = selected ? 1 : 0.6;
  const dashAttr = isDashed ? ' stroke-dasharray="6 3"' : '';
  const selectedClass = selected ? ' tm-edge--selected' : '';
  const label = EDGE_LABELS[edgeType] || edgeType;

  // Compute midpoint for label placement
  const mx = (source.position_x + target.position_x) / 2;
  const my = (source.position_y + target.position_y) / 2;

  return `
    <g class="tm-edge${selectedClass}" data-edge-id="${escapeHtml(edge.id)}">
      <path d="${d}" fill="none" stroke="transparent" stroke-width="12" class="tm-edge-hitarea"/>
      <path d="${d}" fill="none" stroke="${color}" stroke-width="${strokeWidth}" stroke-opacity="${strokeOpacity}"${dashAttr} marker-end="url(#tm-arrowhead-${escapeHtml(edgeType)})"/>
      <text x="${mx}" y="${my - 6}" text-anchor="middle" class="tm-edge-label" fill="${color}" fill-opacity="0.85">${escapeHtml(label)}</text>
    </g>`;
}

/** Build an arrowhead marker def for a given edge type color */
function svgArrowheadMarker(edgeType) {
  const color = edgeColorFor(edgeType);
  return `<marker id="tm-arrowhead-${escapeHtml(edgeType)}" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto" markerUnits="strokeWidth">
      <polygon points="0 0, 10 3.5, 0 7" fill="${color}" fill-opacity="0.7"/>
    </marker>`;
}

/** Show the edge type picker popup at the given screen coordinates.
 *  Calls callback(edgeType) on selection, or nothing on cancel. */
function showEdgeTypePicker(x, y, callback) {
  // Remove any existing picker
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

  // Close on outside click (next tick to avoid catching the triggering event)
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
   */
  constructor(container, store, opts = {}) {
    this.container = container;
    this.store = store;
    this.onNodeDblClick = opts.onNodeDblClick || null;
    this.onEdgeCreate = opts.onEdgeCreate || null;

    this._svg = null;
    this._viewGroup = null;
    this._dragState = null;   // { nodeId, startX, startY, origX, origY }
    this._panState = null;    // { startMX, startMY, startVX, startVY }
    this._edgeDrawState = null; // { sourceNodeId, tempLine (SVG element) }
    this._selectedEdge = null;  // edge id
    this._unsub = null;

    this._init();
  }

  _init() {
    this.container.innerHTML = '';
    this.container.classList.add('tm-canvas-container');

    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('class', 'tm-canvas-svg');
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');

    // Defs: arrowhead markers (one per edge type) + generic fallback + grid
    const edgeMarkers = Object.keys(EDGE_COLORS).map(t => svgArrowheadMarker(t)).join('\n        ');
    svg.innerHTML = `
      <defs>
        <marker id="tm-arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto" markerUnits="strokeWidth">
          <polygon points="0 0, 10 3.5, 0 7" fill="hsl(var(--muted-foreground))" fill-opacity="0.5"/>
        </marker>
        ${edgeMarkers}
        <pattern id="tm-dot-grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.8" fill="hsl(var(--muted-foreground))" fill-opacity="0.15"/>
        </pattern>
      </defs>
      <rect class="tm-canvas-bg" width="10000" height="10000" x="-5000" y="-5000" fill="url(#tm-dot-grid)"/>
      <g class="tm-view-group"></g>
    `;

    this._svg = svg;
    this._viewGroup = svg.querySelector('.tm-view-group');
    this.container.appendChild(svg);

    this._bindEvents();
    this._unsub = this.store.subscribe(() => this.render());
    this.render();
  }

  destroy() {
    if (this._unsub) this._unsub();
    this._unbindEvents();
    this.container.innerHTML = '';
  }

  // ── Rendering ──

  render() {
    const { nodes, edges, selectedNodes } = this.store;
    const { x, y, zoom } = this.store.viewport;

    // Update view transform
    this._viewGroup.setAttribute('transform', `translate(${x}, ${y}) scale(${zoom})`);

    // Build node lookup
    const nodesById = {};
    for (const n of nodes) nodesById[n.id] = n;

    // Render edges then nodes (nodes on top)
    let html = '';
    for (const edge of edges) {
      html += svgEdge(edge, nodesById, edge.id === this._selectedEdge);
    }
    for (const node of nodes) {
      // Coerce positions to numbers for SVG safety.
      node.position_x = Number(node.position_x) || 0;
      node.position_y = Number(node.position_y) || 0;
      const renderer = NODE_RENDERERS[node.kind] || svgAgentNode;
      html += renderer(node, selectedNodes.has(node.id));
    }
    this._viewGroup.innerHTML = html;

    // Re-attach temporary edge line if actively drawing
    if (this._edgeDrawState && this._edgeDrawState.tempLine) {
      this._viewGroup.appendChild(this._edgeDrawState.tempLine);
    }
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

    this._svg.addEventListener('mousedown', this._onMouseDown);
    window.addEventListener('mousemove', this._onMouseMove);
    window.addEventListener('mouseup', this._onMouseUp);
    this._svg.addEventListener('wheel', this._onWheel, { passive: false });
    this._svg.addEventListener('dblclick', this._onDblClick);
    this._svg.addEventListener('click', this._onClick);
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
    window.removeEventListener('keydown', this._onKeyDown);
  }

  _findNodeId(target) {
    const nodeGroup = target.closest('.tm-node');
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

  _handleClick(e) {
    const nodeId = this._findNodeId(e.target);
    const edgeId = this._findEdgeId(e.target);

    if (nodeId) {
      this._selectedEdge = null;
      this.store.selectNode(nodeId, e.shiftKey);
      this.render();
    } else if (edgeId) {
      // Toggle edge selection
      this._selectedEdge = (this._selectedEdge === edgeId) ? null : edgeId;
      this.store.clearSelection();
      this.render();
    } else if (!e.shiftKey) {
      this._selectedEdge = null;
      this.store.clearSelection();
      this.render();
    }
  }

  _handleDblClick(e) {
    const nodeId = this._findNodeId(e.target);
    if (nodeId && this.onNodeDblClick) {
      this.onNodeDblClick(nodeId);
    }
  }

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
      tempLine.setAttribute('stroke', 'hsl(var(--foreground))');
      tempLine.setAttribute('stroke-width', '2');
      tempLine.setAttribute('stroke-opacity', '0.4');
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
      this._dragState = {
        nodeId,
        startX: e.clientX,
        startY: e.clientY,
        origX: node.position_x,
        origY: node.position_y,
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

  _handleMouseMove(e) {
    if (this._edgeDrawState) {
      // Update temp line endpoint to follow cursor in canvas coords
      const pt = this._svgPoint(e.clientX, e.clientY);
      this._edgeDrawState.tempLine.setAttribute('x2', pt.x);
      this._edgeDrawState.tempLine.setAttribute('y2', pt.y);
    } else if (this._dragState) {
      const { nodeId, startX, startY, origX, origY } = this._dragState;
      const zoom = this.store.viewport.zoom;
      const dx = (e.clientX - startX) / zoom;
      const dy = (e.clientY - startY) / zoom;
      this.store.moveNodeLocal(nodeId, origX + dx, origY + dy);
      this.render();
    } else if (this._panState) {
      const { startMX, startMY, startVX, startVY } = this._panState;
      const dx = e.clientX - startMX;
      const dy = e.clientY - startMY;
      this.store.setViewport(startVX + dx, startVY + dy, this.store.viewport.zoom);
      this.render();
    }
  }

  _handleMouseUp(e) {
    if (this._edgeDrawState) {
      const { sourceNodeId, tempLine } = this._edgeDrawState;
      // Remove temp line
      if (tempLine.parentNode) tempLine.remove();
      this._svg.style.cursor = '';

      const targetNodeId = this._findNodeId(e.target);
      this._edgeDrawState = null;

      if (targetNodeId && targetNodeId !== sourceNodeId) {
        // Show edge type picker at the mouse position
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
      // Commit position to server
      const { nodeId } = this._dragState;
      const node = this.store.nodes.find(n => n.id === nodeId);
      if (node) {
        this.store.updateNode(nodeId, {
          position_x: node.position_x,
          position_y: node.position_y,
        });
      }
      this._dragState = null;
    }
    if (this._panState) {
      this._panState = null;
      this._svg.style.cursor = '';
    }
  }

  _handleWheel(e) {
    e.preventDefault();
    const { x, y, zoom } = this.store.viewport;
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.1, Math.min(5, zoom * delta));

    // Zoom towards cursor
    const rect = this._svg.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const newX = mx - (mx - x) * (newZoom / zoom);
    const newY = my - (my - y) * (newZoom / zoom);

    this.store.setViewport(newX, newY, newZoom);
    this.render();
  }

  _handleKeyDown(e) {
    if (e.key === 'Delete' || e.key === 'Backspace') {
      // Avoid deleting edge when user is typing in an input/textarea
      const tag = document.activeElement?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (this._selectedEdge) {
        const edgeId = this._selectedEdge;
        this._selectedEdge = null;
        this.store.deleteEdge(edgeId);
        e.preventDefault();
      }
    }
    // Escape to cancel edge draw or deselect edge
    if (e.key === 'Escape') {
      if (this._edgeDrawState) {
        const { tempLine } = this._edgeDrawState;
        if (tempLine.parentNode) tempLine.remove();
        this._edgeDrawState = null;
        this._svg.style.cursor = '';
        e.preventDefault();
      } else if (this._selectedEdge) {
        this._selectedEdge = null;
        this.render();
        e.preventDefault();
      }
    }
  }

  /** Get SVG coordinates for a canvas position (for adding nodes at click) */
  getCanvasPoint(clientX, clientY) {
    return this._svgPoint(clientX, clientY);
  }
}
