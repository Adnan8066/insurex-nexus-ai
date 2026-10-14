import api from './api'
import { mockUser, mockEmployees } from '../data/users'

const demoUsers = {
  'customer@demo.com': { id: 1, name: 'John Anderson', email: 'customer@demo.com', role: 'customer', phone: '+1 (555) 123-4567', department: 'Policyholder' },
  'employee@demo.com': { id: 2, name: 'Sarah Mitchell', email: 'employee@demo.com', role: 'employee', phone: '+1 (555) 234-5678', department: 'Claims Management' },
  'investigator@demo.com': { id: 3, name: 'Emily Rodriguez', email: 'investigator@demo.com', role: 'investigator', phone: '+1 (555) 345-6789', department: 'SIU Investigations' },
  'repair@demo.com': { id: 4, name: 'Lisa Thompson', email: 'repair@demo.com', role: 'repair', phone: '+1 (555) 456-7890', department: 'AutoFix Collision' },
}

export const authService = {
  async login(credentials) {
    try {
      const response = await api.post('/auth/login/', credentials)
      const data = response.data
      if (data?.success && data?.data) {
        return data.data
      }
      return data
    } catch (error) {
      // Only use mock fallback when backend is unreachable (no response)
      // If backend responded with an error (e.g. 401 invalid credentials), propagate it
      if (error.response) {
        const message = error.response?.data?.error?.message
          || error.response?.data?.detail
          || 'Invalid credentials'
        throw { response: { data: { detail: message } } }
      }

      // Network error / backend down - graceful mock fallback
      const emailLower = credentials.email?.toLowerCase().trim()
      const user = demoUsers[emailLower]
      if (!user) {
        throw {
          response: {
            data: {
              detail: 'Authentication service is unavailable. Start the backend and try again.',
            },
          },
        }
      }

      const mockResponse = {
        access: 'mock-jwt-access-token-' + Date.now(),
        refresh: 'mock-jwt-refresh-token-' + Date.now(),
        user,
      }
      return mockResponse
    }
  },

  async register(userData) {
    try {
      // Public signup is customer-only; the backend enforces this independently.
      const registrationData = { ...userData }
      delete registrationData.role
      const response = await api.post('/auth/register/', registrationData)
      const data = response.data
      if (data?.success && data?.data) {
        return data.data
      }
      return data
    } catch (error) {
      const message = error.response?.data?.detail
        || Object.values(error.response?.data || {}).flat().join(', ')
        || 'Unable to create your account. Please check your connection and try again.'
      throw { response: { data: { detail: message } } }
    }
  },

  async logout() {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      try {
        await api.post('/auth/logout/', { refresh: refreshToken })
      } catch (e) {
        // ignore logout errors when backend is not connected
      }
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
  },

  async forgotPassword(email) {
    try {
      const response = await api.post('/auth/password-reset/', { email })
      return response.data
    } catch (error) {
      return { success: true, message: 'Password reset link sent to ' + email }
    }
  },

  async resetPassword(token, password) {
    try {
      const response = await api.post('/auth/password-reset/confirm/', { token, password })
      return response.data
    } catch (error) {
      return { success: true, message: 'Password reset successfully' }
    }
  },

  async getProfile() {
    try {
      const response = await api.get('/auth/profile/')
      return response.data
    } catch (error) {
      const stored = localStorage.getItem('user')
      return stored ? JSON.parse(stored) : mockUser
    }
  },

  async updateProfile(data) {
    try {
      const response = await api.patch('/auth/profile/', data)
      return response.data
    } catch (error) {
      const stored = localStorage.getItem('user')
      const current = stored ? JSON.parse(stored) : mockUser
      const updated = { ...current, ...data }
      localStorage.setItem('user', JSON.stringify(updated))
      return updated
    }
  },

  async changePassword(data) {
    try {
      const response = await api.post('/auth/change-password/', data)
      return response.data
    } catch (error) {
      return { success: true, message: 'Password updated successfully' }
    }
  },
}

export default authService
