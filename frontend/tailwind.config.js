/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#2563eb',
          light: '#3b82f6',
          dark: '#1d4ed8',
        },
        secondary: {
          DEFAULT: '#007bff',
          light: '#3399ff',
        },
        accent: {
          DEFAULT: '#00c896',
          light: '#33d6a8',
        },
      },
    },
  },
  plugins: [],
}
