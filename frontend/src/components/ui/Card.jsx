import { clsx } from 'clsx'

export function Card({
  children,
  className = '',
  hover = false,
  padding = 'md',
  role,
  tabIndex,
  onClick,
  onKeyDown,
  ...props
}) {
  const isInteractive = typeof onClick === 'function'
  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  }

  return (
    <div
      className={clsx('card', hover && 'hover:shadow-lg transition-shadow', paddingClasses[padding], className)}
      role={isInteractive ? 'button' : role}
      tabIndex={isInteractive ? (tabIndex ?? 0) : tabIndex}
      onClick={onClick}
      onKeyDown={isInteractive ? (event) => {
        onKeyDown?.(event)
        if (event.defaultPrevented || event.target !== event.currentTarget) return
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onClick(event)
        }
      } : onKeyDown}
      onKeyUp={isInteractive ? (event) => {
        if (event.key === ' ') event.preventDefault()
      } : undefined}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({
  children,
  title,
  subtitle,
  action,
  className = '',
  ...props
}) {
  return (
    <div className={clsx('card-header', className)} {...props}>
      <div>
        {title && <h3 id={props.id ? `${props.id}-title` : undefined} className="card-title">{title}</h3>}
        {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
      {children}
    </div>
  )
}

export function CardContent({
  children,
  className = '',
  ...props
}) {
  return (
    <div className={clsx('card-content', className)} {...props}>
      {children}
    </div>
  )
}

export default { Card, CardHeader, CardContent }
