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

function svgEdge(edge, nodesById) {
  const source = nodesById[edge.source_node_id];
  const target = nodesById[edge.target_node_id];
  if (!source || !target) return '';
  const d = computeEdgePath(source, target);
  return `
    <g class="tm-edge" data-edge-id="${escapeHtml(edge.id)}">
      <path d="${d}" fill="none" stroke="hsl(var(--muted-foreground))" stroke-width="1.5" stroke-opacity="0.5" marker-end="url(#tm-arrowhead)"/>
    </g>`;
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

    // Defs: arrowhead marker
    svg.innerHTML = `
      <defs>
        <marker id="tm-arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto" markerUnits="strokeWidth">
          <polygon points="0 0, 10 3.5, 0 7" fill="hsl(var(--muted-foreground))" fill-opacity="0.5"/>
        </marker>
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
      html += svgEdge(edge, nodesById);
    }
    for (const node of nodes) {
      const renderer = NODE_RENDERERS[node.kind] || svgAgentNode;
      html += renderer(node, selectedNodes.has(node.id));
    }
    this._viewGroup.innerHTML = html;
  }

  // ── Events ──

  _bindEvents() {
    this._onMouseDown = this._handleMouseDown.bind(this);
    this._onMouseMove = this._handleMouseMove.bind(this);
    this._onMouseUp = this._handleMouseUp.bind(this);
    this._onWheel = this._handleWheel.bind(this);
    this._onDblClick = this._handleDblClick.bind(this);
    this._onClick = this._handleClick.bind(this);

    this._svg.addEventListener('mousedown', this._onMouseDown);
    window.addEventListener('mousemove', this._onMouseMove);
    window.addEventListener('mouseup', this._onMouseUp);
    this._svg.addEventListener('wheel', this._onWheel, { passive: false });
    this._svg.addEventListener('dblclick', this._onDblClick);
    this._svg.addEventListener('click', this._onClick);
  }

  _unbindEvents() {
    if (!this._svg) return;
    this._svg.removeEventListener('mousedown', this._onMouseDown);
    window.removeEventListener('mousemove', this._onMouseMove);
    window.removeEventListener('mouseup', this._onMouseUp);
    this._svg.removeEventListener('wheel', this._onWheel);
    this._svg.removeEventListener('dblclick', this._onDblClick);
    this._svg.removeEventListener('click', this._onClick);
  }

  _findNodeId(target) {
    const nodeGroup = target.closest('.tm-node');
    return nodeGroup ? nodeGroup.getAttribute('data-node-id') : null;
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
    if (nodeId) {
      this.store.selectNode(nodeId, e.shiftKey);
    } else if (!e.shiftKey) {
      this.store.clearSelection();
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

    if (nodeId) {
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
    if (this._dragState) {
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

  /** Get SVG coordinates for a canvas position (for adding nodes at click) */
  getCanvasPoint(clientX, clientY) {
    return this._svgPoint(clientX, clientY);
  }
}
