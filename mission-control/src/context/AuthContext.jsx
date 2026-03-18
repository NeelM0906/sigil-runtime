import { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '../api'

const AuthContext = createContext(null)

const AUTH_KEY = 'mc_auth'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Restore session from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(AUTH_KEY)
    if (stored) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        localStorage.removeItem(AUTH_KEY)
      }
    }
    setLoading(false)
  }, [])

  async function login(email, password) {
    const data = await authApi.login(email, password)
    const userData = {
      id: data.user_id,
      email: data.email,
      name: data.name,
      role: data.role,
      token: data.token,
    }
    setUser(userData)
    localStorage.setItem(AUTH_KEY, JSON.stringify(userData))
    return userData
  }

  async function register(email, password, name) {
    const data = await authApi.register(email, password, name)
    const userData = {
      id: data.user_id,
      email: data.email,
      name: data.name,
      role: data.role,
      token: data.token,
    }
    setUser(userData)
    localStorage.setItem(AUTH_KEY, JSON.stringify(userData))
    return userData
  }

  async function updateProfile(data) {
    const updated = await authApi.updateProfile(data)
    setUser(prev => {
      const merged = { ...prev, ...updated }
      localStorage.setItem(AUTH_KEY, JSON.stringify(merged))
      return merged
    })
    return updated
  }

  function logout() {
    authApi.logout().catch(() => {})
    setUser(null)
    localStorage.removeItem(AUTH_KEY)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register, updateProfile }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
