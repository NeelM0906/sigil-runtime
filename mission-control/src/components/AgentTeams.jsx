import { useState, useEffect, useMemo, useCallback } from 'react'
import { actiApi, tasksApi } from '../api'
import { useBeings } from '../context/BeingsContext'

// ── Tier helpers ────────────────────────────────────────────
function getTierKey(tierStr) {
  if (!tierStr) return 'baby'
  if (tierStr.includes('🔥') || tierStr.toLowerCase().includes('being')) return 'active'
  if (tierStr.includes('🔵') || tierStr.toLowerCase().includes('contractor')) return 'contractor'
  return 'baby'
}

const TIER_ICON = { active: '🔥', contractor: '🔵', baby: '⚪' }
const TIER_LABEL = { active: 'Active', contractor: 'Contractor', baby: 'Baby' }
const TIER_BADGE_CLASS = {
  active: 'text-red-400 bg-red-500/10 border-red-500/20',
  contractor: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  baby: 'text-slate-400 bg-slate-500/10 border-slate-500/20',
}

const LEVER_LABELS = {
  '0.5': 'Shared Experiences',
  '1': 'Ecosystem / Partnerships',
  '2': 'Speaking / Content',
  '3': 'Revenue / Agreements',
  '4': 'Operations / Execution',
  '5': 'Analytics / Intelligence',
  '6': 'Community / Impact',
  '7': 'Production / Infrastructure',
}

// ── Main Component ──────────────────────────────────────────
export function AgentTeams() {
  const [data, setData] = useState(null)
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [groupBy, setGroupBy] = useState('family')
  const [filter, setFilter] = useState({ tier: '', family: '', search: '' })

  useEffect(() => {
    Promise.all([
      actiApi.architecture(),
      tasksApi.list().catch(() => ({ tasks: [] })),
    ]).then(([archData, taskData]) => {
      setData(archData)
      setTasks(taskData.tasks || [])
    }).catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleBack = useCallback(() => setSelectedTeam(null), [])

  if (loading) return <div className="flex items-center justify-center h-64 text-text-muted text-xs">Loading Agent Teams…</div>
  if (!data) return <div className="text-text-muted text-xs p-4">Failed to load architecture data.</div>

  const { beings, clusters, skill_families, levers, lever_matrix } = data

  if (selectedTeam) {
    return (
      <TeamDetail
        team={selectedTeam}
        clusters={clusters}
        beings={beings}
        tasks={tasks}
        levers={levers}
        leverMatrix={lever_matrix}
        sharedHeartSkills={data.shared_heart_skills || []}
        onBack={handleBack}
      />
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <TeamGrid
        clusters={clusters}
        beings={beings}
        tasks={tasks}
        families={skill_families}
        filter={filter}
        setFilter={setFilter}
        groupBy={groupBy}
        setGroupBy={setGroupBy}
        onSelectTeam={setSelectedTeam}
      />
    </div>
  )
}

// ── Team Grid (top-level view) ──────────────────────────────
function TeamGrid({ clusters, beings, tasks, families, filter, setFilter, groupBy, setGroupBy, onSelectTeam }) {
  const familyNames = useMemo(() => [...new Set(clusters.map(c => c.family))].sort(), [clusters])

  // Build being name → being data lookup
  const beingByName = useMemo(() => {
    const m = {}
    beings.forEach(b => { m[b.name] = b })
    return m
  }, [beings])

  // Task counts per being name
  const taskCountByBeing = useMemo(() => {
    const beingById = {}
    for (const b of beings) beingById[b.id] = b
    const m = {}
    for (const t of tasks) {
      if (t.status === 'done') continue
      for (const aid of (t.assignees || [])) {
        const b = beingById[aid]
        if (b) m[b.name] = (m[b.name] || 0) + 1
      }
    }
    return m
  }, [tasks, beings])

  const filtered = useMemo(() => {
    return clusters.filter(c => {
      if (filter.tier) {
        if (getTierKey(c.tier) !== filter.tier) return false
      }
      if (filter.family && c.family !== filter.family) return false
      if (filter.search) {
        const s = filter.search.toLowerCase()
        if (!c.name.toLowerCase().includes(s) &&
            !c.function.toLowerCase().includes(s) &&
            !c.being.toLowerCase().includes(s)) return false
      }
      return true
    })
  }, [clusters, filter])

  // Group by family or flat
  const grouped = useMemo(() => {
    if (groupBy === 'flat') {
      return [{ family: null, teams: [...filtered].sort((a, b) => a.name.localeCompare(b.name)) }]
    }
    const groups = {}
    for (const c of filtered) {
      if (!groups[c.family]) groups[c.family] = []
      groups[c.family].push(c)
    }
    return Object.entries(groups)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([family, teams]) => ({ family, teams: teams.sort((a, b) => a.name.localeCompare(b.name)) }))
  }, [filtered, groupBy])

  return (
    <div className="flex flex-col gap-3">
      {/* Toolbar */}
      <div className="bg-bg-secondary border border-border rounded-lg px-3 py-2 flex items-center gap-2 flex-wrap">
        <input
          type="text"
          placeholder="Search teams…"
          value={filter.search}
          onChange={e => setFilter({ ...filter, search: e.target.value })}
          className="bg-bg-primary border border-border rounded px-2.5 py-1.5 text-xs text-text-primary placeholder-text-muted w-56 outline-none focus:border-accent-blue"
        />
        <FilterSelect label="Tier" value={filter.tier} onChange={v => setFilter({ ...filter, tier: v })}
          options={[
            { value: '', label: 'All Tiers' },
            { value: 'active', label: '🔥 Active' },
            { value: 'contractor', label: '🔵 Contractor' },
            { value: 'baby', label: '⚪ Baby' },
          ]}
        />
        <FilterSelect label="Family" value={filter.family} onChange={v => setFilter({ ...filter, family: v })}
          options={[{ value: '', label: 'All Families' }, ...familyNames.map(f => ({ value: f, label: f }))]}
        />
        <div className="ml-auto flex items-center gap-1.5">
          <span className="text-[10px] text-text-muted mr-1">Group:</span>
          {[{ id: 'family', label: 'By Family' }, { id: 'flat', label: 'Flat' }].map(g => (
            <button
              key={g.id}
              onClick={() => setGroupBy(g.id)}
              className={`px-2 py-1 text-[10px] rounded transition-colors ${
                groupBy === g.id ? 'bg-accent-blue/20 text-accent-blue' : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              {g.label}
            </button>
          ))}
          <span className="text-[10px] text-text-muted ml-2">{filtered.length} teams</span>
        </div>
      </div>

      {/* Groups */}
      {grouped.map(({ family, teams }) => (
        <div key={family || 'flat'}>
          {family && (
            <div className="flex items-center gap-2 mb-2 px-1">
              <div className="w-1 h-4 rounded-full bg-accent-blue" />
              <span className="text-xs font-semibold text-text-primary">{family}</span>
              <span className="text-[10px] text-text-muted">{teams.length} teams</span>
              <div className="flex-1 h-px bg-border ml-2" />
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2 mb-3">
            {teams.map(c => {
              const tierKey = getTierKey(c.tier)
              const pm = beingByName[c.being]
              const activeTasks = taskCountByBeing[c.being] || 0

              return (
                <div
                  key={c.id + c.family}
                  onClick={() => onSelectTeam(c)}
                  className="bg-bg-secondary border border-border rounded-lg px-3 py-2.5 cursor-pointer hover:border-accent-blue/40 hover:bg-bg-hover transition-all group"
                >
                  {/* Row 1: Name + tier */}
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-sm font-semibold text-text-primary truncate group-hover:text-accent-blue transition-colors">
                      {c.name}
                    </span>
                    <span className={`px-1.5 py-0.5 text-[9px] font-semibold rounded border shrink-0 ${TIER_BADGE_CLASS[tierKey]}`}>
                      {TIER_ICON[tierKey]} {TIER_LABEL[tierKey]}
                    </span>
                  </div>

                  {/* Row 2: Purpose */}
                  <div className="text-[11px] text-text-secondary truncate mb-2">{c.function}</div>

                  {/* Row 3: PM + Family badge */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-[10px] text-text-muted">PM:</span>
                      <span className="text-[10px] text-text-primary font-medium truncate">
                        {c.being}
                      </span>
                    </div>
                    <span className="px-1.5 py-0.5 text-[9px] rounded bg-accent-blue/10 text-accent-blue border border-accent-blue/20 shrink-0 truncate max-w-[120px]">
                      {c.family}
                    </span>
                  </div>

                  {/* Row 4: Tasks indicator */}
                  {activeTasks > 0 && (
                    <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-border/50">
                      <div className="w-1.5 h-1.5 rounded-full bg-accent-blue animate-pulse" />
                      <span className="text-[10px] text-accent-blue">{activeTasks} active task{activeTasks !== 1 ? 's' : ''}</span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {filtered.length === 0 && (
        <div className="text-text-muted text-xs text-center py-12">No teams match your filters.</div>
      )}
    </div>
  )
}

// ── Team Detail View ────────────────────────────────────────
function TeamDetail({ team, clusters, beings, tasks, levers, leverMatrix, sharedHeartSkills, onBack }) {
  const { beings: registryBeings, openBeingDetail } = useBeings()
  const tierKey = getTierKey(team.tier)

  // Find PM being (from both architecture beings and registry)
  const pmBeing = beings.find(b => b.name === team.being)
  const pmRegistry = registryBeings.find(b => b.name === team.being)
  const pmBeingId = pmRegistry?.id || pmBeing?.id

  // Related clusters owned by the same PM (for context, not "members")
  const relatedClusters = useMemo(
    () => clusters.filter(c => c.being === team.being && c.id !== team.id),
    [clusters, team.being, team.id]
  )

  // Lever coverage from PM being
  const pmLevers = pmBeing?.levers || []

  // Tasks assigned to PM being
  const teamTasks = useMemo(() => {
    if (!pmBeingId) return []
    return tasks.filter(t =>
      (t.assignees || []).includes(pmBeingId) && t.status !== 'done'
    )
  }, [tasks, pmBeingId])

  return (
    <div className="flex flex-col gap-3 max-w-5xl">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-xs text-text-muted hover:text-accent-blue transition-colors self-start"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        All Teams
      </button>

      {/* ── Header ──────────────────────────────────────── */}
      <div className="bg-bg-secondary border border-border rounded-lg p-4">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <h1 className="text-lg font-bold text-text-primary">{team.name}</h1>
              <span className={`px-2 py-0.5 text-[10px] font-semibold rounded border ${TIER_BADGE_CLASS[tierKey]}`}>
                {TIER_ICON[tierKey]} {TIER_LABEL[tierKey]}
              </span>
            </div>
            <p className="text-sm text-text-secondary mb-2">{team.function}</p>
            <span className="px-2 py-0.5 text-[10px] rounded bg-accent-blue/10 text-accent-blue border border-accent-blue/20">
              {team.family}
            </span>
          </div>
        </div>

        {/* PM row */}
        <div className="flex items-center gap-3 pt-3 border-t border-border">
          <span className="text-[10px] text-text-muted uppercase tracking-wider">Project Manager</span>
          <button
            onClick={() => pmBeingId && openBeingDetail(pmBeingId)}
            className="flex items-center gap-2 px-2 py-1 rounded bg-bg-card border border-border hover:border-accent-blue/40 transition-colors"
          >
            <div className="w-5 h-5 rounded flex items-center justify-center text-[10px] bg-accent-cyan/15 text-accent-cyan font-bold">
              🎯
            </div>
            <span className="text-xs font-medium text-text-primary">{team.being}</span>
            {pmRegistry && (
              <span className="flex items-center gap-1">
                <div className={`w-1.5 h-1.5 rounded-full ${pmRegistry.status === 'online' ? 'bg-accent-green' : pmRegistry.status === 'busy' ? 'bg-accent-amber' : 'bg-text-muted'}`} />
                <span className="text-[9px] text-text-muted">{pmRegistry.status}</span>
              </span>
            )}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* ── Left column: Members + Tasks ─────────────── */}
        <div className="lg:col-span-2 flex flex-col gap-3">
          {/* Team Positions */}
          <DetailSection title="Positions" icon="👥" count={team.positions || 0}>
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between px-2.5 py-1.5 rounded bg-bg-card border border-border">
                <span className="text-xs text-text-primary">{team.name}</span>
                <span className="text-[10px] font-mono text-accent-cyan">{team.positions || 0}p</span>
              </div>
              <div className="text-[10px] text-text-secondary px-2.5 py-1">{team.function}</div>
            </div>
            {relatedClusters.length > 0 && (
              <div className="mt-2 pt-2 border-t border-border">
                <div className="text-[9px] text-text-muted uppercase tracking-wider mb-1 px-2.5">Related clusters by same PM</div>
                {relatedClusters.map(c => (
                  <div
                    key={c.id}
                    className="flex items-center justify-between px-2.5 py-1 rounded hover:bg-bg-hover transition-colors"
                  >
                    <div className="min-w-0">
                      <div className="text-[10px] text-text-primary truncate">{c.name}</div>
                    </div>
                    <span className="text-[9px] font-mono text-text-muted shrink-0">{c.positions || 0}p</span>
                  </div>
                ))}
              </div>
            )}
          </DetailSection>

          {/* Tasks Section */}
          <DetailSection title="Active Tasks" icon="📋" count={teamTasks.length}>
            {teamTasks.length > 0 ? (
              <div className="flex flex-col gap-1">
                {teamTasks.map(t => (
                  <div key={t.id} className="flex items-center justify-between px-2.5 py-1.5 rounded bg-bg-card border border-border">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                        t.status === 'in_progress' ? 'bg-accent-blue' :
                        t.status === 'in_review' ? 'bg-accent-amber' : 'bg-text-muted'
                      }`} />
                      <span className="text-xs text-text-primary truncate">{t.title}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {t.priority && t.priority !== 'normal' && (
                        <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${
                          t.priority === 'critical' ? 'text-accent-red bg-accent-red/10' :
                          t.priority === 'high' ? 'text-accent-amber bg-accent-amber/10' :
                          'text-text-muted bg-bg-hover'
                        }`}>
                          {t.priority.toUpperCase()}
                        </span>
                      )}
                      <span className="text-[9px] text-text-muted capitalize">{t.status?.replace('_', ' ')}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-text-muted italic py-2">No active tasks assigned to this team.</div>
            )}
          </DetailSection>

          {/* About Section */}
          {team.description && (
            <DetailSection title="About" icon="📄">
              <p className="text-xs text-text-secondary leading-relaxed whitespace-pre-wrap">{team.description}</p>
            </DetailSection>
          )}
        </div>

        {/* ── Right column: Stats + Skills ─────────────── */}
        <div className="flex flex-col gap-3">
          {/* Team Stats */}
          <DetailSection title="Team Stats" icon="📊">
            <div className="flex flex-col gap-2">
              {/* Member counts */}
              <div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mb-1">Members by Tier</div>
                <div className="flex items-center gap-3">
                  {['active', 'contractor', 'baby'].map(tk => {
                    const count = pmClusters.filter(c => getTierKey(c.tier) === tk).length
                    return (
                      <div key={tk} className="flex items-center gap-1">
                        <span className="text-xs">{TIER_ICON[tk]}</span>
                        <span className="text-xs font-bold text-text-primary">{count}</span>
                        <span className="text-[9px] text-text-muted">{TIER_LABEL[tk]}</span>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Lever coverage */}
              {pmLevers.length > 0 && (
                <div>
                  <div className="text-[9px] text-text-muted uppercase tracking-wider mb-1">Lever Coverage</div>
                  <div className="flex flex-wrap gap-1">
                    {pmLevers.map(lv => (
                      <span key={lv} className="px-1.5 py-0.5 text-[9px] bg-accent-blue/10 text-accent-blue rounded border border-accent-blue/20" title={LEVER_LABELS[lv]}>
                        L{lv}
                      </span>
                    ))}
                  </div>
                  <div className="text-[9px] text-text-muted mt-1">{pmLevers.length}/8 levers</div>
                </div>
              )}

              {/* Family */}
              <div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mb-1">Skill Family</div>
                <span className="px-2 py-0.5 text-[10px] rounded bg-accent-blue/10 text-accent-blue border border-accent-blue/20">
                  {team.family}
                </span>
              </div>
            </div>
          </DetailSection>

          {/* Skills & Tools */}
          <DetailSection title="Skills & Tools" icon="🛠">
            <div className="flex flex-col gap-2">
              {/* Heart Skills */}
              <div>
                <div className="text-[9px] text-text-muted uppercase tracking-wider mb-1">Heart Skills (shared)</div>
                <div className="flex flex-wrap gap-1">
                  {(sharedHeartSkills || []).map(s => (
                    <span key={typeof s === 'string' ? s : s.name} className="px-1.5 py-0.5 text-[9px] bg-accent-purple/10 text-accent-purple rounded border border-accent-purple/20">
                      {typeof s === 'string' ? s : s.name}
                    </span>
                  ))}
                </div>
              </div>

              {/* PM's tools/skills from registry */}
              {pmRegistry && (pmRegistry.skills || []).length > 0 && (
                <div>
                  <div className="text-[9px] text-text-muted uppercase tracking-wider mb-1">PM Capabilities</div>
                  <div className="flex flex-wrap gap-1">
                    {pmRegistry.skills.map(s => (
                      <span key={s} className="px-1.5 py-0.5 text-[9px] bg-accent-green/10 text-accent-green rounded border border-accent-green/20">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </DetailSection>
        </div>
      </div>
    </div>
  )
}

// ── Detail Section ──────────────────────────────────────────
function DetailSection({ title, icon, count, children }) {
  return (
    <div className="bg-bg-secondary border border-border rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
        <span className="text-xs">{icon}</span>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary flex-1">{title}</span>
        {count !== undefined && (
          <span className="text-[10px] font-mono text-accent-blue">{count}</span>
        )}
      </div>
      <div className="p-3">{children}</div>
    </div>
  )
}

// ── Filter Select ───────────────────────────────────────────
function FilterSelect({ label, value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="bg-bg-primary border border-border rounded px-2 py-1.5 text-xs text-text-primary outline-none focus:border-accent-blue appearance-none cursor-pointer"
      title={label}
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}
