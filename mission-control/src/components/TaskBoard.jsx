import { useState } from 'react'
import { TASKS, TASK_STATUSES, getBeingById, timeAgo } from '../store'

const STATUS_CONFIG = {
  backlog: { label: 'Backlog', color: 'text-text-muted', dot: 'bg-text-muted' },
  in_progress: { label: 'In Progress', color: 'text-accent-blue', dot: 'bg-accent-blue' },
  in_review: { label: 'In Review', color: 'text-accent-amber', dot: 'bg-accent-amber' },
  done: { label: 'Done', color: 'text-accent-green', dot: 'bg-accent-green' },
}

const PRIORITY_CONFIG = {
  critical: { label: 'CRIT', bg: 'bg-accent-red/15', text: 'text-accent-red', border: 'border-accent-red/30' },
  high: { label: 'HIGH', bg: 'bg-accent-amber/15', text: 'text-accent-amber', border: 'border-accent-amber/30' },
  medium: { label: 'MED', bg: 'bg-accent-blue/15', text: 'text-accent-blue', border: 'border-accent-blue/30' },
  low: { label: 'LOW', bg: 'bg-bg-hover', text: 'text-text-muted', border: 'border-border' },
}

function TaskCard({ task, onDragStart }) {
  const prio = PRIORITY_CONFIG[task.priority]

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, task.id)}
      className="bg-bg-card border border-border rounded-lg p-2.5 cursor-grab active:cursor-grabbing hover:border-border-bright transition-colors group"
    >
      {/* Top row: priority + time */}
      <div className="flex items-center justify-between mb-1.5">
        <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded border ${prio.bg} ${prio.text} ${prio.border}`}>
          {prio.label}
        </span>
        <span className="text-[10px] text-text-muted font-mono">{timeAgo(task.updated)}</span>
      </div>

      {/* Title */}
      <h3 className="text-sm font-medium mb-1 leading-snug">{task.title}</h3>

      {/* Description snippet */}
      <p className="text-xs text-text-secondary mb-2 line-clamp-2 leading-relaxed">{task.description}</p>

      {/* Assignees */}
      <div className="flex items-center gap-1">
        {task.assignees.map(id => {
          const being = getBeingById(id)
          if (!being) return null
          return (
            <div
              key={id}
              className="w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold"
              style={{ backgroundColor: being.color + '22', color: being.color }}
              title={being.name}
            >
              {being.avatar}
            </div>
          )
        })}
        <span className="text-[10px] text-text-muted ml-auto font-mono">{task.id}</span>
      </div>
    </div>
  )
}

function Column({ status, tasks, onDragOver, onDrop, onDragStart }) {
  const config = STATUS_CONFIG[status]

  return (
    <div
      className="flex flex-col min-w-[220px] flex-1"
      onDragOver={(e) => { e.preventDefault(); onDragOver(e, status) }}
      onDrop={(e) => onDrop(e, status)}
    >
      {/* Column header */}
      <div className="flex items-center gap-2 px-2 py-1.5 mb-2">
        <div className={`w-2 h-2 rounded-full ${config.dot}`} />
        <span className={`text-xs font-semibold uppercase tracking-wider ${config.color}`}>
          {config.label}
        </span>
        <span className="text-[10px] text-text-muted font-mono ml-auto">{tasks.length}</span>
      </div>

      {/* Cards */}
      <div className="flex flex-col gap-1.5 flex-1 min-h-[100px] p-1 rounded-lg border border-transparent hover:border-border/50 transition-colors">
        {tasks.map(task => (
          <TaskCard key={task.id} task={task} onDragStart={onDragStart} />
        ))}
      </div>
    </div>
  )
}

export function TaskBoard({ fullWidth = false }) {
  const [tasks, setTasks] = useState(TASKS)
  const [dragOverColumn, setDragOverColumn] = useState(null)

  const handleDragStart = (e, taskId) => {
    e.dataTransfer.setData('text/plain', taskId)
  }

  const handleDragOver = (e, status) => {
    setDragOverColumn(status)
  }

  const handleDrop = (e, newStatus) => {
    e.preventDefault()
    const taskId = e.dataTransfer.getData('text/plain')
    setTasks(prev => prev.map(t =>
      t.id === taskId ? { ...t, status: newStatus, updated: new Date().toISOString() } : t
    ))
    setDragOverColumn(null)
  }

  return (
    <div className={`bg-bg-secondary border border-border rounded-lg ${fullWidth ? 'min-h-[calc(100vh-80px)]' : ''}`}>
      {/* Panel Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-green" />
          <h2 className="text-xs font-semibold uppercase tracking-wider">Task Board</h2>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-text-muted font-mono">
          <span>{tasks.filter(t => t.status === 'in_progress').length} active</span>
          <span>{tasks.filter(t => t.status === 'done').length} done</span>
        </div>
      </div>

      {/* Kanban Columns */}
      <div className="p-2 flex gap-2 overflow-x-auto">
        {TASK_STATUSES.map(status => (
          <Column
            key={status}
            status={status}
            tasks={tasks.filter(t => t.status === status)}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          />
        ))}
      </div>
    </div>
  )
}
