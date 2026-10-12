/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1e3a5f',
          light: '#2a4d7c',
          dark: '#152a42',
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
