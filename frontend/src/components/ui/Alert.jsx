import { clsx } from 'clsx'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from './Button'

// Standard inline error message, with an optional Retry button.
export function Alert({ children, onRetry, className }) {
  return (
    <div
      role="alert"
      className={clsx('flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700', className)}
    >
      <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">{children}</div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="-my-1 flex-shrink-0">
          <RefreshCw className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
          Retry
        </Button>
      )}
    </div>
  )
}

export default Alert
