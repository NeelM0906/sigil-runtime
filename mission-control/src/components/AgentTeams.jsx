import { useState, useEffect, useMemo } from 'react'
import { actiApi } from '../api'
import { useBeings } from '../context/BeingsContext'

// ── Sister color map ────────────────────────────────────────
const SISTER_COLORS = {
  prime: '#F97316',
  scholar: '#3B82F6',
  forge: '#EF4444',
  recovery: '#10B981',
  'sai-memory': '#8B5CF6',
}

const TIER_CONFIG = {
  'Being 🔥': { label: '🔥', color: '#EF4444', bg: 'bg-red-500/10' },
  'Contractor 🔵': { label: '🔵', color: '#3B82F6', bg: 'bg-blue-500/10' },
  'Baby ⚪': { label: '⚪', color: '#94A3B8', bg: 'bg-slate-500/10' },
}

function getTier(tierStr) {
  if (!tierStr) return TIER_CONFIG['Baby ⚪']
  if (tierStr.includes('🔥') || tierStr.toLowerCase().includes('being')) return TIER_CONFIG['Being 🔥']
  if (tierStr.includes('🔵') || tierStr.toLowerCase().includes('contractor')) return TIER_CONFIG['Contractor 🔵']
  return TIER_CONFIG['Baby ⚪']
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

const VIEWS = [
  { id: 'teams', label: 'Team Directory' },
  { id: 'roster', label: 'Being Roster' },
  { id: 'levers', label: 'Lever Matrix' },
]

// ── Main Component ──────────────────────────────────────────
export function AgentTeams() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('teams')
  const [clusterFilter, setClusterFilter] = useState({ tier: '', family: '', being: '', sister: '', search: '' })

  useEffect(() => {
    actiApi.architecture()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64 text-text-muted text-xs">Loading Agent Teams…</div>
  if (!data) return <div className="text-text-muted text-xs p-4">Failed to load architecture data.</div>

  const { beings, clusters, skill_families, levers, lever_matrix, stats } = data

  return (
    <div className="flex flex-col gap-3">
      {/* Stats bar */}
      <StatsBar stats={stats} />

      {/* View toggle */}
      <div className="flex items-center gap-1 bg-bg-secondary border border-border rounded-lg p-1">
        {VIEWS.map(v => (
          <button
            key={v.id}
            onClick={() => setView(v.id)}
            className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
              view === v.id
                ? 'bg-accent-blue/20 text-accent-blue'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      {/* View content */}
      {view === 'teams' && (
        <TeamDirectory
          clusters={clusters}
          beings={beings}
          filter={clusterFilter}
          setFilter={setClusterFilter}
          families={skill_families}
        />
      )}
      {view === 'roster' && (
        <BeingRoster beings={beings} />
      )}
      {view === 'levers' && (
        <LeverMatrix
          levers={levers}
          matrix={lever_matrix}
          beings={beings}
        />
      )}
    </div>
  )
}

// ── Stats Bar ───────────────────────────────────────────────
function StatsBar({ stats }) {
  const items = [
    { label: 'Beings', value: stats.total_beings, color: 'text-accent-blue' },
    { label: 'Teams', value: stats.total_clusters, color: 'text-accent-cyan' },
    { label: 'Positions', value: stats.total_positions.toLocaleString(), color: 'text-accent-green' },
    { label: 'Skill Families', value: stats.total_skill_families, color: 'text-accent-amber' },
    { label: 'Levers', value: stats.total_levers, color: 'text-accent-purple' },
  ]
  return (
    <div className="bg-bg-secondary border border-border rounded-lg px-4 py-2.5 flex items-center gap-6 flex-wrap">
      <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">Agent Teams</span>
      <div className="flex items-center gap-5">
        {items.map(it => (
          <div key={it.label} className="flex items-center gap-1.5">
            <span className={`text-sm font-bold font-mono ${it.color}`}>{it.value}</span>
            <span className="text-[10px] text-text-muted uppercase">{it.label}</span>
          </div>
        ))}
      </div>
      <div className="ml-auto flex items-center gap-3 text-[10px]">
        <span className="flex items-center gap-1">🔥 <span className="text-text-muted">Active</span></span>
        <span className="flex items-center gap-1">🔵 <span className="text-text-muted">Contractor</span></span>
        <span className="flex items-center gap-1">⚪ <span className="text-text-muted">Baby</span></span>
      </div>
    </div>
  )
}

// ── View 1: Team Directory (80 clusters) ────────────────────
function TeamDirectory({ clusters, beings, filter, setFilter, families }) {
  const [expandedCluster, setExpandedCluster] = useState(null)
  const familyNames = useMemo(() => [...new Set(clusters.map(c => c.family))].sort(), [clusters])
  const beingNames = useMemo(() => [...new Set(clusters.map(c => c.being))].sort(), [clusters])
  const sisterIds = useMemo(() => [...new Set(beings.filter(b => b.sister_id).map(b => b.sister_id))].sort(), [beings])

  const beingToSister = useMemo(() => {
    const m = {}
    beings.forEach(b => { m[b.name] = b.sister_id })
    return m
  }, [beings])

  const filtered = useMemo(() => {
    return clusters.filter(c => {
      if (filter.tier) {
        const tier = getTier(c.tier)
        if (filter.tier === 'active' && tier !== TIER_CONFIG['Being 🔥']) return false
        if (filter.tier === 'contractor' && tier !== TIER_CONFIG['Contractor 🔵']) return false
        if (filter.tier === 'baby' && tier !== TIER_CONFIG['Baby ⚪']) return false
      }
      if (filter.family && c.family !== filter.family) return false
      if (filter.being && c.being !== filter.being) return false
      if (filter.sister && beingToSister[c.being] !== filter.sister) return false
      if (filter.search) {
        const s = filter.search.toLowerCase()
        if (!c.name.toLowerCase().includes(s) && !c.function.toLowerCase().includes(s) && !c.being.toLowerCase().includes(s)) return false
      }
      return true
    })
  }, [clusters, filter, beingToSister])

  return (
    <div className="flex flex-col gap-2">
      {/* Filters */}
      <div className="bg-bg-secondary border border-border rounded-lg px-3 py-2 flex items-center gap-2 flex-wrap">
        <input
          type="text"
          placeholder="Search teams…"
          value={filter.search}
          onChange={e => setFilter({ ...filter, search: e.target.value })}
          className="bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary placeholder-text-muted w-48 outline-none focus:border-accent-blue"
        />
        <FilterSelect label="Tier" value={filter.tier} onChange={v => setFilter({ ...filter, tier: v })}
          options={[{ value: '', label: 'All' }, { value: 'active', label: '🔥 Active' }, { value: 'contractor', label: '🔵 Contractor' }, { value: 'baby', label: '⚪ Baby' }]}
        />
        <FilterSelect label="Family" value={filter.family} onChange={v => setFilter({ ...filter, family: v })}
          options={[{ value: '', label: 'All' }, ...familyNames.map(f => ({ value: f, label: f }))]}
        />
        <FilterSelect label="Being" value={filter.being} onChange={v => setFilter({ ...filter, being: v })}
          options={[{ value: '', label: 'All' }, ...beingNames.map(b => ({ value: b, label: b }))]}
        />
        <FilterSelect label="Sister" value={filter.sister} onChange={v => setFilter({ ...filter, sister: v })}
          options={[{ value: '', label: 'All' }, ...sisterIds.map(s => ({ value: s, label: s }))]}
        />
        <span className="text-[10px] text-text-muted ml-auto">{filtered.length} / {clusters.length} teams</span>
      </div>

      {/* Cluster grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
        {filtered.sort((a, b) => b.positions - a.positions).map(c => {
          const tier = getTier(c.tier)
          const sColor = SISTER_COLORS[beingToSister[c.being]] || '#6B7280'
          const isExpanded = expandedCluster === (c.id + c.family)

          return (
            <div
              key={c.id + c.family}
              className={`bg-bg-secondary border rounded-lg overflow-hidden cursor-pointer transition-colors ${
                isExpanded ? 'border-accent-blue/40' : 'border-border hover:border-border-bright'
              }`}
              onClick={() => setExpandedCluster(isExpanded ? null : (c.id + c.family))}
            >
              <div className="px-3 py-2">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs">{tier.label}</span>
                      <span className="text-xs font-semibold text-text-primary truncate">{c.name}</span>
                    </div>
                    <div className="text-[10px] text-text-muted truncate">{c.function}</div>
                  </div>
                  <span className="text-xs font-mono font-bold text-accent-cyan shrink-0">{c.positions}p</span>
                </div>
                <div className="flex items-center justify-between mt-1.5">
                  <span className="text-[9px] text-text-muted">{c.family}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[9px] text-text-secondary">{c.being}</span>
                    <span
                      className="px-1 py-0.5 text-[8px] font-bold rounded"
                      style={{ backgroundColor: sColor + '18', color: sColor }}
                    >
                      {beingToSister[c.being] || '?'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Expanded detail */}
              {isExpanded && (
                <div className="border-t border-border px-3 py-2 bg-bg-primary/50">
                  {c.description && (
                    <p className="text-[11px] text-text-secondary mb-2 leading-relaxed">{c.description}</p>
                  )}
                  <div className="flex items-center gap-3 text-[10px]">
                    <div className="flex items-center gap-1">
                      <span className="text-text-muted">Owner:</span>
                      <span className="text-text-primary font-medium">{c.being}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-text-muted">Family:</span>
                      <span className="text-text-primary">{c.family}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-text-muted">Tier:</span>
                      <span>{tier.label} {c.tier}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── View 2: Being Roster ────────────────────────────────────
function BeingRoster({ beings: actiBeings }) {
  const { beings: registryBeings, openBeingDetail } = useBeings()

  // Group ACT-I beings by sister
  const actiFromRegistry = registryBeings.filter(b => b.type === 'acti')
  const grouped = useMemo(() => {
    const groups = {}
    for (const b of actiFromRegistry) {
      const sister = b.tenant_id?.replace('tenant-', '') || 'unknown'
      if (!groups[sister]) groups[sister] = []
      groups[sister].push(b)
    }
    // Sort groups by sister name
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
  }, [actiFromRegistry])

  // Fallback: if no ACT-I beings registered yet, show from architecture data
  const showFromArch = actiFromRegistry.length === 0 && actiBeings.length > 0
  const archGrouped = useMemo(() => {
    if (!showFromArch) return []
    const groups = {}
    for (const b of actiBeings) {
      if (b.acti_id === 'Apex') continue
      const sister = b.sister_id || 'unknown'
      if (!groups[sister]) groups[sister] = []
      groups[sister].push(b)
    }
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
  }, [actiBeings, showFromArch])

  const displayGroups = showFromArch ? archGrouped : grouped

  return (
    <div className="flex flex-col gap-3">
      {displayGroups.map(([sister, sisterBeings]) => {
        const sColor = SISTER_COLORS[sister] || '#6B7280'
        return (
          <div key={sister} className="bg-bg-secondary border border-border rounded-lg overflow-hidden">
            {/* Sister header */}
            <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: sColor }} />
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: sColor }}>
                {sister}
              </span>
              <span className="text-[10px] text-text-muted">{sisterBeings.length} beings</span>
            </div>

            {/* Beings grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 p-2">
              {sisterBeings.map(b => {
                const isRegistered = !showFromArch
                return (
                  <div
                    key={b.id}
                    className="bg-bg-card border border-border rounded-lg px-3 py-2 hover:border-border-bright transition-colors cursor-pointer"
                    onClick={() => isRegistered && openBeingDetail(b.id)}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-sm font-semibold text-text-primary truncate">{b.name}</span>
                          {isRegistered && (
                            <span className="flex items-center gap-1">
                              <div className={`w-2 h-2 rounded-full ${b.status === 'online' ? 'bg-accent-green' : 'bg-text-muted'}`} />
                              <span className="text-[9px] text-text-muted uppercase">{b.status}</span>
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-text-muted truncate">
                          {b.domain || b.role || b.description || '—'}
                        </div>
                      </div>
                      <span className="text-[9px] px-1.5 py-0.5 rounded border font-bold text-accent-cyan bg-accent-cyan/10 border-accent-cyan/20">
                        ACT-I
                      </span>
                    </div>

                    {/* Clusters count + levers */}
                    <div className="flex items-center justify-between mt-1.5">
                      <div className="flex items-center gap-2 text-[9px] text-text-muted">
                        {b.clusters && <span>{b.clusters.length || (b.skills?.length || 0)} clusters</span>}
                        {b.positions > 0 && <span className="font-mono text-accent-cyan">{b.positions}p</span>}
                      </div>
                      {b.levers && b.levers.length > 0 && (
                        <div className="flex items-center gap-0.5">
                          {['0.5', '1', '2', '3', '4', '5', '6', '7'].map(lv => (
                            <div
                              key={lv}
                              className={`w-1.5 h-1.5 rounded-full ${
                                b.levers.includes(lv) ? 'bg-accent-blue' : 'bg-bg-hover'
                              }`}
                              title={`L${lv}: ${LEVER_LABELS[lv] || lv}`}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}

      {displayGroups.length === 0 && (
        <div className="text-text-muted text-xs text-center py-8">
          No ACT-I beings registered yet. They will appear after the next server restart.
        </div>
      )}
    </div>
  )
}

// ── View 3: Lever Matrix ────────────────────────────────────
function LeverMatrix({ levers, matrix, beings }) {
  const [hoveredLever, setHoveredLever] = useState(null)
  const [hoveredBeing, setHoveredBeing] = useState(null)

  // Only operational beings (those with lever data)
  const operationalBeings = beings
    .filter(b => matrix[b.id])
    .sort((a, b) => (matrix[b.id]?.length || 0) - (matrix[a.id]?.length || 0))

  return (
    <div className="bg-bg-secondary border border-border rounded-lg overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead>
          <tr>
            <th className="text-left px-3 py-2 text-[9px] font-semibold uppercase tracking-wider text-text-muted sticky left-0 bg-bg-secondary z-10 min-w-[160px]">
              Being
            </th>
            {levers.map(lv => (
              <th
                key={lv.id}
                className={`text-center px-1.5 py-2 text-[9px] font-semibold uppercase tracking-wider cursor-pointer transition-colors min-w-[70px] ${
                  hoveredLever === lv.id ? 'text-accent-blue bg-accent-blue/5' : 'text-text-muted'
                }`}
                onMouseEnter={() => setHoveredLever(lv.id)}
                onMouseLeave={() => setHoveredLever(null)}
                title={lv.name}
              >
                <div>L{lv.id}</div>
                <div className="text-[7px] font-normal normal-case tracking-normal mt-0.5 text-text-muted max-w-[70px] truncate">
                  {lv.name.split('/')[0].trim()}
                </div>
              </th>
            ))}
            <th className="text-center px-3 py-2 text-[9px] font-semibold uppercase tracking-wider text-text-muted">
              Coverage
            </th>
          </tr>
        </thead>
        <tbody>
          {operationalBeings.map(b => {
            const bLevers = matrix[b.id] || []
            const sColor = SISTER_COLORS[b.sister_id] || '#6B7280'
            const isHighlighted = hoveredBeing === b.id

            return (
              <tr
                key={b.id}
                className={`border-t border-border/50 transition-colors ${isHighlighted ? 'bg-bg-hover' : 'hover:bg-bg-hover'}`}
                onMouseEnter={() => setHoveredBeing(b.id)}
                onMouseLeave={() => setHoveredBeing(null)}
              >
                <td className="px-3 py-1.5 sticky left-0 bg-bg-secondary z-10">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-1.5 h-4 rounded-full shrink-0"
                      style={{ backgroundColor: sColor }}
                    />
                    <span className="font-medium text-text-primary truncate">{b.name}</span>
                    <span className="text-[9px] font-mono text-accent-cyan shrink-0">{b.positions}p</span>
                  </div>
                </td>
                {levers.map(lv => {
                  const has = bLevers.includes(lv.id)
                  const isColHighlight = hoveredLever === lv.id
                  return (
                    <td
                      key={lv.id}
                      className={`text-center py-1.5 transition-colors ${isColHighlight ? 'bg-accent-blue/5' : ''}`}
                    >
                      {has ? (
                        <div className="w-3 h-3 rounded-full bg-accent-blue mx-auto" />
                      ) : (
                        <div className="w-3 h-3 rounded-full bg-border/30 mx-auto" />
                      )}
                    </td>
                  )
                })}
                <td className="text-center py-1.5 font-mono text-[10px] text-text-secondary">
                  {bLevers.length}/{levers.length}
                </td>
              </tr>
            )
          })}
        </tbody>
        {/* Column totals */}
        <tfoot>
          <tr className="border-t border-border">
            <td className="px-3 py-1.5 text-[9px] font-semibold uppercase text-text-muted sticky left-0 bg-bg-secondary">
              Coverage
            </td>
            {levers.map(lv => {
              const count = operationalBeings.filter(b => (matrix[b.id] || []).includes(lv.id)).length
              return (
                <td key={lv.id} className="text-center py-1.5 font-mono text-[10px] text-text-secondary">
                  {count}/{operationalBeings.length}
                </td>
              )
            })}
            <td />
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

// ── Filter Select ───────────────────────────────────────────
function FilterSelect({ label, value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary outline-none focus:border-accent-blue appearance-none cursor-pointer"
      title={label}
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label === 'All' ? `${label}: All` : o.label}</option>
      ))}
    </select>
  )
}
