import { useEffect, useRef, useCallback } from 'react'

/**
 * useCodeSSE — Subscribe to per-session Code agent SSE events.
 *
 * @param {string|null} sessionId — Code session ID (null = disconnected)
 * @param {Object} handlers — Map of event type to callback
 * @param {Function} onError — Called when SSE connection fails repeatedly
 */
export function useCodeSSE(sessionId, handlers, onError) {
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers
  const onErrorRef = useRef(onError)
  onErrorRef.current = onError

  useEffect(() => {
    if (!sessionId) return

    const url = `/api/mc/code/sessions/${sessionId}/events`
    const source = new EventSource(url)
    let errorCount = 0

    const eventTypes = [
      'code_agent_start', 'code_agent_end',
      'code_turn_start', 'code_turn_end',
      'code_message_start', 'code_message_end',
      'code_text_start', 'code_text_delta', 'code_text_end',
      'code_tool_call_start', 'code_tool_call_delta', 'code_tool_call_end',
      'code_tool_exec_start', 'code_tool_exec_end',
      'code_thinking_start', 'code_thinking_delta', 'code_thinking_end',
      'code_approval_required', 'code_notification',
    ]

    source.onopen = () => {
      errorCount = 0
    }

    for (const type of eventTypes) {
      source.addEventListener(type, (event) => {
        try {
          const data = JSON.parse(event.data)
          handlersRef.current[type]?.(data)
        } catch (err) {
          console.error(`Code SSE parse error (${type}):`, err)
        }
      })
    }

    source.onerror = () => {
      errorCount++
      if (errorCount >= 3) {
        console.warn('Code SSE connection failed repeatedly')
        onErrorRef.current?.()
      }
    }

    return () => source.close()
  }, [sessionId])
}
