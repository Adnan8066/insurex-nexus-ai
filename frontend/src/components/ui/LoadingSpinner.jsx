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

export default { LoadingSpinner, Skeleton }