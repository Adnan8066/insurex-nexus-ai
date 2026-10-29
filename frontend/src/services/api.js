import axios from 'axios'

const configuredApiBase = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')
export const API_BASE_URL = /\/api\/v1$/.test(configuredApiBase)
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

const humanizeField = (field) => {
  const words = String(field).replace(/_/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

const flattenMessages = (value) => {
  if (value == null) return []
  if (typeof value === 'string') return [value]
  if (Array.isArray(value)) return value.flatMap(flattenMessages)
  if (typeof value === 'object') {
    if (typeof value.message === 'string') return [value.message]
    return Object.values(value).flatMap(flattenMessages)
  }
  return [String(value)]
}

const describeFieldErrors = (errors) => {
  if (!errors || typeof errors !== 'object' || Array.isArray(errors)) return flattenMessages(errors).join(' ')
  return Object.entries(errors)
    .map(([field, messages]) => {
      const text = flattenMessages(messages).join(' ')
      if (!text) return ''
      return field === 'non_field_errors' || field === '__all__' ? text : `${humanizeField(field)}: ${text}`
    })
    .filter(Boolean)
    .join(' ')
}

/**
 * Turn any API/axios error into a single human-readable sentence that is safe to render.
 * Never returns an object, so it can go straight into JSX.
 */
export function formatApiError(err, fallback = 'Something went wrong. Please try again.') {
  if (!err) return fallback
  if (typeof err === 'string') return err

  const response = err.response
  if (!response) {
    if (err.code === 'ECONNABORTED') return 'The server took too long to respond. Please try again.'
    if (err.request || err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
      return 'Could not reach the server. Check your internet connection and try again.'
    }
    return fallback
  }

  const data = response.data
  if (typeof data === 'string') {
    // Avoid dumping HTML error pages into the UI.
    return data && data.length < 300 && !/<[a-z!]/i.test(data) ? data : fallback
  }
  if (!data || typeof data !== 'object') return fallback

  if (typeof data.detail === 'string' && data.detail.trim()) return data.detail
  const envelope = data.error
  if (typeof envelope === 'string' && envelope.trim()) return envelope
  if (envelope && typeof envelope === 'object') {
    if (typeof envelope.message === 'string' && envelope.message && envelope.message !== 'An error occurred') {
      return envelope.message
    }
    const details = describeFieldErrors(envelope.details)
    if (details) return details
  }
  if (typeof data.message === 'string' && data.message.trim()) return data.message

  const fields = describeFieldErrors(data.errors || data)
  return fields || fallback
}

export default api
