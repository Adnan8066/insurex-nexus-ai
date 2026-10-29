export function formatCurrency(amount, currency = 'INR', locale = 'en-IN') {
  if (amount === null || amount === undefined) return '—'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatCurrencyCompact(amount, currency = 'INR', locale = 'en-IN') {
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

export function truncate(str, length = 50) {
  if (!str) return ''
  if (str.length <= length) return str
  return str.slice(0, length).trim() + '...'
}
