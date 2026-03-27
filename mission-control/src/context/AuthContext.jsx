import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

const AUTH_KEY = 'mc_auth'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

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

  function _saveUser(data) {
    const userData = {
      id: data.user_id,
      email: data.email,
      name: data.name,
      role: data.role,
      tenant_id: data.tenant_id,
      token: data.token,
    }
    setUser(userData)
    localStorage.setItem(AUTH_KEY, JSON.stringify(userData))
    return userData
  }

  async function login(email, password) {
    const res = await fetch('/api/mc/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    const data = await res.json()
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Invalid credentials')
    }
    return _saveUser(data)
  }

  async function register(email, password, name) {
    const res = await fetch('/api/mc/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    })
    const data = await res.json()
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Registration failed')
    }
    return _saveUser(data)
  }

  function logout() {
    setUser(null)
    localStorage.removeItem(AUTH_KEY)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
