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

const STATUS_CYCLE = ['online', 'busy', 'idle', 'offline']

const TYPE_BADGES = {
  runtime: { label: 'RUNTIME', color: 'text-accent-blue bg-accent-blue/10 border-accent-blue/20' },
  sister: { label: 'SISTER', color: 'text-accent-purple bg-accent-purple/10 border-accent-purple/20' },
  voice_agent: { label: 'VOICE', color: 'text-accent-pink bg-accent-pink/10 border-accent-pink/20' },
  custom: { label: 'CUSTOM', color: 'text-text-muted bg-bg-hover border-border' },
}

function BeingCard({ being, isExpanded, onToggle, onStatusToggle }) {
  const typeBadge = TYPE_BADGES[being.type] || TYPE_BADGES.custom

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
            <button
              onClick={(e) => { e.stopPropagation(); onStatusToggle(being) }}
              className={`flex items-center gap-1 px-1 rounded hover:bg-bg-primary/50 transition-colors`}
              title="Click to toggle status"
            >
              <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[being.status]}`} />
              <span className="text-[10px] text-text-muted uppercase">{STATUS_LABELS[being.status]}</span>
            </button>
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

          <div className="flex items-center gap-2 text-[10px] text-text-muted">
            {being.model_id && <span className="font-mono">{being.model_id}</span>}
            {being.phone && <><span>|</span><span>{being.phone}</span></>}
          </div>
        </div>
      )}
    </div>
  )
}

export function BeingsRegistry({ compact = false }) {
  const { beings, loading, updateBeingStatus, openBeingDetail } = useBeings()
  const [expandedId, setExpandedId] = useState(null)
  const [filterType, setFilterType] = useState('')

  const filtered = filterType ? beings.filter(b => b.type === filterType) : beings

  const handleStatusToggle = async (being) => {
    const currentIdx = STATUS_CYCLE.indexOf(being.status)
    const nextStatus = STATUS_CYCLE[(currentIdx + 1) % STATUS_CYCLE.length]
    await updateBeingStatus(being.id, nextStatus)
  }

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
              <option value="voice_agent">Voice Agents</option>
              <option value="custom">Custom</option>
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

      {/* Being List */}
      <div className={`p-2 flex flex-col gap-1.5 ${compact ? 'max-h-[300px] overflow-y-auto' : ''}`}>
        {filtered.map(being => (
          <BeingCard
            key={being.id}
            being={being}
            isExpanded={expandedId === being.id}
            onToggle={() => {
              if (expandedId === being.id) {
                openBeingDetail(being.id) // Double-click opens detail
              }
              setExpandedId(expandedId === being.id ? null : being.id)
            }}
            onStatusToggle={handleStatusToggle}
          />
        ))}
      </div>
    </div>
  )
}
