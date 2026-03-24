import { useState, useEffect, useCallback, useRef } from 'react'
import { TASK_STATUSES, timeAgo } from '../store'
import { useBeings } from '../context/BeingsContext'
import { tasksApi, actiApi } from '../api'
import { useSharedSSE } from '../context/SSEContext'

const STATUS_CONFIG = {
  backlog: { label: 'Backlog', color: 'text-text-muted', dot: 'bg-text-muted' },
  in_progress: { label: 'In Progress', color: 'text-accent-blue', dot: 'bg-accent-blue' },
  in_review: { label: 'In Review', color: 'text-accent-amber', dot: 'bg-accent-amber' },
  done: { label: 'Done', color: 'text-accent-green', dot: 'bg-accent-green' },
  cancelled: { label: 'Cancelled', color: 'text-text-muted', dot: 'bg-text-muted' },
}

const PRIORITY_CONFIG = {
  critical: { label: 'CRIT', bg: 'bg-accent-red/15', text: 'text-accent-red', border: 'border-accent-red/30' },
  high: { label: 'HIGH', bg: 'bg-accent-amber/15', text: 'text-accent-amber', border: 'border-accent-amber/30' },
  medium: { label: 'MED', bg: 'bg-accent-blue/15', text: 'text-accent-blue', border: 'border-accent-blue/30' },
  low: { label: 'LOW', bg: 'bg-bg-hover', text: 'text-text-muted', border: 'border-border' },
}

const PRIORITIES = ['critical', 'high', 'medium', 'low']

// ── Filters Bar ──────────────────────────────────────────────

function FiltersBar({ filters, setFilters, onCreateClick, beings }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Assignee filter */}
      <select
        value={filters.assignee}
        onChange={e => setFilters(f => ({ ...f, assignee: e.target.value }))}
        className="bg-bg-card border border-border rounded px-2 py-1 text-xs text-text-secondary focus:outline-none focus:border-accent-blue/50"
      >
        <option value="">All Beings</option>
        {beings.map(b => (
          <option key={b.id} value={b.id}>{b.name}</option>
        ))}
      </select>

      {/* Priority filter */}
      <select
        value={filters.priority}
        onChange={e => setFilters(f => ({ ...f, priority: e.target.value }))}
        className="bg-bg-card border border-border rounded px-2 py-1 text-xs text-text-secondary focus:outline-none focus:border-accent-blue/50"
      >
        <option value="">All Priorities</option>
        {PRIORITIES.map(p => (
          <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
        ))}
      </select>

      {/* Date from */}
      <input
        type="date"
        value={filters.from}
        onChange={e => setFilters(f => ({ ...f, from: e.target.value }))}
        className="bg-bg-card border border-border rounded px-2 py-1 text-xs text-text-secondary focus:outline-none focus:border-accent-blue/50"
        placeholder="From"
      />

      {/* Date to */}
      <input
        type="date"
        value={filters.to}
        onChange={e => setFilters(f => ({ ...f, to: e.target.value }))}
        className="bg-bg-card border border-border rounded px-2 py-1 text-xs text-text-secondary focus:outline-none focus:border-accent-blue/50"
        placeholder="To"
      />

      {/* Clear filters */}
      {(filters.assignee || filters.priority || filters.from || filters.to) && (
        <button
          onClick={() => setFilters({ assignee: '', priority: '', from: '', to: '' })}
          className="text-[10px] text-text-muted hover:text-accent-red transition-colors"
        >
          Clear
        </button>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Create task button */}
      <button
        onClick={onCreateClick}
        className="flex items-center gap-1 px-3 py-1 bg-accent-blue/20 text-accent-blue text-xs font-medium rounded hover:bg-accent-blue/30 transition-colors"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        New Task
      </button>
    </div>
  )
}

// ── Create/Edit Modal ────────────────────────────────────────

function TaskModal({ task, onSave, onClose, beings }) {
  const isEdit = !!task?.id
  const [beingSearch, setBeingSearch] = useState('')
  const [assignMode, setAssignMode] = useState('beings')
  const [clusters, setClusters] = useState([])
  const [clusterSearch, setClusterSearch] = useState('')
  const [form, setForm] = useState({
    title: task?.title || '',
    description: task?.description || '',
    priority: task?.priority || 'medium',
    status: task?.status || 'backlog',
    assignees: task?.assignees || [],
  })

  // Load clusters when switching to teams mode
  useEffect(() => {
    if (assignMode === 'teams' && clusters.length === 0) {
      actiApi.architecture().then(data => {
        if (data?.clusters) setClusters(data.clusters)
      }).catch(() => {})
    }
  }, [assignMode, clusters.length])

  const toggleAssignee = (id) => {
    setForm(f => ({
      ...f,
      assignees: f.assignees.includes(id)
        ? f.assignees.filter(a => a !== id)
        : [...f.assignees, id]
    }))
  }

  const assignFromCluster = (cluster) => {
    // Find the being ID that owns this cluster (by name match)
    const ownerBeing = beings.find(b => b.name === cluster.being)
    if (ownerBeing && !form.assignees.includes(ownerBeing.id)) {
      toggleAssignee(ownerBeing.id)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!form.title.trim()) return
    onSave(form)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-bg-secondary border border-border-bright rounded-lg w-full max-w-lg shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <h3 className="text-sm font-semibold">{isEdit ? 'Edit Task' : 'Create Task'}</h3>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary text-lg">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 flex flex-col gap-3">
          <input
            autoFocus
            value={form.title}
            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            placeholder="Task title..."
            className="w-full bg-bg-card border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue/50"
          />

          <textarea
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Description..."
            rows={3}
            className="w-full bg-bg-card border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue/50 resize-none"
          />

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-[10px] uppercase tracking-wider text-text-muted mb-1 block">Priority</label>
              <select
                value={form.priority}
                onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
                className="w-full bg-bg-card border border-border rounded px-2 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-accent-blue/50"
              >
                {PRIORITIES.map(p => (
                  <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="text-[10px] uppercase tracking-wider text-text-muted mb-1 block">Status</label>
              <select
                value={form.status}
                onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
                className="w-full bg-bg-card border border-border rounded px-2 py-1.5 text-xs text-text-secondary focus:outline-none focus:border-accent-blue/50"
              >
                {TASK_STATUSES.map(s => (
                  <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Assignees — searchable multi-select with beings/teams toggle */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[10px] uppercase tracking-wider text-text-muted">Assign</label>
              <div className="flex items-center gap-0.5 bg-bg-card border border-border rounded p-0.5">
                <button
                  type="button"
                  onClick={() => setAssignMode('beings')}
                  className={`px-2 py-0.5 text-[10px] rounded transition-colors ${assignMode === 'beings' ? 'bg-accent-blue/20 text-accent-blue font-medium' : 'text-text-muted hover:text-text-secondary'}`}
                >
                  Beings
                </button>
                <button
                  type="button"
                  onClick={() => setAssignMode('teams')}
                  className={`px-2 py-0.5 text-[10px] rounded transition-colors ${assignMode === 'teams' ? 'bg-accent-cyan/20 text-accent-cyan font-medium' : 'text-text-muted hover:text-text-secondary'}`}
                >
                  Teams
                </button>
              </div>
            </div>
            {/* Selected beings */}
            {form.assignees.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-1.5">
                {form.assignees.map(id => {
                  const b = beings.find(x => x.id === id)
                  if (!b) return null
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => toggleAssignee(id)}
                      className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] border border-accent-blue/30 bg-accent-blue/10 text-accent-blue hover:bg-accent-red/10 hover:text-accent-red hover:border-accent-red/30 transition-colors"
                    >
                      <div className="w-4 h-4 rounded flex items-center justify-center text-[9px] font-bold" style={{ backgroundColor: b.color + '22', color: b.color }}>{b.avatar}</div>
                      {b.name}
                      <span className="ml-0.5 opacity-60">&times;</span>
                    </button>
                  )
                })}
              </div>
            )}

            {assignMode === 'beings' && (
              <>
                {/* Search input */}
                <input
                  type="text"
                  value={beingSearch}
                  onChange={e => setBeingSearch(e.target.value)}
                  placeholder="Search beings..."
                  className="w-full bg-bg-card border border-border rounded px-2 py-1 text-xs text-text-secondary placeholder:text-text-muted focus:outline-none focus:border-accent-blue/50 mb-1.5"
                />
                {/* Filtered being list */}
                <div className="flex flex-wrap gap-1.5 max-h-[120px] overflow-y-auto">
                  {beings
                    .filter(b => !form.assignees.includes(b.id))
                    .filter(b => !beingSearch || b.name.toLowerCase().includes(beingSearch.toLowerCase()) || b.role.toLowerCase().includes(beingSearch.toLowerCase()))
                    .map(being => (
                      <button
                        key={being.id}
                        type="button"
                        onClick={() => { toggleAssignee(being.id); setBeingSearch('') }}
                        className="flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors border border-border bg-bg-card text-text-secondary hover:bg-bg-hover"
                      >
                        <div
                          className="w-4 h-4 rounded flex items-center justify-center text-[9px] font-bold"
                          style={{ backgroundColor: being.color + '22', color: being.color }}
                        >
                          {being.avatar}
                        </div>
                        {being.name}
                        <span className="text-[9px] text-text-muted">{being.role}</span>
                      </button>
                    ))}
                </div>
              </>
            )}

            {assignMode === 'teams' && (
              <>
                <input
                  type="text"
                  value={clusterSearch}
                  onChange={e => setClusterSearch(e.target.value)}
                  placeholder="Search teams/clusters..."
                  className="w-full bg-bg-card border border-border rounded px-2 py-1 text-xs text-text-secondary placeholder:text-text-muted focus:outline-none focus:border-accent-cyan/50 mb-1.5"
                />
                <div className="flex flex-col gap-1 max-h-[120px] overflow-y-auto">
                  {clusters
                    .filter(c => !clusterSearch || c.name.toLowerCase().includes(clusterSearch.toLowerCase()) || c.function.toLowerCase().includes(clusterSearch.toLowerCase()) || c.being.toLowerCase().includes(clusterSearch.toLowerCase()))
                    .slice(0, 20)
                    .map(c => (
                      <button
                        key={c.id + c.family}
                        type="button"
                        onClick={() => { assignFromCluster(c); setClusterSearch('') }}
                        className="flex items-center justify-between px-2 py-1 rounded text-xs transition-colors border border-border bg-bg-card text-text-secondary hover:bg-bg-hover text-left"
                      >
                        <div className="min-w-0 flex-1">
                          <span className="text-text-primary font-medium">{c.name}</span>
                          <span className="text-text-muted ml-1.5">{c.function}</span>
                        </div>
                        <span className="text-[9px] text-accent-cyan shrink-0 ml-2">{c.being}</span>
                      </button>
                    ))}
                  {clusters.length === 0 && (
                    <span className="text-[10px] text-text-muted italic px-2 py-1">Loading teams...</span>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="flex justify-end gap-2 mt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!form.title.trim()}
              className="px-4 py-1.5 bg-accent-blue text-white text-xs font-medium rounded hover:bg-accent-blue/80 disabled:opacity-30 transition-colors"
            >
              {isEdit ? 'Save Changes' : 'Create Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Task Detail Slide-out ────────────────────────────────────

function TaskDetail({ task, history, onClose, onEdit, onDelete, onCancel, getBeingById, onBeingClick, onPreview }) {
  const config = STATUS_CONFIG[task.status]
  const prio = PRIORITY_CONFIG[task.priority]

  const actionLabels = {
    created: 'Task created',
    status_change: 'Status changed',
    updated: 'Task updated',
    deleted: 'Task deleted',
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={onClose}>
      <div
        className="w-full max-w-md bg-bg-secondary border-l border-border-bright h-full overflow-y-auto shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-bg-secondary border-b border-border px-4 py-3 flex items-center justify-between z-10">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${config.dot}`} />
            <span className={`text-xs font-mono ${config.color}`}>{config.label}</span>
            <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded border ${prio.bg} ${prio.text} ${prio.border}`}>
              {prio.label}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {task.status === 'in_progress' && (
              <button
                onClick={() => { if (confirm('Cancel this running task?')) onCancel(task.id) }}
                className="px-2 py-1 text-[10px] text-accent-amber hover:text-accent-red font-medium transition-colors"
              >
                Cancel
              </button>
            )}
            <button
              onClick={() => onEdit(task)}
              className="px-2 py-1 text-[10px] text-text-secondary hover:text-accent-blue transition-colors"
            >
              Edit
            </button>
            <button
              onClick={() => { if (confirm('Delete this task?')) onDelete(task.id) }}
              className="px-2 py-1 text-[10px] text-text-secondary hover:text-accent-red transition-colors"
            >
              Delete
            </button>
            <button onClick={onClose} className="text-text-muted hover:text-text-primary text-lg ml-2">&times;</button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4">
          <h2 className="text-base font-semibold mb-2">{task.title}</h2>
          <p className="text-sm text-text-secondary leading-relaxed mb-4">{task.description}</p>

          {/* Meta */}
          <div className="flex flex-col gap-2 text-xs mb-4">
            <div className="flex items-center justify-between">
              <span className="text-text-muted">ID</span>
              <span className="font-mono text-text-secondary">{task.id}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-text-muted">Created</span>
              <span className="text-text-secondary">{new Date(task.created).toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-text-muted">Updated</span>
              <span className="text-text-secondary">{new Date(task.updated).toLocaleString()}</span>
            </div>
          </div>

          {/* Assignees — clickable to open being detail */}
          <div className="mb-4">
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2">Assigned To</div>
            <div className="flex flex-wrap gap-1.5">
              {task.assignees.map(id => {
                const being = getBeingById(id)
                if (!being) return <span key={id} className="text-xs text-text-muted">{id}</span>
                return (
                  <button
                    key={id}
                    onClick={() => { onClose(); onBeingClick(being.id) }}
                    className="flex items-center gap-1.5 px-2 py-1 rounded border border-border bg-bg-card text-xs hover:bg-bg-hover hover:border-border-bright transition-colors"
                  >
                    <div
                      className="w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold"
                      style={{ backgroundColor: being.color + '22', color: being.color }}
                    >
                      {being.avatar}
                    </div>
                    <span className="hover:underline">{being.name}</span>
                    <div className={`w-1.5 h-1.5 rounded-full ${
                      being.status === 'online' ? 'bg-accent-green' : being.status === 'busy' ? 'bg-accent-amber' : 'bg-text-muted'
                    }`} />
                  </button>
                )
              })}
              {task.assignees.length === 0 && (
                <span className="text-xs text-text-muted italic">Unassigned</span>
              )}
            </div>
          </div>

          {/* Sub-Steps Checklist */}
          <StepChecklist steps={task.steps} />

          {/* Artifacts */}
          <ArtifactList artifacts={task.artifacts} getBeingById={getBeingById} onPreview={onPreview} />

          {/* Activity History */}
          <div>
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2">Activity Log</div>
            <div className="flex flex-col gap-0">
              {history.length === 0 && (
                <span className="text-xs text-text-muted italic">No history yet</span>
              )}
              {history.slice().reverse().map(entry => (
                <div key={entry.id} className="flex gap-3 py-2 border-b border-border/50 last:border-0">
                  {/* Timeline dot */}
                  <div className="flex flex-col items-center mt-1">
                    <div className={`w-2 h-2 rounded-full ${
                      entry.action === 'status_change' ? 'bg-accent-blue'
                      : entry.action === 'created' ? 'bg-accent-green'
                      : entry.action === 'deleted' ? 'bg-accent-red'
                      : 'bg-text-muted'
                    }`} />
                    <div className="w-px flex-1 bg-border/50 mt-1" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium">{actionLabels[entry.action] || entry.action}</span>
                      <span className="text-[10px] text-text-muted font-mono">{timeAgo(entry.timestamp)}</span>
                    </div>

                    {/* Change details */}
                    {entry.details && Object.keys(entry.details).length > 0 && (
                      <div className="mt-1 flex flex-col gap-0.5">
                        {Object.entries(entry.details).map(([key, val]) => (
                          <div key={key} className="text-[10px] text-text-secondary">
                            {typeof val === 'object' && val.from !== undefined
                              ? <><span className="text-text-muted">{key}:</span> <span className="line-through text-text-muted">{JSON.stringify(val.from)}</span> &rarr; <span>{JSON.stringify(val.to)}</span></>
                              : <><span className="text-text-muted">{key}:</span> {JSON.stringify(val)}</>
                            }
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Task Card ────────────────────────────────────────────────

// ── Step Progress Bar (compact, for card) ────────────────────

function StepProgress({ steps, created }) {
  if (!steps || steps.length === 0) return null
  const done = steps.filter(s => s.status === 'done').length
  const total = steps.length
  const pct = Math.round((done / total) * 100)
  const activeStep = steps.find(s => s.status === 'in_progress')
  return (
    <div className="mt-1.5 mb-1">
      <div className="flex items-center justify-between mb-0.5">
        <span className="text-[9px] text-text-muted font-mono">{done}/{total} steps</span>
        <span className="text-[9px] text-text-muted font-mono">{pct}%</span>
      </div>
      <div className="h-1 bg-bg-hover rounded-full overflow-hidden">
        <div
          className="h-full bg-accent-blue rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      {activeStep && (
        <div className="flex items-center gap-1 mt-0.5">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-blue animate-pulse shrink-0" />
          <span className="text-[9px] text-accent-blue truncate">{activeStep.label}</span>
        </div>
      )}
      {created && done < total && (
        <div className="text-[8px] text-text-muted mt-0.5">{timeAgo(created)}</div>
      )}
    </div>
  )
}

// ── Step Checklist (detailed, for detail panel) ──────────────

function StepChecklist({ steps }) {
  if (!steps || steps.length === 0) return null
  const done = steps.filter(s => s.status === 'done').length
  const total = steps.length
  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] uppercase tracking-wider text-text-muted">Sub-Steps</div>
        <span className="text-[10px] text-text-muted font-mono">{done}/{total} complete</span>
      </div>
      <div className="flex flex-col gap-0.5">
        {steps.map(step => (
          <div
            key={step.id}
            className={`flex items-center gap-2 px-2 py-1 rounded text-xs transition-colors ${
              step.status === 'done'
                ? 'text-text-muted'
                : step.status === 'in_progress'
                  ? 'text-accent-blue bg-accent-blue/5'
                  : 'text-text-secondary'
            }`}
          >
            {step.status === 'done' ? (
              <svg className="w-3.5 h-3.5 text-accent-green flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : step.status === 'in_progress' ? (
              <span className="w-3.5 h-3.5 flex items-center justify-center flex-shrink-0">
                <span className="w-2 h-2 rounded-full bg-accent-blue animate-pulse" />
              </span>
            ) : (
              <span className="w-3.5 h-3.5 rounded-full border border-border flex-shrink-0" />
            )}
            <span className={step.status === 'done' ? 'line-through' : ''}>{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Artifact type icons ──────────────────────────────────────

const ARTIFACT_ICONS = {
  pdf: { icon: 'PDF', color: 'text-red-400', bg: 'bg-red-400/10' },
  docx: { icon: 'DOC', color: 'text-blue-400', bg: 'bg-blue-400/10' },
  markdown: { icon: 'MD', color: 'text-gray-400', bg: 'bg-gray-400/10' },
  code: { icon: 'CODE', color: 'text-green-400', bg: 'bg-green-400/10' },
  image: { icon: 'IMG', color: 'text-purple-400', bg: 'bg-purple-400/10' },
  html: { icon: 'HTML', color: 'text-orange-400', bg: 'bg-orange-400/10' },
  csv: { icon: 'CSV', color: 'text-teal-400', bg: 'bg-teal-400/10' },
  json: { icon: 'JSON', color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
  svg: { icon: 'SVG', color: 'text-pink-400', bg: 'bg-pink-400/10' },
}

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

// ── Artifact Badge (compact, for card) ──────────────────────

function ArtifactBadge({ artifacts }) {
  if (!artifacts || artifacts.length === 0) return null
  return (
    <div className="flex items-center gap-1 mt-1">
      <svg className="w-3 h-3 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
      </svg>
      <span className="text-[9px] text-text-muted font-mono">{artifacts.length} artifact{artifacts.length !== 1 ? 's' : ''}</span>
      {artifacts.slice(0, 3).map(a => {
        const cfg = ARTIFACT_ICONS[a.artifact_type] || ARTIFACT_ICONS.code
        return (
          <span key={a.artifact_id} className={`text-[8px] font-bold px-1 rounded ${cfg.bg} ${cfg.color}`}>
            {cfg.icon}
          </span>
        )
      })}
    </div>
  )
}

// ── Artifact Preview Modal ───────────────────────────────────

const PREVIEWABLE_TYPES = new Set(['markdown', 'code', 'json', 'csv', 'html', 'svg', 'image'])

function ArtifactPreview({ artifact, onClose }) {
  const [content, setContent] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!artifact) return
    fetch(`/api/mc/artifacts/${artifact.artifact_id}/preview`)
      .then(r => r.json())
      .then(data => { setContent(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [artifact])

  if (!artifact) return null
  const cfg = ARTIFACT_ICONS[artifact.artifact_type] || ARTIFACT_ICONS.code

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-bg-secondary border border-border rounded-lg w-[90vw] max-w-3xl max-h-[80vh] flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>{cfg.icon}</span>
            <span className="text-sm font-medium">{artifact.title}</span>
            <span className="text-[10px] text-text-muted">{formatFileSize(artifact.file_size)}</span>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={`/api/mc/artifacts/${artifact.artifact_id}/download`}
              className="text-[10px] px-2 py-1 bg-accent-blue/20 text-accent-blue rounded hover:bg-accent-blue/30 transition-colors"
              download
            >
              Download
            </a>
            <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="text-xs text-text-muted text-center py-8">Loading preview...</div>
          ) : content?.type === 'text' ? (
            <pre className="text-xs text-text-secondary font-mono whitespace-pre-wrap break-words leading-relaxed">{content.content}</pre>
          ) : content?.type === 'binary' && (artifact.artifact_type === 'image' || artifact.artifact_type === 'svg') ? (
            <div className="flex items-center justify-center">
              <img src={`/api/mc/artifacts/${artifact.artifact_id}/download`} alt={artifact.title} className="max-w-full max-h-[60vh] object-contain rounded" />
            </div>
          ) : (
            <div className="text-xs text-text-muted text-center py-8">
              Preview not available for this file type.
              <a href={`/api/mc/artifacts/${artifact.artifact_id}/download`} className="text-accent-blue ml-1 hover:underline" download>Download instead</a>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Artifact List (detailed, for detail panel) ──────────────

function ArtifactList({ artifacts, getBeingById, onPreview }) {
  if (!artifacts || artifacts.length === 0) return null
  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] uppercase tracking-wider text-text-muted">Artifacts</div>
        <span className="text-[10px] text-text-muted font-mono">{artifacts.length} file{artifacts.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="flex flex-col gap-1">
        {artifacts.map(a => {
          const cfg = ARTIFACT_ICONS[a.artifact_type] || ARTIFACT_ICONS.code
          const being = a.created_by ? getBeingById(a.created_by) : null
          const filename = a.path ? a.path.split('/').pop() : a.title
          const canPreview = PREVIEWABLE_TYPES.has(a.artifact_type)
          return (
            <div
              key={a.artifact_id}
              className={`flex items-center gap-2 px-2 py-1.5 rounded bg-bg-card border border-border group ${canPreview ? 'cursor-pointer hover:border-accent-blue/40' : ''}`}
              onClick={() => canPreview && onPreview?.(a)}
            >
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.color} shrink-0`}>
                {cfg.icon}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate">{a.title}</div>
                <div className="flex items-center gap-2 text-[9px] text-text-muted">
                  <span>{formatFileSize(a.file_size)}</span>
                  {a.skill_id && <span className="font-mono">{a.skill_id}</span>}
                  {being && <span>{being.name}</span>}
                  <span>{timeAgo(a.created_at)}</span>
                </div>
              </div>
              <a
                href={`/api/mc/artifacts/${a.artifact_id}/download`}
                onClick={e => e.stopPropagation()}
                className="opacity-0 group-hover:opacity-100 text-[10px] text-accent-blue hover:underline transition-opacity shrink-0"
                download
              >
                Download
              </a>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function TaskCard({ task, onDragStart, onClick, getBeingById, onBeingClick }) {
  const prio = PRIORITY_CONFIG[task.priority]
  const isWorking = task.status === 'in_progress' && task.assignees.some(id => {
    const b = getBeingById(id)
    return b && b.status === 'busy'
  })

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, task.id)}
      onClick={() => onClick(task)}
      className={`bg-bg-card border rounded-lg p-2.5 cursor-grab active:cursor-grabbing hover:border-border-bright transition-colors group ${
        isWorking ? 'border-accent-blue/40' : 'border-border'
      }`}
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded border ${prio.bg} ${prio.text} ${prio.border}`}>
            {prio.label}
          </span>
          {isWorking && (
            <span className="flex items-center gap-1 text-[10px] text-accent-blue">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-blue animate-pulse" />
              Working
            </span>
          )}
        </div>
        <span className="text-[10px] text-text-muted font-mono">{timeAgo(task.updated)}</span>
      </div>

      <h3 className="text-sm font-medium mb-1 leading-snug group-hover:text-accent-blue transition-colors">{task.title}</h3>
      <p className="text-xs text-text-secondary mb-1 line-clamp-2 leading-relaxed">{task.description}</p>

      <StepProgress steps={task.steps} created={task.created} />
      <ArtifactBadge artifacts={task.artifacts} />

      <div className="flex items-center gap-1">
        {task.assignees.map(id => {
          const being = getBeingById(id)
          if (!being) return null
          const isBusy = being.status === 'busy'
          return (
            <button
              key={id}
              onClick={(e) => { e.stopPropagation(); onBeingClick(being.id) }}
              className={`w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold hover:ring-1 hover:ring-white/30 transition-all ${isBusy ? 'ring-1 ring-accent-blue/50' : ''}`}
              style={{ backgroundColor: being.color + '22', color: being.color }}
              title={`${being.name}${isBusy ? ' (working...)' : ''}`}
            >
              {being.avatar}
            </button>
          )
        })}
        <span className="text-[10px] text-text-muted ml-auto font-mono">{task.id}</span>
      </div>
    </div>
  )
}

// ── Column ───────────────────────────────────────────────────

function Column({ status, tasks, onDragOver, onDrop, onDragStart, onCardClick, dragOverStatus, getBeingById, onBeingClick }) {
  const config = STATUS_CONFIG[status]
  const isOver = dragOverStatus === status

  return (
    <div
      className="flex flex-col min-w-[220px] flex-1"
      onDragOver={(e) => { e.preventDefault(); onDragOver(e, status) }}
      onDragLeave={() => onDragOver(null, null)}
      onDrop={(e) => onDrop(e, status)}
    >
      <div className="flex items-center gap-2 px-2 py-1.5 mb-2">
        <div className={`w-2 h-2 rounded-full ${config.dot}`} />
        <span className={`text-xs font-semibold uppercase tracking-wider ${config.color}`}>
          {config.label}
        </span>
        <span className="text-[10px] text-text-muted font-mono ml-auto">{tasks.length}</span>
      </div>

      <div className={`flex flex-col gap-1.5 flex-1 min-h-[100px] p-1 rounded-lg border transition-colors ${
        isOver ? 'border-accent-blue/40 bg-accent-blue/5' : 'border-transparent'
      }`}>
        {tasks.map(task => (
          <TaskCard key={task.id} task={task} onDragStart={onDragStart} onClick={onCardClick} getBeingById={getBeingById} onBeingClick={onBeingClick} />
        ))}
      </div>
    </div>
  )
}

// ── Main TaskBoard ───────────────────────────────────────────

export function TaskBoard({ fullWidth = false }) {
  const { beings, getBeingById, openBeingDetail } = useBeings()
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({ assignee: '', priority: '', from: '', to: '' })
  const [dragOverStatus, setDragOverStatus] = useState(null)
  const [showModal, setShowModal] = useState(false) // false | 'create' | task object for edit
  const [detailTask, setDetailTask] = useState(null)
  const [detailHistory, setDetailHistory] = useState([])
  const [previewArtifact, setPreviewArtifact] = useState(null)

  // Fetch tasks from API
  const fetchTasks = useCallback(async () => {
    try {
      const apiFilters = {}
      if (filters.assignee) apiFilters.assignee = filters.assignee
      if (filters.priority) apiFilters.priority = filters.priority
      if (filters.from) apiFilters.from = new Date(filters.from).toISOString()
      if (filters.to) apiFilters.to = new Date(filters.to).toISOString()
      const { tasks: fetched } = await tasksApi.list(apiFilters)
      setTasks(fetched)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { fetchTasks() }, [fetchTasks])

  // Periodic polling every 15s for task board freshness
  useEffect(() => {
    const interval = setInterval(fetchTasks, 15000)
    return () => clearInterval(interval)
  }, [fetchTasks])

  // Real-time task updates via SSE
  const tasksRef = useRef(tasks)
  tasksRef.current = tasks

  useSharedSSE({
    task_update(evt) {
      const { action, task, task_id } = evt
      if (action === 'created' && task) {
        setTasks(prev => {
          if (prev.some(t => t.id === task.id)) return prev
          return [...prev, task]
        })
      } else if (action === 'updated' && task) {
        setTasks(prev => {
          const idx = prev.findIndex(t => t.id === task.id)
          if (idx >= 0) return prev.map(t => t.id === task.id ? task : t)
          // Task not in list yet (may have been created while filters excluded it)
          return [...prev, task]
        })
        // Update detail panel if open
        if (detailTask?.id === task.id) {
          setDetailTask(task)
        }
      } else if (action === 'deleted' && task_id) {
        setTasks(prev => prev.filter(t => t.id !== task_id))
        if (detailTask?.id === task_id) setDetailTask(null)
      }
    },
    task_steps_update(evt) {
      const { task_id, steps, step } = evt
      if (!task_id) return
      setTasks(prev => prev.map(t => {
        if (t.id !== task_id) return t
        // Full steps array (from create_task_steps)
        if (steps) return { ...t, steps }
        // Single step update
        if (step && t.steps) {
          const updated = t.steps.map(s => s.id === step.id ? step : s)
          return { ...t, steps: updated }
        }
        return t
      }))
      // Update detail panel too
      if (detailTask?.id === task_id) {
        setDetailTask(prev => {
          if (!prev || prev.id !== task_id) return prev
          if (steps) return { ...prev, steps }
          if (step && prev.steps) {
            return { ...prev, steps: prev.steps.map(s => s.id === step.id ? step : s) }
          }
          return prev
        })
      }
    },
    artifact_created(evt) {
      const { task_id, artifact } = evt
      if (!task_id || !artifact) return
      setTasks(prev => prev.map(t => {
        if (t.id !== task_id) return t
        const arts = t.artifacts || []
        if (arts.some(a => a.artifact_id === artifact.artifact_id)) return t
        return { ...t, artifacts: [...arts, artifact] }
      }))
      if (detailTask?.id === task_id) {
        setDetailTask(prev => {
          if (!prev || prev.id !== task_id) return prev
          const arts = prev.artifacts || []
          if (arts.some(a => a.artifact_id === artifact.artifact_id)) return prev
          return { ...prev, artifacts: [...arts, artifact] }
        })
      }
    },
  })

  // Drag & drop — persist status change
  const handleDragStart = (e, taskId) => {
    e.dataTransfer.setData('text/plain', taskId)
  }

  const handleDragOver = (_e, status) => {
    setDragOverStatus(status)
  }

  const handleDrop = async (e, newStatus) => {
    e.preventDefault()
    const taskId = e.dataTransfer.getData('text/plain')
    setDragOverStatus(null)

    // Optimistic update
    setTasks(prev => prev.map(t =>
      t.id === taskId ? { ...t, status: newStatus, updated: new Date().toISOString() } : t
    ))

    try {
      await tasksApi.update(taskId, { status: newStatus })
    } catch {
      fetchTasks() // Revert on error
    }
  }

  // CRUD handlers
  const handleCreate = async (formData) => {
    try {
      const { task } = await tasksApi.create(formData)
      setTasks(prev => [...prev, task])
      setShowModal(false)
    } catch (err) {
      alert('Failed to create task: ' + err.message)
    }
  }

  const handleEdit = async (formData) => {
    const taskId = showModal.id
    try {
      const { task } = await tasksApi.update(taskId, formData)
      setTasks(prev => prev.map(t => t.id === taskId ? task : t))
      setShowModal(false)
      // Refresh detail if open
      if (detailTask?.id === taskId) {
        openDetail(task)
      }
    } catch (err) {
      alert('Failed to update task: ' + err.message)
    }
  }

  const handleDelete = async (taskId) => {
    try {
      await tasksApi.delete(taskId)
      setTasks(prev => prev.filter(t => t.id !== taskId))
      setDetailTask(null)
    } catch (err) {
      alert('Failed to delete task: ' + err.message)
    }
  }

  const handleCancel = async (taskId) => {
    try {
      await tasksApi.cancel(taskId)
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: 'cancelled' } : t))
      setDetailTask(null)
    } catch (err) {
      alert('Failed to cancel task: ' + err.message)
    }
  }

  // Detail view
  const openDetail = async (task) => {
    setDetailTask(task)
    try {
      const { history } = await tasksApi.history(task.id)
      setDetailHistory(history)
    } catch {
      setDetailHistory([])
    }
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
          <span>{tasks.length} total</span>
        </div>
      </div>

      {/* Filters */}
      <div className="px-3 py-2 border-b border-border/50">
        <FiltersBar
          filters={filters}
          setFilters={setFilters}
          onCreateClick={() => setShowModal('create')}
          beings={beings}
        />
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-3 mt-2 px-3 py-1.5 bg-accent-red/10 border border-accent-red/20 rounded text-xs text-accent-red">
          {error}
          <button onClick={fetchTasks} className="ml-2 underline">Retry</button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="p-8 text-center text-xs text-text-muted">Loading tasks...</div>
      )}

      {/* Kanban Columns */}
      {!loading && (
        <div className="p-2 flex gap-2 overflow-x-auto">
          {TASK_STATUSES.map(status => (
            <Column
              key={status}
              status={status}
              tasks={tasks.filter(t => t.status === status)}
              onDragStart={handleDragStart}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onCardClick={openDetail}
              dragOverStatus={dragOverStatus}
              getBeingById={getBeingById}
              onBeingClick={openBeingDetail}
            />
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <TaskModal
          task={showModal === 'create' ? null : showModal}
          onSave={showModal === 'create' ? handleCreate : handleEdit}
          onClose={() => setShowModal(false)}
          beings={beings}
        />
      )}

      {/* Detail slide-out */}
      {detailTask && (
        <TaskDetail
          task={detailTask}
          history={detailHistory}
          onClose={() => setDetailTask(null)}
          onEdit={(task) => { setDetailTask(null); setShowModal(task) }}
          onDelete={handleDelete}
          onCancel={handleCancel}
          getBeingById={getBeingById}
          onBeingClick={openBeingDetail}
          onPreview={setPreviewArtifact}
        />
      )}

      {/* Artifact Preview Modal */}
      {previewArtifact && (
        <ArtifactPreview artifact={previewArtifact} onClose={() => setPreviewArtifact(null)} />
      )}
    </div>
  )
}
