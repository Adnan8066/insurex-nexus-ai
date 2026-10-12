export function formatCurrency(amount, currency = 'USD', locale = 'en-US') {
  if (amount === null || amount === undefined) return '—'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatCurrencyCompact(amount, currency = 'USD', locale = 'en-US') {
  if (amount === null || amount === undefined) return '—'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(amount)
}

export function formatDate(date, options = {}) {
  if (!date) return '—'
  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options,
  }
  return new Date(date).toLocaleDateString('en-US', defaultOptions)
}

export function formatDateTime(date, options = {}) {
  if (!date) return '—'
  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  }
  return new Date(date).toLocaleDateString('en-US', defaultOptions)
}

export function formatRelativeTime(date) {
  if (!date) return '—'
  const now = new Date()
  const then = new Date(date)
  const diffMs = now - then
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return formatDate(date)
}

export function formatNumber(num, options = {}) {
  if (num === null || num === undefined) return '—'
  return new Intl.NumberFormat('en-US', options).format(num)
}

export function formatPercentage(value, decimals = 0) {
  if (value === null || value === undefined) return '—'
  return `${Number(value).toFixed(decimals)}%`
}

export function truncate(str, length = 50) {
  if (!str) return ''
  if (str.length <= length) return str
  return str.slice(0, length).trim() + '...'
}

export function getInitials(name) {
  if (!name) return '?'
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

export function classNames(...classes) {
  return classes.filter(Boolean).join(' ')
}

export function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

export function throttle(func, limit) {
  let inThrottle
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

export function generateId(prefix = '') {
  return `${prefix}${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

export function getStatusColor(status) {
  const colors = {
    submitted: 'info',
    'under-review': 'warning',
    'ai-assessment': 'primary',
    investigation: 'warning',
    approved: 'success',
    rejected: 'danger',
    'repair-settlement': 'primary',
    closed: 'neutral',
    pending: 'warning',
    active: 'success',
    inactive: 'neutral',
    expired: 'danger',
    'high-risk': 'danger',
    'medium-risk': 'warning',
    'low-risk': 'success',
    assigned: 'info',
    'in-progress': 'primary',
    completed: 'success',
    cancelled: 'danger',
    paid: 'success',
    'payment-pending': 'warning',
  }
  return colors[status] || 'neutral'
}

export function getPriorityColor(priority) {
  const colors = {
    critical: 'danger',
    high: 'danger',
    medium: 'warning',
    low: 'success',
    none: 'neutral',
  }
  return colors[priority?.toLowerCase()] || 'neutral'
}

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function copyToClipboard(text) {
  return navigator.clipboard.writeText(text)
}

export function downloadFile(data, filename, type = 'application/json') {
  const blob = new Blob([data], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function parseQueryString(queryString) {
  const params = new URLSearchParams(queryString)
  const result = {}
  for (const [key, value] of params) {
    result[key] = value
  }
  return result
}

export function buildQueryString(params) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, value)
    }
  })
  return searchParams.toString()
}

export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj))
}

export function isEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b)
}

export function groupBy(array, key) {
  return array.reduce((result, item) => {
    const groupKey = item[key]
    if (!result[groupKey]) {
      result[groupKey] = []
    }
    result[groupKey].push(item)
    return result
  }, {})
}

export function sortBy(array, key, direction = 'asc') {
  return [...array].sort((a, b) => {
    const aVal = a[key]
    const bVal = b[key]
    if (aVal < bVal) return direction === 'asc' ? -1 : 1
    if (aVal > bVal) return direction === 'asc' ? 1 : -1
    return 0
  })
}

export function filterBy(array, filters) {
  return array.filter((item) => {
    return Object.entries(filters).every(([key, value]) => {
      if (value === undefined || value === null || value === '') return true
      const itemValue = item[key]
      if (Array.isArray(value)) return value.includes(itemValue)
      if (typeof value === 'string') return itemValue?.toLowerCase().includes(value.toLowerCase())
      return itemValue === value
    })
  })
}