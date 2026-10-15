import api from './api'

const responseData = (response) => response.data?.data ?? response.data

export const authService = {
  async login(credentials) {
    const response = await api.post('/auth/login/', credentials)
    return responseData(response)
  },

  async register(userData) {
    try {
      // Public signup is customer-only; the backend enforces this independently.
      const registrationData = { ...userData }
      delete registrationData.role
      const response = await api.post('/auth/register/', registrationData)
      return responseData(response)
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
    const response = await api.post('/auth/password-reset/', { email })
    return responseData(response)
  },

  async resetPassword(token, password) {
    const response = await api.post('/auth/password-reset/confirm/', {
      token,
      password,
      confirm_password: password,
    })
    return responseData(response)
  },

  async getProfile() {
    const response = await api.get('/auth/profile/')
    return responseData(response)
  },

  async updateProfile(data) {
    const profileData = { ...data }
    delete profileData.email
    if (profileData.name) {
      const [firstName, ...lastName] = profileData.name.trim().split(/\s+/)
      profileData.first_name = firstName || ''
      profileData.last_name = lastName.join(' ')
      delete profileData.name
    }
    const response = await api.patch('/auth/profile/', profileData)
    return responseData(response)
  },

  async changePassword(data) {
    const response = await api.post('/auth/change-password/', {
      current_password: data.currentPassword ?? data.current_password,
      new_password: data.newPassword ?? data.new_password,
      confirm_password: data.confirmPassword ?? data.confirm_password ?? data.newPassword ?? data.new_password,
    })
    return responseData(response)
  },
}

export default authService
