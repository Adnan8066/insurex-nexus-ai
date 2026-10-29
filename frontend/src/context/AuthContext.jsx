import { useState, useEffect, useCallback } from 'react'
import { authService } from '../services'
import { formatApiError } from '../services/api'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem('access_token')

    if (token) {
      try {
        const profile = await authService.getProfile()
        setUser(profile)
        localStorage.setItem('user', JSON.stringify(profile))
      } catch {
        localStorage.removeItem('user')
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setUser(null)
      }
    } else {
      localStorage.removeItem('user')
      setUser(null)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  // login and register both answer with { access, refresh, user } (unwrapped by authService).
  const storeSession = ({ access, refresh, user: userData }) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
    return userData
  }

  const login = async (credentials) => {
    setError(null)
    try {
      const userData = storeSession(await authService.login(credentials))
      return { success: true, user: userData }
    } catch (err) {
      const message = formatApiError(err, 'Login failed. Check your email and password and try again.')
      setError(message)
      return { success: false, error: message }
    }
  }

  const register = async (registrationData) => {
    setError(null)
    try {
      const data = await authService.register(registrationData)
      if (data?.access && data?.refresh && data?.user) {
        storeSession(data)
      }
      return { success: true, data }
    } catch (err) {
      const message = formatApiError(err, 'Registration failed. Please check your details and try again.')
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
      const message = formatApiError(err, 'Failed to send reset email')
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
      const message = formatApiError(err, 'Password reset failed')
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
      const message = formatApiError(err, 'Profile update failed')
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
      const message = formatApiError(err, 'Password change failed')
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
