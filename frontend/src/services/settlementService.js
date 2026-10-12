import api from './api'

export const settlementService = {
  async getSettlements(params = {}) {
    const response = await api.get('/settlements/', { params })
    return response.data
  },

  async getSettlement(id) {
    const response = await api.get(`/settlements/${id}/`)
    return response.data
  },

  async createSettlement(data) {
    const response = await api.post('/settlements/', data)
    return response.data
  },

  async updateSettlement(id, data) {
    const response = await api.patch(`/settlements/${id}/`, data)
    return response.data
  },

  async getSettlementByClaim(claimId) {
    const response = await api.get(`/settlements/claim/${claimId}/`)
    return response.data
  },

  async processPayment(settlementId, data) {
    const response = await api.post(`/settlements/${settlementId}/payment/`, data)
    return response.data
  },

  async getPaymentHistory(settlementId) {
    const response = await api.get(`/settlements/${settlementId}/payments/`)
    return response.data
  },
}

export default settlementService