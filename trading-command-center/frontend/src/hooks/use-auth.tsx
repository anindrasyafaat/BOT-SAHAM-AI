import { createContext, useContext, useState, useEffect } from 'react'

interface User {
  id: string
  name: string
  email: string
  role: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  register: (userData: any) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true
  })

  useEffect(() => {
    // Check for existing session
    const checkAuth = async () => {
      try {
        // Mock authentication check
        const mockUser: User = {
          id: '1',
          name: 'Trading User',
          email: 'user@trading.com',
          role: 'trader'
        }
        
        setAuthState({
          user: mockUser,
          isAuthenticated: true,
          isLoading: false
        })
      } catch (error) {
        setAuthState({
          user: null,
          isAuthenticated: false,
          isLoading: false
        })
      }
    }

    checkAuth()
  }, [])

  const login = async (email: string, password: string) => {
    // Mock login
    const mockUser: User = {
      id: '1',
      name: 'Trading User',
      email,
      role: 'trader'
    }
    
    setAuthState({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false
    })
  }

  const logout = () => {
    setAuthState({
      user: null,
      isAuthenticated: false,
      isLoading: false
    })
  }

  const register = async (userData: any) => {
    // Mock registration
    console.log('Registering user:', userData)
  }

  return (
    <AuthContext.Provider value={{
      ...authState,
      login,
      logout,
      register
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}