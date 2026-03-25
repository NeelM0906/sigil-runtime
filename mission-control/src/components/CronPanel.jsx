import { useState, useEffect, useCallback } from 'react'
import { cronApi } from '../api'
import { timeAgo } from '../store'

const TYPE_BADGE = {
  cron: 'bg-accent-blue/15 text-accent-blue border-accent-blue/30',
  at: 'bg-accent-amber/15 text-accent-amber border-accent-amber/30',
  every: 'bg-accent-purple/15 text-accent-purple border-accent-purple/30',
}

const STATUS_DOT = {
  ok: 'bg-accent-green',
  error: 'bg-accent-red',
  running: 'bg-accent-blue animate-pulse',
}

export function CronPanel() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [expandedRuns, setExpandedRuns] = useState(null)
  const [runs, setRuns] = useState([])

  const fetchTasks = useCallback(async () => {
    try {
      const { tasks: t } = await cronApi.list()
      setTasks(t || [])
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchTasks() }, [fetchTasks])

  const toggleEnabled = async (taskId, current) => {
    try {
      await cronApi.update(taskId, { enabled: !current })
      setTasks(prev => prev.map(t => t.id === taskId ? { ...t, enabled: !current } : t))
    } catch (err) { alert('Failed: ' + err.message) }
  }

  const forceRun = async (taskId) => {
    try {
      await cronApi.forceRun(taskId)
      fetchTasks()
    } catch (err) { alert('Run failed: ' + err.message) }
  }

  const deleteTask = async (taskId) => {
    if (!confirm('Delete this scheduled task?')) return
    try {
      await cronApi.remove(taskId)
      setTasks(prev => prev.filter(t => t.id !== taskId))
    } catch (err) { alert('Delete failed: ' + err.message) }
  }

  const loadRuns = async (taskId) => {
    if (expandedRuns === taskId) { setExpandedRuns(null); return }
    try {
      const { runs: r } = await cronApi.runs(taskId)
      setRuns(r || [])
      setExpandedRuns(taskId)
    } catch { setRuns([]) }
  }

  if (loading) return <div className="text-text-muted text-xs p-2">Loading schedules...</div>

  return (
    <div className="bg-bg-secondary border border-border rounded-lg p-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">Scheduled Tasks</h3>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="text-[10px] px-2 py-1 text-accent-blue hover:bg-accent-blue/10 rounded transition-colors"
        >
          {showCreate ? 'Cancel' : '+ Add'}
        </button>
      </div>

      {showCreate && <CreateForm onCreated={() => { setShowCreate(false); fetchTasks() }} />}

      {tasks.length === 0 ? (
        <p className="text-xs text-text-muted py-2">No scheduled tasks. Beings can create them, or add one manually.</p>
      ) : (
        <div className="space-y-2">
          {tasks.map(task => (
            <div key={task.id} className="bg-bg-card border border-border rounded p-2">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => toggleEnabled(task.id, task.enabled)}
                    className={`w-7 h-4 rounded-full transition-colors relative ${task.enabled ? 'bg-accent-green' : 'bg-border'}`}
                  >
                    <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${task.enabled ? 'left-3.5' : 'left-0.5'}`} />
                  </button>
                  <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded border ${TYPE_BADGE[task.schedule_type || 'cron'] || TYPE_BADGE.cron}`}>
                    {(task.schedule_type || 'cron').toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => forceRun(task.id)} className="text-[9px] text-text-muted hover:text-accent-blue transition-colors" title="Run now">▶</button>
                  <button onClick={() => loadRuns(task.id)} className="text-[9px] text-text-muted hover:text-accent-blue transition-colors" title="History">📋</button>
                  <button onClick={() => deleteTask(task.id)} className="text-[9px] text-text-muted hover:text-accent-red transition-colors" title="Delete">✕</button>
                </div>
              </div>
              <p className="text-xs text-text-primary line-clamp-2 mb-1">{task.task_goal}</p>
              <div className="flex items-center gap-2 text-[9px] text-text-muted">
                {task.cron_expression && <span className="font-mono">{task.cron_expression}</span>}
                {task.interval_seconds && <span>{task.interval_seconds}s interval</span>}
                {task.next_run_at && <span>Next: {timeAgo(task.next_run_at)}</span>}
                {task.last_run_at && <span>Last: {timeAgo(task.last_run_at)}</span>}
              </div>

              {expandedRuns === task.id && (
                <div className="mt-2 pt-2 border-t border-border space-y-1">
                  {runs.length === 0 ? (
                    <p className="text-[9px] text-text-muted">No runs yet</p>
                  ) : runs.map((run, i) => (
                    <div key={run.id || i} className="flex items-center gap-2 text-[9px]">
                      <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[run.status] || 'bg-text-muted'}`} />
                      <span className="text-text-muted font-mono">{run.ran_at?.slice(0, 16)}</span>
                      <span className="text-text-muted">{run.duration_ms}ms</span>
                      <span className="text-text-secondary truncate flex-1">{run.result_text?.slice(0, 60) || run.error_detail?.slice(0, 60) || ''}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CreateForm({ onCreated }) {
  const [form, setForm] = useState({
    task_goal: '',
    schedule_type: 'cron',
    cron_expression: '0 7 * * *',
    run_at: '',
    interval_seconds: 3600,
  })
  const [creating, setCreating] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.task_goal.trim()) return
    setCreating(true)
    try {
      await cronApi.create({
        task_goal: form.task_goal,
        schedule_type: form.schedule_type,
        cron_expression: form.schedule_type === 'cron' ? form.cron_expression : undefined,
        run_at: form.schedule_type === 'at' ? form.run_at : undefined,
        interval_seconds: form.schedule_type === 'every' ? form.interval_seconds : undefined,
        delete_after_run: form.schedule_type === 'at',
      })
      onCreated()
    } catch (err) { alert('Create failed: ' + err.message) }
    finally { setCreating(false) }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-3 p-2 bg-bg-card border border-border rounded space-y-2">
      <input
        value={form.task_goal}
        onChange={e => setForm({ ...form, task_goal: e.target.value })}
        placeholder="What should the agent do?"
        className="w-full px-2 py-1.5 bg-bg-primary border border-border rounded text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue"
      />
      <div className="flex gap-2">
        {['cron', 'at', 'every'].map(t => (
          <button
            key={t}
            type="button"
            onClick={() => setForm({ ...form, schedule_type: t })}
            className={`px-2 py-1 text-[10px] rounded border transition-colors ${form.schedule_type === t ? 'border-accent-blue text-accent-blue bg-accent-blue/10' : 'border-border text-text-muted'}`}
          >
            {t === 'cron' ? 'Recurring' : t === 'at' ? 'One-shot' : 'Interval'}
          </button>
        ))}
      </div>
      {form.schedule_type === 'cron' && (
        <input
          value={form.cron_expression}
          onChange={e => setForm({ ...form, cron_expression: e.target.value })}
          placeholder="0 7 * * * (7am daily)"
          className="w-full px-2 py-1.5 bg-bg-primary border border-border rounded text-xs font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue"
        />
      )}
      {form.schedule_type === 'at' && (
        <input
          type="datetime-local"
          value={form.run_at}
          onChange={e => setForm({ ...form, run_at: e.target.value })}
          className="w-full px-2 py-1.5 bg-bg-primary border border-border rounded text-xs text-text-primary focus:outline-none focus:border-accent-blue"
        />
      )}
      {form.schedule_type === 'every' && (
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={form.interval_seconds}
            onChange={e => setForm({ ...form, interval_seconds: parseInt(e.target.value) || 60 })}
            min={60}
            className="w-24 px-2 py-1.5 bg-bg-primary border border-border rounded text-xs font-mono text-text-primary focus:outline-none focus:border-accent-blue"
          />
          <span className="text-[10px] text-text-muted">seconds</span>
        </div>
      )}
      <button
        type="submit"
        disabled={!form.task_goal.trim() || creating}
        className="px-3 py-1.5 text-xs font-medium bg-accent-blue text-white rounded hover:bg-accent-blue/80 disabled:opacity-30 transition-colors"
      >
        {creating ? 'Creating...' : 'Schedule'}
      </button>
    </form>
  )
}
