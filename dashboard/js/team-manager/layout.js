// Sigil Dashboard — Team Manager Tree Layout Algorithm
//
// Pure-computation module. No DOM access, no npm dependencies.
// Implements a hierarchical (Dagre-like) tree layout using BFS ranking
// and centroid-based sibling positioning.

// ── Constants ──

const NODE_WIDTH = 280;
const NODE_HEIGHT = 110;
const NOTE_WIDTH = 200;
const NOTE_HEIGHT = 120;
const RANK_SEP = 80;   // vertical gap between depth levels
const NODE_SEP = 30;   // horizontal gap between siblings

// ── Internal helpers ──

/**
 * Collect all descendant IDs of a given node (recursive).
 * Used to hide entire subtrees when a group is collapsed.
 *
 * @param {string} nodeId
 * @param {Map<string, string[]>} childrenMap  parentId -> [childId, ...]
 * @param {Set<string>} result  accumulator set
 */
function _collectDescendants(nodeId, childrenMap, result) {
  const children = childrenMap.get(nodeId);
  if (!children) return;
  for (const childId of children) {
    result.add(childId);
    _collectDescendants(childId, childrenMap, result);
  }
}

/**
 * Find root nodes: nodes that are never a target in any edge, or nodes
 * whose parent is not in the node set at all.
 *
 * @param {Map<string, object>} treeNodes  id -> node
 * @param {Map<string, string>} parentMap   childId -> parentId
 * @returns {string[]}  root node IDs (stable sort by original array order)
 */
function _findRoots(treeNodes, parentMap) {
  const roots = [];
  for (const [id] of treeNodes) {
    const pid = parentMap.get(id);
    if (!pid || !treeNodes.has(pid)) {
      roots.push(id);
    }
  }
  return roots;
}

/**
 * Assign depth ranks via BFS starting from root nodes.
 * Returns Map<nodeId, rank> where rank 0 = root level.
 *
 * @param {string[]} roots
 * @param {Map<string, string[]>} childrenMap
 * @returns {Map<string, number>}
 */
function _assignRanks(roots, childrenMap) {
  const ranks = new Map();
  const queue = [];

  for (const rootId of roots) {
    ranks.set(rootId, 0);
    queue.push(rootId);
  }

  let head = 0;
  while (head < queue.length) {
    const current = queue[head++];
    const currentRank = ranks.get(current);
    const children = childrenMap.get(current);
    if (!children) continue;
    for (const childId of children) {
      if (!ranks.has(childId)) {
        ranks.set(childId, currentRank + 1);
        queue.push(childId);
      }
    }
  }

  return ranks;
}

/**
 * Compute positions for all tree nodes using a two-pass approach:
 *
 * Pass 1 (bottom-up): compute subtree widths so parents can be centered.
 * Pass 2 (top-down): assign x coordinates starting from root, distributing
 *   children symmetrically under each parent.
 *
 * @param {string[]} roots
 * @param {Map<string, string[]>} childrenMap
 * @param {Map<string, number>} ranks
 * @returns {Map<string, {x: number, y: number}>}
 */
function _computeTreePositions(roots, childrenMap, ranks) {
  // Pass 1: compute the full subtree width (in pixels) for each node.
  // A leaf node has width = NODE_WIDTH.
  // A parent node's width = sum(child widths) + NODE_SEP * (childCount - 1).
  const subtreeWidth = new Map();

  function calcWidth(nodeId) {
    const children = childrenMap.get(nodeId);
    if (!children || children.length === 0) {
      subtreeWidth.set(nodeId, NODE_WIDTH);
      return NODE_WIDTH;
    }
    let total = 0;
    for (const childId of children) {
      total += calcWidth(childId);
    }
    total += NODE_SEP * (children.length - 1);
    subtreeWidth.set(nodeId, total);
    return total;
  }

  for (const rootId of roots) {
    calcWidth(rootId);
  }

  // Pass 2: assign (x, y) coordinates top-down.
  // Multiple roots are laid out side by side with NODE_SEP gap between them.
  const positions = new Map();

  // Calculate total width of all root subtrees
  let totalRootWidth = 0;
  for (const rootId of roots) {
    totalRootWidth += subtreeWidth.get(rootId) || NODE_WIDTH;
  }
  totalRootWidth += NODE_SEP * Math.max(0, roots.length - 1);

  // Start roots centered around x=0
  let rootX = -totalRootWidth / 2;

  for (const rootId of roots) {
    const w = subtreeWidth.get(rootId) || NODE_WIDTH;
    _assignPositions(rootId, rootX + w / 2, 0, childrenMap, ranks, subtreeWidth, positions);
    rootX += w + NODE_SEP;
  }

  return positions;
}

/**
 * Recursive top-down position assignment.
 *
 * @param {string} nodeId
 * @param {number} centerX   the horizontal center for this node
 * @param {number} rank      depth level (used for y)
 * @param {Map<string, string[]>} childrenMap
 * @param {Map<string, number>} ranks
 * @param {Map<string, number>} subtreeWidth
 * @param {Map<string, {x: number, y: number}>} positions  output accumulator
 */
function _assignPositions(nodeId, centerX, rank, childrenMap, ranks, subtreeWidth, positions) {
  // Position is top-left corner (matching dagre convention of center minus half-width/height)
  const x = centerX - NODE_WIDTH / 2;
  const y = rank * (NODE_HEIGHT + RANK_SEP);
  positions.set(nodeId, { x, y });

  const children = childrenMap.get(nodeId);
  if (!children || children.length === 0) return;

  // Compute total width of all children subtrees
  let totalChildWidth = 0;
  for (const childId of children) {
    totalChildWidth += subtreeWidth.get(childId) || NODE_WIDTH;
  }
  totalChildWidth += NODE_SEP * (children.length - 1);

  // Distribute children centered under this node
  let childX = centerX - totalChildWidth / 2;
  for (const childId of children) {
    const childW = subtreeWidth.get(childId) || NODE_WIDTH;
    const childRank = ranks.get(childId);
    _assignPositions(childId, childX + childW / 2, childRank, childrenMap, ranks, subtreeWidth, positions);
    childX += childW + NODE_SEP;
  }
}

/**
 * Compute default stagger positions for sticky notes that have no
 * saved position. Notes are arranged in a grid offset from the main tree.
 *
 * @param {string[]} noteIds
 * @param {number} startX   left edge for note placement
 * @param {number} startY   top edge for note placement
 * @returns {Map<string, {x: number, y: number}>}
 */
function _staggerNotes(noteIds, startX, startY) {
  const positions = new Map();
  const cols = 3;
  const padX = NOTE_WIDTH + NODE_SEP;
  const padY = NOTE_HEIGHT + NODE_SEP;

  for (let i = 0; i < noteIds.length; i++) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    positions.set(noteIds[i], {
      x: startX + col * padX,
      y: startY + row * padY,
    });
  }
  return positions;
}

// ── Main layout function ──

/**
 * Compute a hierarchical tree layout for team-manager nodes.
 *
 * @param {object[]} nodes
 *   Array of node objects. Each must have at least:
 *     - id {string}
 *     - kind {string}  ('agent'|'group'|'human'|'skill'|'pipeline'|'context'|'note')
 *
 * @param {object[]} edges
 *   Array of edge objects. Each must have:
 *     - source_node_id {string}  (parent)
 *     - target_node_id {string}  (child)
 *   May also have: id, edge_type
 *
 * @param {Set<string>} collapsedGroups
 *   Set of node IDs whose children (and all descendants) should be hidden.
 *
 * @param {Object<string, {x: number, y: number}>} savedPositions
 *   Previously persisted positions. Keyed by node ID.
 *   Nodes with saved positions use those instead of computed layout positions.
 *
 * @returns {{
 *   positions: Map<string, {x: number, y: number}>,
 *   visibleNodeIds: Set<string>,
 *   visibleEdges: Array<{source: string, target: string, animated: boolean, style: {stroke: string, strokeWidth: number}}>
 * }}
 */
function layoutNodes(nodes, edges, collapsedGroups = new Set(), savedPositions = {}) {
  // ── 1. Build parent-child maps from edges ──

  // parentMap: childId -> parentId  (first edge wins if duplicates)
  const parentMap = new Map();
  // childrenMap: parentId -> [childId, ...]
  const childrenMap = new Map();

  for (const edge of edges) {
    const src = edge.source_node_id;
    const tgt = edge.target_node_id;
    if (!src || !tgt) continue;

    if (!parentMap.has(tgt)) {
      parentMap.set(tgt, src);
    }
    if (!childrenMap.has(src)) {
      childrenMap.set(src, []);
    }
    childrenMap.get(src).push(tgt);
  }

  // ── 2. Build set of hidden descendants (from collapsed groups) ──

  const hiddenIds = new Set();
  for (const collapsedId of collapsedGroups) {
    _collectDescendants(collapsedId, childrenMap, hiddenIds);
  }

  // ── 3. Partition into visible tree nodes vs. sticky notes ──

  const treeNodes = new Map();  // visible tree nodes
  const noteNodes = new Map();  // sticky notes (separate layout)

  for (const node of nodes) {
    if (hiddenIds.has(node.id)) continue;

    if (node.kind === 'note') {
      noteNodes.set(node.id, node);
    } else {
      treeNodes.set(node.id, node);
    }
  }

  // ── 4. Filter childrenMap to only include visible tree nodes ──

  const visibleChildrenMap = new Map();
  for (const [parentId, children] of childrenMap) {
    if (!treeNodes.has(parentId)) continue;
    const visibleChildren = children.filter(cid => treeNodes.has(cid));
    if (visibleChildren.length > 0) {
      visibleChildrenMap.set(parentId, visibleChildren);
    }
  }

  // ── 5. Find roots and assign ranks via BFS ──

  const roots = _findRoots(treeNodes, parentMap);
  const ranks = _assignRanks(roots, visibleChildrenMap);

  // Any tree nodes not reached by BFS (disconnected) get rank 0
  for (const [id] of treeNodes) {
    if (!ranks.has(id)) {
      ranks.set(id, 0);
    }
  }

  // Re-find roots to include disconnected nodes
  const allRoots = _findRoots(treeNodes, parentMap);

  // Disconnected nodes without children: treat as independent roots
  const connectedRoots = allRoots.filter(id => {
    return !parentMap.has(id) || !treeNodes.has(parentMap.get(id));
  });

  // ── 6. Compute tree positions ──

  const computedPositions = _computeTreePositions(connectedRoots, visibleChildrenMap, ranks);

  // ── 7. Assemble final positions (saved overrides computed) ──

  const positions = new Map();

  for (const [id] of treeNodes) {
    const saved = savedPositions[id];
    if (saved && typeof saved.x === 'number' && typeof saved.y === 'number') {
      positions.set(id, { x: saved.x, y: saved.y });
    } else {
      const computed = computedPositions.get(id);
      if (computed) {
        positions.set(id, computed);
      } else {
        // Fallback for orphan nodes not captured by tree layout
        positions.set(id, { x: 0, y: 0 });
      }
    }
  }

  // ── 8. Sticky note positions ──

  // Determine bounding box of tree nodes for note stagger offset
  let maxTreeX = 0;
  let minTreeY = 0;
  for (const [, pos] of computedPositions) {
    const rightEdge = pos.x + NODE_WIDTH;
    if (rightEdge > maxTreeX) maxTreeX = rightEdge;
    if (pos.y < minTreeY) minTreeY = pos.y;
  }

  const noteStartX = maxTreeX + NODE_SEP * 3;
  const noteStartY = minTreeY;

  const noteIdsNeedingLayout = [];
  for (const [id] of noteNodes) {
    const saved = savedPositions[id];
    if (saved && typeof saved.x === 'number' && typeof saved.y === 'number') {
      positions.set(id, { x: saved.x, y: saved.y });
    } else {
      noteIdsNeedingLayout.push(id);
    }
  }

  if (noteIdsNeedingLayout.length > 0) {
    const staggered = _staggerNotes(noteIdsNeedingLayout, noteStartX, noteStartY);
    for (const [id, pos] of staggered) {
      positions.set(id, pos);
    }
  }

  // ── 9. Compute visible IDs ──

  const visibleNodeIds = new Set();
  for (const [id] of treeNodes) visibleNodeIds.add(id);
  for (const [id] of noteNodes) visibleNodeIds.add(id);

  // ── 10. Compute visible edges ──

  // Determine which nodes are root-level to detect first-level edges
  const rootSet = new Set(connectedRoots);

  const visibleEdges = [];
  for (const edge of edges) {
    const src = edge.source_node_id;
    const tgt = edge.target_node_id;
    if (!visibleNodeIds.has(src) || !visibleNodeIds.has(tgt)) continue;

    const isFirstLevel = rootSet.has(src);
    visibleEdges.push({
      source: src,
      target: tgt,
      animated: isFirstLevel,
      style: { stroke: '#3a3a6a', strokeWidth: 1.5 },
    });
  }

  return { positions, visibleNodeIds, visibleEdges };
}

export { layoutNodes, NODE_WIDTH, NODE_HEIGHT, NOTE_WIDTH, NOTE_HEIGHT, RANK_SEP, NODE_SEP };
