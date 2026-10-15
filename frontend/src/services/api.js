import axios from 'axios'

const configuredApiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')
const API_BASE_URL = /\/api\/v1$/.test(configuredApiBase)
  ? configuredApiBase
  : /\/api$/.test(configuredApiBase)
    ? `${configuredApiBase}/v1`
    : `${configuredApiBase}/api/v1`

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

const describeErrorDetails = (details) => {
  if (typeof details === 'string') return details
  if (Array.isArray(details)) return details.map(String).join(', ')
  if (details && typeof details === 'object') {
    return Object.entries(details)
      .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.map(String).join(', ') : String(messages)}`)
      .join('; ')
  }
  return ''
}

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const payload = error.response?.data
    if (payload?.success === false && payload.error && !payload.detail) {
      const message = payload.error.message
      payload.detail = message && message !== 'An error occurred'
        ? message
        : describeErrorDetails(payload.error.details) || 'The request could not be completed.'
    }

    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
            refresh: refreshToken,
          })

          const responseData = response.data
          const access = responseData?.data?.access || responseData?.access
          if (!access) {
            throw new Error('No access token in refresh response')
          }
          localStorage.setItem('access_token', access)
          originalRequest.headers.Authorization = `Bearer ${access}`

          return api(originalRequest)
        } catch (refreshError) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      }
    }

    return Promise.reject(error)
  }
)

export default api
