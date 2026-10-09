import { useState, useEffect, useCallback } from 'react'

export function useLocalStorage(key, initialValue) {
  const [storedValue, setStoredValue] = useState(() => {
    if (typeof window === 'undefined') return initialValue
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch {
      return initialValue
    }
  })

  const setValue = (value) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value
      setStoredValue(valueToStore)
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore))
      }
    } catch (error) {
      console.error(`Error setting localStorage key "${key}":`, error)
    }
  }

  return [storedValue, setValue]
}

export function useMediaQuery(query) {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const media = window.matchMedia(query)
    if (media.matches !== matches) {
      setMatches(media.matches)
    }
    const listener = () => setMatches(media.matches)
    media.addEventListener('change', listener)
    return () => media.removeEventListener('change', listener)
  }, [matches, query])

  return matches
}

export function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)
    return () => clearTimeout(handler)
  }, [value, delay])

  return debouncedValue
}

export function useAsync(asyncFn, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const execute = useCallback(async (...args) => {
    setLoading(true)
    setError(null)
    try {
      const result = await asyncFn(...args)
      setData(result)
      return result
    } catch (err) {
      setError(err)
      throw err
    } finally {
      setLoading(false)
    }
  }, deps)

  useEffect(() => {
    execute()
  }, [execute])

  return { data, loading, error, execute, setData }
}

export function useToggle(initialValue = false) {
  const [value, setValue] = useState(initialValue)
  const toggle = useCallback(() => setValue((v) => !v), [])
  return [value, toggle, setValue]
}

export function useClickOutside(ref, handler) {
  useEffect(() => {
    const listener = (event) => {
      if (!ref.current || ref.current.contains(event.target)) return
      handler(event)
    }
    document.addEventListener('mousedown', listener)
    document.addEventListener('touchstart', listener)
    return () => {
      document.removeEventListener('mousedown', listener)
      document.removeEventListener('touchstart', listener)
    }
  }, [ref, handler])
}

export function useKeyPress(targetKey, handler) {
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === targetKey) handler(event)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [targetKey, handler])
}

export function useWindowSize() {
  const [size, setSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  })

  useEffect(() => {
    if (typeof window === 'undefined') return
    const handleResize = () =>
      setSize({ width: window.innerWidth, height: window.innerHeight })
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return size
}

export function useOnScreen(ref, rootMargin = '0px') {
  const [isIntersecting, setIsIntersecting] = useState(false)

  useEffect(() => {
    if (!ref.current) return
    const observer = new IntersectionObserver(
      ([entry]) => setIsIntersecting(entry.isIntersecting),
      { rootMargin }
    )
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [ref, rootMargin])

  return isIntersecting
}

export function usePrevious(value) {
  const ref = useRef()
  useEffect(() => {
    ref.current = value
  }, [value])
  return ref.current
}

import { useRef } from 'react'

export function useMounted() {
  const mounted = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])
  return mounted
}

export function useInterval(callback, delay) {
  const savedCallback = useRef()
  useEffect(() => {
    savedCallback.current = callback
  }, [callback])
  useEffect(() => {
    if (delay !== null) {
      const id = setInterval(() => savedCallback.current(), delay)
      return () => clearInterval(id)
    }
  }, [delay])
}

export function useTimeout(callback, delay) {
  const savedCallback = useRef()
  useEffect(() => {
    savedCallback.current = callback
  }, [callback])
  useEffect(() => {
    if (delay !== null) {
      const id = setTimeout(() => savedCallback.current(), delay)
      return () => clearTimeout(id)
    }
  }, [delay])
}

export function useForm(initialValues = {}, validate) {
  const [values, setValues] = useState(initialValues)
  const [errors, setErrors] = useState({})
  const [touched, setTouched] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setValues((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleBlur = (e) => {
    const { name } = e.target
    setTouched((prev) => ({ ...prev, [name]: true }))
    if (validate) {
      const validationErrors = validate(values)
      setErrors(validationErrors)
    }
  }

  const handleSubmit = async (onSubmit) => {
    setIsSubmitting(true)
    const validationErrors = validate ? validate(values) : {}
    setErrors(validationErrors)
    setTouched(Object.keys(values).reduce((acc, key) => ({ ...acc, [key]: true }), {}))

    if (Object.keys(validationErrors).length === 0) {
      await onSubmit(values)
    }
    setIsSubmitting(false)
  }

  const reset = () => {
    setValues(initialValues)
    setErrors({})
    setTouched({})
    setIsSubmitting(false)
  }

  const setFieldValue = (name, value) => {
    setValues((prev) => ({ ...prev, [name]: value }))
  }

  const setFieldError = (name, error) => {
    setErrors((prev) => ({ ...prev, [name]: error }))
  }

  return {
    values,
    errors,
    touched,
    isSubmitting,
    handleChange,
    handleBlur,
    handleSubmit: (onSubmit) => handleSubmit(onSubmit),
    reset,
    setFieldValue,
    setFieldError,
    setValues,
    setErrors,
  }
}