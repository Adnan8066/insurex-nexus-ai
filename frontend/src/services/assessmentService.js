import api from './api'

export const assessmentService = {
  async getAssessments(params = {}) {
    const response = await api.get('/assessments/assessments/', { params })
    return response.data
  },

  async getAgentOutputs(params = {}) {
    const response = await api.get('/assessments/agent-outputs/', { params })
    return response.data
  },

  async getModelStatus() {
    const response = await api.get('/ai/model-status/')
    return response.data
  },

  async assessClaim(data) {
    const response = await api.post('/ai/assess-claim/', data)
    return response.data
  },

  async getRoutingRecommendation(claimData, activeAgentsStatus, claimId = null) {
    const response = await api.post('/ai/route-recommendation/', {
      claim_data: claimData,
      claim_id: claimId,
      active_agents_status: activeAgentsStatus,
    })
    return response.data
  },

  async getRoutingAgents() {
    const response = await api.get('/ai/routing-agents/')
    return response.data
  },

  async getRoutingClaims() {
    const response = await api.get('/ai/routing-claims/')
    return response.data
  },

  async getRoutingModelStatus() {
    const response = await api.get('/ai/routing-model-status/')
    return response.data
  },

  async reviewRoutingRecommendation(payload) {
    const response = await api.post('/ai/route-recommendation/review/', payload)
    return response.data
  },
}

export default assessmentService
