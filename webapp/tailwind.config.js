/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        navy: {
          DEFAULT: '#101423',
          light: '#1e2336',
          lighter: '#2a2f45',
        },
        brand: {
          green: '#3BB2AC',
          orange: '#F8AD55',
          red: '#E63944',
        },
      },
    },
  },
  plugins: [],
}
