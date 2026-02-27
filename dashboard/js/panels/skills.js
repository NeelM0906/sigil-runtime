// Sigil Dashboard — Skills + Governance Panel

export function renderSkills(el, state, api) {
  const skills = state.get('skills') || {};
  const governance = state.get('governance') || {};

  const inactive = (skills.total || 0) - (skills.active || 0);
  const pendingApprovals = governance.pending_approvals || 0;

  el.innerHTML = `
    <div class="card" style="height:100%">
      <div class="card-header">
        <span class="card-title">Skills &amp; Governance</span>
        <div class="flex gap-1">
          <span class="badge">${skills.total || 0}</span>
          ${pendingApprovals > 0 ? `<span class="badge badge-warning">${pendingApprovals} pending</span>` : ''}
        </div>
      </div>
      <div class="flex gap-3 flex-wrap">
        <div class="sub-card" style="flex:1;min-width:160px">
          <div class="sub-card-title">Skills</div>
          <div class="stat-row"><span class="stat-label">Total</span><span class="stat-value">${skills.total || 0}</span></div>
          <div class="stat-row"><span class="stat-label">Active</span><span class="stat-value" style="color:hsl(var(--success))">${skills.active || 0}</span></div>
          ${inactive > 0 ? `<div class="stat-row"><span class="stat-label">Inactive</span><span class="stat-value" style="opacity:0.5">${inactive}</span></div>` : ''}
        </div>
        <div class="sub-card" style="flex:1;min-width:160px">
          <div class="sub-card-title">Governance</div>
          <div class="stat-row">
            <span class="stat-label">Pending</span>
            <span class="stat-value">
              ${pendingApprovals > 0
                ? `<span style="color:hsl(var(--warning))">${pendingApprovals}</span>`
                : '<span style="color:hsl(var(--success))">0</span>'}
            </span>
          </div>
        </div>
      </div>
    </div>`;
}
