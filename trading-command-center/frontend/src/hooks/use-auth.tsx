import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { apiFetch, getToken, setToken } from './use-api'

// Login tunggal (APP_PASSWORD di server). Server adalah satu-satunya sumber kebenaran: UI membaca /api/auth/status.
interface User {
  name: string
  email: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  required: boolean
  login: (password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState({ isAuthenticated: false, isLoading: true, required: true })

  const refresh = useCallback(async () => {
    try {
      const res = await apiFetch('/api/auth/status')
      const s = await res.json()
      setState({ isAuthenticated: !!s.authenticated, required: !!s.required, isLoading: false })
    } catch {
      setState((p) => ({ ...p, isLoading: false }))
    }
  }, [])

  useEffect(() => {
    refresh()
    const onUnauthorized = () => setState((p) => ({ ...p, isAuthenticated: false }))
    window.addEventListener('tcc-unauthorized', onUnauthorized)
    return () => window.removeEventListener('tcc-unauthorized', onUnauthorized)
  }, [refresh])

  const login = async (password: string) => {
    const res = await apiFetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }),
    })
    const body = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(body.detail || 'Login gagal')
    if (body.token) setToken(body.token)
    await refresh()
  }

  const logout = () => {
    setToken(null)
    setState((p) => ({ ...p, isAuthenticated: !p.required }))
  }

  const user = state.isAuthenticated ? { name: 'Admin', email: state.required ? 'login aktif' : 'mode lokal (tanpa password)' } : null
  return (
    <AuthContext.Provider value={{ ...state, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}

export const hasToken = () => !!getToken()
