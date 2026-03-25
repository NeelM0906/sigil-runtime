import { createContext, useContext, useEffect, useRef, useCallback, useState } from 'react'

const SSEContext = createContext(null)

export function SSEProvider({ children }) {
  const listenersRef = useRef({})
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let sseUrl = '/api/mc/events'
    try {
      const stored = localStorage.getItem('mc_auth')
      if (stored) {
        const { token } = JSON.parse(stored)
        if (token) sseUrl = `/api/mc/events?token=${encodeURIComponent(token)}`
      }
    } catch { /* ignore */ }

    const source = new EventSource(sseUrl)

    const eventTypes = [
      'chat_message', 'being_status', 'task_update', 'task_steps_update',
      'artifact_created', 'subagent_event', 'being_typing', 'being_progress',
      'chat_session', 'deliverable_created', 'orchestration_spawn',
    ]

    for (const type of eventTypes) {
      source.addEventListener(type, (event) => {
        try {
          const data = JSON.parse(event.data)
          const handlers = listenersRef.current[type] || []
          for (const handler of handlers) handler(data)
        } catch (err) {
          console.error(`SSE parse error (${type}):`, err)
        }
      })
    }

    source.onopen = () => setConnected(true)
    source.onerror = () => setConnected(false)
    return () => source.close()
  }, [])

  const subscribe = useCallback((eventType, handler) => {
    if (!listenersRef.current[eventType]) listenersRef.current[eventType] = []
    listenersRef.current[eventType].push(handler)
    return () => {
      listenersRef.current[eventType] = listenersRef.current[eventType].filter(h => h !== handler)
    }
  }, [])

  return (
    <SSEContext.Provider value={{ subscribe, connected }}>
      {children}
    </SSEContext.Provider>
  )
}

export function useSharedSSE(handlers) {
  const ctx = useContext(SSEContext)
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  useEffect(() => {
    if (!ctx) return
    const unsubs = []
    for (const [type, handler] of Object.entries(handlersRef.current)) {
      if (typeof handler === 'function') {
        unsubs.push(ctx.subscribe(type, (data) => handlersRef.current[type]?.(data)))
      }
    }
    return () => unsubs.forEach(u => u())
  }, [ctx])
}
