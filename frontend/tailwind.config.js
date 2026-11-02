/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0b1329',
          800: '#111c38',
          700: '#1b2a4a',
          600: '#263b63',
          500: '#344e7e',
        },
        teal: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
        },
        surface: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
        }
      },
      fontFamily: {
        sans: ['Prompt', 'Sarabun', 'Leelawadee UI', 'Segoe UI', 'system-ui', 'sans-serif'],
        body: ['Sarabun', 'Prompt', 'Leelawadee UI', 'sans-serif'],
      },
      fontSize: {
        xs: ['0.925rem', { lineHeight: '1.5' }],
        sm: ['1.025rem', { lineHeight: '1.6' }],
        base: ['1.125rem', { lineHeight: '1.65' }],
        lg: ['1.275rem', { lineHeight: '1.6' }],
        xl: ['1.45rem', { lineHeight: '1.45' }],
        '2xl': ['1.85rem', { lineHeight: '1.3' }],
        '3xl': ['2.25rem', { lineHeight: '1.25' }],
      },
    },
  },
  plugins: [],
}
