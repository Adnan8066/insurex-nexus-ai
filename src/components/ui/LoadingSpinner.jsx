import { clsx } from 'clsx'

export function LoadingSpinner({
  size = 'md',
  className = '',
  ariaLabel = 'Loading',
  ...props
}) {
  const sizeClasses = {
    sm: 'w-4 h-4 border-1.5',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-3',
    xl: 'w-12 h-12 border-4',
  }

  return (
    <span
      className={clsx('loading-spinner', sizeClasses[size], className)}
      role="status"
      aria-label={ariaLabel}
      {...props}
    >
      <span className="sr-only">{ariaLabel}</span>
    </span>
  )
}

export function LoadingOverlay({
  isLoading,
  message = 'Loading...',
  children,
  className = '',
}) {
  if (!isLoading) return children

  return (
    <div className={clsx('relative', className)}>
      {children}
      <div className="absolute inset-0 bg-white/80 flex items-center justify-center gap-3 z-10 rounded-lg">
        <LoadingSpinner size="lg" />
        <span className="text-sm font-medium text-gray-700">{message}</span>
      </div>
    </div>
  )
}

export function Skeleton({
  className = '',
  variant = 'text',
  width,
  height,
  count = 1,
  ...props
}) {
  const baseClasses = 'animate-pulse bg-gray-200 rounded'

  const variantClasses = {
    text: 'h-4',
    title: 'h-6 w-3/4',
    avatar: 'rounded-full',
    card: 'rounded-lg',
    button: 'h-10 rounded-md',
    circular: 'rounded-full',
  }

  const skeletons = Array.from({ length: count }, (_, i) => (
    <div
      key={i}
      className={clsx(baseClasses, variantClasses[variant], className)}
      style={{ width, height }}
      {...props}
    />
  ))

  return <>{skeletons}</>
}

export default { LoadingSpinner, LoadingOverlay, Skeleton }