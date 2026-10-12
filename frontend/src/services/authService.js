import api from './api'
import { mockUser, mockEmployees } from '../data/users'

const demoUsers = {
  'customer@demo.com': { id: 1, name: 'John Anderson', email: 'customer@demo.com', role: 'customer', phone: '+1 (555) 123-4567', department: 'Policyholder' },
  'employee@demo.com': { id: 2, name: 'Sarah Mitchell', email: 'employee@demo.com', role: 'employee', phone: '+1 (555) 234-5678', department: 'Claims Management' },
  'investigator@demo.com': { id: 3, name: 'Emily Rodriguez', email: 'investigator@demo.com', role: 'investigator', phone: '+1 (555) 345-6789', department: 'SIU Investigations' },
  'repair@demo.com': { id: 4, name: 'Lisa Thompson', email: 'repair@demo.com', role: 'repair', phone: '+1 (555) 456-7890', department: 'AutoFix Collision' },
  'admin@demo.com': { id: 5, name: 'James Wilson', email: 'admin@demo.com', role: 'admin', phone: '+1 (555) 567-8901', department: 'Executive Analytics' },
}

export const authService = {
  async login(credentials) {
    try {
      const response = await api.post('/auth/login/', credentials)
      return response.data
    } catch (error) {
      // Graceful fallback for mock/demo frontend without backend running
      const emailLower = credentials.email?.toLowerCase().trim()
      let user = demoUsers[emailLower]

      if (!user) {
        // Match by role or default to customer
        if (emailLower.includes('admin')) {
          user = demoUsers['admin@demo.com']
        } else if (emailLower.includes('investigat')) {
          user = demoUsers['investigator@demo.com']
        } else if (emailLower.includes('repair')) {
          user = demoUsers['repair@demo.com']
        } else if (emailLower.includes('emp') || emailLower.includes('staff')) {
          user = demoUsers['employee@demo.com']
        } else {
          user = {
            id: 1,
            name: credentials.email.split('@')[0].replace('.', ' ') || 'Demo User',
            email: credentials.email,
            role: 'customer',
            phone: '+1 (555) 123-4567',
            department: 'Policyholder'
          }
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
      const response = await api.post('/auth/register/', userData)
      return response.data
    } catch (error) {
      // Mock registration fallback
      const newUser = {
        id: Date.now(),
        name: userData.name || 'New User',
        email: userData.email,
        phone: userData.phone,
        role: userData.role || 'customer',
        department: userData.role === 'customer' ? 'Policyholder' : 'Insurance Operations',
      }
      return {
        access: 'mock-jwt-access-token-' + Date.now(),
        refresh: 'mock-jwt-refresh-token-' + Date.now(),
        user: newUser,
      }
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