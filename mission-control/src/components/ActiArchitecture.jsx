import { useState, useEffect, useMemo } from 'react'
import { actiApi } from '../api'

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
  { id: 'beings', label: 'Being Hierarchy' },
  { id: 'families', label: 'Skill Families' },
  { id: 'clusters', label: 'Cluster Teams' },
  { id: 'levers', label: 'Lever Matrix' },
]

// ── Main Component ──────────────────────────────────────────
export function ActiArchitecture() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('beings')
  const [expandedBeing, setExpandedBeing] = useState(null)
  const [clusterFilter, setClusterFilter] = useState({ tier: '', family: '', being: '', sister: '', search: '' })

  useEffect(() => {
    actiApi.architecture()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64 text-text-muted text-xs">Loading ACT-I Architecture…</div>
  if (!data) return <div className="text-text-muted text-xs p-4">Failed to load architecture data.</div>

  const { beings, clusters, skill_families, levers, lever_matrix, stats, being_sister_map, shared_heart_skills } = data

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
      {view === 'beings' && (
        <BeingHierarchy
          beings={beings}
          expandedBeing={expandedBeing}
          setExpandedBeing={setExpandedBeing}
        />
      )}
      {view === 'families' && (
        <SkillFamilies
          families={skill_families}
          clusters={clusters}
          beings={beings}
        />
      )}
      {view === 'clusters' && (
        <ClusterTeams
          clusters={clusters}
          beings={beings}
          filter={clusterFilter}
          setFilter={setClusterFilter}
          families={skill_families}
        />
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
    { label: 'Clusters', value: stats.total_clusters, color: 'text-accent-cyan' },
    { label: 'Positions', value: stats.total_positions.toLocaleString(), color: 'text-accent-green' },
    { label: 'Skill Families', value: stats.total_skill_families, color: 'text-accent-amber' },
    { label: 'Levers', value: stats.total_levers, color: 'text-accent-purple' },
  ]
  return (
    <div className="bg-bg-secondary border border-border rounded-lg px-4 py-2.5 flex items-center gap-6 flex-wrap">
      <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">ACT-I Architecture</span>
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

// ── View 1: Being Hierarchy ─────────────────────────────────
function BeingHierarchy({ beings, expandedBeing, setExpandedBeing }) {
  // Separate apex and operational
  const apex = beings.filter(b => b.type && (b.type.includes('Apex') || b.acti_id === 'Apex'))
  const operational = beings.filter(b => !b.type || (!b.type.includes('Apex') && b.acti_id !== 'Apex'))

  return (
    <div className="flex flex-col gap-3">
      {/* Apex beings */}
      {apex.length > 0 && (
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-1.5 px-1">Apex</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {apex.map(b => (
              <BeingCard
                key={b.id}
                being={b}
                expanded={expandedBeing === b.id}
                onToggle={() => setExpandedBeing(expandedBeing === b.id ? null : b.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Operational beings */}
      <div>
        <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-1.5 px-1">
          Operational Beings ({operational.length})
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
          {operational.sort((a, b) => b.positions - a.positions).map(b => (
            <BeingCard
              key={b.id}
              being={b}
              expanded={expandedBeing === b.id}
              onToggle={() => setExpandedBeing(expandedBeing === b.id ? null : b.id)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function BeingCard({ being, expanded, onToggle }) {
  const sisterColor = SISTER_COLORS[being.sister_id] || '#6B7280'

  return (
    <div className="bg-bg-secondary border border-border rounded-lg overflow-hidden">
      {/* Card header — always visible */}
      <button
        onClick={onToggle}
        className="w-full text-left px-3 py-2.5 hover:bg-bg-hover transition-colors"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-sm font-semibold text-text-primary truncate">{being.name}</span>
              {being.acti_id && being.acti_id !== 'Apex' && (
                <span className="text-[9px] font-mono text-text-muted">#{being.acti_id}</span>
              )}
            </div>
            <div className="text-[10px] text-text-muted truncate">{being.domain || being.type || '—'}</div>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            {being.positions > 0 && (
              <span className="text-xs font-bold font-mono text-accent-cyan">{being.positions}p</span>
            )}
            <span
              className="px-1.5 py-0.5 text-[9px] font-bold rounded border"
              style={{
                backgroundColor: sisterColor + '18',
                color: sisterColor,
                borderColor: sisterColor + '40',
              }}
            >
              {being.sister_id}
            </span>
          </div>
        </div>

        {/* Lever dots */}
        {being.levers && being.levers.length > 0 && (
          <div className="flex items-center gap-1 mt-1.5">
            {['0.5', '1', '2', '3', '4', '5', '6', '7'].map(lv => (
              <div
                key={lv}
                className={`w-2 h-2 rounded-full ${
                  being.levers.includes(lv) ? 'bg-accent-blue' : 'bg-bg-hover'
                }`}
                title={`L${lv}: ${LEVER_LABELS[lv] || lv}`}
              />
            ))}
            <span className="text-[9px] text-text-muted ml-1">{being.clusters?.length || 0} clusters</span>
          </div>
        )}
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-border px-3 py-2 bg-bg-primary/50">
          {/* Clusters list */}
          {being.clusters && being.clusters.length > 0 && (
            <div className="mb-2">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-text-muted mb-1">Clusters</div>
              <div className="flex flex-col gap-0.5">
                {being.clusters.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-text-primary font-medium truncate">{c.name}</span>
                      <span className="text-text-muted truncate">— {c.function}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-2">
                      <span className="text-[9px] text-text-muted">{c.family}</span>
                      <span className="text-[10px] font-mono text-accent-cyan">{c.positions}p</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Levers detail */}
          {being.levers && being.levers.length > 0 && (
            <div className="mb-2">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-text-muted mb-1">Lever Coverage</div>
              <div className="flex flex-wrap gap-1">
                {being.levers.map(lv => (
                  <span key={lv} className="px-1.5 py-0.5 text-[9px] bg-accent-blue/10 text-accent-blue rounded border border-accent-blue/20">
                    L{lv}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Heart skills */}
          {being.shared_heart_skills && (
            <div>
              <div className="text-[9px] font-semibold uppercase tracking-wider text-text-muted mb-1">Heart Skills</div>
              <div className="flex flex-wrap gap-1">
                {being.shared_heart_skills.map(s => (
                  <span key={s} className="px-1.5 py-0.5 text-[9px] bg-accent-purple/10 text-accent-purple rounded border border-accent-purple/20">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── View 2: Skill Families ──────────────────────────────────
function SkillFamilies({ families, clusters, beings }) {
  const [expandedFamily, setExpandedFamily] = useState(null)

  return (
    <div className="flex flex-col gap-2">
      {families.map(fam => {
        const famClusters = clusters.filter(c => c.family === fam.name)
        const isExpanded = expandedFamily === fam.name

        return (
          <div key={fam.name} className="bg-bg-secondary border border-border rounded-lg overflow-hidden">
            <button
              onClick={() => setExpandedFamily(isExpanded ? null : fam.name)}
              className="w-full text-left px-3 py-2.5 hover:bg-bg-hover transition-colors flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-text-primary">{fam.name}</span>
                <span className="text-[10px] text-text-muted">{fam.clusters_count} clusters</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono font-bold text-accent-cyan">{fam.positions.toLocaleString()}p</span>
                <div className="flex items-center gap-1">
                  {fam.key_beings.map(kb => {
                    const being = beings.find(b => b.name === kb.trim())
                    const sColor = being ? SISTER_COLORS[being.sister_id] : '#6B7280'
                    return (
                      <span
                        key={kb}
                        className="px-1 py-0.5 text-[8px] font-bold rounded"
                        style={{ backgroundColor: sColor + '18', color: sColor }}
                        title={kb.trim()}
                      >
                        {being?.sister_id || '?'}
                      </span>
                    )
                  })}
                </div>
                <span className="text-text-muted text-xs">{isExpanded ? '▾' : '▸'}</span>
              </div>
            </button>

            {isExpanded && (
              <div className="border-t border-border">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="text-text-muted text-[9px] uppercase tracking-wider">
                      <th className="text-left px-3 py-1.5 font-semibold">Cluster</th>
                      <th className="text-left px-3 py-1.5 font-semibold">Function</th>
                      <th className="text-left px-3 py-1.5 font-semibold">Being</th>
                      <th className="text-center px-3 py-1.5 font-semibold">Tier</th>
                      <th className="text-right px-3 py-1.5 font-semibold">Positions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {famClusters.sort((a, b) => b.positions - a.positions).map(c => {
                      const tier = getTier(c.tier)
                      return (
                        <tr key={c.id} className="border-t border-border/50 hover:bg-bg-hover">
                          <td className="px-3 py-1.5 font-medium text-text-primary">{c.name}</td>
                          <td className="px-3 py-1.5 text-text-secondary">{c.function}</td>
                          <td className="px-3 py-1.5 text-text-secondary">{c.being}</td>
                          <td className="px-3 py-1.5 text-center">{tier.label}</td>
                          <td className="px-3 py-1.5 text-right font-mono text-accent-cyan">{c.positions}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── View 3: Cluster Teams ───────────────────────────────────
function ClusterTeams({ clusters, beings, filter, setFilter, families }) {
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
          placeholder="Search clusters…"
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
        <span className="text-[10px] text-text-muted ml-auto">{filtered.length} / {clusters.length}</span>
      </div>

      {/* Cluster grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
        {filtered.sort((a, b) => b.positions - a.positions).map(c => {
          const tier = getTier(c.tier)
          const sColor = SISTER_COLORS[beingToSister[c.being]] || '#6B7280'

          return (
            <div key={c.id + c.family} className="bg-bg-secondary border border-border rounded-lg px-3 py-2">
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
          )
        })}
      </div>
    </div>
  )
}

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

// ── View 4: Lever Matrix ────────────────────────────────────
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
