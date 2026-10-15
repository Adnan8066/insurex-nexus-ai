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

  async approveSettlement(id, data) {
    const response = await api.post(`/settlements/${id}/approve/`, data)
    return response.data
  },

  async rejectSettlement(id, data = {}) {
    const response = await api.post(`/settlements/${id}/reject/`, data)
    return response.data
  },

  async updateSettlement(id, data) {
    const response = await api.patch(`/settlements/${id}/`, data)
    return response.data
  },

  async getSettlementByClaim(claimId) {
    const response = await api.get(`/settlements/by-claim/${claimId}/`)
    return response.data
  },

  async processPayment(settlementId, data) {
    const response = await api.post(`/settlements/${settlementId}/pay/`, data)
    return response.data
  },

  async completePayment(settlementId, paymentId) {
    const response = await api.post(`/settlements/${settlementId}/complete-payment/`, { payment_id: paymentId })
    return response.data
  },

  async getPaymentHistory(settlementId) {
    const response = await api.get(`/settlements/${settlementId}/payments/`)
    return response.data
  },
}

export default settlementService
