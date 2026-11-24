import { useEffect, useRef } from 'react'

// Calls `callback` every `intervalMs` while the page is visible and the component is mounted.
// Polling pauses when the tab is hidden and refreshes once when it becomes visible again.
// The latest callback is always used, so callers can pass a new function on every render.
export function usePolling(callback, intervalMs = 30000, enabled = true) {
  const callbackRef = useRef(callback)

  useEffect(() => {
    callbackRef.current = callback
  }, [callback])

  useEffect(() => {
    if (!enabled || typeof document === 'undefined') return undefined

    let timerId = null
    const isVisible = () => document.visibilityState === 'visible'
    const tick = () => {
      if (isVisible()) callbackRef.current()
    }
    const start = () => {
      if (timerId === null) timerId = window.setInterval(tick, intervalMs)
    }
    const stop = () => {
      if (timerId !== null) {
        window.clearInterval(timerId)
        timerId = null
      }
    }
    const handleVisibilityChange = () => {
      if (isVisible()) {
        tick()
        start()
      } else {
        stop()
      }
    }

    if (isVisible()) start()
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      stop()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [intervalMs, enabled])
}

export default usePolling
