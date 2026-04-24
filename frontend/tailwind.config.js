/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        veins: {
          bg:        '#0a0a0a',
          secondary: '#111116',
          elevated:  '#1a1a22',
          border:    '#242430',
          accent:    '#10b981',
          red:       '#ef4444',
          yellow:    '#f59e0b',
        },
      },
      animation: {
        fadeIn: 'fadeIn 0.2s ease-out forwards',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
