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
}

export default adminUserService
