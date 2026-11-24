import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Vitest runs without globals, so React Testing Library does not clean up the DOM by itself.
afterEach(() => {
  cleanup()
})
