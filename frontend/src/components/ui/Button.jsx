import { clsx } from 'clsx'

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  fullWidth = false,
  leftIcon,
  rightIcon,
  className = '',
  type = 'button',
  ...props
}) {
  const baseClasses = 'btn'
  const variantClasses = `btn-${variant}`
  const sizeClasses = size !== 'md' ? `btn-${size}` : ''
  const widthClass = fullWidth ? 'w-full' : ''

  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={clsx(baseClasses, variantClasses, sizeClasses, widthClass, className)}
      {...props}
    >
      {loading && <span className="loading-spinner" aria-hidden="true" />}
      {!loading && leftIcon && <span aria-hidden="true">{leftIcon}</span>}
      <span>{children}</span>
      {!loading && rightIcon && <span aria-hidden="true">{rightIcon}</span>}
    </button>
  )
}

export default Button