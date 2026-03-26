import { useState } from 'react'
import { useBeings } from '../context/BeingsContext'

const STATUS_COLORS = {
  online: 'bg-accent-green',
  busy: 'bg-accent-amber',
  idle: 'bg-accent-cyan',
  offline: 'bg-text-muted',
}

const STATUS_LABELS = {
  online: 'Online',
  busy: 'Busy',
  idle: 'Idle',
  offline: 'Offline',
}

const TYPE_BADGES = {
  runtime: { label: 'PRIMARY', color: 'text-accent-orange bg-accent-orange/10 border-accent-orange/20' },
  sister: { label: 'SISTER', color: 'text-accent-purple bg-accent-purple/10 border-accent-purple/20' },
  voice: { label: 'VOICE', color: 'text-accent-pink bg-accent-pink/10 border-accent-pink/20' },
  subagent: { label: 'SUB-AGENT', color: 'text-accent-amber bg-accent-amber/10 border-accent-amber/20' },
  acti: { label: 'ACT-I', color: 'text-accent-cyan bg-accent-cyan/10 border-accent-cyan/20' },
  custom: { label: 'CUSTOM', color: 'text-text-muted bg-bg-hover border-border' },
}

// Section config: core beings only
const SECTIONS = [
  { key: 'sai', label: 'SAI', dot: 'bg-accent-orange', types: ['runtime'] },
  { key: 'sisters', label: 'Sisters', dot: 'bg-accent-purple', types: ['sister'] },
]

function BeingCard({ being, isExpanded, onToggle, onOpenDetail }) {
  const typeBadge = TYPE_BADGES[being.type] || TYPE_BADGES.custom
  const isVoice = being.type === 'voice'

  return (
    <div
      className={`border rounded-lg transition-all ${
        isExpanded ? 'border-border-bright bg-bg-hover' : 'border-border bg-bg-card hover:bg-bg-hover'
      }`}
    >
      {/* Header row */}
      <div className="flex items-center gap-3 p-3 cursor-pointer" onClick={onToggle}>
        {/* Avatar */}
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold shrink-0"
          style={{ backgroundColor: being.color + '22', color: being.color }}
        >
          {being.avatar}
        </div>

        {/* Name + Role */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{being.name}</span>
            {!isVoice && (
              <span className="flex items-center gap-1 px-1">
                <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[being.status]}`} />
                <span className="text-[10px] text-text-muted uppercase">{STATUS_LABELS[being.status]}</span>
              </span>
            )}
            {isVoice && (
              <span className="flex items-center gap-1 px-1">
                <div className="w-2 h-2 rounded-full bg-text-muted" />
                <span className="text-[10px] text-text-muted uppercase">API</span>
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-text-secondary truncate">{being.role}</span>
            <span className={`px-1 py-0 text-[9px] font-bold rounded border ${typeBadge.color}`}>
              {typeBadge.label}
            </span>
          </div>
        </div>

        {/* Expand chevron */}
        <svg
          className={`w-4 h-4 text-text-muted transition-transform shrink-0 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Expanded preview */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-0 border-t border-border">
          <p className="text-xs text-text-secondary mt-2 mb-2 leading-relaxed">{being.description}</p>

          {(being.tools || []).length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {being.tools.slice(0, 4).map(t => (
                <span key={typeof t === 'string' ? t : t.name} className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-accent-blue/10 text-accent-blue border border-accent-blue/20">
                  {typeof t === 'string' ? t : t.name}
                </span>
              ))}
              {being.tools.length > 4 && (
                <span className="px-1.5 py-0.5 text-[10px] text-text-muted">+{being.tools.length - 4} more</span>
              )}
            </div>
          )}

          {(being.skills || []).length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {being.skills.map(s => (
                <span key={s} className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-accent-green/10 text-accent-green border border-accent-green/20">
                  {s}
                </span>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between mt-2">
            <div className="flex items-center gap-2 text-[10px] text-text-muted">
              {being.model_id && <span className="font-mono">{being.model_id}</span>}
              {being.agent_id && <><span>|</span><span className="font-mono">bland:{being.agent_id.slice(-8)}</span></>}
              {being.workspace && <><span>|</span><span className="font-mono">{being.workspace}</span></>}
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); onOpenDetail?.(being.id) }}
              className="flex items-center gap-1 px-2 py-0.5 rounded border border-accent-blue/30 bg-accent-blue/10 text-accent-blue text-[10px] font-medium hover:bg-accent-blue/20 transition-colors"
            >
              View Detail
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export function BeingsRegistry({ compact = false }) {
  const { beings, loading, openBeingDetail } = useBeings()
  const [expandedId, setExpandedId] = useState(null)
  const [filterType, setFilterType] = useState('')

  // Group beings into sections
  const sections = SECTIONS.map(sec => ({
    ...sec,
    beings: beings.filter(b => sec.types.includes(b.type)),
  })).filter(sec => sec.beings.length > 0)

  // Apply filter
  const filteredSections = filterType
    ? sections.filter(sec => sec.types.includes(filterType))
    : sections

  return (
    <div className="bg-bg-secondary border border-border rounded-lg">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-cyan" />
          <h2 className="text-xs font-semibold uppercase tracking-wider">Beings Registry</h2>
        </div>
        <div className="flex items-center gap-2">
          {!compact && (
            <select
              value={filterType}
              onChange={e => setFilterType(e.target.value)}
              className="bg-bg-card border border-border rounded px-1.5 py-0.5 text-[10px] text-text-secondary focus:outline-none"
            >
              <option value="">All Types</option>
              <option value="runtime">Runtime</option>
              <option value="sister">Sisters</option>
            </select>
          )}
          <span className="text-[10px] text-text-muted font-mono">
            {beings.filter(b => b.status === 'online').length}/{beings.length} online
          </span>
        </div>
      </div>

      {loading && (
        <div className="p-4 text-center text-xs text-text-muted">Loading beings...</div>
      )}

      {/* Sectioned Being List */}
      <div className={`p-2 flex flex-col gap-2 ${compact ? 'max-h-[400px] overflow-y-auto' : ''}`}>
        {filteredSections.map(sec => (
          <div key={sec.key}>
            {/* Section header */}
            <div className="flex items-center gap-1.5 px-1 py-1">
              <div className={`w-1 h-1 rounded-full ${sec.dot}`} />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">{sec.label}</span>
              <span className="text-[10px] text-text-muted font-mono ml-auto">{sec.beings.length}</span>
            </div>
            <div className="flex flex-col gap-1.5">
              {sec.beings.map(being => (
                <BeingCard
                  key={being.id}
                  being={being}
                  isExpanded={expandedId === being.id}
                  onToggle={() => {
                    setExpandedId(expandedId === being.id ? null : being.id)
                  }}
                  onOpenDetail={() => openBeingDetail(being.id)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
