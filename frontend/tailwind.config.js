/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Poppins', 'system-ui', 'sans-serif'] },
      colors: {
        brand: {
          50: '#fffbeb',
          100: '#fff3c4',
          200: '#ffe58f',
          300: '#ffd84d',
          400: '#ffcd32',
          500: '#f2b92a',
          600: '#ea6a1f',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
        },
        ink: '#262626',
      },
    },
  },
  plugins: [],
}
