import { SUBAGENTS, getBeingById } from '../store'

const STATUS_CONFIG = {
  running: { label: 'Running', color: 'text-accent-blue', dot: 'bg-accent-blue', animate: true },
  waiting: { label: 'Waiting', color: 'text-accent-amber', dot: 'bg-accent-amber', animate: false },
  complete: { label: 'Complete', color: 'text-accent-green', dot: 'bg-accent-green', animate: false },
  failed: { label: 'Failed', color: 'text-accent-red', dot: 'bg-accent-red', animate: false },
  spawning: { label: 'Spawning', color: 'text-accent-cyan', dot: 'bg-accent-cyan', animate: true },
}

function ProgressBar({ value, status }) {
  const colorMap = {
    running: 'bg-accent-blue',
    waiting: 'bg-accent-amber',
    complete: 'bg-accent-green',
    failed: 'bg-accent-red',
    spawning: 'bg-accent-cyan',
  }

  return (
    <div className="w-full h-1 rounded-full bg-bg-primary overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${colorMap[status] || 'bg-accent-blue'}`}
        style={{ width: `${value}%` }}
      />
    </div>
  )
}

function SubAgentRow({ agent }) {
  const config = STATUS_CONFIG[agent.status]
  const spawner = getBeingById(agent.spawnedBy)

  return (
    <div className="bg-bg-card border border-border rounded-lg p-2.5 hover:border-border-bright transition-colors">
      <div className="flex items-center gap-2 mb-1.5">
        {/* Status dot */}
        <div className={`w-2 h-2 rounded-full ${config.dot} ${config.animate ? 'animate-pulse' : ''}`} />

        {/* Name */}
        <span className="text-xs font-medium flex-1 truncate">{agent.name}</span>

        {/* Status label */}
        <span className={`text-[10px] font-mono ${config.color}`}>{config.label.toUpperCase()}</span>

        {/* Spawner avatar */}
        {spawner && (
          <div
            className="w-4 h-4 rounded flex items-center justify-center text-[8px] font-bold"
            style={{ backgroundColor: spawner.color + '22', color: spawner.color }}
            title={`Spawned by ${spawner.name}`}
          >
            {spawner.avatar}
          </div>
        )}
      </div>

      {/* Goal */}
      <p className="text-[10px] text-text-secondary mb-1.5 truncate">{agent.goal}</p>

      {/* Progress bar */}
      <div className="flex items-center gap-2">
        <ProgressBar value={agent.progress} status={agent.status} />
        <span className="text-[10px] text-text-muted font-mono w-8 text-right">{agent.progress}%</span>
      </div>

      {/* Meta */}
      <div className="flex items-center gap-2 mt-1 text-[9px] text-text-muted">
        <span>Task: {agent.parentTask}</span>
        <span>|</span>
        <span>Depth: {agent.depth}</span>
      </div>
    </div>
  )
}

export function SubAgentTracker() {
  const active = SUBAGENTS.filter(a => a.status === 'running' || a.status === 'spawning')
  const other = SUBAGENTS.filter(a => a.status !== 'running' && a.status !== 'spawning')

  return (
    <div className="bg-bg-secondary border border-border rounded-lg">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-amber" />
          <h2 className="text-xs font-semibold uppercase tracking-wider">Sub-Agents</h2>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-text-muted font-mono">
          <span>{active.length} active</span>
          <span>{SUBAGENTS.length} total</span>
        </div>
      </div>

      {/* Agent List */}
      <div className="p-2 flex flex-col gap-1.5 max-h-[400px] overflow-y-auto">
        {active.map(agent => (
          <SubAgentRow key={agent.id} agent={agent} />
        ))}
        {other.map(agent => (
          <SubAgentRow key={agent.id} agent={agent} />
        ))}
      </div>
    </div>
  )
}
