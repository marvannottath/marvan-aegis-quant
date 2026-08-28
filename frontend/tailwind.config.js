/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        darkbg: '#0B0F19',
        darkcard: '#111827',
        darkborder: '#1F2937',
        accentblue: '#3b82f6',
        accentgreen: '#10b981',
        accentred: '#ef4444'
      },
    },
  },
  plugins: [],
}
