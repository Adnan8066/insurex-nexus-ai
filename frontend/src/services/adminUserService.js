import api from './api'

const adminUserService = {
  async getUsers() {
    const response = await api.get('/auth/users/')
    const data = response.data?.data ?? response.data
    return data.users || []
  },

  async createUser(userData) {
    const response = await api.post('/auth/users/', userData)
    const data = response.data?.data ?? response.data
    return data.user
  },

  // Resolves to { action: 'deleted' | 'deactivated', message }.
  async deleteUser(userId) {
    const response = await api.delete(`/auth/users/${userId}/`)
    const body = response.data || {}
    return { action: body.data?.action, message: body.message }
  },
}

export default adminUserService
