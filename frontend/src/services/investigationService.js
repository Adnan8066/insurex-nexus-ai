import api from './api'

export const investigationService = {
  async getInvestigations(params = {}) {
    const response = await api.get('/investigations/', { params })
    return response.data
  },

  async getInvestigation(id) {
    const response = await api.get(`/investigations/${id}/`)
    return response.data
  },

  async addNote(id, data) {
    const response = await api.post(`/investigations/${id}/notes/`, data)
    return response.data
  },

  async getFraudAlerts(params = {}) {
    const response = await api.get('/investigations/fraud-alerts/', { params })
    return response.data
  },

  async reviewFraudAlert(id, data = {}) {
    const response = await api.post(`/investigations/fraud-alerts/${id}/review/`, data)
    return response.data
  },

  async escalateFraudAlert(id) {
    const response = await api.post(`/investigations/fraud-alerts/${id}/escalate/`)
    return response.data
  },

  async dismissFraudAlert(id, data = {}) {
    const response = await api.post(`/investigations/fraud-alerts/${id}/dismiss/`, data)
    return response.data
  },
}

export default investigationService
