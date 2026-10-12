import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authService } from '../services'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadUser = useCallback(async () => {
    const storedUser = localStorage.getItem('user')
    const token = localStorage.getItem('access_token')

    if (storedUser && token) {
      try {
        setUser(JSON.parse(storedUser))
      } catch {
        localStorage.removeItem('user')
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      }
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const login = async (credentials) => {
    setError(null)
    try {
      const data = await authService.login(credentials)
      const { access, refresh, user: userData } = data

      localStorage.setItem('access_token', access)
      localStorage.setItem('refresh_token', refresh)
      localStorage.setItem('user', JSON.stringify(userData))

      setUser(userData)
      return { success: true, user: userData }
    } catch (err) {
      const message = err.response?.data?.detail || err.response?.data?.non_field_errors?.[0] || 'Login failed'
      setError(message)
      return { success: false, error: message }
    }
  }

  const register = async (userData) => {
    setError(null)
    try {
      const data = await authService.register(userData)
      return { success: true, data }
    } catch (err) {
      const message = err.response?.data?.detail || Object.values(err.response?.data || {}).flat().join(', ') || 'Registration failed'
      setError(message)
      return { success: false, error: message }
    }
  }

  const logout = async () => {
    try {
      await authService.logout()
    } catch {
      // Ignore logout errors
    } finally {
      setUser(null)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    }
  }

  const forgotPassword = async (email) => {
    setError(null)
    try {
      await authService.forgotPassword(email)
      return { success: true }
    } catch (err) {
      const message = err.response?.data?.detail || 'Failed to send reset email'
      setError(message)
      return { success: false, error: message }
    }
  }

  const resetPassword = async (token, password) => {
    setError(null)
    try {
      await authService.resetPassword(token, password)
      return { success: true }
    } catch (err) {
      const message = err.response?.data?.detail || 'Password reset failed'
      setError(message)
      return { success: false, error: message }
    }
  }

  const updateProfile = async (profileData) => {
    setError(null)
    try {
      const updatedUser = await authService.updateProfile(profileData)
      setUser(updatedUser)
      localStorage.setItem('user', JSON.stringify(updatedUser))
      return { success: true, user: updatedUser }
    } catch (err) {
      const message = err.response?.data?.detail || 'Profile update failed'
      setError(message)
      return { success: false, error: message }
    }
  }

  const changePassword = async (passwordData) => {
    setError(null)
    try {
      await authService.changePassword(passwordData)
      return { success: true }
    } catch (err) {
      const message = err.response?.data?.detail || 'Password change failed'
      setError(message)
      return { success: false, error: message }
    }
  }

  const hasRole = (roles) => {
    if (!user) return false
    const roleArray = Array.isArray(roles) ? roles : [roles]
    return roleArray.includes(user.role)
  }

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    forgotPassword,
    resetPassword,
    updateProfile,
    changePassword,
    hasRole,
    isAuthenticated: !!user,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}