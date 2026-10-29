import api from './api'

export const analyticsService = {
  async getDashboardSummary(timeframe = '30d') {
    const response = await api.get('/analytics/dashboard/', { params: { timeframe } })
    return response.data
  },

  async getClaimsTrend(days = 30) {
    const response = await api.get('/analytics/claims-trend/', { params: { days } })
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

  async getOverviewAnalytics(timeframe = 'quarter') {
    const response = await api.get('/analytics/overview/', { params: { timeframe } })
    return response.data
  },

  async exportReport(format = 'csv', params = {}) {
    const response = await api.post('/analytics/export/', { format, ...params }, { responseType: 'blob' })
    return response.data
  },

  async getAvailableTimeframes() {
    return [
      { value: 'week', label: 'Last 7 Days' },
      { value: 'month', label: 'Last 30 Days' },
      { value: 'quarter', label: 'Current Quarter' },
      { value: 'ytd', label: 'Year to Date' },
      { value: 'year', label: 'Last Year' },
    ]
  },
}

export default analyticsService