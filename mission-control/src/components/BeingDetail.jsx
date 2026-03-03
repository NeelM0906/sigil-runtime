import { useState, useEffect } from 'react'
import { useBeings } from '../context/BeingsContext'
import { tasksApi } from '../api'
import { timeAgo } from '../store'

const STATUS_COLORS = {
  online: 'bg-accent-green',
  busy: 'bg-accent-amber',
  idle: 'bg-accent-cyan',
  offline: 'bg-text-muted',
}

const STATUS_CYCLE = ['online', 'busy', 'idle', 'offline']

const PRIORITY_CONFIG = {
  critical: { label: 'CRIT', bg: 'bg-accent-red/15', text: 'text-accent-red', border: 'border-accent-red/30' },
  high: { label: 'HIGH', bg: 'bg-accent-amber/15', text: 'text-accent-amber', border: 'border-accent-amber/30' },
  medium: { label: 'MED', bg: 'bg-accent-blue/15', text: 'text-accent-blue', border: 'border-accent-blue/30' },
  low: { label: 'LOW', bg: 'bg-bg-hover', text: 'text-text-muted', border: 'border-border' },
}

const STATUS_DOT = {
  backlog: 'bg-text-muted',
  in_progress: 'bg-accent-blue',
  in_review: 'bg-accent-amber',
  done: 'bg-accent-green',
}

export function BeingDetail({ onOpenTask }) {
  const { selectedBeingId, closeBeingDetail, getBeingById, updateBeingStatus } = useBeings()
  const [assignedTasks, setAssignedTasks] = useState([])
  const [loadingTasks, setLoadingTasks] = useState(false)

  const being = selectedBeingId ? getBeingById(selectedBeingId) : null

  useEffect(() => {
    if (!being) return
    setLoadingTasks(true)
    tasksApi.list({ assignee: being.id })
      .then(({ tasks }) => setAssignedTasks(tasks))
      .catch(() => setAssignedTasks([]))
      .finally(() => setLoadingTasks(false))
  }, [being?.id])

  if (!being) return null

  const activeTasks = assignedTasks.filter(t => t.status === 'in_progress' || t.status === 'in_review')
  const completedTasks = assignedTasks.filter(t => t.status === 'done')
  const backlogTasks = assignedTasks.filter(t => t.status === 'backlog')

  const handleStatusToggle = () => {
    const currentIdx = STATUS_CYCLE.indexOf(being.status)
    const nextStatus = STATUS_CYCLE[(currentIdx + 1) % STATUS_CYCLE.length]
    updateBeingStatus(being.id, nextStatus)
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={closeBeingDetail}>
      <div
        className="w-full max-w-md bg-bg-secondary border-l border-border-bright h-full overflow-y-auto shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-bg-secondary border-b border-border z-10">
          <div className="px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold"
                style={{ backgroundColor: being.color + '22', color: being.color }}
              >
                {being.avatar}
              </div>
              <div>
                <h2 className="text-sm font-semibold">{being.name}</h2>
                <div className="text-xs text-text-secondary">{being.role}</div>
              </div>
            </div>
            <button onClick={closeBeingDetail} className="text-text-muted hover:text-text-primary text-lg">&times;</button>
          </div>

          {/* Status bar */}
          <div className="px-4 pb-3 flex items-center gap-3">
            <button
              onClick={handleStatusToggle}
              className="flex items-center gap-1.5 px-2 py-1 rounded border border-border bg-bg-card hover:bg-bg-hover transition-colors text-xs"
              title="Click to toggle status"
            >
              <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[being.status]}`} />
              <span className="uppercase text-[10px] font-mono">{being.status}</span>
            </button>
            {being.model_id && (
              <span className="text-[10px] font-mono text-text-muted">{being.model_id}</span>
            )}
            {being.phone && (
              <span className="text-[10px] text-text-muted">{being.phone}</span>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-4 flex flex-col gap-4">
          {/* Description */}
          <div>
            <p className="text-sm text-text-secondary leading-relaxed">{being.description}</p>
          </div>

          {/* Tools */}
          <div>
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2">Tools ({being.tools.length})</div>
            <div className="flex flex-col gap-1">
              {being.tools.map(tool => {
                const name = typeof tool === 'string' ? tool : tool.name
                const desc = typeof tool === 'string' ? '' : tool.description
                return (
                  <div key={name} className="flex items-start gap-2 px-2 py-1.5 rounded bg-bg-card border border-border">
                    <span className="text-[10px] font-mono text-accent-blue shrink-0 mt-0.5">{name}</span>
                    {desc && <span className="text-[10px] text-text-muted">{desc}</span>}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Skills */}
          <div>
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2">Skills</div>
            <div className="flex flex-wrap gap-1">
              {being.skills.map(skill => (
                <span key={skill} className="px-2 py-0.5 text-[10px] rounded bg-accent-purple/10 text-accent-purple border border-accent-purple/20">
                  {skill}
                </span>
              ))}
            </div>
          </div>

          {/* Meta */}
          {(being.workspace || being.tenant_id) && (
            <div className="flex flex-col gap-1 text-[10px]">
              {being.workspace && (
                <div className="flex items-center justify-between">
                  <span className="text-text-muted">Workspace</span>
                  <span className="font-mono text-text-secondary">{being.workspace}</span>
                </div>
              )}
              {being.tenant_id && (
                <div className="flex items-center justify-between">
                  <span className="text-text-muted">Tenant</span>
                  <span className="font-mono text-text-secondary">{being.tenant_id}</span>
                </div>
              )}
              {being.agent_id && (
                <div className="flex items-center justify-between">
                  <span className="text-text-muted">Agent ID</span>
                  <span className="font-mono text-text-secondary truncate max-w-[200px]">{being.agent_id}</span>
                </div>
              )}
            </div>
          )}

          {/* Assigned Tasks */}
          <div>
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2">
              Assigned Tasks ({assignedTasks.length})
            </div>

            {loadingTasks && (
              <div className="text-xs text-text-muted">Loading tasks...</div>
            )}

            {!loadingTasks && assignedTasks.length === 0 && (
              <div className="text-xs text-text-muted italic">No tasks assigned</div>
            )}

            {/* Active tasks */}
            {activeTasks.length > 0 && (
              <div className="mb-2">
                <div className="text-[10px] text-accent-blue mb-1">Active</div>
                {activeTasks.map(task => (
                  <TaskRow key={task.id} task={task} onClick={() => { closeBeingDetail(); onOpenTask?.(task) }} />
                ))}
              </div>
            )}

            {/* Backlog */}
            {backlogTasks.length > 0 && (
              <div className="mb-2">
                <div className="text-[10px] text-text-muted mb-1">Backlog</div>
                {backlogTasks.map(task => (
                  <TaskRow key={task.id} task={task} onClick={() => { closeBeingDetail(); onOpenTask?.(task) }} />
                ))}
              </div>
            )}

            {/* Completed */}
            {completedTasks.length > 0 && (
              <div>
                <div className="text-[10px] text-accent-green mb-1">Completed</div>
                {completedTasks.map(task => (
                  <TaskRow key={task.id} task={task} onClick={() => { closeBeingDetail(); onOpenTask?.(task) }} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function TaskRow({ task, onClick }) {
  const prio = PRIORITY_CONFIG[task.priority]
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2 px-2 py-1.5 rounded border border-border bg-bg-card hover:bg-bg-hover transition-colors text-left mb-1"
    >
      <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_DOT[task.status]}`} />
      <span className="text-xs flex-1 truncate">{task.title}</span>
      <span className={`px-1 py-0 text-[9px] font-bold rounded border ${prio.bg} ${prio.text} ${prio.border}`}>
        {prio.label}
      </span>
      <span className="text-[9px] text-text-muted font-mono">{timeAgo(task.updated)}</span>
    </button>
  )
}
