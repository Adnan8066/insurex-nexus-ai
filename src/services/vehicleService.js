import api from './api'

export const vehicleService = {
  async getVehicles(params = {}) {
    const response = await api.get('/vehicles/', { params })
    return response.data
  },

  async getVehicle(id) {
    const response = await api.get(`/vehicles/${id}/`)
    return response.data
  },

  async createVehicle(data) {
    const response = await api.post('/vehicles/', data)
    return response.data
  },

  async updateVehicle(id, data) {
    const response = await api.patch(`/vehicles/${id}/`, data)
    return response.data
  },

  async deleteVehicle(id) {
    const response = await api.delete(`/vehicles/${id}/`)
    return response.data
  },

  async getVehicleHistory(vehicleId) {
    const response = await api.get(`/vehicles/${vehicleId}/history/`)
    return response.data
  },

  async getVehicleClaims(vehicleId) {
    const response = await api.get(`/vehicles/${vehicleId}/claims/`)
    return response.data
  },

  async uploadVehicleDocument(vehicleId, formData) {
    const response = await api.post(`/vehicles/${vehicleId}/documents/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },
}

export default vehicleService