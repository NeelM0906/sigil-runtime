import { useState, useRef, useEffect, useCallback } from 'react'
import Markdown from 'react-markdown'
import { codeApi } from '../api'
import { useCodeSSE } from '../hooks/useCodeSSE'

// ── Tool Badge ──────────────────────────────────────────────

function ToolBadge({ name, status }) {
  const colors = {
    running: 'border-accent-amber/40 bg-accent-amber/10 text-accent-amber',
    done: 'border-accent-green/40 bg-accent-green/10 text-accent-green',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border ${colors[status] || colors.running}`}>
      {status === 'running' && (
        <span className="w-1.5 h-1.5 rounded-full bg-accent-amber animate-pulse" />
      )}
      {status === 'done' && (
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      )}
      {name}
    </span>
  )
}

// ── Diff Block ──────────────────────────────────────────────

function DiffBlock({ toolName, args, result }) {
  const [expanded, setExpanded] = useState(false)

  // Parse edit tool args to show diff-like view
  const isEdit = toolName === 'edit'
  const isWrite = toolName === 'write'
  const isRead = toolName === 'read'
  const isBash = toolName === 'bash'

  let parsedArgs = {}
  try {
    parsedArgs = typeof args === 'string' ? JSON.parse(args) : (args || {})
  } catch { parsedArgs = {} }

  const filePath = parsedArgs.path || parsedArgs.file_path || ''

  return (
    <div className="my-1 rounded border border-border bg-bg-primary">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-2 py-1 text-[11px] font-mono hover:bg-bg-hover transition-colors"
      >
        <span className={`${expanded ? 'rotate-90' : ''} transition-transform text-text-muted`}>&#9654;</span>
        {isEdit && <span className="text-accent-amber">EDIT</span>}
        {isWrite && <span className="text-accent-green">WRITE</span>}
        {isRead && <span className="text-accent-blue">READ</span>}
        {isBash && <span className="text-accent-purple">BASH</span>}
        {!isEdit && !isWrite && !isRead && !isBash && <span className="text-text-secondary">{toolName}</span>}
        {filePath && <span className="text-text-secondary truncate">{filePath}</span>}
        {isBash && parsedArgs.command && <span className="text-text-secondary truncate">$ {parsedArgs.command}</span>}
      </button>
      {expanded && (
        <div className="border-t border-border px-2 py-1 text-[11px] font-mono overflow-x-auto max-h-64 overflow-y-auto">
          {isEdit && parsedArgs.old_string && (
            <div>
              <div className="text-accent-red/80 whitespace-pre-wrap">- {parsedArgs.old_string}</div>
              <div className="text-accent-green/80 whitespace-pre-wrap">+ {parsedArgs.new_string}</div>
            </div>
          )}
          {isWrite && parsedArgs.content && (
            <pre className="text-accent-green/80 whitespace-pre-wrap">{parsedArgs.content.slice(0, 2000)}</pre>
          )}
          {result && (
            <pre className="text-text-secondary whitespace-pre-wrap mt-1">{
              typeof result === 'string' ? result.slice(0, 2000) : JSON.stringify(result, null, 2).slice(0, 2000)
            }</pre>
          )}
          {!isEdit && !isWrite && !result && (
            <pre className="text-text-muted whitespace-pre-wrap">{JSON.stringify(parsedArgs, null, 2).slice(0, 1000)}</pre>
          )}
        </div>
      )}
    </div>
  )
}

// ── Session Sidebar ─────────────────────────────────────────

function CodeSessionSidebar({ sessions, activeId, onSelect, onCreate, onDelete }) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <span className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Sessions</span>
        <button
          onClick={onCreate}
          className="text-[10px] px-2 py-0.5 rounded bg-accent-blue/20 text-accent-blue hover:bg-accent-blue/30 transition-colors"
        >
          + New
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 && (
          <div className="px-3 py-8 text-center text-text-muted text-[11px]">
            No sessions yet.<br />Click + New to start coding.
          </div>
        )}
        {sessions.map(s => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`w-full text-left px-3 py-2 text-xs border-b border-border/50 transition-colors group ${
              activeId === s.id
                ? 'bg-accent-blue/10 border-l-2 border-l-accent-blue'
                : 'hover:bg-bg-hover border-l-2 border-l-transparent'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className={`font-medium truncate ${activeId === s.id ? 'text-accent-blue' : 'text-text-primary'}`}>
                {s.title}
              </span>
              {s.is_streaming && (
                <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse flex-shrink-0" />
              )}
            </div>
            <div className="text-[10px] text-text-muted mt-0.5">
              {s.message_count || 0} messages
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(s.id) }}
              className="hidden group-hover:block absolute right-2 top-2 text-text-muted hover:text-accent-red text-[10px]"
            >
              x
            </button>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Chat Panel ──────────────────────────────────────────────

function CodeChatPanel({ messages, streaming, streamingText, tools, onSend, onAbort }) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  const handleSubmit = (e) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || streaming) return
    setInput('')
    onSend(text)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
        {messages.length === 0 && !streaming && (
          <div className="flex items-center justify-center h-full text-text-muted text-sm">
            Send a message to start coding
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`${msg.role === 'user' ? 'flex justify-end' : ''}`}>
            {msg.role === 'user' ? (
              <div className="max-w-[85%] px-3 py-2 rounded-lg bg-accent-blue/15 border border-accent-blue/20 text-sm">
                {msg.content}
              </div>
            ) : (
              <div className="max-w-full">
                {/* Tool calls */}
                {msg.tools && msg.tools.map((tool, ti) => (
                  <DiffBlock key={ti} toolName={tool.name} args={tool.args} result={tool.result} />
                ))}
                {/* Text response */}
                {msg.content && (
                  <div className="prose prose-invert prose-sm max-w-none text-sm">
                    <Markdown>{msg.content}</Markdown>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Streaming response */}
        {streaming && (
          <div className="max-w-full">
            {/* Active tool badges */}
            {tools.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-1">
                {tools.map((t, i) => (
                  <ToolBadge key={i} name={t.name} status={t.status} />
                ))}
              </div>
            )}
            {/* Streaming text */}
            {streamingText && (
              <div className="prose prose-invert prose-sm max-w-none text-sm">
                <Markdown>{streamingText}</Markdown>
                <span className="inline-block w-2 h-4 bg-accent-blue animate-pulse ml-0.5" />
              </div>
            )}
            {!streamingText && tools.length === 0 && (
              <div className="flex items-center gap-2 text-text-muted text-sm">
                <span className="w-2 h-2 rounded-full bg-accent-blue animate-pulse" />
                Thinking...
              </div>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-border p-2">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={streaming ? 'Agent is working...' : 'Ask the coding agent...'}
            disabled={streaming}
            className="flex-1 bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue/50 disabled:opacity-50"
            autoFocus
          />
          {streaming ? (
            <button
              type="button"
              onClick={onAbort}
              className="px-4 py-2 rounded bg-accent-red/20 text-accent-red text-xs font-medium hover:bg-accent-red/30 transition-colors"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="px-4 py-2 rounded bg-accent-blue text-white text-xs font-medium hover:bg-accent-blue/80 transition-colors disabled:opacity-30"
            >
              Send
            </button>
          )}
        </form>
      </div>
    </div>
  )
}

// ── Activity Panel (right side) ─────────────────────────────

function CodeActivityPanel({ tools, usage }) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-border">
        <span className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">Activity</span>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {tools.length === 0 && (
          <div className="text-text-muted text-[11px] text-center py-8">
            Tool calls will appear here
          </div>
        )}
        {tools.map((t, i) => (
          <div key={i} className="mb-2 rounded border border-border bg-bg-primary p-2">
            <div className="flex items-center gap-2">
              <ToolBadge name={t.name} status={t.status} />
              {t.file && <span className="text-[10px] text-text-muted font-mono truncate">{t.file}</span>}
            </div>
            {t.result_preview && (
              <pre className="text-[10px] text-text-secondary font-mono mt-1 max-h-20 overflow-hidden">
                {t.result_preview.slice(0, 500)}
              </pre>
            )}
          </div>
        ))}

        {/* Usage stats */}
        {usage && (
          <div className="mt-4 pt-3 border-t border-border">
            <div className="text-[10px] text-text-muted uppercase tracking-wider mb-2">Usage</div>
            <div className="grid grid-cols-2 gap-1 text-[11px]">
              <div className="text-text-secondary">Input</div>
              <div className="text-text-primary font-mono">{usage.input_tokens?.toLocaleString() || 0}</div>
              <div className="text-text-secondary">Output</div>
              <div className="text-text-primary font-mono">{usage.output_tokens?.toLocaleString() || 0}</div>
              {usage.cost > 0 && <>
                <div className="text-text-secondary">Cost</div>
                <div className="text-text-primary font-mono">${usage.cost.toFixed(4)}</div>
              </>}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main CodeWorkspace ──────────────────────────────────────

export function CodeWorkspace() {
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [activeTools, setActiveTools] = useState([])
  const [allTools, setAllTools] = useState([])
  const [usage, setUsage] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [healthy, setHealthy] = useState(null)

  // Check health on mount
  useEffect(() => {
    codeApi.health()
      .then(h => setHealthy(h))
      .catch(() => setHealthy(false))
  }, [])

  // Load sessions on mount
  useEffect(() => {
    codeApi.sessions()
      .then(({ sessions: s }) => setSessions(s || []))
      .catch(() => {})
  }, [])

  // SSE event handlers
  useCodeSSE(activeSessionId, {
    code_agent_start: () => {
      setStreaming(true)
      setStreamingText('')
      setActiveTools([])
    },
    code_agent_end: () => {
      setStreaming(false)
      // Finalize streaming text into messages
      setStreamingText(prev => {
        if (prev) {
          setMessages(msgs => [...msgs, {
            role: 'assistant',
            content: prev,
            tools: [...allTools],
          }])
        }
        return ''
      })
      setActiveTools([])
      // Refresh sessions list for updated message counts
      codeApi.sessions().then(({ sessions: s }) => setSessions(s || [])).catch(() => {})
    },
    code_text_delta: (data) => {
      setStreamingText(prev => prev + (data.data?.delta || data.delta || ''))
    },
    code_text_end: (data) => {
      const content = data.data?.content || data.content || ''
      if (content) {
        setStreamingText(content)
      }
    },
    code_tool_call_start: (data) => {
      const name = data.data?.tool_name || data.tool_name || 'tool'
      setActiveTools(prev => [...prev, { name, status: 'running' }])
    },
    code_tool_call_end: (data) => {
      const name = data.data?.tool_name || data.tool_name || 'tool'
      const args = data.data?.arguments || data.arguments || ''
      setActiveTools(prev =>
        prev.map(t => t.name === name && t.status === 'running' ? { ...t, status: 'done', args } : t)
      )
      setAllTools(prev => [...prev, { name, args, status: 'done' }])
    },
    code_tool_exec_start: (data) => {
      const name = data.data?.tool_name || data.tool_name || 'tool'
      setActiveTools(prev =>
        prev.map(t => t.name === name ? { ...t, status: 'running' } : t)
      )
    },
    code_tool_exec_end: (data) => {
      const name = data.data?.tool_name || data.tool_name || 'tool'
      const result = data.data?.result_preview || data.result_preview || ''
      setActiveTools(prev =>
        prev.map(t => t.name === name ? { ...t, status: 'done', result_preview: result } : t)
      )
      setAllTools(prev =>
        prev.map((t, i) => i === prev.length - 1 && t.name === name ? { ...t, result: result } : t)
      )
    },
    code_message_end: (data) => {
      const u = data.data?.usage || data.usage
      if (u) setUsage(prev => {
        if (!prev) return u
        return {
          input_tokens: (prev.input_tokens || 0) + (u.input_tokens || 0),
          output_tokens: (prev.output_tokens || 0) + (u.output_tokens || 0),
          cost: (prev.cost || 0) + (u.cost || 0),
        }
      })
    },
  })

  const handleCreateSession = useCallback(async () => {
    try {
      const { session } = await codeApi.createSession('Code session')
      setSessions(prev => [session, ...prev])
      setActiveSessionId(session.id)
      setMessages([])
      setStreamingText('')
      setActiveTools([])
      setAllTools([])
      setUsage(null)
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }, [])

  const handleDeleteSession = useCallback(async (id) => {
    try {
      await codeApi.deleteSession(id)
      setSessions(prev => prev.filter(s => s.id !== id))
      if (activeSessionId === id) {
        setActiveSessionId(null)
        setMessages([])
      }
    } catch (err) {
      console.error('Failed to delete session:', err)
    }
  }, [activeSessionId])

  const handleSelectSession = useCallback((id) => {
    setActiveSessionId(id)
    setMessages([])
    setStreamingText('')
    setActiveTools([])
    setAllTools([])
    setUsage(null)
    // Load history for this session
    codeApi.messages(id)
      .then(data => {
        const msgs = data.messages || []
        setMessages(msgs.map(m => ({
          role: m.role || 'assistant',
          content: typeof m.content === 'string' ? m.content :
            (m.content || []).filter(b => b.type === 'text').map(b => b.text).join('\n'),
        })))
      })
      .catch(() => {})
  }, [])

  const handleSend = useCallback(async (text) => {
    if (!activeSessionId) return
    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setAllTools([])
    try {
      await codeApi.prompt(activeSessionId, text)
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    }
  }, [activeSessionId])

  const handleAbort = useCallback(async () => {
    if (!activeSessionId) return
    try {
      await codeApi.abort(activeSessionId)
    } catch (err) {
      console.error('Abort failed:', err)
    }
  }, [activeSessionId])

  // Not configured state
  if (healthy === false) {
    return (
      <div className="rounded-lg border border-border bg-bg-card p-8 text-center">
        <div className="text-2xl mb-3">&#128187;</div>
        <h3 className="text-sm font-semibold text-text-primary mb-1">Code Agent Not Available</h3>
        <p className="text-xs text-text-secondary">
          The Pi coding agent is not configured. Set <code className="text-accent-blue">BOMBA_PI_ENABLED=true</code> and ensure <code className="text-accent-blue">pi</code> CLI is installed.
        </p>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] rounded-lg border border-border bg-bg-card overflow-hidden">
      {/* Session Sidebar */}
      {sidebarOpen && (
        <div className="w-52 flex-shrink-0 border-r border-border bg-bg-secondary">
          <CodeSessionSidebar
            sessions={sessions}
            activeId={activeSessionId}
            onSelect={handleSelectSession}
            onCreate={handleCreateSession}
            onDelete={handleDeleteSession}
          />
        </div>
      )}

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-bg-secondary">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-text-muted hover:text-text-primary text-xs"
            title="Toggle sidebar"
          >
            {sidebarOpen ? '\u2630' : '\u2630'}
          </button>
          <div className="w-px h-4 bg-border" />
          {activeSessionId ? (
            <>
              <span className="text-xs font-medium text-text-primary">
                {sessions.find(s => s.id === activeSessionId)?.title || 'Session'}
              </span>
              {streaming && (
                <span className="flex items-center gap-1 text-[10px] text-accent-green">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
                  Running
                </span>
              )}
            </>
          ) : (
            <span className="text-xs text-text-muted">Select or create a session</span>
          )}
          <div className="ml-auto flex items-center gap-2">
            {healthy && (
              <span className="text-[10px] text-text-muted font-mono">
                {healthy.model?.split('/').pop() || 'code agent'}
              </span>
            )}
            <div className={`w-2 h-2 rounded-full ${healthy ? 'bg-accent-green' : 'bg-text-muted'}`}
              title={healthy ? 'Connected' : 'Disconnected'} />
          </div>
        </div>

        {/* Content */}
        {!activeSessionId ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-4 opacity-30">&#9000;</div>
              <h3 className="text-sm font-semibold text-text-secondary mb-2">Code Workspace</h3>
              <p className="text-xs text-text-muted mb-4">AI-powered coding agent with file editing, shell access, and more.</p>
              <button
                onClick={handleCreateSession}
                className="px-4 py-2 rounded bg-accent-blue text-white text-xs font-medium hover:bg-accent-blue/80 transition-colors"
              >
                Start New Session
              </button>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex min-h-0">
            {/* Chat panel */}
            <div className="flex-1 min-w-0">
              <CodeChatPanel
                messages={messages}
                streaming={streaming}
                streamingText={streamingText}
                tools={activeTools}
                onSend={handleSend}
                onAbort={handleAbort}
              />
            </div>
            {/* Activity panel */}
            <div className="w-64 flex-shrink-0 border-l border-border bg-bg-secondary">
              <CodeActivityPanel tools={allTools} usage={usage} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
