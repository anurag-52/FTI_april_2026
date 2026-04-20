import { useState, useEffect, createContext, useContext } from 'react'
import { getMe } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewModeState] = useState(() => {
    return localStorage.getItem('viewMode') || null
  })

  // Sync viewMode with user role initial load
  useEffect(() => {
    if (user && !viewMode) {
      setViewMode(user.role)
    }
  }, [user])

  const setViewMode = (mode) => {
    setViewModeState(mode)
    localStorage.setItem('viewMode', mode)
  }

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    const cached = localStorage.getItem('user')
    if (token && cached) {
      setUser(JSON.parse(cached))
      // Refresh from server in background
      getMe().then(u => {
        setUser(u)
        localStorage.setItem('user', JSON.stringify(u))
      }).catch(() => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        setUser(null)
      }).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = (token, userData) => {
    localStorage.setItem('access_token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setUser(null)
    window.location.href = '/login'
  }

  const refreshUser = async () => {
    const u = await getMe()
    setUser(u)
    localStorage.setItem('user', JSON.stringify(u))
    return u
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser, viewMode, setViewMode }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
