import { clsx } from 'clsx'
import { forwardRef } from 'react'

export const Input = forwardRef(function Input({
  label,
  hint,
  error,
  className = '',
  id,
  ...props
}, ref) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')

  return (
    <div className={clsx('input-group', className)}>
      {label && (
        <label htmlFor={inputId} className="input-label">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
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
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')

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
  className = '',
  id,
  ...props
}, ref) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')

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
        {placeholder && (
          <option value="" disabled>
            {placeholder}
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