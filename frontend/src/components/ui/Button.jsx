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
  const isDisabled = disabled || loading
  const combinedClassName = clsx(
    baseClasses,
    variantClasses,
    sizeClasses,
    widthClass,
    className
  )

  if (asChild && isValidElement(children)) {
    return cloneElement(children, {
      ...props,
      className: clsx(combinedClassName, children.props.className),
      'aria-disabled': isDisabled || undefined,
      'aria-busy': loading || undefined,
      tabIndex: isDisabled ? -1 : children.props.tabIndex,
      onClick: (event) => {
        if (isDisabled) {
          event.preventDefault()
          event.stopPropagation()
          return
        }
        children.props.onClick?.(event)
        props.onClick?.(event)
      },
    })
  }

  return (
    <button
      type={type}
      disabled={isDisabled}
      aria-busy={loading || undefined}
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
