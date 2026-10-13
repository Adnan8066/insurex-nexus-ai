import { clsx } from 'clsx'
import { isValidElement, cloneElement } from 'react'

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
  asChild = false,
  ...props
}) {
  const baseClasses = 'btn'
  const variantClasses = `btn-${variant}`
  const sizeClasses = size !== 'md' ? `btn-${size}` : ''
  const widthClass = fullWidth ? 'w-full' : ''
  const combinedClassName = clsx(
    baseClasses,
    variantClasses,
    sizeClasses,
    widthClass,
    className
  )

  if (asChild && isValidElement(children)) {
    return cloneElement(children, {
      className: clsx(combinedClassName, children.props.className),
      'aria-disabled': disabled || loading || undefined,
      ...props,
    })
  }

  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={combinedClassName}
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
