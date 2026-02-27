// Sigil Dashboard — Skills + Governance Panel

export function renderSkills(el, state, api) {
  const skills = state.get('skills') || {};
  const governance = state.get('governance') || {};

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Skills &amp; Governance</span>
        <div class="flex gap-2">
          <span class="badge">${skills.total || 0} skills</span>
          <span class="badge badge-success">${skills.active || 0} active</span>
        </div>
      </div>
      <div class="flex gap-3 flex-wrap">
        <!-- Skills summary -->
        <div style="flex:1;min-width:200px;border:1px solid hsl(var(--border)/0.5);border-radius:var(--radius);padding:var(--space-3)">
          <div class="text-xs text-muted font-medium mb-2">Registered Skills</div>
          <div class="stat-row"><span class="stat-label">Total</span><span class="stat-value">${skills.total || 0}</span></div>
          <div class="stat-row"><span class="stat-label">Active</span><span class="stat-value">${skills.active || 0}</span></div>
          <div class="stat-row"><span class="stat-label">Inactive</span><span class="stat-value">${(skills.total || 0) - (skills.active || 0)}</span></div>
        </div>
        <!-- Governance -->
        <div style="flex:1;min-width:200px;border:1px solid hsl(var(--border)/0.5);border-radius:var(--radius);padding:var(--space-3)">
          <div class="text-xs text-muted font-medium mb-2">Governance</div>
          <div class="stat-row">
            <span class="stat-label">Pending approvals</span>
            <span class="stat-value">
              ${governance.pending_approvals > 0
                ? `<span class="badge badge-warning">${governance.pending_approvals}</span>`
                : '<span class="badge badge-success">0</span>'}
            </span>
          </div>
        </div>
      </div>
    </div>`;
}
