import { useState, useRef, useEffect, useCallback } from 'react'
import Markdown from 'react-markdown'
import { useBeings } from '../context/BeingsContext'
import { chatApi, tasksApi } from '../api'
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

// ── Highlighted @mentions in content ─────────────────────────

function HighlightedContent({ content, getBeingById }) {
  // Custom renderer that colors @mentions inside markdown text nodes
  const renderMention = (text) => {
    const parts = text.split(/(@\w+)/g)
    return parts.map((part, i) => {
      if (part.startsWith('@')) {
        const name = part.slice(1).toLowerCase()
        const being = getBeingById(name) || null
        if (being) {
          return <span key={i} className="font-medium" style={{ color: being.color }}>{part}</span>
        }
        return <span key={i} className="font-medium text-accent-blue">{part}</span>
      }
      return <span key={i}>{part}</span>
    })
  }

  return (
    <Markdown
      components={{
        // Headings
        h1: ({ children }) => <h3 className="text-base font-bold mt-3 mb-1.5 text-text-primary">{children}</h3>,
        h2: ({ children }) => <h4 className="text-sm font-bold mt-2.5 mb-1 text-text-primary">{children}</h4>,
        h3: ({ children }) => <h5 className="text-sm font-semibold mt-2 mb-1 text-text-primary">{children}</h5>,
        // Paragraphs
        p: ({ children }) => <p className="mb-1.5 last:mb-0">{children}</p>,
        // Bold / italic
        strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
        em: ({ children }) => <em className="italic">{children}</em>,
        // Lists
        ul: ({ children }) => <ul className="list-disc list-inside mb-1.5 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside mb-1.5 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="text-sm">{children}</li>,
        // Tables
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="text-xs w-full border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="border-b border-border">{children}</thead>,
        th: ({ children }) => <th className="text-left px-2 py-1 font-semibold text-text-secondary">{children}</th>,
        td: ({ children }) => <td className="px-2 py-1 border-t border-border/50">{children}</td>,
        // Code
        code: ({ children, className }) => {
          const isBlock = className?.includes('language-')
          if (isBlock) {
            return <code className="block bg-black/20 rounded p-2 my-1.5 text-xs font-mono overflow-x-auto">{children}</code>
          }
          return <code className="bg-black/20 rounded px-1 py-0.5 text-xs font-mono">{children}</code>
        },
        pre: ({ children }) => <pre className="my-1.5">{children}</pre>,
        // Horizontal rule
        hr: () => <hr className="border-border/50 my-2" />,
        // Links
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-accent-blue hover:underline">{children}</a>
        ),
        // Blockquote
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-accent-blue/40 pl-2 my-1.5 text-text-secondary italic">{children}</blockquote>
        ),
      }}
    >
      {content}
    </Markdown>
  )
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
  const [typingBeings, setTypingBeings] = useState(new Map()) // Map<being_id, being_name>
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Load messages from API
  const fetchMessages = useCallback(async () => {
    try {
      const apiFilters = {}
      if (filters.search) apiFilters.search = filters.search
      if (filters.sender) apiFilters.sender = filters.sender
      if (filters.target) apiFilters.target = filters.target
      const { messages: fetched } = await chatApi.list(apiFilters)
      setMessages(fetched)
    } catch (err) {
      console.error('Failed to load messages:', err)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { fetchMessages() }, [fetchMessages])

  // SSE: incoming LLM responses and system messages arrive here
  useSSE({
    chat_message(data) {
      // Avoid duplicating the user message we already added optimistically
      if (data.sender === 'user') return
      setTypingBeings(prev => {
        const next = new Map(prev)
        next.delete(data.sender)
        return next
      })
      setMessages(prev => {
        // De-duplicate by id
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
        }
        return next
      })
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
    setInput('')
    setTargets([])

    try {
      // POST returns the saved user message; LLM responses arrive via SSE
      const { message: saved } = await chatApi.send({
        sender: 'user',
        targets: tempMsg.targets,
        content,
        mode,
      })

      // Replace temp message with the persisted one
      setMessages(prev => prev.map(m => m.id === tempMsg.id ? saved : m))
    } catch (err) {
      console.error('Failed to send message:', err)
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
    <div className="bg-bg-secondary border border-border rounded-lg flex flex-col h-[calc(100vh-80px)]">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-pink" />
          <h2 className="text-xs font-semibold uppercase tracking-wider">Communications</h2>
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
    </div>
  )
}
