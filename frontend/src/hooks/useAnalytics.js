import { useState, useEffect, useCallback, useRef } from 'react'
import { analyticsService } from '../services/analyticsService'

export function useAnalytics(timeframe = 'quarter', autoRefresh = false, refreshInterval = 60000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const intervalRef = useRef(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [summary, trend, fraudRisk] = await Promise.all([
        analyticsService.getDashboardSummary(timeframe),
        analyticsService.getClaimsTrend(getDaysFromTimeframe(timeframe)),
        analyticsService.getFraudRiskDistribution(timeframe),
      ])

      setData({ summary, trend, fraudRisk })
      setLastUpdated(new Date())
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [timeframe])

  const refresh = useCallback(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      intervalRef.current = setInterval(refresh, refreshInterval)
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [autoRefresh, refreshInterval, refresh])

  return { data, loading, error, refresh, lastUpdated }
}

function getDaysFromTimeframe(timeframe) {
  const mapping = {
    week: 7,
    month: 30,
    quarter: 90,
    ytd: 365,
    year: 365,
  }
  return mapping[timeframe] || 30
}

export function useAutoRefresh(enabled, interval = 60000, onRefresh) {
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const intervalRef = useRef(null)

  const refresh = useCallback(async () => {
    if (isRefreshing) return
    setIsRefreshing(true)
    try {
      await onRefresh()
      setLastRefresh(new Date())
    } finally {
      setIsRefreshing(false)
    }
  }, [onRefresh, isRefreshing])

  useEffect(() => {
    if (enabled && interval > 0) {
      intervalRef.current = setInterval(refresh, interval)
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [enabled, interval, refresh])

  return { refresh, isRefreshing, lastRefresh }
}

export function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

export function useRetry(operation, maxRetries = 3, delay = 1000) {
  const [retryCount, setRetryCount] = useState(0)
  const [isRetrying, setIsRetrying] = useState(false)

  const retry = useCallback(async () => {
    if (retryCount >= maxRetries) {
      throw new Error(`Max retries (${maxRetries}) exceeded`)
    }
    
    setIsRetrying(true)
    setRetryCount((prev) => prev + 1)
    
    await new Promise((resolve) => setTimeout(resolve, delay))
    
    try {
      await operation()
    } finally {
      setIsRetrying(false)
    }
  }, [operation, retryCount, maxRetries, delay])

  const reset = useCallback(() => {
    setRetryCount(0)
    setIsRetrying(false)
  }, [])

  return { retry, isRetrying, retryCount, reset, canRetry: retryCount < maxRetries }
}

export default useAnalytics
