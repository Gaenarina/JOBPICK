'use client'

import { createContext, useContext, useState, useEffect } from 'react'

const AUTH_KEY = 'jobpick_user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    try {
      const saved = localStorage.getItem(AUTH_KEY)
      setUser(saved ? JSON.parse(saved) : null)
    } catch (error) {
      console.error('인증 정보 로딩 실패:', error)
      localStorage.removeItem(AUTH_KEY)
      setUser(null)
    }
    setMounted(true)
  }, [])

  const login = (email, password, name = '홍길동') => {
    const userData = { email, name }
    setUser(userData)
    localStorage.setItem(AUTH_KEY, JSON.stringify(userData))
  }

  const signup = (name, email) => {
    const userData = { email, name: name || '홍길동' }
    setUser(userData)
    localStorage.setItem(AUTH_KEY, JSON.stringify(userData))
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem(AUTH_KEY)
  }

  return (
    <AuthContext.Provider value={{ user, login, signup, logout, isAuthenticated: !!user, mounted }}>
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
