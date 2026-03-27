import { useState, useEffect, useCallback, useContext } from 'react'
import { useSharedSSE, SSEContext } from '../context/SSEContext'
import { deliverablesApi } from '../api'
import { useSession } from '../context/SessionContext'

function authUrl(url) {
  if (!url) return url
  try {
    const stored = localStorage.getItem('mc_auth')
    if (stored) {
      const { token } = JSON.parse(stored)
      if (token) {
        const sep = url.includes('?') ? '&' : '?'
        return `${url}${sep}token=${encodeURIComponent(token)}`
      }
    }
  } catch { /* ignore */ }
  return url
}

const STATUS_CONFIG = {
  spawning: { label: 'Working', dot: 'bg-accent-blue', text: 'text-accent-blue', pulse: true },
  completed: { label: 'Done', dot: 'bg-accent-green', text: 'text-accent-green', pulse: false },
  failed: { label: 'Failed', dot: 'bg-accent-red', text: 'text-accent-red', pulse: false },
}

const FILE_ICONS = {
  html: { icon: '\u{1F310}', label: 'Website' },
  htm: { icon: '\u{1F310}', label: 'Website' },
  css: { icon: '\u{1F3A8}', label: 'Stylesheet' },
  js: { icon: '\u{26A1}', label: 'Script' },
  jsx: { icon: '\u{269B}', label: 'Component' },
  ts: { icon: '\u{1F4D8}', label: 'TypeScript' },
  tsx: { icon: '\u{269B}', label: 'Component' },
  py: { icon: '\u{1F40D}', label: 'Python' },
  json: { icon: '\u{1F4CB}', label: 'Data' },
  md: { icon: '\u{1F4DD}', label: 'Document' },
  txt: { icon: '\u{1F4C4}', label: 'Text' },
  pdf: { icon: '\u{1F4D5}', label: 'PDF' },
  csv: { icon: '\u{1F4CA}', label: 'Spreadsheet' },
  sql: { icon: '\u{1F5C3}', label: 'Database' },
  svg: { icon: '\u{1F58C}', label: 'Vector' },
  png: { icon: '\u{1F5BC}', label: 'Image' },
  jpg: { icon: '\u{1F5BC}', label: 'Image' },
  jpeg: { icon: '\u{1F5BC}', label: 'Image' },
  gif: { icon: '\u{1F39E}', label: 'GIF' },
  mp4: { icon: '\u{1F39E}', label: 'Video' },
  mov: { icon: '\u{1F39E}', label: 'Video' },
  webm: { icon: '\u{1F39E}', label: 'Video' },
  yaml: { icon: '\u{2699}', label: 'Config' },
  yml: { icon: '\u{2699}', label: 'Config' },
}

function getFileInfo(filename) {
  const ext = (filename || '').split('.').pop()?.toLowerCase() || ''
  return FILE_ICONS[ext] || { icon: '\u{1F4C1}', label: ext.toUpperCase() || 'File' }
}

function formatBytes(bytes) {
  if (!bytes || bytes < 1024) return `${bytes || 0} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ── Agent spawn card ─────────────────────────────────────────

function SpawnCard({ spawn }) {
  const cfg = STATUS_CONFIG[spawn.status] || STATUS_CONFIG.spawning

  return (
    <div className={`p-2.5 rounded-lg border transition-all ${
      spawn.status === 'spawning'
        ? 'border-accent-blue/30 bg-accent-blue/5'
        : spawn.status === 'completed'
        ? 'border-accent-green/20 bg-accent-green/5'
        : 'border-accent-red/20 bg-accent-red/5'
    }`}>
      <div className="flex items-center gap-2">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shrink-0"
          style={{ backgroundColor: (spawn.being_color || '#666') + '22', color: spawn.being_color || '#666' }}
        >
          {spawn.being_avatar || '?'}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium text-text-primary break-words">{spawn.being_name}</span>
            <span className="text-[9px] text-text-muted px-1 py-0 rounded bg-bg-hover uppercase">{spawn.being_type}</span>
          </div>
          <p className="text-[10px] text-text-secondary mt-0.5 whitespace-pre-wrap break-words">{spawn.title}</p>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <div className={`w-2 h-2 rounded-full ${cfg.dot} ${cfg.pulse ? 'animate-pulse' : ''}`} />
          <span className={`text-[10px] font-mono ${cfg.text}`}>{cfg.label}</span>
        </div>
      </div>

      {spawn.status === 'spawning' && (
        <div className="mt-2 w-full h-1 rounded-full bg-bg-primary overflow-hidden">
          <div className="h-full rounded-full bg-accent-blue animate-[progress_2s_ease-in-out_infinite]" style={{ width: '60%' }} />
        </div>
      )}

      {spawn.status === 'completed' && spawn.output_preview && (
        <p className="mt-1.5 text-[10px] text-text-muted whitespace-pre-wrap break-words">{spawn.output_preview}</p>
      )}
    </div>
  )
}

// ── Deliverable card ─────────────────────────────────────────

function DeliverableCard({ item }) {
  const info = getFileInfo(item.filename)
  const isWebViewable = /\.(html?|svg|png|jpg|jpeg|gif|pdf|txt|md|mp4|mov|webm)$/i.test(item.filename || '')

  return (
    <div className="p-2.5 rounded-lg border border-accent-purple/20 bg-accent-purple/5 transition-all hover:border-accent-purple/40">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-accent-purple/15 flex items-center justify-center text-sm shrink-0">
          {info.icon}
        </div>

        <div className="flex-1 min-w-0">
          <span className="text-xs font-medium text-text-primary block break-words">{item.filename}</span>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[9px] text-accent-purple px-1 py-0 rounded bg-accent-purple/10 uppercase">{info.label}</span>
            {item.line_count > 0 && (
              <span className="text-[9px] text-text-muted">{item.line_count} lines</span>
            )}
            {item.byte_size > 0 && (
              <span className="text-[9px] text-text-muted">{formatBytes(item.byte_size)}</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1.5 mt-2">
        {isWebViewable && item.url && (
          <a
            href={authUrl(item.url)}
            target="_blank"
            rel="noopener noreferrer"
            className="px-2 py-0.5 text-[10px] font-medium rounded bg-accent-purple/20 text-accent-purple hover:bg-accent-purple/30 transition-colors"
          >
            Open
          </a>
        )}
        {item.url && (
          <a
            href={authUrl(item.url)}
            download={item.filename}
            className="px-2 py-0.5 text-[10px] font-medium rounded bg-bg-hover text-text-secondary hover:text-text-primary transition-colors"
          >
            Download
          </a>
        )}
      </div>
    </div>
  )
}

// ── Session group header ─────────────────────────────────────

function SessionHeader({ name, activeCount, totalCount }) {
  return (
    <div className="flex items-center gap-2 mb-1.5 px-1">
      <div className="flex-1 h-px bg-border/50" />
      <div className="flex items-center gap-1.5">
        {activeCount > 0 && (
          <div className="w-1.5 h-1.5 rounded-full bg-accent-blue animate-pulse" />
        )}
        <span className="text-[9px] text-text-muted font-medium truncate max-w-[160px]">{name}</span>
        <span className="text-[9px] text-text-muted font-mono">{totalCount - activeCount}/{totalCount}</span>
      </div>
      <div className="flex-1 h-px bg-border/50" />
    </div>
  )
}

// ── Main tracker ─────────────────────────────────────────────

export function OrchestrationTracker() {
  const [deliverables, setDeliverables] = useState([])
  const { activeSessionId } = useSession()

  // Load deliverables scoped to active session
  const loadDeliverables = useCallback(() => {
    deliverablesApi.list(null, activeSessionId).then(data => {
      const items = Array.isArray(data) ? data : data?.deliverables || []
      setDeliverables(items)
    }).catch(() => {})
  }, [activeSessionId])
  const sseCtx = useContext(SSEContext)
  useEffect(() => { loadDeliverables() }, [loadDeliverables])
  useEffect(() => {
    if (sseCtx?.connected) return
    const interval = setInterval(loadDeliverables, 10000)
    return () => clearInterval(interval)
  }, [sseCtx?.connected, loadDeliverables])

  useSharedSSE({
    deliverable_created(data) {
      if (!activeSessionId) return
      if (!data.session_id) return
      if (data.session_id !== activeSessionId) return
      setDeliverables(prev => {
        if (prev.some(d => d.id === data.id)) return prev
        return [data, ...prev]
      })
    },
    being_typing(data) {
      if (!data.active) {
        setTimeout(loadDeliverables, 1000)
      }
    },
  })

  return (
    <div className="bg-bg-secondary border border-border rounded-lg flex flex-col" style={{ maxHeight: 'calc(100vh - 100px)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-text-primary">Outputs</span>
        {deliverables.length > 0 && (
          <span className="text-[9px] font-mono text-accent-purple">{deliverables.length}</span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-2">
        {deliverables.length === 0 && (
          <div className="text-center py-8">
            <div className="text-text-muted text-xs mb-1">No outputs yet</div>
            <div className="text-text-muted text-[10px]">Files, videos, and documents will appear here</div>
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          {deliverables.map(d => (
            <DeliverableCard key={d.id} item={d} />
          ))}
        </div>
      </div>
    </div>
  )
}
