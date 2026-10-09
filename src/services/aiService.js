import api from './api'

export const aiService = {
  async getClaimAssessment(claimId) {
    const response = await api.get(`/ai/assessment/${claimId}/`)
    return response.data
  },

  async triggerAssessment(claimId) {
    const response = await api.post(`/ai/assessment/${claimId}/trigger/`)
    return response.data
  },

  async getFraudAnalysis(claimId) {
    const response = await api.get(`/ai/fraud-analysis/${claimId}/`)
    return response.data
  },

  async getDecisionFlow(claimId) {
    const response = await api.get(`/ai/decision-flow/${claimId}/`)
    return response.data
  },

  async getRLOptimization(params = {}) {
    const response = await api.get('/ai/rl-optimization/', { params })
    return response.data
  },

  async getAgentOutputs(claimId) {
    const response = await api.get(`/ai/agents/${claimId}/`)
    return response.data
  },

  async getModelPerformance() {
    const response = await api.get('/ai/model-performance/')
    return response.data
  },

  async retrainModels() {
    const response = await api.post('/ai/retrain/')
    return response.data
  },
}

export default aiService