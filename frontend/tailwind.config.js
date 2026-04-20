/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand:   '#0F4C81',
        success: '#16A34A',
        danger:  '#DC2626',
        warning: '#D97706',
        bg:      '#F8FAFC',
        card:    '#FFFFFF',
        border:  '#E2E8F0',
        text:    '#1E293B',
        muted:   '#64748B',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '12px',
        btn: '8px',
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.08)',
      },
      minHeight: {
        tap: '48px',
      }
    },
  },
  plugins: [],
}
