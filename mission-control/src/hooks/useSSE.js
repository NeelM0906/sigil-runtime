import { useEffect, useRef, useCallback } from 'react'

/**
 * useSSE — Subscribe to Mission Control server-sent events.
 *
 * @param {Object} handlers — Map of event type to callback: { chat_message: fn, being_status: fn, ... }
 * @param {string} url — SSE endpoint (default: /api/mc/events)
 */
export function useSSE(handlers, url = '/api/mc/events') {
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  useEffect(() => {
    const source = new EventSource(url)

    const eventTypes = ['chat_message', 'being_status', 'task_update', 'subagent_event', 'being_typing']

    for (const type of eventTypes) {
      source.addEventListener(type, (event) => {
        try {
          const data = JSON.parse(event.data)
          handlersRef.current[type]?.(data)
        } catch (err) {
          console.error(`SSE parse error (${type}):`, err)
        }
      })
    }

    source.onerror = () => {
      // EventSource auto-reconnects — just log
      console.warn('SSE connection error, reconnecting...')
    }

    return () => source.close()
  }, [url])
}
