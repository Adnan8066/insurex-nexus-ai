import api from './api'

const callbackService = {
  request: async (details) => {
    const response = await api.post('/customers/callback-requests/', details)
    return response.data
  },
}

export default callbackService
