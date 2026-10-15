import api from './api'

export const assessmentService = {
  async getAssessments(params = {}) {
    const response = await api.get('/assessments/assessments/', { params })
    return response.data
  },

  async getAssessment(id) {
    const response = await api.get(`/assessments/assessments/${id}/`)
    return response.data
  },

  async createAssessment(data) {
    const response = await api.post('/assessments/assessments/', data)
    return response.data
  },

  async reviewAssessment(id) {
    const response = await api.post(`/assessments/assessments/${id}/review/`)
    return response.data
  },

  async requestReview(id) {
    const response = await api.post(`/assessments/assessments/${id}/request-review/`)
    return response.data
  },

  async getAgentOutputs(params = {}) {
    const response = await api.get('/assessments/agent-outputs/', { params })
    return response.data
  },

  async getDecisionFlows(params = {}) {
    const response = await api.get('/assessments/decision-flows/', { params })
    return response.data
  },

  async getDecisionFlowForClaim(claimId) {
    const response = await api.get(`/ai/decision-flow/${claimId}/`)
    return response.data
  },

  async getModelPerformance(params = {}) {
    const response = await api.get('/assessments/model-performance/', { params })
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
}

export default assessmentService
