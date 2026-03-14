/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./src/**/*.{js,jsx,ts,tsx}', './public/index.html'],
  theme: {
    extend: {
      colors: {
        primary: '#16345f',
        'primary-dark': '#0d2241',
        'primary-soft': '#d8e3f2',
        'background-light': '#eef3f9',
        'background-dark': '#08111f',
        ink: '#0f1727',
        graphite: '#334155',
        ivory: '#ffffff',
        'ivory-dark': '#e2e8f0',
      },
      fontFamily: {
        display: ['Source Serif 4', 'serif'],
        sans: ['IBM Plex Sans', 'sans-serif'],
        serif: ['Source Serif 4', 'serif'],
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        lg: '0.5rem',
        xl: '0.75rem',
        '2xl': '1rem',
        full: '9999px',
      },
      boxShadow: {
        subtle: '0 1px 3px 0 rgba(8,17,31,0.06), 0 1px 2px -1px rgba(8,17,31,0.06)',
        card: '0 18px 45px -28px rgba(8,17,31,0.35), 0 10px 20px -18px rgba(8,17,31,0.2)',
        elevated: '0 28px 55px -30px rgba(8,17,31,0.42), 0 18px 28px -24px rgba(8,17,31,0.3)',
      },
      animation: {
        'ping-slow': 'ping 2s cubic-bezier(0,0,0.2,1) infinite',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms')({ strategy: 'class' }),
    require('@tailwindcss/container-queries'),
  ],
};
