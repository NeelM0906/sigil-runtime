// Sigil Dashboard — Memory Panel

export function renderMemory(el, state, api) {
  const mem = state.get('memory') || {};

  const cards = [
    {
      title: 'Working',
      icon: '&#128221;',
      items: [['Notes', mem.working_notes || 0]],
    },
    {
      title: 'Semantic',
      icon: '&#129504;',
      items: [
        ['Active', mem.semantic_memories || 0],
        ['Archived', mem.archived_memories || 0],
      ],
    },
    {
      title: 'Procedural',
      icon: '&#9881;',
      items: [
        ['Strategies', mem.procedural_strategies || 0],
        ['Avg success', `${((mem.procedural_avg_success || 0) * 100).toFixed(1)}%`],
      ],
    },
    {
      title: 'History',
      icon: '&#128172;',
      items: [
        ['Turns', mem.conversation_turns || 0],
        ['Summaries', mem.session_summaries || 0],
      ],
    },
  ];

  const totalCount = (mem.semantic_memories || 0) + (mem.procedural_strategies || 0) + (mem.working_notes || 0);

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Memory</span>
        <span class="badge">${totalCount} total</span>
      </div>
      <div class="flex gap-3 flex-wrap" role="group" aria-label="Memory subsystems">
        ${cards.map(c => `
          <div class="sub-card" style="flex:1;min-width:130px">
            <div class="sub-card-title">${c.title}</div>
            ${c.items.map(([label, val]) => `
              <div class="stat-row">
                <span class="stat-label">${label}</span>
                <span class="stat-value">${val}</span>
              </div>
            `).join('')}
          </div>
        `).join('')}
      </div>
    </div>`;
}
