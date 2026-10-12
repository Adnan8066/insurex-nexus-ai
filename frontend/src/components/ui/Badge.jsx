import { clsx } from 'clsx'

export function Badge({
  children,
  variant = 'neutral',
  size = 'md',
  className = '',
  ...props
}) {
  const variantClasses = {
    primary: 'badge-primary',
    success: 'badge-success',
    warning: 'badge-warning',
    danger: 'badge-danger',
    info: 'badge-info',
    neutral: 'badge-neutral',
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm',
  }

  return (
    <span
      className={clsx('badge', variantClasses[variant], sizeClasses[size], className)}
      {...props}
    >
      {children}
    </span>
  )
}

export function StatusBadge({ status, ...props }) {
  const statusConfig = {
    submitted: { label: 'Submitted', variant: 'info' },
    'under-review': { label: 'Under Review', variant: 'warning' },
    'ai-assessment': { label: 'AI Assessment', variant: 'primary' },
    investigation: { label: 'Investigation', variant: 'warning' },
    approved: { label: 'Approved', variant: 'success' },
    rejected: { label: 'Rejected', variant: 'danger' },
    'repair-settlement': { label: 'Repair/Settlement', variant: 'primary' },
    closed: { label: 'Closed', variant: 'neutral' },
    pending: { label: 'Pending', variant: 'warning' },
    active: { label: 'Active', variant: 'success' },
    inactive: { label: 'Inactive', variant: 'neutral' },
    expired: { label: 'Expired', variant: 'danger' },
    'high-risk': { label: 'High Risk', variant: 'danger' },
    'medium-risk': { label: 'Medium Risk', variant: 'warning' },
    'low-risk': { label: 'Low Risk', variant: 'success' },
    assigned: { label: 'Assigned', variant: 'info' },
    'in-progress': { label: 'In Progress', variant: 'primary' },
    completed: { label: 'Completed', variant: 'success' },
    cancelled: { label: 'Cancelled', variant: 'danger' },
  }

  const config = statusConfig[status] || { label: status, variant: 'neutral' }

  return <Badge variant={config.variant} {...props}>{config.label}</Badge>
}

export default { Badge, StatusBadge }