/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: '#0f1f3d',
        blue: '#1a3a6b',
        accent: '#2563eb',
        light: '#e8edf7',
        success: '#16a34a',
        warning: '#d97706',
        danger: '#dc2626',
        muted: '#64748b',
        surface: '#f8fafc',
      },
    },
  },
  plugins: [],
}
