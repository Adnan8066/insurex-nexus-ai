import { clsx } from 'clsx'
import { forwardRef, useId } from 'react'

export const Input = forwardRef(function Input({
  label,
  hint,
  error,
  className = '',
  id,
  leftIcon,
  rightIcon,
  style,
  ...props
}, ref) {
  const generatedId = useId()
  const inputId = id || `${label?.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'input'}-${generatedId}`
  // Inline padding wins over the .input-field component class without depending on CSS layer order.
  const inputStyle = {
    ...(leftIcon ? { paddingLeft: '2.5rem' } : {}),
    ...(rightIcon ? { paddingRight: '2.75rem' } : {}),
    ...style,
  }

  return (
    <div className={clsx('input-group', className)}>
      {label && (
        <label htmlFor={inputId} className="input-label">
          {label}
        </label>
      )}
      <div className="relative">
        {leftIcon && (
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center" aria-hidden="true">
            {leftIcon}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          className={clsx('input-field', error && 'input-error')}
          style={inputStyle}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
          {...props}
        />
        {rightIcon && (
          <span className="absolute inset-y-0 right-3 flex items-center">
            {rightIcon}
          </span>
        )}
      </div>
      {error && (
        <p id={`${inputId}-error`} className="input-error-text" role="alert">
          {error}
        </p>
      )}
      {hint && !error && (
        <p id={`${inputId}-hint`} className="input-hint">
          {hint}
        </p>
      )}
    </div>
  )
})

Input.displayName = 'Input'

export const Textarea = forwardRef(function Textarea({
  label,
  hint,
  error,
  className = '',
  id,
  rows = 4,
  ...props
}, ref) {
  const generatedId = useId()
  const inputId = id || `${label?.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'textarea'}-${generatedId}`

  return (
    <div className={clsx('input-group', className)}>
      {label && (
        <label htmlFor={inputId} className="input-label">
          {label}
        </label>
      )}
      <textarea
        ref={ref}
        id={inputId}
        rows={rows}
        className={clsx('input-field', error && 'input-error')}
        aria-invalid={!!error}
        aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
        {...props}
      />
      {error && (
        <p id={`${inputId}-error`} className="input-error-text" role="alert">
          {error}
        </p>
      )}
      {hint && !error && (
        <p id={`${inputId}-hint`} className="input-hint">
          {hint}
        </p>
      )}
    </div>
  )
})

Textarea.displayName = 'Textarea'

export const Select = forwardRef(function Select({
  label,
  hint,
  error,
  options = [],
  placeholder,
  allowEmpty = false,
  className = '',
  id,
  ...props
}, ref) {
  const generatedId = useId()
  const inputId = id || `${label?.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'select'}-${generatedId}`

  return (
    <div className={clsx('input-group', className)}>
      {label && (
        <label htmlFor={inputId} className="input-label">
          {label}
        </label>
      )}
      <select
        ref={ref}
        id={inputId}
        className={clsx('input-field', error && 'input-error')}
        aria-invalid={!!error}
        aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
        {...props}
      >
        {(placeholder || allowEmpty) && (
          <option value="" disabled={!allowEmpty}>
            {placeholder || ''}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <p id={`${inputId}-error`} className="input-error-text" role="alert">
          {error}
        </p>
      )}
      {hint && !error && (
        <p id={`${inputId}-hint`} className="input-hint">
          {hint}
        </p>
      )}
    </div>
  )
})

Select.displayName = 'Select'

export default { Input, Textarea, Select }
