import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePolling } from './usePolling'

function setVisibility(state) {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => state })
  document.dispatchEvent(new Event('visibilitychange'))
}

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    setVisibility('visible')
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('calls the callback on each interval while the page is visible', () => {
    const callback = vi.fn()
    renderHook(() => usePolling(callback, 1000))

    act(() => { vi.advanceTimersByTime(3000) })
    expect(callback).toHaveBeenCalledTimes(3)
  })

  it('pauses while the tab is hidden and refreshes once when it becomes visible', () => {
    const callback = vi.fn()
    renderHook(() => usePolling(callback, 1000))

    act(() => { setVisibility('hidden') })
    act(() => { vi.advanceTimersByTime(5000) })
    expect(callback).not.toHaveBeenCalled()

    act(() => { setVisibility('visible') })
    expect(callback).toHaveBeenCalledTimes(1)
    act(() => { vi.advanceTimersByTime(1000) })
    expect(callback).toHaveBeenCalledTimes(2)
  })

  it('stops polling when unmounted', () => {
    const callback = vi.fn()
    const { unmount } = renderHook(() => usePolling(callback, 1000))
    unmount()

    act(() => { vi.advanceTimersByTime(5000) })
    act(() => { setVisibility('hidden') })
    act(() => { setVisibility('visible') })
    expect(callback).not.toHaveBeenCalled()
  })

  it('does nothing when disabled', () => {
    const callback = vi.fn()
    renderHook(() => usePolling(callback, 1000, false))

    act(() => { vi.advanceTimersByTime(5000) })
    expect(callback).not.toHaveBeenCalled()
  })

  it('uses the latest callback without restarting the timer', () => {
    const first = vi.fn()
    const second = vi.fn()
    const { rerender } = renderHook(({ cb }) => usePolling(cb, 1000), { initialProps: { cb: first } })

    act(() => { vi.advanceTimersByTime(1000) })
    rerender({ cb: second })
    act(() => { vi.advanceTimersByTime(1000) })

    expect(first).toHaveBeenCalledTimes(1)
    expect(second).toHaveBeenCalledTimes(1)
  })
})
