import api from './api'

export const policyService = {
  async getPolicies(params = {}) {
    const response = await api.get('/policies/', { params })
    return response.data
  },

  async getPolicy(id) {
    const response = await api.get(`/policies/${id}/`)
    return response.data
  },

  async createPolicy(data) {
    const response = await api.post('/policies/', data)
    return response.data
  },

  async updatePolicy(id, data) {
    const response = await api.patch(`/policies/${id}/`, data)
    return response.data
  },

  async deletePolicy(id) {
    const response = await api.delete(`/policies/${id}/`)
    return response.data
  },

  async getPolicyDocuments(policyId) {
    const response = await api.get(`/policies/${policyId}/documents/`)
    return response.data
  },

  async uploadPolicyDocument(policyId, formData) {
    const response = await api.post(`/policies/${policyId}/documents/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  async getCoverageDetails(policyId) {
    const response = await api.get(`/policies/${policyId}/coverage/`)
    return response.data
  },

  async getPremiumHistory(policyId) {
    const response = await api.get(`/policies/${policyId}/premium-history/`)
    return response.data
  },
}

export default policyService