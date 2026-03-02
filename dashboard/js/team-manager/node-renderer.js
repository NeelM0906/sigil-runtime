// Sigil Dashboard -- Team Manager Rich SVG Node Renderer
// Vanilla ES6 module. Renders rich node cards as SVG <g> groups.
// Port of the React OrgNode.tsx reference to pure SVG with foreignObject for text clamping.

const SVG_NS = 'http://www.w3.org/2000/svg';
const XHTML_NS = 'http://www.w3.org/1999/xhtml';

// ── Color system ──

export const NODE_COLORS = {
  group:         '#4a9eff',   // blue  (top-level team)
  groupMember:   '#f0883e',   // orange (agent in team)
  groupSubAgent: '#a5d6ff',   // light blue
  pipeline:      '#d946ef',   // magenta
  agent:         '#f0883e',   // orange
  skill:         '#3fb950',   // green
  human:         '#d29922',   // gold
  context:       '#8b5cf6',   // purple
  settings:      '#6e7681',   // gray
  note:          '#fbbf24',   // yellow (sticky note)
};

// Fixed team color palette for team indicator dots
const TEAM_COLORS = [
  '#4a9eff', '#f0883e', '#3fb950', '#d946ef',
  '#d29922', '#8b5cf6', '#ef4444', '#06b6d4',
];

function teamColor(teamName) {
  if (!teamName) return '#6e7681';
  let hash = 0;
  for (let i = 0; i < teamName.length; i++) {
    hash = ((hash << 5) - hash + teamName.charCodeAt(i)) | 0;
  }
  return TEAM_COLORS[Math.abs(hash) % TEAM_COLORS.length];
}

// ── Helpers ──

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `${r}, ${g}, ${b}`;
}

/** Unique ID counter for SVG filter/clipPath IDs to avoid collisions. */
let _uid = 0;
function uid(prefix) {
  return `${prefix}-${++_uid}`;
}

/**
 * Resolve the actual display color for a node based on nesting context.
 * @param {object} node - { kind, parentId, ... }
 * @param {string|null} parentKind - parent node's kind, or null for top-level
 * @param {boolean} [parentIsMember=false] - true if parent is itself a group-within-a-group
 * @returns {string} hex color
 */
export function getNodeColor(node, parentKind, parentIsMember = false) {
  if (node.kind === 'pipeline') return NODE_COLORS.pipeline;
  if (node.kind === 'group') {
    // Sub-agent: parent is an agent, or parent is a member-agent (group inside group)
    const isSubAgent = parentKind === 'agent' || parentIsMember;
    if (isSubAgent) return NODE_COLORS.groupSubAgent;
    // Member agent: group inside a group (team)
    if (parentKind === 'group') return NODE_COLORS.groupMember;
    // Top-level team
    return NODE_COLORS.group;
  }
  return NODE_COLORS[node.kind] || NODE_COLORS.settings;
}

/**
 * Resolve the kind badge text for a node.
 * @param {object} node - { kind, parentId, ... }
 * @param {string|null} parentKind - parent node's kind, or null
 * @param {boolean} [parentIsMember=false] - true if parent is itself a group-within-a-group
 * @returns {string}
 */
export function getKindBadgeText(node, parentKind, parentIsMember = false) {
  if (node.kind === 'human') return 'YOU';
  if (node.kind === 'pipeline') return 'PROJECT MGR';
  if (node.kind === 'group') {
    const isSubAgent = parentKind === 'agent' || parentIsMember;
    if (isSubAgent) return 'SUB-AGENT';
    if (parentKind === 'group') return 'AGENT';
    return 'TEAM';
  }
  return node.kind.toUpperCase();
}

/**
 * Truncate text to fit within a given pixel width (approximate).
 * Uses a rough 7.5px per character at 14px font, 6.5px at 12px.
 * @param {string} text
 * @param {number} maxWidth - available width in pixels
 * @param {number} [fontSize=14]
 * @returns {string}
 */
export function truncateText(text, maxWidth, fontSize = 14) {
  if (!text) return '';
  const charWidth = fontSize <= 12 ? 6.5 : 7.5;
  const maxChars = Math.floor(maxWidth / charWidth);
  if (text.length <= maxChars) return text;
  return text.slice(0, Math.max(1, maxChars - 1)) + '\u2026';
}

// ── SVG element factory helpers ──

function el(tag, attrs, children) {
  const node = document.createElementNS(SVG_NS, tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined) continue;
      node.setAttribute(k, String(v));
    }
  }
  if (typeof children === 'string') {
    node.textContent = children;
  } else if (Array.isArray(children)) {
    for (const c of children) {
      if (c) node.appendChild(c);
    }
  } else if (children instanceof Node) {
    node.appendChild(children);
  }
  return node;
}

function htmlEl(tag, attrs, children) {
  const node = document.createElementNS(XHTML_NS, tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined) continue;
      if (k === 'style' && typeof v === 'object') {
        Object.assign(node.style, v);
      } else {
        node.setAttribute(k, String(v));
      }
    }
  }
  if (typeof children === 'string') {
    node.textContent = children;
  } else if (Array.isArray(children)) {
    for (const c of children) {
      if (c) node.appendChild(c);
    }
  } else if (children instanceof Node) {
    node.appendChild(children);
  }
  return node;
}

// ── Glow filter builder ──

function createGlowFilter(id, color, strength) {
  // strength: "0 0 12px color" -- we parse the blur radius
  const match = strength.match(/(\d+)px/);
  const blur = match ? parseInt(match[1], 10) : 8;
  const stdDev = blur / 2;

  const filter = el('filter', { id, x: '-20%', y: '-20%', width: '140%', height: '140%' });
  const flood = el('feFlood', { 'flood-color': color, 'flood-opacity': '0.5', result: 'glow-color' });
  const composite = el('feComposite', { in: 'glow-color', in2: 'SourceGraphic', operator: 'in', result: 'glow-shape' });
  const gaussianBlur = el('feGaussianBlur', { in: 'glow-shape', stdDeviation: String(stdDev), result: 'glow-blur' });
  const merge = el('feMerge');
  merge.appendChild(el('feMergeNode', { in: 'glow-blur' }));
  merge.appendChild(el('feMergeNode', { in: 'SourceGraphic' }));
  filter.appendChild(flood);
  filter.appendChild(composite);
  filter.appendChild(gaussianBlur);
  filter.appendChild(merge);
  return filter;
}

// ── Connection handle builder ──

function createHandle(cx, cy, type, hovered) {
  const size = hovered ? 12 : 8;
  const handle = el('circle', {
    cx, cy,
    r: size / 2,
    fill: '#4a9eff',
    stroke: '#1c2333',
    'stroke-width': '2',
    class: `tm-node-handle tm-node-handle--${type}`,
    'data-handle-type': type,
  });
  return handle;
}

// ── Main node renderer ──

/**
 * Create a rich SVG node group for the team manager canvas.
 *
 * @param {object} node - Node data: { id, kind, name, parentId, promptBody, config, team,
 *                         assignedSkills, validationErrors, pipelineSteps, ... }
 * @param {object} options
 * @param {boolean} [options.selected=false]
 * @param {boolean} [options.multiSelected=false]
 * @param {boolean} [options.hovered=false]
 * @param {boolean} [options.collapsed=false]
 * @param {number}  [options.childCount=0]
 * @param {number}  [options.stepCount=0]
 * @param {string[]} [options.skills=[]] - Resolved skill names
 * @param {string|null} [options.team=null] - Team name override (falls back to node.team)
 * @param {string[]} [options.validationErrors=[]]
 * @param {string|null} [options.parentKind=null] - Parent node kind for nesting resolution
 * @param {boolean} [options.parentIsMember=false] - Whether parent is itself a member-agent
 * @param {function|null} [options.onRemove=null]
 * @param {function|null} [options.onAddChild=null]
 * @param {function|null} [options.onCollapse=null]
 * @returns {SVGGElement}
 */
export function createNodeSVG(node, options = {}) {
  const {
    selected = false,
    multiSelected = false,
    hovered = false,
    collapsed = false,
    childCount = 0,
    stepCount = 0,
    skills = [],
    team = null,
    validationErrors = [],
    parentKind = null,
    parentIsMember = false,
    onRemove = null,
    onAddChild = null,
    onCollapse = null,
  } = options;

  const kind = node.kind || 'agent';
  const isRoot = kind === 'human';
  const isGroup = kind === 'group';
  const isPipeline = kind === 'pipeline';
  const hasErrors = (validationErrors.length || (node.validationErrors && node.validationErrors.length)) > 0;

  // Resolve color and badge text using nesting context
  const color = getNodeColor(node, parentKind, parentIsMember);
  const badgeText = getKindBadgeText(node, parentKind, parentIsMember);
  const rgb = hexToRgb(color);

  // Determine if this is a member (group inside group) or sub-agent
  const isMember = isGroup && parentKind === 'group';
  const isSubAgent = isGroup && (parentKind === 'agent' || parentIsMember);

  // Dimensions
  const nodeWidth = (isGroup || isPipeline) ? 280 : isRoot ? 260 : 240;
  const nodeHeight = 110;
  const padding = 12;

  // Background color
  let bgColor;
  if (isPipeline) {
    bgColor = `rgba(${hexToRgb(NODE_COLORS.pipeline)}, 0.06)`;
  } else if (isGroup) {
    if (isSubAgent) bgColor = `rgba(${hexToRgb(NODE_COLORS.groupSubAgent)}, 0.06)`;
    else if (isMember) bgColor = `rgba(${hexToRgb(NODE_COLORS.groupMember)}, 0.06)`;
    else bgColor = `rgba(${hexToRgb(NODE_COLORS.group)}, 0.06)`;
  } else if (isRoot) {
    bgColor = `rgba(${hexToRgb(NODE_COLORS.human)}, 0.08)`;
  } else {
    bgColor = '#1c2333';
  }

  // Border opacity
  const borderOpacity = selected ? 1 : 0.7;

  // ── Build the group ──
  const g = el('g', {
    class: [
      'tm-node-rich',
      selected ? 'tm-node-rich--selected' : '',
      multiSelected ? 'tm-node-rich--multi' : '',
      hovered ? 'tm-node-rich--hovered' : '',
    ].filter(Boolean).join(' '),
    'data-node-id': node.id,
    'data-node-kind': kind,
  });

  // ── Defs (filters, clipPaths) scoped to this node ──
  const defs = el('defs');
  const filterId = uid('glow');
  const clipId = uid('name-clip');

  // Glow filter
  if (selected || multiSelected || hovered) {
    const blurPx = selected ? 12 : multiSelected ? 10 : 8;
    defs.appendChild(createGlowFilter(filterId, color, `0 0 ${blurPx}px`));
  }

  // Name text clip path
  const nameMaxWidth = nodeWidth - padding * 2 - 56; // reserve space for badge
  defs.appendChild((() => {
    const clip = el('clipPath', { id: clipId });
    clip.appendChild(el('rect', { x: 0, y: 0, width: nameMaxWidth, height: 20 }));
    return clip;
  })());

  g.appendChild(defs);

  // ── Background rect ──
  const bgRect = el('rect', {
    x: 0, y: 0,
    width: nodeWidth,
    height: nodeHeight,
    rx: 8, ry: 8,
    fill: bgColor,
    stroke: multiSelected ? '#8b5cf6' : 'transparent',
    'stroke-width': multiSelected ? 1 : 0,
  });
  if (selected || multiSelected || hovered) {
    bgRect.setAttribute('filter', `url(#${filterId})`);
  }
  g.appendChild(bgRect);

  // ── Left border line ──
  const isDashed = isGroup || isPipeline;
  const leftBorder = el('line', {
    x1: 0, y1: 4,
    x2: 0, y2: nodeHeight - 4,
    stroke: `rgba(${rgb}, ${borderOpacity})`,
    'stroke-width': 4,
    'stroke-linecap': 'round',
  });
  if (isDashed) {
    leftBorder.setAttribute('stroke-dasharray', '8 4');
  }
  g.appendChild(leftBorder);

  // ── Validation error dot ──
  if (hasErrors) {
    g.appendChild(el('circle', {
      cx: 14, cy: 14,
      r: 4,
      fill: '#f85149',
    }));
  }

  // ── Kind badge (top-right) ──
  const badgeCharWidth = 6.2;
  const badgePadH = 12;
  const badgeW = badgeText.length * badgeCharWidth + badgePadH;
  const badgeH = 16;
  const badgeX = nodeWidth - badgeW - 8;
  const badgeY = 6;

  const badgeGroup = el('g', { class: 'tm-node-badge' });
  badgeGroup.appendChild(el('rect', {
    x: badgeX, y: badgeY,
    width: badgeW, height: badgeH,
    rx: badgeH / 2,
    fill: color,
  }));
  badgeGroup.appendChild(el('text', {
    x: badgeX + badgeW / 2,
    y: badgeY + badgeH / 2 + 1,
    'text-anchor': 'middle',
    'dominant-baseline': 'central',
    'font-size': 9,
    'font-weight': 700,
    'letter-spacing': '0.05em',
    fill: '#ffffff',
    class: 'tm-node-badge-text',
  }, badgeText));
  g.appendChild(badgeGroup);

  // ── Vertical layout tracker ──
  let yOffset = padding + 6; // start below top padding

  // ── Name text ──
  const nameText = truncateText(node.name || node.label || kind, nameMaxWidth, 14);
  const nameEl = el('text', {
    x: padding,
    y: yOffset + 14,
    'font-size': 14,
    'font-weight': 700,
    fill: '#ffffff',
    'clip-path': `url(#${clipId})`,
    class: 'tm-node-name',
  }, nameText);
  g.appendChild(nameEl);
  yOffset += 20;

  // ── Description text (2-line clamp via foreignObject) ──
  const description = (isGroup || isPipeline)
    ? (node.promptBody || '')
    : (node.config?.description || node.description || '');

  const descFO = el('foreignObject', {
    x: padding,
    y: yOffset,
    width: nodeWidth - padding * 2,
    height: 32,
  });
  const descDiv = htmlEl('div', {
    xmlns: XHTML_NS,
    style: {
      fontSize: '12px',
      lineHeight: '1.3',
      color: '#8b8b8b',
      overflow: 'hidden',
      display: '-webkit-box',
      WebkitLineClamp: '2',
      WebkitBoxOrient: 'vertical',
      wordBreak: 'break-word',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif',
    },
  }, description || '\u00A0');
  descFO.appendChild(descDiv);
  g.appendChild(descFO);
  yOffset += 34;

  // ── Group child count + collapse toggle ──
  if (isGroup) {
    const toggleColor = isSubAgent ? NODE_COLORS.groupSubAgent
      : isMember ? NODE_COLORS.groupMember
      : NODE_COLORS.group;
    const arrow = collapsed ? '\u25B8' : '\u25BE';
    const childLabel = isMember
      ? (childCount === 1 ? 'sub-agent' : 'sub-agents')
      : (childCount === 1 ? 'agent' : 'agents');
    const collapseText = `${arrow} ${childCount} ${childLabel}${collapsed ? ' (collapsed)' : ''}`;

    const collapseGroup = el('g', {
      class: 'tm-node-collapse-toggle',
      cursor: 'pointer',
    });
    collapseGroup.appendChild(el('text', {
      x: padding,
      y: yOffset + 10,
      'font-size': 11,
      fill: toggleColor,
      class: 'tm-node-collapse-text',
    }, collapseText));

    if (collapsed) {
      // Dim suffix for "(collapsed)"
      // The full text is rendered above; this is intentional for simplicity.
      // In SVG we cannot easily do inline spans, so we render it all in one color.
    }

    if (onCollapse) {
      collapseGroup.addEventListener('click', (e) => {
        e.stopPropagation();
        onCollapse(node.id);
      });
      collapseGroup.addEventListener('mousedown', (e) => e.stopPropagation());
    }
    g.appendChild(collapseGroup);
    yOffset += 16;
  }

  // ── Pipeline step count ──
  if (isPipeline) {
    const steps = stepCount || (node.pipelineSteps ? node.pipelineSteps.length : 0);
    const stepLabel = steps === 1 ? 'step' : 'steps';
    g.appendChild(el('text', {
      x: padding,
      y: yOffset + 10,
      'font-size': 11,
      fill: NODE_COLORS.pipeline,
      class: 'tm-node-step-count',
    }, `${steps} ${stepLabel}`));
    yOffset += 16;
  }

  // ── Team indicator ──
  const teamName = team || node.team;
  if (teamName) {
    const tColor = teamColor(teamName);
    const teamGroup = el('g', { class: 'tm-node-team' });
    teamGroup.appendChild(el('circle', {
      cx: padding + 3,
      cy: yOffset + 5,
      r: 3,
      fill: tColor,
    }));
    const truncatedTeam = truncateText(teamName, nodeWidth - padding * 2 - 16, 10);
    teamGroup.appendChild(el('text', {
      x: padding + 10,
      y: yOffset + 8,
      'font-size': 10,
      fill: '#a0a0a0',
      class: 'tm-node-team-text',
    }, truncatedTeam));
    g.appendChild(teamGroup);
    yOffset += 14;
  }

  // ── Skill badges ──
  const skillNames = skills.length > 0 ? skills : (node.assignedSkills || []);
  if (skillNames.length > 0) {
    const maxVisible = 3;
    const visible = skillNames.slice(0, maxVisible);
    const remaining = skillNames.length - maxVisible;

    const skillGroup = el('g', { class: 'tm-node-skills' });
    let sx = padding;
    const skillY = yOffset + 2;

    for (const name of visible) {
      const label = truncateText(String(name), 60, 9);
      const pillW = label.length * 5.4 + 10;

      skillGroup.appendChild(el('rect', {
        x: sx, y: skillY,
        width: pillW, height: 14,
        rx: 7,
        fill: 'rgba(63, 185, 80, 0.12)',
      }));
      skillGroup.appendChild(el('text', {
        x: sx + pillW / 2,
        y: skillY + 10,
        'text-anchor': 'middle',
        'font-size': 9,
        'font-weight': 600,
        fill: NODE_COLORS.skill,
        class: 'tm-node-skill-text',
      }, label));
      sx += pillW + 3;
    }

    if (remaining > 0) {
      const moreLabel = `+${remaining} more`;
      const moreW = moreLabel.length * 5.4 + 10;
      skillGroup.appendChild(el('rect', {
        x: sx, y: skillY,
        width: moreW, height: 14,
        rx: 7,
        fill: 'rgba(63, 185, 80, 0.08)',
      }));
      skillGroup.appendChild(el('text', {
        x: sx + moreW / 2,
        y: skillY + 10,
        'text-anchor': 'middle',
        'font-size': 9,
        'font-weight': 600,
        fill: 'rgba(63, 185, 80, 0.6)',
        class: 'tm-node-skill-text',
      }, moreLabel));
    }

    g.appendChild(skillGroup);
    yOffset += 18;
  }

  // ── Connection handles ──
  // Top center (target)
  g.appendChild(createHandle(nodeWidth / 2, 0, 'target', hovered));
  // Bottom center (source)
  g.appendChild(createHandle(nodeWidth / 2, nodeHeight, 'source', hovered));

  // ── Hover action buttons ──
  if (hovered) {
    // X / Remove button (top-left, offset outside node) -- not for root/human
    if (!isRoot && onRemove) {
      const removeBtn = el('g', {
        class: 'tm-node-action tm-node-action--remove',
        cursor: 'pointer',
      });
      const removeBg = el('circle', {
        cx: -8, cy: 6,
        r: 8,
        fill: 'rgba(120, 120, 120, 0.6)',
      });
      const removeText = el('text', {
        x: -8, y: 10,
        'text-anchor': 'middle',
        'font-size': 10,
        fill: '#dddddd',
        'pointer-events': 'none',
        class: 'tm-node-action-label',
      }, '\u00D7');
      removeBtn.appendChild(removeBg);
      removeBtn.appendChild(removeText);

      // Hover color change via events
      removeBtn.addEventListener('mouseenter', () => {
        removeBg.setAttribute('fill', 'rgba(248, 81, 73, 0.8)');
        removeText.setAttribute('fill', '#ffffff');
      });
      removeBtn.addEventListener('mouseleave', () => {
        removeBg.setAttribute('fill', 'rgba(120, 120, 120, 0.6)');
        removeText.setAttribute('fill', '#dddddd');
      });
      removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        onRemove(node.id);
      });
      removeBtn.addEventListener('mousedown', (e) => e.stopPropagation());
      g.appendChild(removeBtn);
    }

    // + / Add child button (bottom-right)
    if (onAddChild) {
      const addBtn = el('g', {
        class: 'tm-node-action tm-node-action--add',
        cursor: 'pointer',
      });
      addBtn.appendChild(el('circle', {
        cx: nodeWidth - 6,
        cy: nodeHeight - 6,
        r: 10,
        fill: 'rgba(74, 158, 255, 0.15)',
        stroke: '#4a9eff',
        'stroke-width': 1,
      }));
      addBtn.appendChild(el('text', {
        x: nodeWidth - 6,
        y: nodeHeight - 2,
        'text-anchor': 'middle',
        'font-size': 14,
        fill: '#4a9eff',
        'pointer-events': 'none',
        class: 'tm-node-action-label',
      }, '+'));
      addBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        onAddChild(node.id);
      });
      addBtn.addEventListener('mousedown', (e) => e.stopPropagation());
      g.appendChild(addBtn);
    }
  }

  return g;
}

// ── Sticky note renderer ──

const STICKY_COLORS = {
  yellow: '#fbbf24',
  blue:   '#60a5fa',
  green:  '#34d399',
  pink:   '#f472b6',
};

/**
 * Create a sticky note SVG group.
 *
 * @param {object} note - { id, text, color, ... }
 * @param {object} [options={}]
 * @param {boolean} [options.selected=false]
 * @param {boolean} [options.hovered=false]
 * @returns {SVGGElement}
 */
export function createStickyNoteSVG(note, options = {}) {
  const { selected = false, hovered = false } = options;

  const noteWidth = 200;
  const noteHeight = 120;
  const noteColor = STICKY_COLORS[note.color] || STICKY_COLORS.yellow;
  const rgb = hexToRgb(noteColor);

  // Random-ish rotation based on ID hash for visual variety
  let rotation = 0;
  if (note.id) {
    let h = 0;
    for (let i = 0; i < note.id.length; i++) {
      h = ((h << 3) - h + note.id.charCodeAt(i)) | 0;
    }
    rotation = (h % 5) - 2; // range: -2 to 2
  }

  const g = el('g', {
    class: [
      'tm-sticky-note',
      selected ? 'tm-sticky-note--selected' : '',
      hovered ? 'tm-sticky-note--hovered' : '',
    ].filter(Boolean).join(' '),
    'data-node-id': note.id,
    'data-node-kind': 'note',
    transform: `rotate(${rotation})`,
  });

  // Background rectangle
  g.appendChild(el('rect', {
    x: 0, y: 0,
    width: noteWidth,
    height: noteHeight,
    rx: 3, ry: 3,
    fill: `rgba(${rgb}, 0.15)`,
    stroke: `rgba(${rgb}, ${selected ? 0.8 : 0.4})`,
    'stroke-width': selected ? 2 : 1,
  }));

  // Top fold / ear
  const foldSize = 16;
  g.appendChild(el('path', {
    d: `M ${noteWidth - foldSize} 0 L ${noteWidth} 0 L ${noteWidth} ${foldSize} Z`,
    fill: `rgba(${rgb}, 0.25)`,
  }));

  // Note text via foreignObject (handwriting-style)
  const textFO = el('foreignObject', {
    x: 10, y: 10,
    width: noteWidth - 20,
    height: noteHeight - 20,
  });
  const textDiv = htmlEl('div', {
    xmlns: XHTML_NS,
    style: {
      fontSize: '12px',
      lineHeight: '1.4',
      color: noteColor,
      fontFamily: '"Segoe Print", "Comic Sans MS", "Patrick Hand", cursive, sans-serif',
      overflow: 'hidden',
      display: '-webkit-box',
      WebkitLineClamp: '5',
      WebkitBoxOrient: 'vertical',
      wordBreak: 'break-word',
    },
  }, note.text || note.label || '');
  textFO.appendChild(textDiv);
  g.appendChild(textFO);

  // Glow on hover/selection
  if (selected || hovered) {
    const glowId = uid('sticky-glow');
    const defs = el('defs');
    defs.appendChild(createGlowFilter(glowId, noteColor, `0 0 ${selected ? 10 : 6}px`));
    g.insertBefore(defs, g.firstChild);
    g.querySelector('rect').setAttribute('filter', `url(#${glowId})`);
  }

  return g;
}

export { createNodeSVG as default };
