import api from './api'

export const claimService = {
  async getClaims(params = {}) {
    const response = await api.get('/claims/', { params })
    return response.data
  },

  async getClaim(id) {
    const response = await api.get(`/claims/${id}/`)
    return response.data
  },

  async createClaim(data) {
    const response = await api.post('/claims/', data)
    return response.data
  },

  async updateClaim(id, data) {
    const response = await api.patch(`/claims/${id}/`, data)
    return response.data
  },

  async deleteClaim(id) {
    const response = await api.delete(`/claims/${id}/`)
    return response.data
  },

  async getClaimDocuments(claimId) {
    const response = await api.get(`/claims/${claimId}/documents/`)
    return response.data
  },

  async uploadClaimDocument(claimId, formData) {
    const response = await api.post(`/claims/${claimId}/documents/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  async getClaimTimeline(claimId) {
    const response = await api.get(`/claims/${claimId}/timeline/`)
    return response.data
  },

  async submitClaimAssessment(claimId, data) {
    const response = await api.post(`/claims/${claimId}/assessment/`, data)
    return response.data
  },

  async updateClaimStatus(claimId, status) {
    const response = await api.patch(`/claims/${claimId}/status/`, { status })
    return response.data
  },

  async assignInvestigator(claimId, investigatorId) {
    const response = await api.post(`/claims/${claimId}/assign-investigator/`, {
      investigator_id: investigatorId,
    })
    return response.data
  },

  async assignRepairShop(claimId, repairShopId) {
    const response = await api.post(`/claims/${claimId}/assign-repair-shop/`, {
      repair_shop_id: repairShopId,
    })
    return response.data
  },
}

export default claimService