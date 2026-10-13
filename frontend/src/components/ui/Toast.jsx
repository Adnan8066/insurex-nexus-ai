import { useState, useCallback, createContext, useContext, useEffect } from 'react'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import { clsx } from 'clsx'
import { Button } from './Button'

const ToastContext = createContext(null)

const toastIcons = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const toastStyles = {
  success: 'bg-green-50 border-green-200 text-green-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
}

function Toast({ toast, onClose }) {
  const Icon = toastIcons[toast.type] || Info
  const baseStyle = toastStyles[toast.type] || toastStyles.info

  return (
    <div
      className={clsx(
        'toast-enter flex items-start gap-3 p-4 rounded-xl border shadow-lg min-w-[320px] max-w-md',
        baseStyle,
        toast.persistent && 'ring-2',
        toast.persistent ? 'ring-offset-2 ring-offset-white' : ''
      )}
      role="alert"
      aria-live="polite"
    >
      <div className={clsx('flex-shrink-0 w-5 h-5 mt-0.5', toast.type === 'success' && 'text-green-500', toast.type === 'error' && 'text-red-500', toast.type === 'warning' && 'text-yellow-500', toast.type === 'info' && 'text-blue-500')}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        {toast.title && (
          <p className="font-medium text-gray-900">{toast.title}</p>
        )}
        {toast.message && (
          <p className="text-sm text-gray-600 mt-1">{toast.message}</p>
        )}
        {toast.action && (
          <div className="mt-3">
            <Button
              variant={toast.type === 'error' ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => {
                toast.action.onClick()
                if (!toast.action.persist) onClose(toast.id)
              }}
              className="flex items-center gap-1.5"
            >
              {toast.action.icon}
              {toast.action.label}
            </Button>
          </div>
        )}
      </div>
      {!toast.persistent && (
        <button
          onClick={() => onClose(toast.id)}
          className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

function ToastContainer({ position = 'top-right', toasts, onClose }) {
  const positionClasses = {
    'top-right': 'fixed top-4 right-4 z-[9999] flex flex-col gap-2 items-end',
    'top-left': 'fixed top-4 left-4 z-[9999] flex flex-col gap-2 items-start',
    'bottom-right': 'fixed bottom-4 right-4 z-[9999] flex flex-col-reverse gap-2 items-end',
    'bottom-left': 'fixed bottom-4 left-4 z-[9999] flex flex-col-reverse gap-2 items-start',
    'top-center': 'fixed top-4 left-1/2 -translate-x-1/2 z-[9999] flex flex-col gap-2 items-center',
    'bottom-center': 'fixed bottom-4 left-1/2 -translate-x-1/2 z-[9999] flex flex-col-reverse gap-2 items-center',
  }

  return (
    <div className={positionClasses[position]} aria-live="polite" aria-atomic="true">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onClose={onClose} />
      ))}
    </div>
  )
}

export function ToastProvider({ children, position = 'top-right', maxToasts = 5 }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random()
    const newToast = {
      id,
      type: 'info',
      title: '',
      message: '',
      persistent: false,
      duration: 5000,
      ...toast,
    }

    setToasts((prev) => {
      const updated = [newToast, ...prev].slice(0, maxToasts)
      return updated
    })

    if (!newToast.persistent && newToast.duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, newToast.duration)
    }

    return id
  }, [maxToasts])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const clearAll = useCallback(() => {
    setToasts([])
  }, [])

  const toastMethods = {
    success: (message, options = {}) => addToast({ type: 'success', message, ...options }),
    error: (message, options = {}) => addToast({ type: 'error', message, persistent: true, ...options }),
    warning: (message, options = {}) => addToast({ type: 'warning', message, ...options }),
    info: (message, options = {}) => addToast({ type: 'info', message, ...options }),
    dismiss: removeToast,
    clear: clearAll,
  }

  return (
    <ToastContext.Provider value={toastMethods}>
      {children}
      <ToastContainer position={position} toasts={toasts} onClose={removeToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

export function useToastActions() {
  const { success, error, warning, info, dismiss, clear } = useToast()
  
  return {
    showSuccess: (message, options) => success(message, options),
    showError: (message, options) => error(message, options),
    showWarning: (message, options) => warning(message, options),
    showInfo: (message, options) => info(message, options),
    dismiss,
    clear,
    showRetryToast: (message, onRetry, options = {}) => 
      error(message, {
        persistent: true,
        action: {
          label: 'Retry',
          onClick: onRetry,
          icon: <span className="w-4 h-4">↻</span>,
          persist: false,
          ...options.action,
        },
        ...options,
      }),
  }
}

export default ToastProvider