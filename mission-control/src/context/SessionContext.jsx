import { createContext, useContext, useState, useEffect } from 'react'

const SessionContext = createContext({ activeSessionId: null, setActiveSessionId: () => {} })

export function SessionProvider({ children }) {
  const [activeSessionId, setActiveSessionId] = useState(() => {
    try { return localStorage.getItem('mc_active_session') } catch { return null }
  })

  // Sync to localStorage
  useEffect(() => {
    try {
      if (activeSessionId) localStorage.setItem('mc_active_session', activeSessionId)
      else localStorage.removeItem('mc_active_session')
    } catch { /* ignore */ }
  }, [activeSessionId])

  return (
    <SessionContext.Provider value={{ activeSessionId, setActiveSessionId }}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSession() {
  return useContext(SessionContext)
}
