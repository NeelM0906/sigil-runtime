// Sigil Dashboard — Memory Panel

export function renderMemory(el, state, api) {
  const mem = state.get('memory') || {};

  const cards = [
    {
      title: 'Working / Episodic',
      items: [
        ['Notes', mem.working_notes || 0],
      ],
    },
    {
      title: 'Semantic',
      items: [
        ['Memories', mem.semantic_memories || 0],
        ['Archived', mem.archived_memories || 0],
      ],
    },
    {
      title: 'Procedural',
      items: [
        ['Strategies', mem.procedural_strategies || 0],
        ['Avg success', `${((mem.procedural_avg_success || 0) * 100).toFixed(1)}%`],
      ],
    },
    {
      title: 'Conversation',
      items: [
        ['Turns stored', mem.conversation_turns || 0],
        ['Summaries', mem.session_summaries || 0],
      ],
    },
  ];

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Memory System</span>
        <span class="badge">${(mem.semantic_memories || 0) + (mem.procedural_strategies || 0)} total</span>
      </div>
      <div class="flex gap-3 flex-wrap">
        ${cards.map(c => `
          <div style="flex:1;min-width:140px;border:1px solid hsl(var(--border)/0.5);border-radius:var(--radius);padding:var(--space-3)">
            <div class="text-xs text-muted font-medium mb-2">${c.title}</div>
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
