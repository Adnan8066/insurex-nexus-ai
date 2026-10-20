import { useLayoutEffect, useRef, useState } from 'react'
import './SegmentedTabs.css'

const DEFAULT_TABS = [
  { value: 'toyota', label: 'Toyota' },
  { value: 'charter', label: 'Charter Communications' },
  { value: 'lennar', label: 'Lennar' },
  { value: 'carrier', label: 'Carrier' },
  { value: 'natwest', label: 'NatWest Group' },
]

/** Animated, accessible segmented navigation. Pass `value` to control selection. */
export function SegmentedTabs({
  tabs = DEFAULT_TABS,
  value,
  defaultValue,
  onChange,
  ariaLabel = 'Options',
  className = '',
}) {
  const [internalValue, setInternalValue] = useState(defaultValue ?? tabs[0]?.value)
  const selectedValue = value === undefined ? internalValue : value
  const selectedIndex = Math.max(0, tabs.findIndex((tab) => tab.value === selectedValue))
  const trackRef = useRef(null)
  const tabRefs = useRef([])
  const [indicator, setIndicator] = useState({ left: 0, width: 0, ready: false })

  useLayoutEffect(() => {
    const track = trackRef.current
    const selectedTab = tabRefs.current[selectedIndex]
    if (!track || !selectedTab) return undefined

    const updateIndicator = () => {
      setIndicator({ left: selectedTab.offsetLeft, width: selectedTab.offsetWidth, ready: true })
    }

    updateIndicator()
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(updateIndicator)
    observer?.observe(track)
    tabRefs.current.forEach((tab) => tab && observer?.observe(tab))
    window.addEventListener('resize', updateIndicator)

    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', updateIndicator)
    }
  }, [selectedIndex, tabs])

  const selectTab = (tab) => {
    if (value === undefined) setInternalValue(tab.value)
    onChange?.(tab.value, tab)
  }

  const handleKeyDown = (event, index) => {
    let nextIndex
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length
    else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length
    else if (event.key === 'Home') nextIndex = 0
    else if (event.key === 'End') nextIndex = tabs.length - 1
    else return

    event.preventDefault()
    tabRefs.current[nextIndex]?.focus()
    selectTab(tabs[nextIndex])
  }

  return (
    <div className={`segmented-tabs ${className}`.trim()}>
      <div
        ref={trackRef}
        className="segmented-tabs__track"
        role="tablist"
        aria-label={ariaLabel}
        style={{ '--segment-left': `${indicator.left}px`, '--segment-width': `${indicator.width}px` }}
      >
        <span
          aria-hidden="true"
          className={`segmented-tabs__indicator${indicator.ready ? ' is-ready' : ''}`}
        />
        {tabs.map((tab, index) => {
          const active = index === selectedIndex
          return (
            <button
              key={tab.value}
              ref={(element) => { tabRefs.current[index] = element }}
              type="button"
              role="tab"
              aria-selected={active}
              tabIndex={active ? 0 : -1}
              className={`segmented-tabs__tab${active ? ' is-active' : ''}`}
              onClick={() => selectTab(tab)}
              onKeyDown={(event) => handleKeyDown(event, index)}
            >
              {tab.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default SegmentedTabs
