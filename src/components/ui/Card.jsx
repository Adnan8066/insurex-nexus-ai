import { clsx } from 'clsx'

export function Card({
  children,
  className = '',
  hover = false,
  padding = 'md',
  ...props
}) {
  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  }

  return (
    <div
      className={clsx('card', hover && 'hover:shadow-lg transition-shadow', paddingClasses[padding], className)}
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
        {title && <h3 className="card-title">{title}</h3>}
        {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
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

export function CardFooter({
  children,
  className = '',
  ...props
}) {
  return (
    <div className={clsx('card-footer', className)} {...props}>
      {children}
    </div>
  )
}

export default { Card, CardHeader, CardContent, CardFooter }