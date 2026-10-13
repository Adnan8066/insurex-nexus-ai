import { useState, useEffect, Component } from 'react'
import { RefreshCw, AlertTriangle, AlertCircle, WifiOff } from 'lucide-react'
import { clsx } from 'clsx'
import { Button } from '../ui/Button'
import { Card, CardContent } from '../ui/Card'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0,
    }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: (this.state.retryCount || 0) + 1,
    })
    if (this.props.onRetry) {
      this.props.onRetry(this.state.retryCount + 1)
    }
  }

  render() {
    const { hasError, error, errorInfo, retryCount } = this.state
    const { fallback, children, onError } = this.props

    if (hasError) {
      if (fallback) {
        return fallback({ error, errorInfo, resetError: this.handleRetry, retryCount })
      }

      return (
        <div className="error-boundary-fallback p-6">
          <div className="max-w-md mx-auto text-center">
            <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-8 h-8 text-red-500" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
            <p className="text-gray-600 mb-4">
              We encountered an unexpected error. Please try again or contact support if the problem persists.
            </p>
            
            {import.meta.env.DEV && error && (
              <details className="text-left mb-4 p-3 bg-gray-100 rounded text-xs text-gray-700 overflow-auto max-h-48">
                <summary className="font-medium cursor-pointer mb-2">Error Details</summary>
                <pre>{error.toString()}</pre>
                {errorInfo && errorInfo.componentStack && (
                  <pre className="mt-2">{errorInfo.componentStack}</pre>
                )}
              </details>
            )}

            <div className="flex items-center justify-center gap-3">
              <Button 
                variant="primary" 
                onClick={this.handleRetry}
                loading={retryCount > 0}
                className="flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Retry Connection
              </Button>
              {retryCount > 0 && (
                <span className="text-sm text-gray-500">Attempt #{retryCount}</span>
              )}
            </div>

            {this.props.showSupportLink && (
              <div className="mt-6 pt-4 border-t border-gray-200">
                <p className="text-sm text-gray-500">Error ID: {Date.now()}</p>
              </div>
            )}
          </div>
        </div>
      )
    }

    return children
  }
}

export function withErrorBoundary(Component, errorBoundaryProps = {}) {
  return function WrappedComponent(props) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <Component {...props} />
      </ErrorBoundary>
    )
  }
}

export function DashboardErrorFallback({ error, errorInfo, resetError, retryCount }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="card p-6 animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-10 bg-gray-200 rounded w-1/2"></div>
        </div>
      ))}
    </div>
  )
}

export function ChartErrorFallback({ error, errorInfo, resetError, retryCount, title = 'Chart' }) {
  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">{title}</h3>
      </div>
      <div className="card-content flex items-center justify-center h-64">
        <div className="text-center p-4">
          <div className="w-12 h-12 bg-yellow-50 rounded-full flex items-center justify-center mx-auto mb-3">
            <AlertTriangle className="w-6 h-6 text-yellow-500" />
          </div>
          <p className="text-gray-600 mb-3">Unable to load {title.toLowerCase()}</p>
          <Button variant="primary" size="sm" onClick={resetError} loading={retryCount > 0} className="flex items-center gap-2 mx-auto">
            <RefreshCw className="w-4 h-4" />
            Retry
          </Button>
        </div>
      </div>
    </div>
  )
}

export function DataTableErrorFallback({ error, errorInfo, resetError, retryCount, title = 'Data' }) {
  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">{title}</h3>
      </div>
      <div className="card-content p-8 text-center">
        <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
          <WifiOff className="w-6 h-6 text-gray-400" />
        </div>
        <p className="text-gray-600 mb-3">Unable to load {title.toLowerCase()}</p>
        <p className="text-sm text-gray-500 mb-4">The data table could not be loaded. Please try again.</p>
        <Button variant="primary" size="sm" onClick={resetError} loading={retryCount > 0} className="flex items-center gap-2 mx-auto">
          <RefreshCw className="w-4 h-4" />
          Retry
        </Button>
      </div>
    </div>
  )
}

export default ErrorBoundary
