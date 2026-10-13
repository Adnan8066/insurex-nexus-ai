import api from './api'

export const aiService = {
  async assessClaim(data) {
    const response = await api.post('/ai/assess-claim/', data)
    return response.data
  },

  async predictRepairCost(data) {
    const response = await api.post('/ai/predict-repair-cost/', data)
    return response.data
  },

  async detectFraud(data) {
    const response = await api.post('/ai/detect-fraud/', data)
    return response.data
  },

  async predictTotalLoss(data) {
    const response = await api.post('/ai/predict-total-loss/', data)
    return response.data
  },

  async runAgent(agentType, data = {}) {
    const response = await api.post(`/ai/run-agent/${agentType}/`, data)
    return response.data
  },

  async getDecisionFlow(claimId) {
    const response = await api.get(`/ai/decision-flow/${claimId}/`)
    return response.data
  },
}

export default aiService
