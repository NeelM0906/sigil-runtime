import { useState, useRef, useEffect, useCallback, Children } from 'react'
import Markdown from 'react-markdown'
import { useBeings } from '../context/BeingsContext'
import { chatApi, tasksApi, deliverablesApi } from '../api'
import { useSSE } from '../hooks/useSSE'
import { timeAgo } from '../store'

// ── Inline Task Card ─────────────────────────────────────────

function InlineTaskCard({ taskId }) {
  const [task, setTask] = useState(null)
  useEffect(() => {
    if (!taskId) return
    tasksApi.get(taskId).then(({ task: t }) => setTask(t)).catch(() => {})
  }, [taskId])

  if (!task) return null

  const prioColors = {
    critical: 'border-accent-red/30 bg-accent-red/5',
    high: 'border-accent-amber/30 bg-accent-amber/5',
    medium: 'border-accent-blue/30 bg-accent-blue/5',
    low: 'border-border bg-bg-card',
  }
  const statusDot = {
    backlog: 'bg-text-muted', in_progress: 'bg-accent-blue',
    in_review: 'bg-accent-amber', done: 'bg-accent-green',
  }

  return (
    <div className={`mt-1.5 px-2 py-1.5 rounded border text-[10px] ${prioColors[task.priority] || prioColors.low}`}>
      <div className="flex items-center gap-1.5">
        <div className={`w-1.5 h-1.5 rounded-full ${statusDot[task.status]}`} />
        <span className="font-medium text-text-primary">{task.title}</span>
        <span className="text-text-muted font-mono ml-auto">{task.id || task.task_id}</span>
      </div>
    </div>
  )
}

// ── Message Bubble ───────────────────────────────────────────

function MessageBubble({ msg, getBeingById, onBeingClick }) {
  const isUser = msg.sender === 'user'
  const isSystem = msg.type === 'system'
  const being = (!isUser && !isSystem) ? getBeingById(msg.sender) : null

  // System messages
  if (isSystem) {
    return (
      <div className="flex items-center gap-2 py-1">
        <div className="flex-1 h-px bg-border/50" />
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-bg-card border border-border">
          <svg className="w-3 h-3 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-[10px] text-text-secondary">{msg.content}</span>
          {msg.taskRef && <InlineTaskCard taskId={msg.taskRef} />}
        </div>
        <div className="flex-1 h-px bg-border/50" />
      </div>
    )
  }

  // Type badge
  const typeBadge = msg.type === 'group'
    ? { label: 'GROUP', color: 'bg-accent-purple/15 text-accent-purple' }
    : msg.type === 'broadcast'
    ? { label: 'ALL', color: 'bg-accent-cyan/15 text-accent-cyan' }
    : null

  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <button
        onClick={() => !isUser && being && onBeingClick(being.id)}
        className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 hover:ring-1 hover:ring-white/20 transition-all"
        style={{
          backgroundColor: isUser ? '#3b82f622' : (being?.color || '#666') + '22',
          color: isUser ? '#3b82f6' : being?.color || '#666'
        }}
      >
        {isUser ? 'U' : being?.avatar || '?'}
      </button>

      <div className={`max-w-[75%] ${isUser ? 'text-right' : ''}`}>
        {/* Header: sender + targets + mode + type */}
        <div className={`flex items-center gap-1.5 mb-0.5 flex-wrap ${isUser ? 'justify-end' : ''}`}>
          <span className="text-xs font-medium">{isUser ? 'You' : being?.name || msg.sender}</span>

          {msg.targets && msg.targets.length > 0 && (
            <span className="text-[10px] text-text-muted">
              &rarr;&nbsp;{msg.targets.map(t => {
                const b = getBeingById(t)
                return b ? `@${b.name}` : `@${t}`
              }).join(', ')}
            </span>
          )}

          {typeBadge && (
            <span className={`px-1 py-0 text-[9px] font-bold rounded ${typeBadge.color}`}>
              {typeBadge.label}
            </span>
          )}

          {msg.mode && (
            <span className={`px-1 py-0 text-[9px] font-bold rounded ${
              msg.mode === 'parallel' ? 'bg-accent-green/15 text-accent-green'
              : msg.mode === 'sequential' ? 'bg-accent-amber/15 text-accent-amber'
              : 'bg-accent-cyan/15 text-accent-cyan'
            }`}>
              {msg.mode.toUpperCase()}
            </span>
          )}
        </div>

        {/* Content */}
        <div className={`text-sm leading-relaxed px-3 py-2 rounded-lg ${
          isUser
            ? 'bg-accent-blue/15 text-text-primary border border-accent-blue/20'
            : 'bg-bg-card text-text-primary border border-border'
        }`}>
          <HighlightedContent content={msg.content} getBeingById={getBeingById} />
        </div>

        {/* Task reference */}
        {msg.taskRef && <InlineTaskCard taskId={msg.taskRef} />}

        <div className="text-[10px] text-text-muted mt-0.5 font-mono">
          {new Date(msg.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  )
}

// ── Deliverable Card ─────────────────────────────────────────

const FILE_ICONS = {
  html: { icon: '\u{1F310}', label: 'Website', color: '#e44d26' },
  css: { icon: '\u{1F3A8}', label: 'Stylesheet', color: '#264de4' },
  js: { icon: '\u26A1', label: 'JavaScript', color: '#f7df1e' },
  javascript: { icon: '\u26A1', label: 'JavaScript', color: '#f7df1e' },
  py: { icon: '\u{1F40D}', label: 'Python', color: '#3776ab' },
  python: { icon: '\u{1F40D}', label: 'Python', color: '#3776ab' },
  json: { icon: '\u{1F4CB}', label: 'JSON', color: '#6b7280' },
  md: { icon: '\u{1F4DD}', label: 'Markdown', color: '#6b7280' },
  sql: { icon: '\u{1F5C3}\uFE0F', label: 'SQL', color: '#336791' },
  svg: { icon: '\u{1F5BC}\uFE0F', label: 'SVG', color: '#ffb13b' },
  default: { icon: '\u{1F4C4}', label: 'File', color: '#6b7280' },
}

function DeliverableCard({ filename, url, fileType, lineCount, byteSize }) {
  const info = FILE_ICONS[fileType] || FILE_ICONS.default
  const isViewable = ['html', 'htm', 'svg'].includes(fileType)
  const sizeLabel = byteSize > 1024
    ? `${(byteSize / 1024).toFixed(1)} KB`
    : `${byteSize} bytes`

  return (
    <div className="my-2 p-3 rounded-lg border border-border bg-bg-card/50 backdrop-blur">
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
          style={{ backgroundColor: info.color + '20' }}
        >
          {info.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-text-primary break-words">{filename}</div>
          <div className="text-[10px] text-text-muted">
            {info.label} &middot; {lineCount} lines &middot; {sizeLabel}
          </div>
        </div>
        <div className="flex gap-1.5">
          {isViewable && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 rounded-md text-[11px] font-medium bg-accent-blue/15 text-accent-blue hover:bg-accent-blue/25 transition-colors"
            >
              Open
            </a>
          )}
          <a
            href={url}
            download={filename}
            className="px-3 py-1.5 rounded-md text-[11px] font-medium bg-bg-hover text-text-secondary hover:text-text-primary transition-colors"
          >
            Download
          </a>
        </div>
      </div>
    </div>
  )
}

// ── @mention processing for text children ────────────────────

function MentionText({ children, getBeingById }) {
  const processed = Children.toArray(children).flatMap((child, ci) => {
    if (typeof child !== 'string') return [child]
    const parts = child.split(/(@\w+)/g)
    if (parts.length === 1) return [child]
    return parts.map((part, pi) => {
      if (part.startsWith('@')) {
        const name = part.slice(1).toLowerCase()
        const being = getBeingById(name) || null
        if (being) {
          return <span key={`${ci}-${pi}`} className="font-medium" style={{ color: being.color }}>{part}</span>
        }
        return <span key={`${ci}-${pi}`} className="font-medium text-accent-blue">{part}</span>
      }
      return part
    })
  })
  return <>{processed}</>
}

// ── Markdown segment with @mention support ───────────────────

function MarkdownSegment({ content, getBeingById }) {
  const m = (children) => <MentionText getBeingById={getBeingById}>{children}</MentionText>

  return (
    <Markdown
      components={{
        h1: ({ children }) => <h3 className="text-base font-bold mt-3 mb-1.5 text-text-primary">{m(children)}</h3>,
        h2: ({ children }) => <h4 className="text-sm font-bold mt-2.5 mb-1 text-text-primary">{m(children)}</h4>,
        h3: ({ children }) => <h5 className="text-sm font-semibold mt-2 mb-1 text-text-primary">{m(children)}</h5>,
        p: ({ children }) => <p className="mb-1.5 last:mb-0">{m(children)}</p>,
        strong: ({ children }) => <strong className="font-semibold text-text-primary">{m(children)}</strong>,
        em: ({ children }) => <em className="italic">{m(children)}</em>,
        ul: ({ children }) => <ul className="list-disc list-inside mb-1.5 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside mb-1.5 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="text-sm">{m(children)}</li>,
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="text-xs w-full border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="border-b border-border">{children}</thead>,
        th: ({ children }) => <th className="text-left px-2 py-1 font-semibold text-text-secondary">{m(children)}</th>,
        td: ({ children }) => <td className="px-2 py-1 border-t border-border/50">{m(children)}</td>,
        code: ({ children, className }) => {
          const isBlock = className?.includes('language-')
          if (isBlock) {
            return <code className="block bg-black/20 rounded p-2 my-1.5 text-xs font-mono overflow-x-auto">{children}</code>
          }
          return <code className="bg-black/20 rounded px-1 py-0.5 text-xs font-mono">{children}</code>
        },
        pre: ({ children }) => <pre className="my-1.5">{children}</pre>,
        hr: () => <hr className="border-border/50 my-2" />,
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-accent-blue hover:underline">{children}</a>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-accent-blue/40 pl-2 my-1.5 text-text-secondary italic">{children}</blockquote>
        ),
      }}
    >
      {content}
    </Markdown>
  )
}

// ── Highlighted @mentions + markdown + deliverable cards ─────

const DELIVERABLE_RE = /\[DELIVERABLE:(.*?):(.*?):(.*?):(\d+):(\d+)\]/g

function HighlightedContent({ content, getBeingById }) {
  // Split on deliverable markers first
  const segments = content.split(DELIVERABLE_RE)

  // segments pattern: [text, fname, url, type, lines, bytes, text, fname, ...]
  const elements = []
  let idx = 0
  while (idx < segments.length) {
    const text = segments[idx]
    if (text) {
      elements.push(
        <MarkdownSegment key={`md-${idx}`} content={text} getBeingById={getBeingById} />
      )
    }
    idx++
    // Check if next 5 items form a deliverable
    if (idx + 4 < segments.length && segments[idx] !== undefined) {
      const fname = segments[idx]
      const url = segments[idx + 1]
      const ftype = segments[idx + 2]
      const lines = parseInt(segments[idx + 3], 10)
      const bytes = parseInt(segments[idx + 4], 10)
      if (fname && url) {
        elements.push(
          <DeliverableCard
            key={`dlv-${idx}`}
            filename={fname}
            url={url}
            fileType={ftype}
            lineCount={lines}
            byteSize={bytes}
          />
        )
      }
      idx += 5
    }
  }

  return <>{elements}</>
}

// ── Mention Dropdown ─────────────────────────────────────────

// Chat-routable types — voice agents use Bland API, not chat
const CHAT_ROUTABLE_TYPES = new Set(['runtime', 'sister', 'subagent'])

function MentionDropdown({ filter, onSelect, beings }) {
  const filtered = beings
    .filter(b => CHAT_ROUTABLE_TYPES.has(b.type))
    .filter(b =>
      b.name.toLowerCase().includes(filter.toLowerCase()) ||
      b.id.toLowerCase().includes(filter.toLowerCase()) ||
      (b.role || '').toLowerCase().includes(filter.toLowerCase())
    )

  if (filtered.length === 0) return null

  return (
    <div className="absolute bottom-full left-0 mb-1 w-64 bg-bg-card border border-border-bright rounded-lg shadow-xl overflow-hidden z-50">
      {filtered.map(being => (
        <button
          key={being.id}
          onClick={() => onSelect(being)}
          className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-bg-hover transition-colors"
        >
          <div
            className="w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold"
            style={{ backgroundColor: being.color + '22', color: being.color }}
          >
            {being.avatar}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium">{being.name}</div>
            <div className="text-[10px] text-text-muted truncate">{being.role}</div>
          </div>
          <div className={`w-2 h-2 rounded-full ${
            being.status === 'online' ? 'bg-accent-green'
            : being.status === 'busy' ? 'bg-accent-amber'
            : 'bg-text-muted'
          }`} />
        </button>
      ))}
    </div>
  )
}

// ── Search & Filter Bar ──────────────────────────────────────

function ChatFilters({ filters, setFilters, beings, onClear }) {
  const hasFilters = filters.search || filters.sender || filters.target

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border/50">
      <svg className="w-3.5 h-3.5 text-text-muted shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <input
        type="text"
        value={filters.search}
        onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
        placeholder="Search messages..."
        className="flex-1 bg-transparent text-xs text-text-primary placeholder:text-text-muted focus:outline-none"
      />
      <select
        value={filters.sender}
        onChange={e => setFilters(f => ({ ...f, sender: e.target.value }))}
        className="bg-bg-card border border-border rounded px-1.5 py-0.5 text-[10px] text-text-secondary focus:outline-none"
      >
        <option value="">All Senders</option>
        <option value="user">You</option>
        {beings.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
      </select>
      <select
        value={filters.target}
        onChange={e => setFilters(f => ({ ...f, target: e.target.value }))}
        className="bg-bg-card border border-border rounded px-1.5 py-0.5 text-[10px] text-text-secondary focus:outline-none"
      >
        <option value="">All Targets</option>
        {beings.map(b => <option key={b.id} value={b.id}>@{b.name}</option>)}
      </select>
      {hasFilters && (
        <button onClick={onClear} className="text-[10px] text-text-muted hover:text-accent-red transition-colors">
          Clear
        </button>
      )}
    </div>
  )
}

// ── Session Sidebar ──────────────────────────────────────────

function SessionSidebar({ sessions, activeSessionId, onSelect, onCreate, onRename, onDelete }) {
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')

  const handleCreate = () => {
    if (!newName.trim()) return
    onCreate(newName.trim())
    setNewName('')
    setCreating(false)
  }

  const handleRename = (id) => {
    if (!editName.trim()) return
    onRename(id, editName.trim())
    setEditingId(null)
  }

  return (
    <div className="w-48 border-r border-border flex flex-col shrink-0">
      <div className="flex items-center justify-between px-2 py-2 border-b border-border/50">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Sessions</span>
        <button
          onClick={() => setCreating(!creating)}
          className="w-5 h-5 flex items-center justify-center rounded text-text-muted hover:text-accent-blue hover:bg-accent-blue/10 transition-colors"
          title="New session"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>
      </div>

      {creating && (
        <div className="px-2 py-1.5 border-b border-border/30">
          <input
            autoFocus
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setCreating(false) }}
            placeholder="Session name..."
            className="w-full bg-bg-card border border-border rounded px-2 py-1 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue/50"
          />
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {sessions.map(s => (
          <div
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`group flex items-center gap-1.5 px-2 py-1.5 cursor-pointer text-xs transition-colors ${
              s.id === activeSessionId
                ? 'bg-accent-blue/10 text-accent-blue border-l-2 border-accent-blue'
                : 'text-text-secondary hover:bg-bg-hover border-l-2 border-transparent'
            }`}
          >
            {editingId === s.id ? (
              <input
                autoFocus
                value={editName}
                onChange={e => setEditName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleRename(s.id); if (e.key === 'Escape') setEditingId(null) }}
                onBlur={() => handleRename(s.id)}
                className="flex-1 bg-bg-card border border-border rounded px-1 py-0.5 text-xs text-text-primary focus:outline-none"
                onClick={e => e.stopPropagation()}
              />
            ) : (
              <>
                <svg className="w-3 h-3 shrink-0 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span className="flex-1 truncate">{s.name}</span>
                <div className="hidden group-hover:flex items-center gap-0.5">
                  <button
                    onClick={e => { e.stopPropagation(); setEditingId(s.id); setEditName(s.name) }}
                    className="w-4 h-4 flex items-center justify-center rounded text-text-muted hover:text-text-primary"
                    title="Rename"
                  >
                    <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  {s.id !== 'general' && (
                    <button
                      onClick={e => { e.stopPropagation(); onDelete(s.id) }}
                      className="w-4 h-4 flex items-center justify-center rounded text-text-muted hover:text-accent-red"
                      title="Delete"
                    >
                      <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main Chat Window ─────────────────────────────────────────

export function ChatWindow() {
  const { beings, getBeingById, openBeingDetail } = useBeings()
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)
  const [input, setInput] = useState('')
  const [mentionFilter, setMentionFilter] = useState(null)
  const [targets, setTargets] = useState([])
  const [execMode, setExecMode] = useState('auto')
  const [filters, setFilters] = useState({ search: '', sender: '', target: '' })
  const [showFilters, setShowFilters] = useState(false)
  const [typingBeings, setTypingBeings] = useState(new Map())
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Session state
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [showSessions, setShowSessions] = useState(true)
  const activeSessionRef = useRef(activeSessionId)
  activeSessionRef.current = activeSessionId
  const [awaitingReplySince, setAwaitingReplySince] = useState(null)

  // Load sessions on mount (scoped to user)
  useEffect(() => {
    chatApi.sessions().then(({ sessions: s }) => {
      setSessions(s)
      if (s.length > 0 && !activeSessionId) setActiveSessionId(s[0].id)
    }).catch(() => {})
  }, [])

  // Load messages from API
  const isInitialLoad = useRef(true)
  const fetchMessages = useCallback(async () => {
    if (isInitialLoad.current) setLoading(true)
    try {
      const apiFilters = { session_id: activeSessionId }
      if (filters.search) apiFilters.search = filters.search
      if (filters.sender) apiFilters.sender = filters.sender
      if (filters.target) apiFilters.target = filters.target
      const { messages: fetched } = await chatApi.list(apiFilters)
      setMessages(prev => {
        if (prev.length === fetched.length && prev.length > 0 && prev[prev.length - 1]?.id === fetched[fetched.length - 1]?.id) return prev
        return fetched
      })
      if (awaitingReplySince && fetched.some(msg => msg.sender !== 'user' && msg.timestamp > awaitingReplySince)) {
        setAwaitingReplySince(null)
      }
    } catch (err) {
      console.error('Failed to load messages:', err)
    } finally {
      if (isInitialLoad.current) {
        setLoading(false)
        isInitialLoad.current = false
      }
    }
  }, [filters, activeSessionId, awaitingReplySince])

  useEffect(() => { fetchMessages() }, [fetchMessages])

  useEffect(() => {
    if (!awaitingReplySince && typingBeings.size === 0) return undefined
    const interval = window.setInterval(() => {
      fetchMessages()
    }, 2000)
    return () => window.clearInterval(interval)
  }, [awaitingReplySince, typingBeings, fetchMessages])

  useEffect(() => {
    const onFocus = () => { fetchMessages() }
    window.addEventListener('focus', onFocus)
    document.addEventListener('visibilitychange', onFocus)
    return () => {
      window.removeEventListener('focus', onFocus)
      document.removeEventListener('visibilitychange', onFocus)
    }
  }, [fetchMessages])

  // Session CRUD handlers
  const handleCreateSession = async (name) => {
    try {
      const { session } = await chatApi.createSession(name)
      setSessions(prev => [session, ...prev])
      setActiveSessionId(session.id)
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  const handleRenameSession = async (id, name) => {
    try {
      const { session } = await chatApi.renameSession(id, name)
      setSessions(prev => prev.map(s => s.id === id ? session : s))
    } catch (err) {
      console.error('Failed to rename session:', err)
    }
  }

  const handleDeleteSession = async (id) => {
    try {
      await chatApi.deleteSession(id)
      setSessions(prev => prev.filter(s => s.id !== id))
      if (activeSessionId === id) setActiveSessionId('general')
    } catch (err) {
      console.error('Failed to delete session:', err)
    }
  }

  // SSE: incoming LLM responses and system messages arrive here
  useSSE({
    chat_message(data) {
      if (data.sender === 'user') return
      setTypingBeings(prev => {
        const next = new Map(prev)
        next.delete(data.sender)
        return next
      })
      // Only show messages for the active session (or if no session_id, show in general)
      const msgSession = data.session_id || 'general'
      if (msgSession !== activeSessionRef.current) return
      setAwaitingReplySince(null)
      setMessages(prev => {
        if (prev.some(m => m.id === data.id)) return prev
        return [...prev, data]
      })
    },
    being_typing(data) {
      setTypingBeings(prev => {
        const next = new Map(prev)
        if (data.active) {
          next.set(data.being_id, data.being_name)
        } else {
          next.delete(data.being_id)
          window.setTimeout(() => {
            fetchMessages()
          }, 250)
        }
        return next
      })
    },
    chat_session(data) {
      if (data.action === 'deleted') {
        setSessions(prev => prev.filter(s => s.id !== data.session_id))
        if (activeSessionRef.current === data.session_id) setActiveSessionId('general')
      } else {
        // Refresh sessions list on create/update
        chatApi.sessions().then(({ sessions: s }) => setSessions(s)).catch(() => {})
      }
    },
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleInputChange = (e) => {
    const val = e.target.value
    setInput(val)

    const atMatch = val.match(/@(\w*)$/)
    if (atMatch) {
      setMentionFilter(atMatch[1])
    } else {
      setMentionFilter(null)
    }
  }

  const handleMentionSelect = (being) => {
    const newInput = input.replace(/@\w*$/, `@${being.name} `)
    setInput(newInput)
    setMentionFilter(null)
    if (!targets.includes(being.id)) {
      setTargets([...targets, being.id])
    }
    inputRef.current?.focus()
  }

  const fileInputRef = useRef(null)
  const [uploading, setUploading] = useState(false)

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = '' // reset for re-upload of same file
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('being_id', targets[0] || 'prime')
      const stored = localStorage.getItem('mc_auth')
      const token = stored ? JSON.parse(stored).token : ''
      const res = await fetch('/api/mc/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      })
      if (!res.ok) throw new Error('Upload failed')
      const result = await res.json()
      // Send a system-style message about the upload
      const summary = `[Uploaded: ${result.filename} — ${result.chunks} chunks indexed${result.tables ? `, ${result.tables} tables extracted` : ''}${result.pinecone_vectors ? `, ${result.pinecone_vectors} vectors stored` : ''}]`
      await chatApi.send({
        targets: targets.length ? targets : ['prime'],
        content: summary,
        mode: 'auto',
        session_id: activeSessionId,
      })
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim()) return

    const content = input.trim()
    const mode = targets.length > 1 ? execMode : (targets.length === 1 ? null : null)

    // Optimistic: add user message immediately
    const tempMsg = {
      id: `temp-${Date.now()}`,
      type: targets.length === 0 ? 'broadcast' : targets.length === 1 ? 'direct' : 'group',
      sender: 'user',
      targets: [...targets],
      content,
      timestamp: new Date().toISOString(),
      mode,
      taskRef: null,
    }
    setMessages(prev => [...prev, tempMsg])
    setAwaitingReplySince(tempMsg.timestamp)
    setInput('')
    setTargets([])

    try {
      // POST returns the saved user message; LLM responses arrive via SSE
      const { message: saved } = await chatApi.send({
        targets: tempMsg.targets,
        content,
        mode,
        session_id: activeSessionId,
      })

      // Replace temp message with the persisted one
      setMessages(prev => prev.map(m => m.id === tempMsg.id ? saved : m))
    } catch (err) {
      console.error('Failed to send message:', err)
      setAwaitingReplySince(null)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const removeTarget = (id) => {
    setTargets(targets.filter(t => t !== id))
  }

  return (
    <div className="bg-bg-secondary border border-border rounded-lg flex h-[calc(100vh-80px)]">
      {/* Session Sidebar */}
      {showSessions && (
        <SessionSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelect={setActiveSessionId}
          onCreate={handleCreateSession}
          onRename={handleRenameSession}
          onDelete={handleDeleteSession}
        />
      )}

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSessions(!showSessions)}
            className={`p-1 rounded transition-colors ${showSessions ? 'bg-accent-blue/10 text-accent-blue' : 'text-text-muted hover:text-text-secondary'}`}
            title="Toggle sessions"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
            </svg>
          </button>
          <div className="w-1.5 h-1.5 rounded-full bg-accent-pink" />
          <h2 className="text-xs font-semibold uppercase tracking-wider">
            {sessions.find(s => s.id === activeSessionId)?.name || 'Communications'}
          </h2>
          <span className="text-[10px] text-text-muted font-mono">{messages.length} msgs</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-1 rounded transition-colors ${showFilters ? 'bg-accent-blue/20 text-accent-blue' : 'text-text-muted hover:text-text-secondary'}`}
            title="Search & Filter"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </button>
          <div className="text-[10px] text-text-muted font-mono">
            SSE live
          </div>
        </div>
      </div>

      {/* Search & Filters */}
      {showFilters && (
        <ChatFilters
          filters={filters}
          setFilters={setFilters}
          beings={beings}
          onClear={() => setFilters({ search: '', sender: '', target: '' })}
        />
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {loading && (
          <div className="text-center text-xs text-text-muted py-8">Loading messages...</div>
        )}
        {!loading && messages.length === 0 && (
          <div className="text-center text-xs text-text-muted py-8">No messages yet. Start a conversation.</div>
        )}
        {messages.map(msg => (
          <MessageBubble
            key={msg.id}
            msg={msg}
            getBeingById={getBeingById}
            onBeingClick={openBeingDetail}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Typing indicators */}
      {typingBeings.size > 0 && (
        <div className="px-3 py-1.5 border-t border-border/30 flex flex-col gap-1">
          {[...typingBeings.entries()].map(([id, name]) => (
            <div key={id} className="flex items-center gap-2 text-xs text-text-secondary">
              <div className="flex gap-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-accent-blue animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-accent-blue animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-accent-blue animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="font-medium">{name}</span>
              <span className="text-text-muted">is responding...</span>
            </div>
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-border p-3 shrink-0">
        {/* Active targets */}
        {targets.length > 0 && (
          <div className="flex items-center gap-1 mb-2 flex-wrap">
            <span className="text-[10px] text-text-muted mr-1">To:</span>
            {targets.map(id => {
              const b = getBeingById(id)
              if (!b) return null
              return (
                <button
                  key={id}
                  onClick={() => removeTarget(id)}
                  className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border transition-colors hover:bg-bg-hover"
                  style={{ borderColor: b.color + '40', color: b.color, backgroundColor: b.color + '10' }}
                >
                  <div className="w-3.5 h-3.5 rounded flex items-center justify-center text-[8px] font-bold" style={{ backgroundColor: b.color + '33' }}>
                    {b.avatar}
                  </div>
                  {b.name}
                  <span className="opacity-60">&times;</span>
                </button>
              )
            })}

            {/* Execution mode selector — only visible with 2+ targets */}
            {targets.length > 1 && (
              <div className="flex items-center gap-0.5 ml-2 bg-bg-card rounded border border-border p-0.5">
                {['auto', 'parallel', 'sequential'].map(mode => (
                  <button
                    key={mode}
                    onClick={() => setExecMode(mode)}
                    className={`px-1.5 py-0.5 rounded text-[9px] font-bold transition-colors ${
                      execMode === mode
                        ? mode === 'parallel' ? 'bg-accent-green/20 text-accent-green'
                          : mode === 'sequential' ? 'bg-accent-amber/20 text-accent-amber'
                          : 'bg-accent-cyan/20 text-accent-cyan'
                        : 'text-text-muted hover:text-text-secondary'
                    }`}
                  >
                    {mode === 'auto' ? 'AUTO' : mode === 'parallel' ? 'PARA' : 'SEQ'}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="relative flex gap-2">
          {mentionFilter !== null && (
            <MentionDropdown
              filter={mentionFilter}
              onSelect={handleMentionSelect}
              beings={beings}
            />
          )}
          <input
            ref={inputRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Message... (@ to mention a being)"
            className="flex-1 bg-bg-card border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue/50 transition-colors"
          />
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.csv,.html,.png,.jpg,.jpeg"
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            title="Upload document"
            className="px-2 py-2 text-text-muted hover:text-accent-blue disabled:opacity-30 transition-colors"
          >
            {uploading ? (
              <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" /></svg>
            )}
          </button>
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="px-4 py-2 bg-accent-blue text-white text-xs font-medium rounded-lg hover:bg-accent-blue/80 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>

        {/* Input hints */}
        <div className="flex items-center gap-3 mt-1.5 text-[9px] text-text-muted">
          <span>@ mention beings</span>
          <span>|</span>
          <span>Enter to send</span>
          {targets.length === 0 && <span className="ml-auto">Broadcasting to all</span>}
        </div>
      </div>
      </div>{/* end chat area */}
    </div>
  )
}
