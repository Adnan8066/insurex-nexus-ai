import api from './api'

const workforceService = {
  async getEmployees() {
    const response = await api.get('/workforce/employees/')
    return response.data
  },

  async getEmployeeProfile(id) {
    const response = await api.get(`/workforce/employees/${id}/`)
    return response.data
  },

  async updateEmployeeProfile(id, payload) {
    const response = await api.patch(`/workforce/employees/${id}/`, payload)
    return response.data
  },
}

export default workforceService
