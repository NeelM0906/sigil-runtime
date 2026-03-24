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

// ── Diff Line ───────────────────────────────────────────────

function DiffLine({ type, content, lineNum }) {
  const styles = {
    add: 'bg-accent-green/10 text-accent-green/90',
    remove: 'bg-accent-red/10 text-accent-red/90',
    context: 'text-text-secondary',
  }
  const prefix = { add: '+', remove: '-', context: ' ' }
  return (
    <div className={`flex font-mono text-[11px] leading-5 ${styles[type]}`}>
      <span className="w-8 text-right pr-2 text-text-muted/50 select-none flex-shrink-0">{lineNum || ''}</span>
      <span className="w-4 text-center select-none flex-shrink-0 opacity-60">{prefix[type]}</span>
      <span className="whitespace-pre-wrap break-all flex-1">{content}</span>
    </div>
  )
}

// ── Diff Block ──────────────────────────────────────────────

function DiffBlock({ toolName, args, result }) {
  const [expanded, setExpanded] = useState(true)

  const isEdit = toolName === 'edit'
  const isWrite = toolName === 'write'
  const isRead = toolName === 'read'
  const isBash = toolName === 'bash'
  const isGrep = toolName === 'grep'
  const isFind = toolName === 'find'
  const isLs = toolName === 'ls'
  const isReadOnly = isRead || isGrep || isFind || isLs

  let parsedArgs = {}
  try {
    parsedArgs = typeof args === 'string' ? JSON.parse(args) : (args || {})
  } catch { parsedArgs = {} }

  const filePath = parsedArgs.path || parsedArgs.file_path || ''

  const toolColors = {
    edit: { label: 'EDIT', color: 'text-accent-amber', border: 'border-accent-amber/30', icon: 'M' },
    write: { label: 'WRITE', color: 'text-accent-green', border: 'border-accent-green/30', icon: '+' },
    read: { label: 'READ', color: 'text-accent-blue', border: 'border-accent-blue/30', icon: 'R' },
    bash: { label: 'BASH', color: 'text-accent-purple', border: 'border-accent-purple/30', icon: '$' },
    grep: { label: 'GREP', color: 'text-accent-cyan', border: 'border-accent-cyan/30', icon: '?' },
    find: { label: 'FIND', color: 'text-accent-cyan', border: 'border-accent-cyan/30', icon: '/' },
    ls: { label: 'LS', color: 'text-accent-cyan', border: 'border-accent-cyan/30', icon: 'D' },
  }
  const tc = toolColors[toolName] || { label: toolName.toUpperCase(), color: 'text-text-secondary', border: 'border-border', icon: '>' }

  // Build diff lines for edit tool
  const diffLines = []
  if (isEdit && parsedArgs.old_string) {
    const oldLines = (parsedArgs.old_string || '').split('\n')
    const newLines = (parsedArgs.new_string || '').split('\n')
    oldLines.forEach((l, i) => diffLines.push({ type: 'remove', content: l, lineNum: i + 1 }))
    newLines.forEach((l, i) => diffLines.push({ type: 'add', content: l, lineNum: i + 1 }))
  }

  return (
    <div className={`my-1.5 rounded border ${tc.border} bg-bg-primary overflow-hidden`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-2 py-1.5 text-[11px] font-mono hover:bg-bg-hover/50 transition-colors"
      >
        <span className={`${expanded ? 'rotate-90' : ''} transition-transform text-text-muted text-[9px]`}>&#9654;</span>
        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${tc.color} bg-current/10`}>
          {tc.label}
        </span>
        {filePath && <span className="text-text-primary truncate">{filePath}</span>}
        {isBash && parsedArgs.command && (
          <span className="text-text-secondary truncate">$ {parsedArgs.command}</span>
        )}
        {isEdit && (
          <span className="ml-auto text-[9px] text-text-muted">
            <span className="text-accent-red">-{(parsedArgs.old_string || '').split('\n').length}</span>
            {' '}
            <span className="text-accent-green">+{(parsedArgs.new_string || '').split('\n').length}</span>
          </span>
        )}
      </button>

      {/* Content */}
      {expanded && (
        <div className="border-t border-border/50">
          {/* Edit: unified diff view */}
          {isEdit && diffLines.length > 0 && (
            <div className="max-h-80 overflow-y-auto">
              {diffLines.map((line, i) => (
                <DiffLine key={i} type={line.type} content={line.content} lineNum={line.lineNum} />
              ))}
            </div>
          )}

          {/* Write: all-green (new file) */}
          {isWrite && parsedArgs.content && (
            <div className="max-h-80 overflow-y-auto">
              {parsedArgs.content.slice(0, 3000).split('\n').map((line, i) => (
                <DiffLine key={i} type="add" content={line} lineNum={i + 1} />
              ))}
            </div>
          )}

          {/* Bash: command + output */}
          {isBash && (
            <div className="max-h-80 overflow-y-auto">
              {parsedArgs.command && (
                <div className="px-3 py-1 bg-accent-purple/5 text-[11px] font-mono text-accent-purple/80 border-b border-border/30">
                  $ {parsedArgs.command}
                </div>
              )}
              {result && (
                <pre className="px-3 py-1 text-[11px] font-mono text-text-secondary whitespace-pre-wrap">
                  {typeof result === 'string' ? result.slice(0, 3000) : JSON.stringify(result, null, 2).slice(0, 3000)}
                </pre>
              )}
            </div>
          )}

          {/* Read-only tools: show result */}
          {isReadOnly && result && (
            <pre className="px-3 py-1 text-[11px] font-mono text-text-secondary whitespace-pre-wrap max-h-80 overflow-y-auto">
              {typeof result === 'string' ? result.slice(0, 3000) : JSON.stringify(result, null, 2).slice(0, 3000)}
            </pre>
          )}

          {/* Fallback: raw args */}
          {!isEdit && !isWrite && !isBash && !isReadOnly && (
            <pre className="px-3 py-1 text-[11px] font-mono text-text-muted whitespace-pre-wrap max-h-60 overflow-y-auto">
              {JSON.stringify(parsedArgs, null, 2).slice(0, 1500)}
            </pre>
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

// ── File Tree ───────────────────────────────────────────────

function FileTreeNode({ node, depth, touchedFiles, onFileClick }) {
  const [expanded, setExpanded] = useState(depth < 1)
  const isTouched = touchedFiles.has(node.path)

  if (node.type === 'dir') {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-1 px-1 py-0.5 text-[11px] hover:bg-bg-hover/50 transition-colors"
          style={{ paddingLeft: `${depth * 12 + 4}px` }}
        >
          <span className={`text-[8px] text-text-muted transition-transform ${expanded ? 'rotate-90' : ''}`}>&#9654;</span>
          <span className="text-accent-amber/70 text-[10px]">&#128193;</span>
          <span className="text-text-secondary truncate">{node.name}</span>
        </button>
        {expanded && node.children && node.children.map((child, i) => (
          <FileTreeNode key={i} node={child} depth={depth + 1} touchedFiles={touchedFiles} onFileClick={onFileClick} />
        ))}
      </div>
    )
  }

  // File extension icon
  const ext = node.name.split('.').pop()?.toLowerCase()
  const iconColors = {
    py: 'text-accent-blue', js: 'text-accent-amber', jsx: 'text-accent-amber',
    ts: 'text-accent-blue', tsx: 'text-accent-blue', json: 'text-accent-green',
    md: 'text-text-muted', css: 'text-accent-pink', html: 'text-accent-red',
    sql: 'text-accent-cyan', yaml: 'text-accent-purple', yml: 'text-accent-purple',
    toml: 'text-accent-green', txt: 'text-text-muted', sh: 'text-accent-purple',
  }
  const iconColor = iconColors[ext] || 'text-text-muted'

  return (
    <button
      onClick={() => onFileClick(node.path)}
      className={`w-full flex items-center gap-1 px-1 py-0.5 text-[11px] hover:bg-bg-hover/50 transition-colors ${
        isTouched ? 'bg-accent-amber/5' : ''
      }`}
      style={{ paddingLeft: `${depth * 12 + 4}px` }}
      title={node.path}
    >
      <span className={`text-[10px] ${iconColor}`}>&#128196;</span>
      <span className={`truncate ${isTouched ? 'text-accent-amber font-medium' : 'text-text-primary'}`}>
        {node.name}
      </span>
      {isTouched && <span className="ml-auto text-[8px] text-accent-amber">M</span>}
    </button>
  )
}

function CodeFileTree({ tree, touchedFiles, onFileClick, loading }) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex flex-col border-t border-border">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-between px-3 py-1.5 hover:bg-bg-hover/30 transition-colors"
      >
        <span className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Files</span>
        <span className={`text-[8px] text-text-muted transition-transform ${collapsed ? '' : 'rotate-90'}`}>&#9654;</span>
      </button>
      {!collapsed && (
        <div className="overflow-y-auto max-h-[40vh]">
          {loading && (
            <div className="px-3 py-3 text-[10px] text-text-muted text-center">Loading...</div>
          )}
          {!loading && tree.length === 0 && (
            <div className="px-3 py-3 text-[10px] text-text-muted text-center">No files</div>
          )}
          {tree.map((node, i) => (
            <FileTreeNode key={i} node={node} depth={0} touchedFiles={touchedFiles} onFileClick={onFileClick} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── File Viewer (replaces chat when viewing a file) ─────────

function FileViewer({ filePath, content, size, truncated, onClose }) {
  const ext = filePath.split('.').pop()?.toLowerCase()
  const lineCount = content ? content.split('\n').length : 0

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-bg-secondary">
        <button
          onClick={onClose}
          className="text-text-muted hover:text-text-primary text-xs"
          title="Back to chat"
        >
          &#8592;
        </button>
        <span className="text-xs font-mono text-text-primary truncate">{filePath}</span>
        <span className="ml-auto text-[10px] text-text-muted">
          {lineCount} lines | {size > 1024 ? `${(size / 1024).toFixed(1)}KB` : `${size}B`}
          {truncated && ' (truncated)'}
        </span>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-auto bg-bg-primary">
        <pre className="text-[11px] font-mono leading-5">
          {content.split('\n').map((line, i) => (
            <div key={i} className="flex hover:bg-bg-hover/30">
              <span className="w-10 text-right pr-3 text-text-muted/40 select-none flex-shrink-0">{i + 1}</span>
              <span className="text-text-primary whitespace-pre-wrap break-all">{line}</span>
            </div>
          ))}
        </pre>
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

// ── Changes & Activity Panel (right side) ───────────────────

function CodeActivityPanel({ tools, usage, streaming }) {
  const [activeTab, setActiveTab] = useState('changes')

  // Group tools by file for Changes view
  const fileChanges = []
  const seenFiles = new Set()
  for (const t of tools) {
    let parsedArgs = {}
    try { parsedArgs = typeof t.args === 'string' ? JSON.parse(t.args) : (t.args || {}) } catch { /* */ }
    const filePath = parsedArgs.path || parsedArgs.file_path || ''
    if (filePath && (t.name === 'edit' || t.name === 'write')) {
      if (!seenFiles.has(filePath)) {
        seenFiles.add(filePath)
        fileChanges.push({ path: filePath, edits: [] })
      }
      fileChanges.find(f => f.path === filePath)?.edits.push(t)
    }
  }

  // Separate write-tools (bash, non-file) for Activity tab
  const activities = tools.filter(t => {
    let parsedArgs = {}
    try { parsedArgs = typeof t.args === 'string' ? JSON.parse(t.args) : (t.args || {}) } catch { /* */ }
    return t.name === 'bash' || t.name === 'read' || t.name === 'grep' || t.name === 'find' || t.name === 'ls'
  })

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex items-center gap-0.5 px-2 py-1.5 border-b border-border">
        {['changes', 'activity', 'usage'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-2 py-0.5 text-[10px] font-medium rounded transition-colors ${
              activeTab === tab
                ? 'bg-accent-blue/20 text-accent-blue'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {tab === 'changes' && `Changes${fileChanges.length ? ` (${fileChanges.length})` : ''}`}
            {tab === 'activity' && `Activity${tools.length ? ` (${tools.length})` : ''}`}
            {tab === 'usage' && 'Usage'}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Changes tab: file-grouped diffs */}
        {activeTab === 'changes' && (
          <div className="px-2 py-1">
            {fileChanges.length === 0 && !streaming && (
              <div className="text-text-muted text-[11px] text-center py-8">
                No file changes yet
              </div>
            )}
            {streaming && fileChanges.length === 0 && (
              <div className="flex items-center gap-2 text-text-muted text-[11px] py-4 justify-center">
                <span className="w-1.5 h-1.5 rounded-full bg-accent-blue animate-pulse" />
                Waiting for file changes...
              </div>
            )}
            {fileChanges.map((fc, i) => (
              <div key={i} className="mb-2">
                {/* File header */}
                <div className="flex items-center gap-2 px-1 py-1 text-[11px]">
                  <span className="text-accent-amber">M</span>
                  <span className="font-mono text-text-primary truncate">{fc.path.split('/').pop()}</span>
                  <span className="text-text-muted font-mono truncate text-[9px] ml-auto">{fc.path}</span>
                </div>
                {/* Diffs for this file */}
                {fc.edits.map((edit, ei) => (
                  <DiffBlock key={ei} toolName={edit.name} args={edit.args} result={edit.result} />
                ))}
              </div>
            ))}
          </div>
        )}

        {/* Activity tab: all tool calls */}
        {activeTab === 'activity' && (
          <div className="px-2 py-1">
            {tools.length === 0 && (
              <div className="text-text-muted text-[11px] text-center py-8">
                Tool calls will appear here
              </div>
            )}
            {[...tools].reverse().map((t, i) => {
              let parsedArgs = {}
              try { parsedArgs = typeof t.args === 'string' ? JSON.parse(t.args) : (t.args || {}) } catch { /* */ }
              const filePath = parsedArgs.path || parsedArgs.file_path || ''
              const cmd = parsedArgs.command || ''

              return (
                <div key={i} className="flex items-center gap-2 px-1 py-1 border-b border-border/30 text-[11px]">
                  <ToolBadge name={t.name} status={t.status} />
                  <span className="text-text-secondary font-mono truncate text-[10px]">
                    {filePath || cmd || ''}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {/* Usage tab */}
        {activeTab === 'usage' && (
          <div className="px-3 py-3">
            {!usage ? (
              <div className="text-text-muted text-[11px] text-center py-8">
                No usage data yet
              </div>
            ) : (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div className="rounded border border-border bg-bg-primary p-2 text-center">
                    <div className="text-text-muted text-[9px] uppercase mb-1">Input</div>
                    <div className="text-text-primary font-mono font-medium">{usage.input_tokens?.toLocaleString() || 0}</div>
                  </div>
                  <div className="rounded border border-border bg-bg-primary p-2 text-center">
                    <div className="text-text-muted text-[9px] uppercase mb-1">Output</div>
                    <div className="text-text-primary font-mono font-medium">{usage.output_tokens?.toLocaleString() || 0}</div>
                  </div>
                </div>
                {usage.cost > 0 && (
                  <div className="rounded border border-border bg-bg-primary p-2 text-center text-[11px]">
                    <div className="text-text-muted text-[9px] uppercase mb-1">Cost</div>
                    <div className="text-accent-green font-mono font-medium">${usage.cost.toFixed(4)}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Approval Dialog ─────────────────────────────────────────

function ApprovalDialog({ request, onRespond }) {
  if (!request) return null

  const { request_id, method, title, message, options } = request

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-bg-card border border-accent-amber/40 rounded-lg p-4 max-w-md w-full mx-4 shadow-xl">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-full bg-accent-amber/20 flex items-center justify-center text-accent-amber text-sm">
            ?
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">{title || 'Permission Required'}</h3>
            {message && <p className="text-xs text-text-secondary mt-0.5">{message}</p>}
          </div>
        </div>

        {/* Select method: show options as buttons */}
        {method === 'select' && options && options.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {options.map((opt, i) => {
              const isAllow = /allow|approve|yes/i.test(opt)
              const isDeny = /deny|reject|block|no/i.test(opt)
              const color = isAllow ? 'bg-accent-green/20 text-accent-green hover:bg-accent-green/30 border-accent-green/30'
                : isDeny ? 'bg-accent-red/20 text-accent-red hover:bg-accent-red/30 border-accent-red/30'
                : 'bg-bg-hover text-text-primary hover:bg-bg-hover/80 border-border'
              return (
                <button
                  key={i}
                  onClick={() => onRespond(request_id, { value: opt })}
                  className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors ${color}`}
                >
                  {opt}
                </button>
              )
            })}
          </div>
        )}

        {/* Confirm method: yes/no */}
        {method === 'confirm' && (
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => onRespond(request_id, { confirmed: true })}
              className="flex-1 px-3 py-1.5 rounded text-xs font-medium bg-accent-green/20 text-accent-green hover:bg-accent-green/30 border border-accent-green/30 transition-colors"
            >
              Allow
            </button>
            <button
              onClick={() => onRespond(request_id, { confirmed: false })}
              className="flex-1 px-3 py-1.5 rounded text-xs font-medium bg-accent-red/20 text-accent-red hover:bg-accent-red/30 border border-accent-red/30 transition-colors"
            >
              Deny
            </button>
          </div>
        )}

        {/* Fallback: cancel */}
        <button
          onClick={() => onRespond(request_id, { cancelled: true })}
          className="mt-2 w-full px-3 py-1 rounded text-[10px] text-text-muted hover:text-text-secondary transition-colors"
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}

// ── Main CodeWorkspace ──────────────────────────────────────

export function CodeWorkspace({ initialPrompt = null, onConsumePrompt = null }) {
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
  const [pendingApproval, setPendingApproval] = useState(null)
  const [fileTree, setFileTree] = useState([])
  const [fileTreeLoading, setFileTreeLoading] = useState(false)
  const [touchedFiles, setTouchedFiles] = useState(new Set())
  const [viewingFile, setViewingFile] = useState(null) // {path, content, size, truncated}

  // Handle cross-tab initial prompt
  useEffect(() => {
    if (!initialPrompt) return
    const run = async () => {
      try {
        const { session } = await codeApi.createSession('Code session')
        setSessions(prev => [session, ...prev])
        setActiveSessionId(session.id)
        setMessages([{ role: 'user', content: initialPrompt }])
        setAllTools([])
        setUsage(null)
        await codeApi.prompt(session.id, initialPrompt)
      } catch (err) {
        console.error('Failed to run initial prompt:', err)
      }
      onConsumePrompt?.()
    }
    run()
  }, [initialPrompt, onConsumePrompt])

  // Load file tree on mount
  useEffect(() => {
    setFileTreeLoading(true)
    codeApi.files(3)
      .then(({ tree }) => setFileTree(tree || []))
      .catch(() => {})
      .finally(() => setFileTreeLoading(false))
  }, [])

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
      // Track touched files
      if (name === 'edit' || name === 'write' || name === 'read') {
        try {
          const parsed = typeof args === 'string' ? JSON.parse(args) : (args || {})
          const fp = parsed.path || parsed.file_path || ''
          if (fp) setTouchedFiles(prev => new Set([...prev, fp]))
        } catch { /* ignore */ }
      }
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
    code_approval_required: (data) => {
      const d = data.data || data
      setPendingApproval({
        request_id: d.request_id,
        method: d.method,
        title: d.title,
        message: d.message,
        options: d.options || [],
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

  const handleApprovalRespond = useCallback(async (requestId, response) => {
    if (!activeSessionId) return
    setPendingApproval(null)
    try {
      await codeApi.respondUi(activeSessionId, requestId, response)
    } catch (err) {
      console.error('Approval response failed:', err)
    }
  }, [activeSessionId])

  const handleFileClick = useCallback(async (filePath) => {
    try {
      const result = await codeApi.readFile(filePath)
      setViewingFile(result)
    } catch (err) {
      console.error('Failed to read file:', err)
    }
  }, [])

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
    <div className="flex h-[calc(100vh-4rem)] rounded-lg border border-border bg-bg-card overflow-hidden relative">
      {/* Approval Dialog */}
      <ApprovalDialog request={pendingApproval} onRespond={handleApprovalRespond} />

      {/* Session Sidebar + File Tree */}
      {sidebarOpen && (
        <div className="w-56 flex-shrink-0 border-r border-border bg-bg-secondary flex flex-col">
          <CodeSessionSidebar
            sessions={sessions}
            activeId={activeSessionId}
            onSelect={handleSelectSession}
            onCreate={handleCreateSession}
            onDelete={handleDeleteSession}
          />
          <CodeFileTree
            tree={fileTree}
            touchedFiles={touchedFiles}
            onFileClick={handleFileClick}
            loading={fileTreeLoading}
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
          {viewingFile ? (
            <>
              <button
                onClick={() => setViewingFile(null)}
                className="text-[10px] text-accent-blue hover:underline"
              >
                &#8592; Chat
              </button>
              <span className="text-xs font-mono text-text-primary truncate">{viewingFile.path}</span>
            </>
          ) : activeSessionId ? (
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
        ) : viewingFile ? (
          <div className="flex-1 min-h-0">
            <FileViewer
              filePath={viewingFile.path}
              content={viewingFile.content}
              size={viewingFile.size}
              truncated={viewingFile.truncated}
              onClose={() => setViewingFile(null)}
            />
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
              <CodeActivityPanel tools={allTools} usage={usage} streaming={streaming} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
