import { useState, useRef, useEffect } from 'react'
import { CHAT_MESSAGES } from '../store'
import { useBeings } from '../context/BeingsContext'

function MessageBubble({ msg, getBeingById }) {
  const isUser = msg.sender === 'user'
  const being = !isUser ? getBeingById(msg.sender) : null

  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
        style={{
          backgroundColor: isUser ? '#3b82f622' : (being?.color || '#666') + '22',
          color: isUser ? '#3b82f6' : being?.color || '#666'
        }}
      >
        {isUser ? 'U' : being?.avatar || '?'}
      </div>

      <div className={`max-w-[75%] ${isUser ? 'text-right' : ''}`}>
        {/* Sender + targets */}
        <div className={`flex items-center gap-1.5 mb-0.5 ${isUser ? 'justify-end' : ''}`}>
          <span className="text-xs font-medium">{isUser ? 'You' : being?.name || msg.sender}</span>
          {msg.targets.length > 0 && (
            <span className="text-[10px] text-text-muted">
              &rarr;&nbsp;{msg.targets.map(t => {
                const b = getBeingById(t)
                return b ? `@${b.name}` : `@${t}`
              }).join(', ')}
            </span>
          )}
          {msg.mode && (
            <span className={`px-1 py-0.5 text-[9px] font-bold rounded ${
              msg.mode === 'parallel'
                ? 'bg-accent-cyan/15 text-accent-cyan'
                : 'bg-accent-amber/15 text-accent-amber'
            }`}>
              {msg.mode === 'parallel' ? 'PARALLEL' : 'SEQUENTIAL'}
            </span>
          )}
        </div>

        {/* Message content */}
        <div className={`text-sm leading-relaxed px-3 py-2 rounded-lg ${
          isUser
            ? 'bg-accent-blue/15 text-text-primary border border-accent-blue/20'
            : 'bg-bg-card text-text-primary border border-border'
        }`}>
          {msg.content}
        </div>

        <div className="text-[10px] text-text-muted mt-0.5 font-mono">
          {new Date(msg.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  )
}

function MentionDropdown({ filter, onSelect, beings }) {
  const filtered = beings.filter(b =>
    b.name.toLowerCase().includes(filter.toLowerCase()) ||
    b.id.toLowerCase().includes(filter.toLowerCase())
  )

  if (filtered.length === 0) return null

  return (
    <div className="absolute bottom-full left-0 mb-1 w-56 bg-bg-card border border-border-bright rounded-lg shadow-xl overflow-hidden z-50">
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
          <div>
            <div className="text-xs font-medium">{being.name}</div>
            <div className="text-[10px] text-text-muted">{being.role}</div>
          </div>
          <div className={`ml-auto w-2 h-2 rounded-full ${
            being.status === 'online' ? 'bg-accent-green' : being.status === 'busy' ? 'bg-accent-amber' : 'bg-text-muted'
          }`} />
        </button>
      ))}
    </div>
  )
}

export function ChatWindow() {
  const { beings, getBeingById } = useBeings()
  const [messages, setMessages] = useState(CHAT_MESSAGES)
  const [input, setInput] = useState('')
  const [mentionFilter, setMentionFilter] = useState(null)
  const [targets, setTargets] = useState([])
  const [execMode, setExecMode] = useState('auto')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleInputChange = (e) => {
    const val = e.target.value
    setInput(val)

    // Detect @mention
    const atMatch = val.match(/@(\w*)$/)
    if (atMatch) {
      setMentionFilter(atMatch[1])
    } else {
      setMentionFilter(null)
    }
  }

  const handleMentionSelect = (being) => {
    // Replace the @partial with @Name
    const newInput = input.replace(/@\w*$/, `@${being.name} `)
    setInput(newInput)
    setMentionFilter(null)
    if (!targets.includes(being.id)) {
      setTargets([...targets, being.id])
    }
    inputRef.current?.focus()
  }

  const handleSend = () => {
    if (!input.trim()) return

    const newMsg = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      targets,
      content: input.trim(),
      timestamp: new Date().toISOString(),
      mode: targets.length > 1 ? execMode : null,
    }

    setMessages([...messages, newMsg])
    setInput('')
    setTargets([])

    // Simulate responses from targeted beings
    if (targets.length > 0) {
      targets.forEach((targetId, i) => {
        setTimeout(() => {
          const being = getBeingById(targetId)
          if (!being) return
          const responses = [
            `Acknowledged. Processing your request now.`,
            `On it. I'll have results shortly.`,
            `Understood. Let me analyze and get back to you.`,
            `Copy that. Working on it.`,
          ]
          setMessages(prev => [...prev, {
            id: `msg-${Date.now()}-${i}`,
            sender: targetId,
            targets: [],
            content: responses[Math.floor(Math.random() * responses.length)],
            timestamp: new Date().toISOString(),
            mode: null,
          }])
        }, 1000 + i * 800)
      })
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
        </div>
        <div className="flex items-center gap-2">
          {/* Execution mode toggle */}
          <div className="flex items-center gap-1 text-[10px]">
            {['auto', 'parallel', 'sequential'].map(mode => (
              <button
                key={mode}
                onClick={() => setExecMode(mode)}
                className={`px-2 py-0.5 rounded transition-colors ${
                  execMode === mode
                    ? 'bg-accent-cyan/20 text-accent-cyan'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                {mode.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {messages.map(msg => (
          <MessageBubble key={msg.id} msg={msg} getBeingById={getBeingById} />
        ))}
        <div ref={messagesEndRef} />
      </div>

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
                  {b.name}
                  <span className="opacity-60">&times;</span>
                </button>
              )
            })}
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
            placeholder="Message... (use @ to mention beings)"
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
      </div>
    </div>
  )
}
