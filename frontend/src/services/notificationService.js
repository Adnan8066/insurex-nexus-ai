import api from './api'

const notificationService = {
  async getNotifications(params = {}) {
    const response = await api.get('/notifications/', { params })
    return response.data
  },
  async markRead(id) {
    const response = await api.post(`/notifications/${id}/mark-read/`)
    return response.data
  },
  async markAllRead() {
    const response = await api.post('/notifications/mark-all-read/')
    return response.data
  },
  async getUnreadCount() {
    const response = await api.get('/notifications/unread-count/')
    return response.data
  },
  async getPreferences() {
    const response = await api.get('/notifications/preferences/')
    return response.data
  },
  async updatePreferences(data) {
    const response = await api.patch('/notifications/preferences/', data)
    return response.data
  },
}

export default notificationService
