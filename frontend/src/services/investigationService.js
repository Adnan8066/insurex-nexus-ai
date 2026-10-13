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

  async createInvestigation(data) {
    const response = await api.post('/investigations/', data)
    return response.data
  },

  async updateInvestigation(id, data) {
    const response = await api.patch(`/investigations/${id}/`, data)
    return response.data
  },

  async deleteInvestigation(id) {
    const response = await api.delete(`/investigations/${id}/`)
    return response.data
  },

  async startInvestigation(id) {
    const response = await api.post(`/investigations/${id}/start/`)
    return response.data
  },

  async completeInvestigation(id, data = {}) {
    const response = await api.post(`/investigations/${id}/complete/`, data)
    return response.data
  },

  async getNotes(id) {
    const response = await api.get(`/investigations/${id}/notes/`)
    return response.data
  },

  async addNote(id, data) {
    const response = await api.post(`/investigations/${id}/notes/`, data)
    return response.data
  },

  async getEvidence(id) {
    const response = await api.get(`/investigations/${id}/evidence/`)
    return response.data
  },

  async addEvidence(id, data) {
    const response = await api.post(`/investigations/${id}/evidence/`, data)
    return response.data
  },

  async getFraudAlerts(params = {}) {
    const response = await api.get('/investigations/fraud-alerts/', { params })
    return response.data
  },

  async getFraudAlert(id) {
    const response = await api.get(`/investigations/fraud-alerts/${id}/`)
    return response.data
  },

  async updateFraudAlert(id, data) {
    const response = await api.patch(`/investigations/fraud-alerts/${id}/`, data)
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

  async getHighRiskAlerts() {
    const response = await api.get('/investigations/fraud-alerts/high-risk/')
    return response.data
  },
}

export default investigationService
