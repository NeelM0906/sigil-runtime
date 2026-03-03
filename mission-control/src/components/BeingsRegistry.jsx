import { useState } from 'react'
import { BEINGS } from '../store'

const STATUS_COLORS = {
  online: 'bg-accent-green',
  busy: 'bg-accent-amber',
  offline: 'bg-text-muted',
}

const STATUS_LABELS = {
  online: 'Online',
  busy: 'Busy',
  offline: 'Offline',
}

function BeingCard({ being, isExpanded, onToggle }) {
  return (
    <div
      className={`border rounded-lg transition-all cursor-pointer ${
        isExpanded ? 'border-border-bright bg-bg-hover' : 'border-border bg-bg-card hover:bg-bg-hover'
      }`}
      onClick={onToggle}
    >
      {/* Header row */}
      <div className="flex items-center gap-3 p-3">
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
            <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[being.status]}`} />
            <span className="text-[10px] text-text-muted uppercase">{STATUS_LABELS[being.status]}</span>
          </div>
          <div className="text-xs text-text-secondary truncate">{being.role}</div>
        </div>

        {/* Metrics */}
        <div className="text-right shrink-0">
          <div className="text-xs font-mono text-text-secondary">{being.metrics.successRate}%</div>
          <div className="text-[10px] text-text-muted">{being.metrics.tasksCompleted} tasks</div>
        </div>

        {/* Expand chevron */}
        <svg
          className={`w-4 h-4 text-text-muted transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Expanded details */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-0 border-t border-border">
          <p className="text-xs text-text-secondary mt-2 mb-3 leading-relaxed">{being.description}</p>

          {/* Tools */}
          <div className="mb-2">
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Tools</div>
            <div className="flex flex-wrap gap-1">
              {being.tools.map(tool => (
                <span key={tool} className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-accent-blue/10 text-accent-blue border border-accent-blue/20">
                  {tool}
                </span>
              ))}
            </div>
          </div>

          {/* Skills */}
          <div>
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Skills</div>
            <div className="flex flex-wrap gap-1">
              {being.skills.map(skill => (
                <span key={skill} className="px-1.5 py-0.5 text-[10px] rounded bg-accent-purple/10 text-accent-purple border border-accent-purple/20">
                  {skill}
                </span>
              ))}
            </div>
          </div>

          {/* Uptime bar */}
          <div className="mt-2 flex items-center gap-2 text-[10px] text-text-muted">
            <span>Uptime: {being.metrics.uptime}</span>
            <span>|</span>
            <span>Tasks: {being.metrics.tasksCompleted}</span>
            <span>|</span>
            <span>Success: {being.metrics.successRate}%</span>
          </div>
        </div>
      )}
    </div>
  )
}

export function BeingsRegistry({ compact = false }) {
  const [expandedId, setExpandedId] = useState(null)

  return (
    <div className="bg-bg-secondary border border-border rounded-lg">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-cyan" />
          <h2 className="text-xs font-semibold uppercase tracking-wider">Beings Registry</h2>
        </div>
        <span className="text-[10px] text-text-muted font-mono">{BEINGS.length} beings</span>
      </div>

      {/* Being List */}
      <div className={`p-2 flex flex-col gap-1.5 ${compact ? 'max-h-[300px] overflow-y-auto' : ''}`}>
        {BEINGS.map(being => (
          <BeingCard
            key={being.id}
            being={being}
            isExpanded={expandedId === being.id}
            onToggle={() => setExpandedId(expandedId === being.id ? null : being.id)}
          />
        ))}
      </div>
    </div>
  )
}
