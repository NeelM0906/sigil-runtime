import { useState, useEffect } from 'react'
import { codeApi } from '../api'

export function CodeStatusCard({ onOpenCode }) {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const check = () => {
      codeApi.health()
        .then(h => { setHealth(h); setError(false) })
        .catch(() => setError(true))
    }
    check()
    const interval = setInterval(check, 15000)
    return () => clearInterval(interval)
  }, [])

  if (error) return null // Don't show card if code agent not available

  const isRunning = health?.running
  const sessionCount = health?.session_count || 0
  const model = health?.model?.split('/').pop() || 'code agent'

  return (
    <div className="rounded-lg border border-border bg-bg-card p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-accent-purple/20 flex items-center justify-center text-[10px]">
            &gt;_
          </div>
          <span className="text-xs font-semibold text-text-primary">Code Agent</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-accent-green animate-pulse' : 'bg-text-muted'}`} />
          <span className="text-[10px] text-text-muted">{isRunning ? 'Active' : 'Idle'}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-2">
        <div className="rounded bg-bg-primary px-2 py-1.5 text-center">
          <div className="text-sm font-mono font-medium text-text-primary">{sessionCount}</div>
          <div className="text-[9px] text-text-muted uppercase">Sessions</div>
        </div>
        <div className="rounded bg-bg-primary px-2 py-1.5 text-center">
          <div className="text-[10px] font-mono text-text-secondary truncate">{model}</div>
          <div className="text-[9px] text-text-muted uppercase">Model</div>
        </div>
      </div>

      <button
        onClick={onOpenCode}
        className="w-full px-3 py-1.5 rounded bg-accent-purple/15 text-accent-purple text-[11px] font-medium hover:bg-accent-purple/25 transition-colors"
      >
        Open Code Workspace
      </button>
    </div>
  )
}
