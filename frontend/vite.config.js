import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true
  },
  resolve: {
    alias: {
      '@': resolve('src')
    }
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    css: false,
    include: ['src/**/*.test.{js,jsx}'],
  }
})