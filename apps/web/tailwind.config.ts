import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          DEFAULT: '#1E40AF',
          50: '#EFF6FF',
          500: '#3B82F6',
          700: '#1D4ED8',
          900: '#1E3A8A',
        },
        severity: {
          critical: '#B00020',
          high: '#C84300',
          medium: '#B88400',
          low: '#2A7A2A',
          info: '#6B7280',
        },
      },
    },
  },
  plugins: [],
};

export default config;
