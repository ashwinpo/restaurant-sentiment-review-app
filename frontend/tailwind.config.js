/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bloomin-red': '#D02927',
        'bloomin-green': '#8DC63F', 
        'bloomin-blue': '#009AD9',
      }
    },
  },
  plugins: [],
}
