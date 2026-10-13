import api from './api'

export const repairService = {
  async getShops(params = {}) {
    const response = await api.get('/repair-shops/shops/', { params })
    return response.data
  },

  async getShop(id) {
    const response = await api.get(`/repair-shops/shops/${id}/`)
    return response.data
  },

  async createShop(data) {
    const response = await api.post('/repair-shops/shops/', data)
    return response.data
  },

  async updateShop(id, data) {
    const response = await api.patch(`/repair-shops/shops/${id}/`, data)
    return response.data
  },

  async approveShop(id) {
    const response = await api.post(`/repair-shops/shops/${id}/approve/`)
    return response.data
  },

  async suspendShop(id) {
    const response = await api.post(`/repair-shops/shops/${id}/suspend/`)
    return response.data
  },

  async getJobs(params = {}) {
    const response = await api.get('/repair-shops/jobs/', { params })
    return response.data
  },

  async getJob(id) {
    const response = await api.get(`/repair-shops/jobs/${id}/`)
    return response.data
  },

  async createJob(data) {
    const response = await api.post('/repair-shops/jobs/', data)
    return response.data
  },

  async updateJob(id, data) {
    const response = await api.patch(`/repair-shops/jobs/${id}/`, data)
    return response.data
  },

  async startJob(id) {
    const response = await api.post(`/repair-shops/jobs/${id}/start/`)
    return response.data
  },

  async completeJob(id, data = {}) {
    const response = await api.post(`/repair-shops/jobs/${id}/complete/`, data)
    return response.data
  },

  async getJobEstimates(id) {
    const response = await api.get(`/repair-shops/jobs/${id}/estimates/`)
    return response.data
  },

  async addJobEstimate(id, data) {
    const response = await api.post(`/repair-shops/jobs/${id}/estimates/`, data)
    return response.data
  },

  async getMyJobs() {
    const response = await api.get('/repair-shops/jobs/my-jobs/')
    return response.data
  },
}

export default repairService
