/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'nh-primary': '#1e40af',
        'nh-secondary': '#3b82f6',
        'nh-accent': '#06b6d4',
        'nh-dark': '#0f172a',
        'nh-darker': '#020617',
      },
    },
  },
  plugins: [],
}
