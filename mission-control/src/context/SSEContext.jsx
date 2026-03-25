import { createContext, useContext, useEffect, useRef, useCallback, useState } from 'react'

const SSEContext = createContext(null)

export function SSEProvider({ children }) {
  const listenersRef = useRef({})
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  const connect = useCallback(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    let token = ''
    try {
      const stored = localStorage.getItem('mc_auth')
      if (stored) token = JSON.parse(stored).token || ''
    } catch { /* ignore */ }

    if (!token) return

    const ws = new WebSocket(`${proto}//${host}/ws?token=${encodeURIComponent(token)}`)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      console.log('[WS] Connected')
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const eventType = msg.event
        if (!eventType || eventType === 'keepalive' || eventType === 'pong') return
        const handlers = listenersRef.current[eventType] || []
        for (const handler of handlers) {
          try { handler(msg.data) } catch (err) { console.error(`[WS] Handler error (${eventType}):`, err) }
        }
      } catch (err) {
        console.error('[WS] Parse error:', err)
      }
    }

    ws.onclose = (event) => {
      setConnected(false)
      wsRef.current = null
      if (event.code === 4001) {
        console.error('[WS] Auth failed — not reconnecting')
        return
      }
      console.warn(`[WS] Closed (code=${event.code}). Reconnecting...`)
      const delay = Math.min(1000 * Math.pow(2, Math.random() * 3), 10000)
      reconnectTimeoutRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => { /* onclose fires after onerror */ }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  const subscribe = useCallback((eventType, handler) => {
    if (!listenersRef.current[eventType]) listenersRef.current[eventType] = []
    listenersRef.current[eventType].push(handler)
    return () => {
      listenersRef.current[eventType] = (listenersRef.current[eventType] || []).filter(h => h !== handler)
    }
  }, [])

  const send = useCallback((type, data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...data }))
    }
  }, [])

  return (
    <SSEContext.Provider value={{ subscribe, connected, send }}>
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

export function useWSSend() {
  const ctx = useContext(SSEContext)
  return ctx?.send || (() => {})
}

export { SSEContext }
