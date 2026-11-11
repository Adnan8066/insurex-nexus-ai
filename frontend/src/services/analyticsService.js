import api from './api'

export const analyticsService = {
  async getDashboardSummary(timeframe = '30d') {
    const response = await api.get('/analytics/dashboard/', { params: { timeframe } })
    return response.data
  },

  // Zero-filled buckets for a dashboard timeframe; granularity is 'day' or 'month'.
  async getClaimsTrendForTimeframe(timeframe, granularity = 'day') {
    const response = await api.get('/analytics/claims-trend/', { params: { timeframe, granularity } })
    return response.data
  },

  async getFraudRiskDistribution(timeframe = '30d') {
    const response = await api.get('/analytics/fraud-risk/', { params: { timeframe } })
    return response.data
  },
}

export default analyticsService