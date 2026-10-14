import { useContext } from 'react'
import { ToastContext } from './toastContext'

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
